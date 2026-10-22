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

def obtener_stat(player_data, category_key, target_stat_key, default=0):
    for grupo in player_data.get('stats', []) or []:
        if isinstance(grupo, dict) and grupo.get('key') == category_key:
            for stat_nombre, stat_info in (grupo.get('stats') or {}).items():
                if isinstance(stat_info, dict) and stat_info.get('key') == target_stat_key:
                    valor = stat_info.get('stat', {}).get('value')
                    return valor if valor is not None else default
    return default

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
            player_stats = content.get('playerStats') or {}
            for p_id_str, p_data in player_stats.items():
                try: jugador_id = int(p_id_str)
                except ValueError: continue
                nombre_jugador = extraer_nombre(p_data.get('name'))
                upsert_jugador(conn, jugador_id, nombre_jugador)
                conn.execute(text("""
                    INSERT INTO stats_jugador_partido (
                        partido_id, jugador_id, equipo_id, minutos_jugados, rating, 
                        goles, asistencias, xg, xa, tarjeta_amarilla, tarjeta_roja
                    ) VALUES (
                        :pid, :jid, :eqid, :min, :rat, :gol, :ast, :xg, :xa, :ta, :tr
                    ) ON CONFLICT (partido_id, jugador_id) DO UPDATE SET
                        minutos_jugados = EXCLUDED.minutos_jugados, rating = EXCLUDED.rating,
                        goles = EXCLUDED.goles, asistencias = EXCLUDED.asistencias,
                        xg = EXCLUDED.xg, xa = EXCLUDED.xa, 
                        tarjeta_amarilla = EXCLUDED.tarjeta_amarilla, tarjeta_roja = EXCLUDED.tarjeta_roja
                """), {
                    "pid": partido_id, "jid": jugador_id, "eqid": p_data.get('teamId'),
                    "min": obtener_stat(p_data, 'top_stats', 'minutes_played', 0),
                    "rat": obtener_stat(p_data, 'top_stats', 'rating_title', None),
                    "gol": obtener_stat(p_data, 'top_stats', 'goals', 0),
                    "ast": obtener_stat(p_data, 'top_stats', 'assists', 0),
                    "xg": obtener_stat(p_data, 'top_stats', 'expected_goals', 0.0),
                    "xa": obtener_stat(p_data, 'top_stats', 'expected_assists', 0.0),
                    "ta": obtener_stat(p_data, 'discipline', 'yellow_cards', 0) > 0,
                    "tr": obtener_stat(p_data, 'discipline', 'red_cards', 0) > 0
                })

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

            eventos = match_facts.get('events', {}).get('events', []) if isinstance(match_facts.get('events'), dict) else []
            for ev in eventos:
                ev_id = ev.get('eventId')
                if not ev_id: continue 
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
                    "det": ev.get('card') or ev.get('goalDescription')
                })

            tiros = (content.get('shotmap') or {}).get('shots', [])
            for t in tiros:
                t_id = t.get('id')
                if not t_id: continue
                j_id = t.get('playerId') or None
                if j_id: upsert_jugador(conn, j_id, t.get('playerName', 'Desc'))
                conn.execute(text("""
                    INSERT INTO tiros (tiro_id, partido_id, equipo_id, jugador_id, minuto, x, y, xg, xgot, tipo_tiro, resultado)
                    VALUES (:tid, :pid, :eqid, :jid, :min, :x, :y, :xg, :xgot, :tipo, :res)
                    ON CONFLICT (tiro_id) DO NOTHING
                """), {
                    "tid": t_id, "pid": partido_id, "eqid": t.get('teamId'), "jid": j_id,
                    "min": t.get('min'), "x": t.get('x'), "y": t.get('y'),
                    "xg": t.get('expectedGoals'), "xgot": t.get('expectedGoalsOnTarget'),
                    "tipo": t.get('shotType'), "res": t.get('eventType')
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