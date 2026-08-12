import LanusStats as ls
import pandas as pd
import time

# Inicializamos el motor de FBRef
fbref = ls.Fbref()

def laboratorio_fbref():
    print("--- 📊 INICIANDO LABORATORIO FBREF (MODO SCOUTING) ---")

    # 1. ESTADÍSTICAS POR EQUIPO (GCA - Creación de Goles)
    # 'gca' = Goal Creating Actions
    print("\n[1] Analizando Creación de Goles por Equipo (2024)")
    try:
        df_gca_teams = fbref.get_teams_season_stats('gca', 'Copa de la Liga', season='2024')
        if not df_gca_teams.empty:
            print(f"✅ Éxito. Datos de {len(df_gca_teams)} equipos obtenidos.")
            # En FBRef las columnas suelen ser multi-índice, imprimimos las primeras
            print(df_gca_teams.head(3))
        time.sleep(3) # Pausa de seguridad
    except Exception as e:
        print(f"❌ Error en equipos GCA: {e}")

    # 2. TODAS LAS STATS DE JUGADORES (El bloque más pesado)
    print("\n[2] Extrayendo Stats Globales de Jugadores (Copa de la Liga 2024)")
    try:
        # 'get_all_player_season_stats' es excelente para tu tabla 'jugadores_metricas_avanzadas'
        df_all_players = fbref.get_all_player_season_stats("Copa de la Liga", "2024")
        if not df_all_players.empty:
            print(f"✅ Scouting masivo completado: {len(df_all_players)} jugadores.")
            # Buscamos columnas de xG o pases clave
            print(df_all_players.columns.tolist()[:10]) 
        time.sleep(3)
    except Exception as e:
        print(f"❌ Error en scouting masivo: {e}")

    # 3. STATS DE UN PARTIDO ESPECÍFICO (Arsenal vs Luton - Ejemplo del usuario)
    print("\n[3] Analizando Estadísticas de Match (Arsenal vs Luton)")
    try:
        match_url = "https://fbref.com/en/matches/77d7e2d6/Arsenal-Luton-Town-April-3-2024-Premier-League"
        match_stats = fbref.get_general_match_team_stats(match_url)
        if isinstance(match_stats, pd.DataFrame):
            print("✅ Estadísticas de equipo por partido obtenidas.")
            print(match_stats)
        time.sleep(3)
    except Exception as e:
        print(f"❌ Error en match stats: {e}")

    # 4. TABLA DE POSICIONES (Tournament Table)
    print("\n[4] Extrayendo Tabla de Posiciones (Premier League)")
    try:
        # Ideal para tu tabla 'posiciones'
        table_url = "https://fbref.com/en/comps/9/Premier-League-Stats"
        df_table = fbref.get_tournament_table(table_url)
        if not df_table.empty:
            print(f"✅ Tabla obtenida. Líder actual: {df_table.iloc[0, 1]}")
    except Exception as e:
        print(f"❌ Error en tabla: {e}")

if __name__ == "__main__":
    laboratorio_fbref()