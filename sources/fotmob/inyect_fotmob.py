import html
import json
import os
import re
from pathlib import Path
from sqlalchemy import create_engine, text

# Connection string en la variable de entorno ARGSTATS_DB_URL (ver .env.example)
DB_URL = os.getenv("ARGSTATS_DB_URL", "postgresql://usuario:contraseña@localhost:5432/nombre_db")
engine = create_engine(DB_URL)



def upsert_equipo(conn, equipo_id, nombre, nombre_corto=None):
    if not nombre_corto:
        nombre_corto = nombre
    conn.execute(text("""
        INSERT INTO equipos (equipo_id, nombre_fuente, nombre_corto)
        VALUES (:id, :nombre, :corto)
        ON CONFLICT (equipo_id) DO UPDATE SET
            nombre_fuente = EXCLUDED.nombre_fuente,
            nombre_corto = EXCLUDED.nombre_corto
    """), {"id": equipo_id, "nombre": nombre, "corto": nombre_corto})

def upsert_jugador(conn, jugador_id, nombre):
    conn.execute(text("""
        INSERT INTO jugadores (jugador_id, nombre_completo) VALUES (:jid, :nom)
        ON CONFLICT (jugador_id) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo
    """), {"jid": jugador_id, "nom": nombre})

def upsert_edicion(conn, torneo, temporada):
    res = conn.execute(text("""
        INSERT INTO ediciones (nombre_torneo, temporada)
        VALUES (:torneo, :temp)
        ON CONFLICT (nombre_torneo, temporada) DO UPDATE 
        SET nombre_torneo = EXCLUDED.nombre_torneo
        RETURNING edicion_id
    """), {"torneo": torneo, "temp": temporada})
    return res.scalar()

# --- Estadísticas de jugador ------------------------------------------------
# Columnas de stats_jugador_partido que salen de playerStats: (columna, clave
# de FotMob, "value" o "total" en las fracciones). Son las métricas que también
# publican otras fuentes; lo propio de FotMob va a la columna `fotmob`.
COLUMNAS_STATS = [
    ('tiros_al_arco', 'ShotsOnTarget', 'value'),
    ('tiros_bloqueados', 'blocked_shots', 'value'),
    ('tiros_al_palo', 'shots_woodwork', 'value'),
    ('xgot', 'expected_goals_on_target_variant', 'value'),
    ('npxg', 'expected_goals_non_penalty', 'value'),
    ('grandes_ocasiones_falladas', 'big_chance_missed_title', 'value'),
    ('pases_precisos', 'accurate_passes', 'value'),
    ('pases_intentados', 'accurate_passes', 'total'),
    ('pases_ultimo_tercio', 'passes_into_final_third', 'value'),
    ('pases_largos_precisos', 'long_balls_accurate', 'value'),
    ('pases_largos_intentados', 'long_balls_accurate', 'total'),
    ('centros_precisos', 'accurate_crosses', 'value'),
    ('centros_intentados', 'accurate_crosses', 'total'),
    ('ocasiones_creadas', 'chances_created', 'value'),
    ('grandes_ocasiones_creadas', 'big_chance_created_team_title', 'value'),
    ('toques', 'touches', 'value'),
    ('toques_area_rival', 'touches_opp_box', 'value'),
    ('regates_exitosos', 'dribbles_succeeded', 'value'),
    ('regates_intentados', 'dribbles_succeeded', 'total'),
    ('perdidas', 'dispossessed', 'value'),
    ('offsides', 'Offsides', 'value'),
    ('entradas', 'matchstats.headers.tackles', 'value'),
    ('intercepciones', 'interceptions', 'value'),
    ('despejes', 'clearances', 'value'),
    ('bloqueos', 'shot_blocks', 'value'),
    ('recuperaciones', 'recoveries', 'value'),
    ('regateado', 'dribbled_past', 'value'),
    ('duelos_ganados', 'duel_won', 'value'),
    ('duelos_perdidos', 'duel_lost', 'value'),
    ('duelos_terrestres_ganados', 'ground_duels_won', 'value'),
    ('duelos_terrestres_intentados', 'ground_duels_won', 'total'),
    ('duelos_aereos_ganados', 'aerials_won', 'value'),
    ('duelos_aereos_intentados', 'aerials_won', 'total'),
    ('faltas_cometidas', 'fouls', 'value'),
    ('faltas_recibidas', 'was_fouled', 'value'),
    ('penales_ganados', 'penalties_won', 'value'),
    ('penales_cometidos', 'conceded_penalties', 'value'),
    ('penales_errados', 'missed_penalty', 'value'),
    ('errores_gol', 'errors_led_to_goal', 'value'),
    ('goles_en_contra', 'owngoal', 'value'),
]
# Solo de arqueros: en el resto quedan en NULL (no aplica)
COLUMNAS_ARQUERO = [
    ('atajadas', 'saves', 'value'),
    ('goles_recibidos', 'goals_conceded', 'value'),
    ('xgot_recibido', 'expected_goals_on_target_faced', 'value'),
    ('penales_atajados', 'saved_penalties', 'value'),
]
# Claves con columna propia o que se calculan con otras: no se repiten en `fotmob`
CLAVES_CON_COLUMNA = {
    'minutes_played', 'rating_title', 'goals', 'assists', 'expected_goals', 'expected_assists',
    'total_shots', 'ShotsOffTarget',
    *(k for _, k, _ in COLUMNAS_STATS), *(k for _, k, _ in COLUMNAS_ARQUERO),
}
CLAVES_DERIVADAS = {'xg_and_xa', 'shot_accuracy', 'goals_prevented', None}


