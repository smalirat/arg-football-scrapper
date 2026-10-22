import pandas as pd
from sqlalchemy import create_engine, text
from psycopg2.extras import execute_values
from collections import defaultdict
from datetime import datetime, date
import os, json, logging
from configs.config_footballdatauk import ids_equipo, PREFIJOS_EDICION, clean_nan

logging.basicConfig(
    filename='auditoria_completa.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Connection string en la variable de entorno ARGSTATS_DB_URL (ver .env.example)
DB_URL = os.getenv("ARGSTATS_DB_URL", "postgresql://usuario:contraseña@localhost:5432/nombre_db")
engine = create_engine(DB_URL)


def cargar_candidatos(conn):
    """
    Partidos de primera de la base, indexados por (temporada, local, visitante).
    Se traen una sola vez para no hacer una consulta por fila del CSV.
    """
    res = conn.execute(text("""
        SELECT p.partido_id, e.temporada, p.equipo_local_id, p.equipo_visitante_id,
               p.goles_local, p.goles_visitante, LEFT(p.fecha_utc::text, 10)
        FROM partidos p JOIN ediciones e USING (edicion_id)
        WHERE e.nombre_torneo LIKE ANY(:prefijos)
    """), {"prefijos": [f"{p}%" for p in PREFIJOS_EDICION]})

    indice = defaultdict(list)
    for pid, temporada, loc, vis, gl, gv, dia in res:
        indice[(temporada, loc, vis)].append({
            "partido_id": pid, "goles": (gl, gv),
            # Los partidos de Kaggle no tienen fecha; los de FotMob sí
            "dia": date.fromisoformat(dia) if dia else None,
        })
    return indice


def buscar_partido(indice, row):
    """Devuelve (partido_id, None) si hay un único partido que coincide, o (None, motivo)."""
    ids_loc, ids_vis = ids_equipo(row['Home']), ids_equipo(row['Away'])
    if not ids_loc or not ids_vis:
        return None, "sin_mapeo"

    temporada = str(row['Season']).strip()
    candidatos = [c for loc in ids_loc for vis in ids_vis for c in indice[(temporada, loc, vis)]]
    if not candidatos:
        return None, "sin_partido"

    con_resultado = [c for c in candidatos if c["goles"] == (row['HG'], row['AG'])]
    if not con_resultado:
        return None, "discrepancia_goles"

    # La fecha del CSV es hora de Reino Unido y la de la base UTC: se acepta ±1 día
    dia_csv = datetime.strptime(row['Date'], "%d/%m/%Y").date()
    en_fecha = [c for c in con_resultado if c["dia"] is None or abs((c["dia"] - dia_csv).days) <= 1]
    if len(en_fecha) != 1:
        return None, "ambiguo" if en_fecha else "fecha_distinta"

    return en_fecha[0]["partido_id"], None


def integrar():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(script_dir, '..', '..', 'data', 'footballdatauk', 'ARG.csv')

    df = pd.read_csv(ruta_csv)
    print(f"Cruzando {len(df)} filas de cuotas contra los partidos de la base...")

    stats = defaultdict(int)
    odds_por_partido = {}

    with engine.begin() as conn:
        indice = cargar_candidatos(conn)

        for _, row in df.iterrows():
            partido_id, motivo = buscar_partido(indice, row)

            if motivo:
                stats[motivo] += 1
                logging.info(f"{motivo.upper()}: {row['Season']} {row['Date']} {row['Home']}-{row['Away']} {row['HG']}-{row['AG']}")
                continue

            # Si dos filas del CSV caen en el mismo partido, no se carga ninguna
            if partido_id in odds_por_partido:
                stats["duplicado"] += 1
                logging.info(f"DUPLICADO: partido {partido_id} ya tenía cuotas de otra fila ({row['Date']} {row['Home']}-{row['Away']})")
                odds_por_partido[partido_id] = None
                continue

            odds_por_partido[partido_id] = {
                "fuente": "footballdatauk",
                "hora_inicio": row['Time'],
                "fecha_csv": row['Date'],
                "odds": {
                    "pinnacle": {"H": clean_nan(row['PSCH']), "D": clean_nan(row['PSCD']), "A": clean_nan(row['PSCA'])},
                    "avg": {"H": clean_nan(row['AvgCH']), "D": clean_nan(row['AvgCD']), "A": clean_nan(row['AvgCA'])}
                }
            }

        filas = [(pid, json.dumps(m)) for pid, m in odds_por_partido.items() if m is not None]

        # Las cuotas se agregan a la metadata existente (||): no se pisan las
        # estadísticas que guarda FotMob en esa misma columna
        execute_values(conn.connection.cursor(), """
            UPDATE partidos p SET metadata = CASE
                WHEN jsonb_typeof(p.metadata) = 'object' THEN p.metadata || v.m::jsonb
                ELSE v.m::jsonb
            END
            FROM (VALUES %s) AS v(partido_id, m)
            WHERE p.partido_id = v.partido_id
        """, filas, page_size=1000)

    print(f"\n--- PROCESO FINALIZADO ---")
    print(f"✅ Partidos con cuotas: {len(filas)}")
    for motivo, n in sorted(stats.items()):
        print(f"⚠️  {motivo}: {n}")
    print("Detalle de las filas no cargadas en auditoria_completa.log")


if __name__ == "__main__":
    integrar()
