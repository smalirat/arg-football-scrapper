import pandas as pd
from sqlalchemy import create_engine, text
import os

# Configuración de tu DB
DB_URL = "postgresql://postgres:5432@localhost:5432/Argstats"
engine = create_engine(DB_URL)

# Diccionario de mapeo (SOLO EQUIPOS QUE CREEMOS QUE YA TIENEN ID)
MAPEO_EQUIPOS = {
    'Aldosivi': 0, 'All Boys': 1, 'Argentinos Jrs': 7, 'Arsenal Sarandi': 8,
    'Atl. Rafaela': 10, 'Atl. Tucuman': 11, 'Banfield': 14, 'Barracas Central': 95,
    'Belgrano': 16, 'Boca Juniors': 17, 'Central Cordoba': 19, 'Chacarita Juniors': 21,
    'Colon Santa FE': 25, 'Colon Santa Fe': 25,
    'Defensa y Justicia': 27, 'Estudiantes L.P.': 37,
    'Gimnasia L.P.': 43, 'Godoy Cruz': 46, 'Huracan': 48, 'Ind. Rivadavia': 55, 
    'Independiente': 56, 'Instituto': 57, 'Lanus': 63, 'Newells Old Boys': 66, 
    'Olimpo Bahia Blanca': 68, 'Patronato': 69, 'Platense': 70, 'Quilmes': 71, 
    'Racing Club': 73, 'River Plate': 75, 'Rosario Central': 76, 'San Lorenzo': 77, 
    'San Martin S.J.': 80, 'San Martin T.': 81, 'Sarmiento Junin': 84, 
    'Talleres Cordoba': 88, 'Temperley': 90, 'Tigre': 91, 'Union de Santa Fe': 93, 
    'Velez Sarsfield': 94, 'Crucero del Norte': 26, 'Estudiantes Rio Cuarto': 38, 
    'Gimnasia Mendoza': 44, 'Nueva Chicago': 67, 'Dep. Riestra': 102
}

def validar_contra_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(script_dir, '..', '..', 'data', 'footballdatauk', 'ARG.csv')
    
    df = pd.read_csv(ruta_csv)
    nombres_csv = set(df['Home'].unique()) | set(df['Away'].unique())

    print("--- COMPARANDO DICCIONARIO VS BASE DE DATOS ---")
    
    with engine.connect() as conn:
        # Traemos la verdad de la base de datos
        res = conn.execute(text("SELECT equipo_id, nombre_fuente FROM equipos"))
        db_data = {row[0]: row[1] for row in res}

    errores_identidad = []
    ids_no_encontrados = []
    nombres_no_mapeados = []

    for nombre in nombres_csv:
        if nombre not in MAPEO_EQUIPOS:
            nombres_no_mapeados.append(nombre)
            continue
            
        id_asig = MAPEO_EQUIPOS[nombre]
        
        if id_asig not in db_data:
            ids_no_encontrados.append(f"ID {id_asig} (asignado a '{nombre}') no existe en la DB.")
        else:
            nombre_db = db_data[id_asig]
            # Imprimimos la relación para que vos la veas a ojo
            print(f"OK: {nombre} (CSV) -> ID {id_asig} -> {nombre_db}")

    print("\n--- REPORTE FINAL ---")
    
    if nombres_no_mapeados:
        print("\n❓ EQUIPOS EN CSV PERO FUERA DEL SCRIPT (Ej: Riestra):")
        for n in sorted(nombres_no_mapeados): print(f"   - {n}")

    if ids_no_encontrados:
        print("\n❌ IDs QUE NO ESTÁN EN TU TABLA EQUIPOS (Error de número):")
        for i in ids_no_encontrados: print(f"   - {i}")

if __name__ == "__main__":
    validar_contra_db()