def stats_por_clave(player_data):
    """Todas las estadísticas de un jugador por su clave de FotMob (la primera vez que aparece)."""
    stats = {}
    for grupo in player_data.get('stats', []) or []:
        for stat_info in (grupo.get('stats') or {}).values() if isinstance(grupo, dict) else []:
            if isinstance(stat_info, dict):
                stats.setdefault(stat_info.get('key'), stat_info.get('stat') or {})
    return stats


def valor_stat(stats, clave, campo='value', faltante=0):
    """FotMob no manda la estadística cuando vale 0: si el jugador tiene estadísticas, lo que falta es 0."""
    stat = stats.get(clave)
    if stat is None:
        return faltante
    valor = stat.get(campo)
    return valor if valor is not None else faltante


def stats_fotmob(player_data, stats):
    """JSON con lo propio de FotMob: lo que no tiene columna ni se calcula con otras."""
    propias = {}
    for clave, stat in stats.items():
        if clave in CLAVES_CON_COLUMNA or clave in CLAVES_DERIVADAS or 'value' not in stat:
            continue
        propias[clave] = [stat['value'], stat['total']] if 'total' in stat else stat['value']
    if player_data.get('isPotm'):
        propias['jugador_del_partido'] = True
    return json.dumps(propias) if propias else None


def tarjetas_por_jugador(eventos):
    """(amarilla, roja) por jugador según los eventos (la doble amarilla cuenta en las dos). None si no hay eventos."""
    if not eventos:
        return None
    tarjetas = {}
    for ev in eventos:
        if ev.get('type') != 'Card':
            continue
        j_id = (ev.get('player') or {}).get('id') or ev.get('playerId')
        if not j_id:
            continue
        amarilla, roja = tarjetas.get(int(j_id), (False, False))
        carta = ev.get('card')
        tarjetas[int(j_id)] = (amarilla or carta in ('Yellow', 'YellowRed'), roja or carta in ('Red', 'YellowRed'))
    return tarjetas


COLUMNAS_INSERT_STATS = [
    'minutos_jugados', 'rating', 'goles', 'asistencias', 'xg', 'xa', 'tarjeta_amarilla', 'tarjeta_roja', 'tiros',
    *(c for c, _, _ in COLUMNAS_STATS), *(c for c, _, _ in COLUMNAS_ARQUERO), 'fotmob',
]
SQL_STATS = text(f"""
    INSERT INTO stats_jugador_partido (partido_id, jugador_id, equipo_id, {', '.join(COLUMNAS_INSERT_STATS)})
    VALUES (:partido_id, :jugador_id, :equipo_id, {', '.join(':' + c for c in COLUMNAS_INSERT_STATS)})
    ON CONFLICT (partido_id, jugador_id) DO UPDATE SET
        {', '.join(f'{c} = EXCLUDED.{c}' for c in COLUMNAS_INSERT_STATS)}
""")


