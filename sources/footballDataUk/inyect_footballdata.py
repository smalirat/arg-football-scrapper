import pandas as pd
from sqlalchemy import create_engine, text
import os, json, logging
from configs.config_footballdatauk import MAPEO_EQUIPOS, obtener_ids_edicion_especiales, clean_nan

logging.basicConfig(
    filename='auditoria_completa.log', 
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    encoding='utf-8'
)

# Reemplazar con tus credenciales y nombre de la base de datos
# Podes probar configurando un .env general y usando python-dotenv para cargarlo
DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
engine = create_engine(DB_URL)

def integrar():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(script_dir, '..', '..', 'data', 'footballdatauk', 'ARG.csv')
    
    df = pd.read_csv(ruta_csv)
    print(f"Iniciando carga masiva de {len(df)} filas como Fase Regular...")

    stats = {"ok": 0, "insert": 0, "discrepancia": 0}

    with engine.begin() as conn:
        for _, row in df.iterrows():
            id_loc = MAPEO_EQUIPOS.get(row['Home'])
            id_vis = MAPEO_EQUIPOS.get(row['Away'])
            
            if id_loc is None or id_vis is None: continue

            ids_sugeridos = obtener_ids_edicion_especiales(row['Season'], row['Date'])
            if not ids_sugeridos: continue

            # Buscamos si existe el partido en CUALQUIER etapa para actualizar metadata
            query_match = text("""
                SELECT partido_id FROM partidos 
                WHERE equipo_local_id = :loc AND equipo_visitante_id = :vis
                AND edicion_id IN :ids AND goles_local = :hg AND goles_visitante = :ag
            """)
            res = conn.execute(query_match, {
                "loc": id_loc, "vis": id_vis, "ids": tuple(ids_sugeridos),
                "hg": row['HG'], "ag": row['AG']
            }).fetchone()

            metadata = {
                "fuente": "footballdatauk",
                "hora_inicio": row['Time'],
                "fecha_csv": row['Date'],
                "odds": {
                    "pinnacle": {"H": clean_nan(row['PSCH']), "D": clean_nan(row['PSCD']), "A": clean_nan(row['PSCA'])},
                    "avg": {"H": clean_nan(row['AvgCH']), "D": clean_nan(row['AvgCD']), "A": clean_nan(row['AvgCA'])}
                }
            }

            if res:
                conn.execute(text("UPDATE partidos SET metadata = :m WHERE partido_id = :pid"), 
                             {"m": json.dumps(metadata), "pid": res[0]})
                stats["ok"] += 1
            else:
                # Si no existe exactamente, chequeamos si es una discrepancia de goles en la misma edición
                # (Solo para loguear, pero seguiremos con el INSERT como Fase Regular si no hay match)
                query_check = text("""
                    SELECT partido_id FROM partidos 
                    WHERE equipo_local_id = :loc AND equipo_visitante_id = :vis
                    AND edicion_id IN :ids
                """)
                exists = conn.execute(query_check, {"loc": id_loc, "vis": id_vis, "ids": tuple(ids_sugeridos)}).fetchone()
                
                if exists:
                    logging.info(f"DISCREPANCIA (Se insertará como nuevo): {row['Home']}-{row['Away']} {row['HG']}-{row['AG']}")

                # INSERTAR como Fase Regular (etapa_id = 1)
                conn.execute(text("""
                    INSERT INTO partidos (edicion_id, equipo_local_id, equipo_visitante_id, goles_local, goles_visitante, metadata, etapa_id)
                    VALUES (:ed, :loc, :vis, :hg, :ag, :m, 1)
                """), {
                    "ed": ids_sugeridos[0], "loc": id_loc, "vis": id_vis, 
                    "hg": row['HG'], "ag": row['AG'], "m": json.dumps(metadata)
                })
                stats["insert"] += 1

    print(f"\n--- PROCESO FINALIZADO ---")
    print(f"✅ Updates realizados: {stats['ok']}")
    print(f"➕ Inserts (Fase Regular): {stats['insert']}")

if __name__ == "__main__":
    integrar()