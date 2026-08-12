import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:admin@localhost:5432/Argstats"
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




def procesar_ligas(conn, carpeta_leagues):
    archivos = list(Path(carpeta_leagues).glob('*.json'))
    print(f"Procesando {len(archivos)} archivos de ligas...")

    for archivo in archivos:
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
            detalles = data.get('details') or {}
            if not detalles:
                continue
            torneo = detalles.get('name')
            temporada = detalles.get('selectedSeason')
            edicion_id = upsert_edicion(conn, torneo, temporada)
            tables_data = data.get('table') or []
            if tables_data and isinstance(tables_data, list) and tables_data[0].get('data'):
                t_data = tables_data[0]['data']
                zonas = t_data.get('tables') if 'tables' in t_data else [{'leagueName': None, 'table': t_data.get('table', {})}]
                for zona in zonas:
                    nombre_zona = zona.get('leagueName')
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
            torneo = gen.get('leagueName', 'Desconocido')
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
                "fecha": fecha, "ronda": gen.get('matchRound', 'N/A'), "gl": goles_loc, "gv": goles_vis,
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

            lineups = content.get('lineup') or {}
            for team in lineups.get('lineup', []):
                t_id = team.get('teamId')
                for row in team.get('players', []):
                    for p in row:
                        j_id = p.get('id')
                        if not j_id: continue
                        upsert_jugador(conn, j_id, extraer_nombre(p.get('name')))
                        conn.execute(text("""
                            INSERT INTO alineaciones (partido_id, equipo_id, jugador_id, es_titular, dorsal, posicion)
                            VALUES (:pid, :eqid, :jid, TRUE, :dorsal, :pos)
                            ON CONFLICT (partido_id, jugador_id) DO NOTHING
                        """), {"pid": partido_id, "eqid": t_id, "jid": j_id, "dorsal": p.get('shirtNumber'), "pos": p.get('role')})

                for p in team.get('bench', []):
                    j_id = p.get('id')
                    if not j_id: continue
                    upsert_jugador(conn, j_id, extraer_nombre(p.get('name')))
                    conn.execute(text("""
                        INSERT INTO alineaciones (partido_id, equipo_id, jugador_id, es_titular, dorsal, posicion)
                        VALUES (:pid, :eqid, :jid, FALSE, :dorsal, :pos)
                        ON CONFLICT (partido_id, jugador_id) DO NOTHING
                    """), {"pid": partido_id, "eqid": t_id, "jid": j_id, "dorsal": p.get('shirtNumber'), "pos": p.get('role')})

            eventos = match_facts.get('events', {}).get('events', []) if isinstance(match_facts.get('events'), dict) else []
            for ev in eventos:
                ev_id = ev.get('eventId')
                if not ev_id: continue 
                j_id = (ev.get('player') or {}).get('id')
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
                j_id = t.get('playerId')
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
    raiz = Path(__file__).parent.parent.parent.parent
    carpeta_leagues = raiz / "jsons" / "fotmob" / "leagues"
    carpeta_matches = raiz / "jsons" / "fotmob" / "matches"
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