import pandas as pd
from sqlalchemy import create_engine, text
import os
from configs.config_footballdatauk import MAPEO_EQUIPOS

# Configuración de tu DB
# Connection string en la variable de entorno ARGSTATS_DB_URL (ver .env.example)
DB_URL = os.getenv("ARGSTATS_DB_URL", "postgresql://usuario:contraseña@localhost:5432/nombre_db")
engine = create_engine(DB_URL)

def validar_contra_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(script_dir, '..', '..', 'data', 'footballdatauk', 'ARG.csv')

    df = pd.read_csv(ruta_csv)
    nombres_csv = set(df['Home'].unique()) | set(df['Away'].unique())

    print("--- COMPARANDO MAPEO VS BASE DE DATOS ---")

    with engine.connect() as conn:
        # Traemos la verdad de la base de datos
        res = conn.execute(text("SELECT equipo_id, nombre_fuente FROM equipos"))
        db_data = {row[0]: row[1] for row in res}

    ids_no_encontrados = []
    nombres_no_mapeados = []

    for nombre in sorted(nombres_csv):
        if nombre not in MAPEO_EQUIPOS:
            nombres_no_mapeados.append(nombre)
            continue

        # Cada equipo puede tener ID de Kaggle (histórico) y de FotMob (desde 2024)
        partes = []
        for fuente, id_asig in MAPEO_EQUIPOS[nombre].items():
            if id_asig is None:
                continue
            if id_asig not in db_data:
                ids_no_encontrados.append(f"ID {fuente} {id_asig} (asignado a '{nombre}') no existe en la DB.")
            else:
                partes.append(f"{fuente} {id_asig} -> {db_data[id_asig]}")

        # Imprimimos la relación para que vos la veas a ojo
        print(f"OK: {nombre} (CSV) | " + " | ".join(partes))

    print("\n--- REPORTE FINAL ---")

    if nombres_no_mapeados:
        print("\n❓ EQUIPOS EN CSV SIN MAPEO (agregarlos en configs/config_footballdatauk.py):")
        for n in sorted(nombres_no_mapeados): print(f"   - {n}")

    if ids_no_encontrados:
        print("\n❌ IDs QUE NO ESTÁN EN TU TABLA EQUIPOS (Error de número):")
        for i in ids_no_encontrados: print(f"   - {i}")

    if not nombres_no_mapeados and not ids_no_encontrados:
        print("\nTodo mapeado: se puede correr inyect_footballdata.py")

if __name__ == "__main__":
    validar_contra_db()
