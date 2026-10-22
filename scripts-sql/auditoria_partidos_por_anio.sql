-- =====================================================================
-- AUDITORÍA DE PARTIDOS POR AÑO (para correr en el SQL Editor de Supabase)
--
-- Cada query (salvo la 0) tiene un CTE "params" arriba: cambiá el año ahí
-- ('2026', '2025', ...) y corré la query.
--
-- El año sale de fecha_utc (FotMob la guarda en ISO, ej. 2025-01-24T22:00:00Z,
-- y la edición de FotMob usa ese mismo año como temporada). Los partidos que
-- vienen de Kaggle o Football-Data no tienen fecha_utc, así que para ellos
-- se usa ediciones.temporada.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 0. PANORAMA GENERAL: cuántos partidos hay por año y de qué fuente
-- ---------------------------------------------------------------------
SELECT
    COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada)                          AS anio,
    COUNT(*)                                                             AS partidos,
    COUNT(*) FILTER (WHERE p.estado IN ('FT', 'AET', 'Pen'))             AS terminados,
    COUNT(*) FILTER (WHERE p.fecha_utc IS NULL)                          AS sin_fecha,
    COUNT(*) FILTER (WHERE p.partido_id >= 9000000000)                   AS historicos_kaggle,
    COUNT(*) FILTER (WHERE p.metadata->>'fuente' = 'footballdatauk')     AS con_odds,
    COUNT(DISTINCT p.edicion_id)                                         AS ediciones
FROM partidos p
JOIN ediciones e USING (edicion_id)
GROUP BY 1
ORDER BY 1 DESC NULLS LAST;


-- ---------------------------------------------------------------------
-- 1. RESUMEN DEL AÑO POR TORNEO
--    Para comparar contra lo esperado (ej. LPF 2025: 28 equipos).
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio),
partidos_anio AS (
    SELECT p.*
    FROM partidos p
    JOIN ediciones e USING (edicion_id), params
    WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
)
SELECT
    e.edicion_id,
    e.nombre_torneo,
    e.temporada,
    COUNT(DISTINCT pa.partido_id)                                              AS partidos,
    COUNT(DISTINCT pa.partido_id) FILTER (WHERE pa.estado IN ('FT','AET','Pen')) AS terminados,
    COUNT(DISTINCT pa.partido_id) FILTER (WHERE pa.estado IS NULL
                                       OR pa.estado NOT IN ('FT','AET','Pen'))   AS no_terminados,
    COUNT(DISTINCT eq.equipo_id)                                               AS equipos,
    COUNT(DISTINCT pa.ronda)                                                   AS rondas,
    MIN(pa.fecha_utc)                                                          AS primer_partido,
    MAX(pa.fecha_utc)                                                          AS ultimo_partido
FROM partidos_anio pa
JOIN ediciones e USING (edicion_id)
CROSS JOIN LATERAL (VALUES (pa.equipo_local_id), (pa.equipo_visitante_id)) AS eq(equipo_id)
GROUP BY e.edicion_id, e.nombre_torneo, e.temporada
ORDER BY partidos DESC;


-- ---------------------------------------------------------------------
-- 2. PARTIDOS POR FECHA/RONDA DE CADA TORNEO
--    "faltan" > 0 indica una ronda incompleta (esperado = equipos / 2).
--    En copas/eliminatorias el esperado no aplica: mirá solo la cantidad.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio),
partidos_anio AS (
    SELECT p.*
    FROM partidos p
    JOIN ediciones e USING (edicion_id), params
    WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
),
equipos_por_edicion AS (
    SELECT pa.edicion_id, COUNT(DISTINCT eq.equipo_id) AS equipos
    FROM partidos_anio pa
    CROSS JOIN LATERAL (VALUES (pa.equipo_local_id), (pa.equipo_visitante_id)) AS eq(equipo_id)
    GROUP BY pa.edicion_id
)
SELECT
    e.nombre_torneo,
    pa.ronda,
    COUNT(*)                         AS partidos,
    epe.equipos / 2                  AS esperados,
    GREATEST(epe.equipos / 2 - COUNT(*), 0) AS faltan,
    MIN(pa.fecha_utc)                AS desde,
    MAX(pa.fecha_utc)                AS hasta
FROM partidos_anio pa
JOIN ediciones e USING (edicion_id)
JOIN equipos_por_edicion epe USING (edicion_id)
GROUP BY e.nombre_torneo, pa.ronda, epe.equipos
ORDER BY
    e.nombre_torneo,
    NULLIF(regexp_replace(pa.ronda, '\D', '', 'g'), '')::int NULLS LAST,
    pa.ronda;


