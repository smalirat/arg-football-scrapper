import pandas as pd
import numpy as np
from LanusStats import Transfermarkt

# Parche para compatibilidad de Numpy
if not hasattr(np, 'NAN'):
    np.NAN = np.nan

tm = Transfermarkt()

def laboratorio_tm_final():
    print("--- 💰 PROCESANDO DATOS FINALES TRANSFERMARKT ---")

    # 1. VALUACIÓN DE EQUIPOS
    try:
        df_valuations = tm.get_league_teams_valuations(league="Primera Division Argentina", season="2024")
        # Usamos los nombres reales detectados en tu consola
        print("\n[1] Top 3 Equipos por Valor:")
        print(df_valuations[['Club', 'Total market value (M€)']].head(3))
    except Exception as e:
        print(f"❌ Error en Bloque 1: {e}")

    # 2. PLANTEL DE LANÚS
    try:
        df_lanus = tm.scrape_players_for_teams(team_name="Club Atletico Lanus", team_id="333", season="2024")
        print("\n[2] Muestra de Plantel de Lanús:")
        # Usamos 'Jugadores' y 'Valor de mercado'
        print(df_lanus[['Jugadores', 'Posicion', 'Valor de mercado']].head(5))
    except Exception as e:
        print(f"❌ Error en Bloque 2: {e}")

    # 3. PENALES (DIBU)
    try:
        penalties_data = tm.get_keepers_penalty_data("Emiliano Martinez", "111873")
        df_penales = penalties_data[0] # Tomamos la primera tabla de la tupla
        print("\n[3] Últimos Penales contra el Dibu Martínez:")
        print(df_penales[['Seasons', 'Penalty Kicker', 'Final Result']].head(5))
    except Exception as e:
        print(f"❌ Error en Bloque 3: {e}")

if __name__ == "__main__":
    laboratorio_tm_final()