def fila_stats(partido_id, jugador_id, p_data, tarjetas):
    stats = stats_por_clave(p_data)
    arquero = bool(p_data.get('isGoalkeeper'))
    # Total de tiros: a veces no viene total_shots, pero siempre es al arco + afuera + bloqueados
    tiros = valor_stat(stats, 'total_shots', faltante=None)
    if tiros is None:
        tiros = sum(valor_stat(stats, k) for k in ('ShotsOnTarget', 'ShotsOffTarget', 'blocked_shots'))
    amarilla, roja = (None, None) if tarjetas is None else tarjetas.get(jugador_id, (False, False))
    fila = {
        'partido_id': partido_id, 'jugador_id': jugador_id, 'equipo_id': p_data.get('teamId'),
        'minutos_jugados': valor_stat(stats, 'minutes_played'),
        'rating': valor_stat(stats, 'rating_title', faltante=None),
        'goles': valor_stat(stats, 'goals'),
        'asistencias': valor_stat(stats, 'assists'),
        'xg': valor_stat(stats, 'expected_goals', faltante=0.0),
        'xa': valor_stat(stats, 'expected_assists', faltante=0.0),
        'tarjeta_amarilla': amarilla, 'tarjeta_roja': roja, 'tiros': tiros,
        'fotmob': stats_fotmob(p_data, stats),
    }
    fila.update({c: valor_stat(stats, k, campo) for c, k, campo in COLUMNAS_STATS})
    fila.update({c: valor_stat(stats, k, campo) if arquero else None for c, k, campo in COLUMNAS_ARQUERO})
    return fila

def extraer_nombre(obj_name):
    """Maneja inconsistencias: a veces es string, a veces diccionario"""
    if isinstance(obj_name, dict):
        return obj_name.get('fullName', 'Desconocido')
    return str(obj_name) if obj_name else 'Desconocido'


# --- Nombres de edición ---------------------------------------------------
# La base usa edición = competición/etapa + temporada, con el nombre sin año
# (ej. "Liga Profesional Clausura" · "2026"). FotMob cambió de formato con el
# tiempo, así que se normaliza al formato de la base.

ALIAS_LIGA = {"Primera B Nacional": "Primera Nacional"}

def ronda_playoff(texto):
    """'8th Finals' -> '1/8', 'Quarter-finals' -> '1/4', 'Semi-finals' -> '1/2', 'Final' -> 'final'"""
    texto = texto.strip().lower()
    m = re.fullmatch(r"(\d+)(st|nd|rd|th) finals", texto)
    if m:
        return f"1/{m.group(1)}"
    return {"quarter-finals": "1/4", "semi-finals": "1/2", "final": "final"}.get(texto)

def normalizar_ronda(ronda):
    """'Clausura - Round 13' -> ('Clausura', '13', False); 'Apertura - 8th Finals' -> ('Apertura', '1/8', True)"""
    ronda = str(ronda) if ronda is not None else 'N/A'
    m = re.fullmatch(r"\s*(.+?)\s+-\s+(.+?)\s*", ronda)
    if not m:
        return None, ronda, False
    etapa, resto = m.group(1), m.group(2)
    numero = re.fullmatch(r"Round\s+(\d+)", resto)
    if numero:
        return etapa, numero.group(1), False
    playoff = ronda_playoff(resto)
    if playoff:
        return etapa, playoff, True
    return etapa, resto, False

def normalizar_torneo(nombre, etapa, es_playoff=False):
    """'Liga Profesional Argentina' + 'Clausura' -> 'Liga Profesional Clausura' (+ ' Playoff' si corresponde)"""
    if etapa and etapa.lower() not in nombre.lower():
        nombre = f"{nombre.removesuffix(' Argentina')} {etapa}"
    if es_playoff and 'playoff' not in nombre.lower():
        nombre = f"{nombre} Playoff"
    return nombre

def edicion_de_tabla(liga, tabla):
    """(edición, zona) de una tabla de posiciones: 'Clausura Group A' -> ('<liga> Clausura', 'Group A')"""
    liga = ALIAS_LIGA.get(liga, liga)
    tabla = re.sub(r"\s+", " ", tabla).strip() if tabla else None
    if not tabla:
        return liga, None
    etapa = re.fullmatch(r"(Apertura|Clausura)\s*(?:-\s*)?(.+)", tabla)
    if etapa:
        return normalizar_torneo(liga, etapa.group(1)), etapa.group(2)
    # Una zona suelta pertenece a la liga; cualquier otro nombre es su propia competición
    if re.fullmatch(r"(Zona|Group|Grupo)\s+\S+", tabla):
        return liga, tabla
    return tabla, None




