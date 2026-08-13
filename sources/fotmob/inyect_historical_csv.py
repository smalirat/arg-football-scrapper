import pandas as pd
from sqlalchemy import create_engine, text
import os
from pathlib import Path

# Reemplazar con tus credenciales y nombre de la base de datos
# Podes probar configurando un .env general y usando python-dotenv para cargarlo
DB_URL = "postgresql://usuario:contraseña@localhost:5432/nombre_db"
engine = create_engine(DB_URL)

def cargar_datos(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: No se encontró el archivo en: {os.path.abspath(file_path)}")
        return

    df = pd.read_csv(file_path)
    print(f"Procesando {len(df)} partidos...")

    # engine.begin() abre la conexión y maneja el COMMIT automáticamente al terminar el bloque
    with engine.begin() as conn:
        
        # --- PASO 0: Crear tablas desde el script SQL ---
        print("Verificando/Creando tablas iniciales...")
        # Sube un nivel desde la carpeta del script (..) y entra a la carpeta del SQL
        ruta_sql = Path(__file__).parent.parent / 'scripts-sql' / 'creacion-inicial.sql'
        
        if not ruta_sql.exists():
            print(f"ERROR: No se encontró el archivo SQL en: {ruta_sql}")
            return
            
        script_creacion = ruta_sql.read_text(encoding='utf-8')
        conn.execute(text(script_creacion))
        print("Tablas listas.")

        # --- PASO 1: Cargar Equipos ---
        print("Cargando equipos...")
        locales = df[['local_team_id', 'local_team']].rename(columns={'local_team_id': 'id', 'local_team': 'nombre'})
        visitantes = df[['visitor_team_id', 'visitor_team']].rename(columns={'visitor_team_id': 'id', 'visitor_team': 'nombre'})
        equipos_unicos = pd.concat([locales, visitantes]).drop_duplicates('id')

        for _, row in equipos_unicos.iterrows():
            conn.execute(text("""
                INSERT INTO equipos (equipo_id, nombre_fuente)
                VALUES (:id, :nombre)
                ON CONFLICT (equipo_id) DO NOTHING
            """), {"id": row['id'], "nombre": row['nombre']})

       # --- PASO 2: Cargar Ediciones (Torneos) ---
        print("Cargando torneos...")
        torneos = df['date_name'].unique()
        for torneo in torneos:
            # Extraemos la última palabra del string como temporada (ej: "1931" de "Campeonato 1931")
            partes_nombre = str(torneo).split()
            temporada_aprox = partes_nombre[-1] if partes_nombre else "N/A"
            
            conn.execute(text("""
                INSERT INTO ediciones (nombre_torneo, temporada)
                VALUES (:nombre, :temporada)
                ON CONFLICT (nombre_torneo, temporada) DO NOTHING
            """), {"nombre": torneo, "temporada": temporada_aprox})

        # --- PASO 3: Cargar Partidos ---
        print("Insertando partidos...")
        res = conn.execute(text("SELECT edicion_id, nombre_torneo FROM ediciones"))
        map_torneos = {row[1]: row[0] for row in res}

        for idx, row in df.iterrows():
            # Generamos un ID ficticio muy alto para la data histórica del CSV
            # Así evitamos que colisione con los match_id de la API
            fake_match_id = 9000000000 + idx 
            
            conn.execute(text("""
                INSERT INTO partidos (
                    partido_id, edicion_id, equipo_local_id, equipo_visitante_id, 
                    goles_local, goles_visitante, estado
                ) VALUES (
                    :p_id, :edicion, :loc_id, :vis_id, :loc_g, :vis_g, 'FT'
                )
                ON CONFLICT (partido_id) DO NOTHING
            """), {
                "p_id": fake_match_id,
                "edicion": map_torneos[row['date_name']],
                "loc_id": row['local_team_id'],
                "vis_id": row['visitor_team_id'],
                "loc_g": row['local_result'],
                "vis_g": row['visitor_result']
            })

    # Si el código llega hasta aquí sin errores, SQLAlchemy hace el commit de todo automáticamente
    print("¡Carga completada con éxito!")

if __name__ == "__main__":
    # Obtiene la ruta de la carpeta donde está este script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ruta dinámica: sube un nivel y entra a data/kaggle/liga_2023.csv
    ruta_final = os.path.join(script_dir, '..', 'data', 'kaggle', 'liga_2023.csv')
    
    print(f"Ruta generada: {os.path.abspath(ruta_final)}")
    cargar_datos(ruta_final)