-- ---------------------------------------------------------------------
-- 3. PARTIDOS POR EQUIPO EN CADA TORNEO
--    Un equipo con menos partidos que el resto = partidos que faltan.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio),
partidos_anio AS (
    SELECT p.*
    FROM partidos p
    JOIN ediciones e USING (edicion_id), params
    WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
),
por_equipo AS (
    SELECT
        pa.edicion_id,
        eq.equipo_id,
        COUNT(*)                                        AS jugados,
        COUNT(*) FILTER (WHERE eq.es_local)             AS de_local,
        COUNT(*) FILTER (WHERE NOT eq.es_local)         AS de_visitante
    FROM partidos_anio pa
    CROSS JOIN LATERAL (VALUES (pa.equipo_local_id, true),
                               (pa.equipo_visitante_id, false)) AS eq(equipo_id, es_local)
    GROUP BY pa.edicion_id, eq.equipo_id
)
SELECT
    e.nombre_torneo,
    t.nombre_corto,
    t.nombre_fuente,
    pe.jugados,
    pe.de_local,
    pe.de_visitante,
    MAX(pe.jugados) OVER (PARTITION BY pe.edicion_id) - pe.jugados AS menos_que_el_maximo
FROM por_equipo pe
JOIN ediciones e USING (edicion_id)
JOIN equipos t USING (equipo_id)
ORDER BY e.nombre_torneo, pe.jugados, t.nombre_fuente;


-- ---------------------------------------------------------------------
-- 4. ESTADOS DE LOS PARTIDOS DEL AÑO
--    FT/AET/Pen = terminados. PP (postergado), Ab (suspendido),
--    Can (cancelado) o N/A (sin jugar / sin dato) conviene revisarlos.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio)
SELECT
    e.nombre_torneo,
    COALESCE(p.estado, '(null)') AS estado,
    COUNT(*)                     AS partidos
FROM partidos p
JOIN ediciones e USING (edicion_id), params
WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- Detalle de los que no están terminados:
WITH params AS (SELECT '2026'::text AS anio)
SELECT
    p.partido_id, e.nombre_torneo, p.ronda, p.fecha_utc, p.estado,
    l.nombre_fuente AS local, p.goles_local, p.goles_visitante, v.nombre_fuente AS visitante
FROM partidos p
JOIN ediciones e USING (edicion_id)
JOIN equipos l ON l.equipo_id = p.equipo_local_id
JOIN equipos v ON v.equipo_id = p.equipo_visitante_id, params
WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
  AND (p.estado IS NULL OR p.estado NOT IN ('FT', 'AET', 'Pen'))
ORDER BY p.fecha_utc;


-- ---------------------------------------------------------------------
-- 5. COBERTURA DEL DETALLE (¿los partidos tienen alineaciones, stats, etc.?)
--    Porcentaje de partidos terminados que tienen cada tipo de dato.
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio),
partidos_anio AS (
    SELECT p.partido_id, p.edicion_id, p.metadata
    FROM partidos p
    JOIN ediciones e USING (edicion_id), params
    WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
      AND p.estado IN ('FT', 'AET', 'Pen')
)
SELECT
    e.nombre_torneo,
    COUNT(*) AS terminados,
    ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM alineaciones x          WHERE x.partido_id = pa.partido_id)) / COUNT(*), 1) AS pct_alineaciones,
    ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM stats_jugador_partido x WHERE x.partido_id = pa.partido_id)) / COUNT(*), 1) AS pct_stats_jugador,
    ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM eventos x               WHERE x.partido_id = pa.partido_id)) / COUNT(*), 1) AS pct_eventos,
    ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM tiros x                 WHERE x.partido_id = pa.partido_id)) / COUNT(*), 1) AS pct_tiros,
    ROUND(100.0 * COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM momentum x              WHERE x.partido_id = pa.partido_id)) / COUNT(*), 1) AS pct_momentum,
    ROUND(100.0 * COUNT(*) FILTER (WHERE pa.metadata IS NOT NULL
                                     AND pa.metadata::text NOT IN ('{}', '[]', 'null')) / COUNT(*), 1)                                 AS pct_metadata
FROM partidos_anio pa
JOIN ediciones e USING (edicion_id)
GROUP BY e.nombre_torneo
ORDER BY terminados DESC;


-- ---------------------------------------------------------------------
-- 6. POSIBLES DUPLICADOS
--    Mismo cruce local-visitante en la misma edición más de una vez.
--    En liga con ida y vuelta puede ser legítimo (2 veces); 3+ o dos
--    con la misma fecha casi seguro es un duplicado (ej. un insert de
--    Football-Data que no encontró match contra FotMob).
-- ---------------------------------------------------------------------
WITH params AS (SELECT '2026'::text AS anio)
SELECT
    e.nombre_torneo,
    l.nombre_fuente AS local,
    v.nombre_fuente AS visitante,
    COUNT(*)                                            AS veces,
    array_agg(p.partido_id ORDER BY p.fecha_utc)        AS ids,
    array_agg(COALESCE(LEFT(p.fecha_utc::text, 10), p.metadata->>'fecha_csv', '?')
              ORDER BY p.fecha_utc)                     AS fechas,
    array_agg(p.goles_local || '-' || p.goles_visitante ORDER BY p.fecha_utc) AS resultados
FROM partidos p
JOIN ediciones e USING (edicion_id)
JOIN equipos l ON l.equipo_id = p.equipo_local_id
JOIN equipos v ON v.equipo_id = p.equipo_visitante_id, params
WHERE COALESCE(LEFT(p.fecha_utc::text, 4), e.temporada) = params.anio
GROUP BY e.nombre_torneo, l.nombre_fuente, v.nombre_fuente
HAVING COUNT(*) > 1
ORDER BY veces DESC, e.nombre_torneo;