def procesar_ligas(conn, carpeta_leagues):
    archivos = list(Path(carpeta_leagues).glob('*.json'))
    print(f"Procesando {len(archivos)} archivos de ligas...")

    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
            detalles = data.get('details') or {}
            if not detalles:
                continue
            torneo = html.unescape(detalles.get('name') or 'Desconocido')
            temporada = detalles.get('selectedSeason')
            tables_data = data.get('table') or []
            if tables_data and isinstance(tables_data, list) and tables_data[0].get('data'):
                t_data = tables_data[0]['data']
                zonas = t_data.get('tables') if 'tables' in t_data else [{'leagueName': None, 'table': t_data.get('table', {})}]
                for zona in zonas:
                    # Cada tabla va a la edición de su etapa, igual que los partidos
                    nombre_edicion, nombre_zona = edicion_de_tabla(torneo, zona.get('leagueName'))
                    edicion_id = upsert_edicion(conn, nombre_edicion, temporada)
                    equipos_zona = (zona.get('table') or {}).get('all', [])
                    for equipo in equipos_zona:
                        eq_id = equipo.get('id')
                        if not eq_id: continue
                        upsert_equipo(conn, eq_id, equipo.get('name', 'Desconocido'), equipo.get('shortName'))
                        score_str = equipo.get('scoresStr', '0-0').split('-')
                        gf = int(score_str[0]) if len(score_str) > 0 and score_str[0].isdigit() else 0
                        gc = int(score_str[1]) if len(score_str) > 1 and score_str[1].isdigit() else 0

                        conn.execute(text("""
                            INSERT INTO posiciones (
                                edicion_id, equipo_id, zona, posicion, partidos_jugados, 
                                victorias, empates, derrotas, goles_favor, goles_contra, diferencia_gol, puntos
                            ) VALUES (
                                :ed_id, :eq_id, :zona, :pos, :pj, :v, :e, :d, :gf, :gc, :dif, :pts
                            ) ON CONFLICT (edicion_id, equipo_id) DO UPDATE SET
                                zona = EXCLUDED.zona, posicion = EXCLUDED.posicion, partidos_jugados = EXCLUDED.partidos_jugados,
                                victorias = EXCLUDED.victorias, empates = EXCLUDED.empates, derrotas = EXCLUDED.derrotas,
                                goles_favor = EXCLUDED.goles_favor, goles_contra = EXCLUDED.goles_contra,
                                diferencia_gol = EXCLUDED.diferencia_gol, puntos = EXCLUDED.puntos
                        """), {
                            "ed_id": edicion_id, "eq_id": eq_id, "zona": nombre_zona, "pos": equipo.get('idx'),
                            "pj": equipo.get('played', 0), "v": equipo.get('wins', 0), "e": equipo.get('draws', 0),
                            "d": equipo.get('losses', 0), "gf": gf, "gc": gc, "dif": equipo.get('goalConDiff', 0),
                            "pts": equipo.get('pts', 0)
                        })

            transfers_obj = data.get('transfers') or {}
            if isinstance(transfers_obj, dict):
                lista_transferencias = transfers_obj.get('data') or []
                for t in lista_transferencias:
                    j_id = t.get('playerId')
                    if not j_id: continue
                    
                    upsert_jugador(conn, j_id, t.get('name', 'Desconocido'))
                    
                    conn.execute(text("""
                        INSERT INTO transferencias (jugador_id, fecha, equipo_origen_id, equipo_destino_id, tipo_transferencia)
                        VALUES (:jid, :fecha, :ori, :dest, :tipo)
                    """), {
                        "jid": j_id,
                        "fecha": t.get('transferDate'),
                        "ori": t.get('fromClubId'),
                        "dest": t.get('toClubId'),
                        "tipo": t.get('transferType', {}).get('text')
                    })




def procesar_partidos(conn, carpeta_matches):
    archivos = list(Path(carpeta_matches).glob('*.json'))
    print(f"Procesando {len(archivos)} archivos de partidos...")

    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
            gen = data.get('general') or {}
            head = data.get('header') or {}
            status = head.get('status') or {}
            content = data.get('content') or {}
            match_facts = content.get('matchFacts') or {}
            if not gen or not head or 'teams' not in head:
                continue
            partido_id = int(gen['matchId'])
            fecha = gen.get('matchTimeUTCDate')
            año = fecha[:4] if fecha else "Desc"
            etapa, ronda, es_playoff = normalizar_ronda(gen.get('matchRound', 'N/A'))
            torneo = normalizar_torneo(gen.get('leagueName', 'Desconocido'), etapa, es_playoff)
            edicion_id = upsert_edicion(conn, torneo, año)
            loc_id = head['teams'][0]['id']
            vis_id = head['teams'][1]['id']
            upsert_equipo(conn, loc_id, head['teams'][0]['name'])
            upsert_equipo(conn, vis_id, head['teams'][1]['name'])
            goles_loc = head['teams'][0].get('score', 0)
            goles_vis = head['teams'][1].get('score', 0)
            penales_loc, penales_vis = None, None
            if 'penalties' in status.get('reason', {}):
                pens = status['reason']['penalties']
                penales_loc = pens[0] if len(pens) > 0 else None
                penales_vis = pens[1] if len(pens) > 1 else None
            metadata_json = json.dumps(content.get('stats', {})) 
            conn.execute(text("""
                INSERT INTO partidos (
                    partido_id, edicion_id, equipo_local_id, equipo_visitante_id, 
                    fecha_utc, ronda, goles_local, goles_visitante, penales_local, penales_visitante, estado, metadata
                ) VALUES (
                    :p_id, :ed_id, :loc, :vis, :fecha, :ronda, :gl, :gv, :pl, :pv, :est, :meta
                ) ON CONFLICT (partido_id) DO UPDATE SET
                    estado = EXCLUDED.estado, goles_local = EXCLUDED.goles_local, goles_visitante = EXCLUDED.goles_visitante,
                    penales_local = EXCLUDED.penales_local, penales_visitante = EXCLUDED.penales_visitante
            """), {
                "p_id": partido_id, "ed_id": edicion_id, "loc": loc_id, "vis": vis_id,
                "fecha": fecha, "ronda": ronda, "gl": goles_loc, "gv": goles_vis,
                "pl": penales_loc, "pv": penales_vis, "est": status.get('reason', {}).get('short', 'N/A'),
                "meta": metadata_json
            })
            eventos = match_facts.get('events', {}).get('events', []) if isinstance(match_facts.get('events'), dict) else []
            tarjetas = tarjetas_por_jugador(eventos)

            player_stats = content.get('playerStats') or {}
            for p_id_str, p_data in player_stats.items():
                try: jugador_id = int(p_id_str)
                except ValueError: continue
                nombre_jugador = extraer_nombre(p_data.get('name'))
                upsert_jugador(conn, jugador_id, nombre_jugador)
                conn.execute(SQL_STATS, fila_stats(partido_id, jugador_id, p_data, tarjetas))

            # (equipo_id, jugador, es_titular). FotMob tiene dos formatos de lineup:
            # el viejo (lineup.lineup[].players/bench) y el actual (homeTeam/awayTeam con starters/subs).
            lineups = content.get('lineup') or {}
            jugadores_lineup = []
            for team in lineups.get('lineup', []):
                t_id = team.get('teamId')
                for row in team.get('players', []):
                    jugadores_lineup += [(t_id, p, True) for p in row]
                jugadores_lineup += [(t_id, p, False) for p in team.get('bench', [])]
            for team_key in ('homeTeam', 'awayTeam'):
                team = lineups.get(team_key) or {}
                jugadores_lineup += [(team.get('id'), p, True) for p in team.get('starters') or []]
                jugadores_lineup += [(team.get('id'), p, False) for p in team.get('subs') or []]

            for t_id, p, es_titular in jugadores_lineup:
                j_id = p.get('id')
                if not j_id: continue
                posicion = p.get('role') or p.get('positionId')
                upsert_jugador(conn, j_id, extraer_nombre(p.get('name')))
                conn.execute(text("""
                    INSERT INTO alineaciones (partido_id, equipo_id, jugador_id, es_titular, dorsal, posicion)
                    VALUES (:pid, :eqid, :jid, :tit, :dorsal, :pos)
                    ON CONFLICT (partido_id, jugador_id) DO NOTHING
                """), {"pid": partido_id, "eqid": t_id, "jid": j_id, "tit": es_titular, "dorsal": p.get('shirtNumber'),
                       "pos": str(posicion) if posicion is not None else None})

            # Desde el Clausura 2026 FotMob manda eventId 0 en goles y tarjetas: se les
            # da un ID negativo estable por partido (no choca con los de FotMob) y se
            # rehacen en cada carga para no duplicarlos si cambia la lista
            conn.execute(text("DELETE FROM eventos WHERE evento_id < 0 AND partido_id = :pid"), {"pid": partido_id})
            sinteticos = 0
            for ev in eventos:
                ev_id = ev.get('eventId')
                if not ev_id:
                    if ev.get('type') not in ('Goal', 'Card', 'MissedPenalty'): continue
                    sinteticos += 1
                    ev_id = -(partido_id * 1000 + sinteticos)
                # FotMob manda id 0 cuando no sabe quién fue (pasa en el ascenso): queda en NULL
                j_id = (ev.get('player') or {}).get('id') or None
                if j_id: upsert_jugador(conn, j_id, extraer_nombre((ev.get('player') or {}).get('name')))
                conn.execute(text("""
                    INSERT INTO eventos (evento_id, partido_id, equipo_id, jugador_id, minuto, tipo_evento, detalle)
                    VALUES (:evid, :pid, :eqid, :jid, :min, :tipo, :det)
                    ON CONFLICT (evento_id) DO NOTHING
                """), {
                    "evid": ev_id, "pid": partido_id,
                    "eqid": loc_id if ev.get('isHome') else vis_id,
                    "jid": j_id, "min": ev.get('time'),
                    "tipo": ev.get('type'),
                    # En el formato nuevo el gol en contra viene aparte (ownGoal), no en goalDescription
                    "det": ev.get('card') or ev.get('goalDescription') or ('Own goal' if ev.get('ownGoal') in (True, 'True', 'true') else None)
                })

            tiros = (content.get('shotmap') or {}).get('shots', [])
            for t in tiros:
                t_id = t.get('id')
                if not t_id: continue
                j_id = t.get('playerId') or None
                if j_id: upsert_jugador(conn, j_id, t.get('playerName', 'Desc'))
                conn.execute(text("""
                    INSERT INTO tiros (tiro_id, partido_id, equipo_id, jugador_id, minuto, x, y, xg, xgot, tipo_tiro, resultado, situacion)
                    VALUES (:tid, :pid, :eqid, :jid, :min, :x, :y, :xg, :xgot, :tipo, :res, :sit)
                    ON CONFLICT (tiro_id) DO UPDATE SET situacion = EXCLUDED.situacion
                """), {
                    "tid": t_id, "pid": partido_id, "eqid": t.get('teamId'), "jid": j_id,
                    "min": t.get('min'), "x": t.get('x'), "y": t.get('y'),
                    "xg": t.get('expectedGoals'), "xgot": t.get('expectedGoalsOnTarget'),
                    "tipo": t.get('shotType'), "res": t.get('eventType'), "sit": t.get('situation')
                })

            momentum_data = (((match_facts.get('momentum') or {}).get('main') or {}).get('data') or [])
            for m in momentum_data:
                conn.execute(text("""
                    INSERT INTO momentum (partido_id, minuto, valor)
                    VALUES (:pid, :min, :val)
                    ON CONFLICT (partido_id, minuto) DO NOTHING
                """), {"pid": partido_id, "min": m.get('minute'), "val": m.get('value')})


if __name__ == "__main__":
    # Misma carpeta donde guarda fotmob_scraper.py: <repo>/data/fotmob
    raiz = Path(__file__).resolve().parents[2]
    carpeta_leagues = raiz / "data" / "fotmob" / "leagues"
    carpeta_matches = raiz / "data" / "fotmob" / "matches"
    with engine.begin() as conn:
        print("--- Iniciando proceso de carga de Big Data ---")
        if carpeta_leagues.exists():
            procesar_ligas(conn, carpeta_leagues)
        else:
            print(f"Advertencia: No se encontró la carpeta {carpeta_leagues.resolve()}")
        if carpeta_matches.exists():
            procesar_partidos(conn, carpeta_matches)
        else:
            print(f"Advertencia: No se encontró la carpeta {carpeta_matches.resolve()}")
        print("--- Carga finalizada y guardada con éxito ---")