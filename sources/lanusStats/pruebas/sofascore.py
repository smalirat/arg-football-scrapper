import pandas as pd
import time
from LanusStats import SofaScore

# Usamos una sola instancia pero con esperas
sofa = SofaScore()

def test_bloque_tactico(url):
    print("\n[2] Analizando Táctica (Promedios y Alineaciones)...")
    try:
        # 1. Posiciones Promedio
        data = sofa.get_players_average_positions(url)
        
        # SofaScore devuelve una TUPLA: (DataFrame_Local, DataFrame_Visita)
        if isinstance(data, tuple):
            df_local, df_visita = data
            print(f"✅ Éxito Local: {len(df_local)} jugadores mapeados.")
            print(f"✅ Éxito Visita: {len(df_visita)} jugadores mapeados.")
            
            # Esto es lo que va a tu tabla de Posiciones en la DB
            print("\nEjemplo de data para tu DB (Local):")
            print(df_local[['name', 'averageX', 'averageY']].head(3))
        
        # 2. Alineaciones
        lineups = sofa.get_lineups(url)
        if isinstance(lineups, tuple):
            print(f"✅ Alineaciones obtenidas para ambos equipos.")
            
    except Exception as e:
        print(f"❌ Error en Bloque Táctico: {e}")

def test_bloque_heatmap(url, jugador):
    print(f"\n[3] Analizando Heatmap para: {jugador}")
    try:
        # Agregamos una pequeña espera para que el browser no se sature
        time.sleep(2) 
        heatmap = sofa.get_player_heatmap(url, jugador)
        if not heatmap.empty:
            print(f"✅ Heatmap obtenido. Filas de datos: {len(heatmap)}")
    except Exception as e:
        print(f"❌ Error en Heatmap: {e}")

if __name__ == "__main__":
    print("--- ⚽ INICIANDO TEST SELECTIVO SOFASCORE ---")
    
    # Poné acá tu URL de acceso
    mi_url = "https://www.sofascore.com/es-la/football/match/everton-arsenal/RY#id:14023987" 
    mi_jugador = "Max Dowman"

    # Corremos los bloques con pausas para no cerrar la ventana
    # 1. Probamos la Táctica (Lo que falló por la tupla)
    test_bloque_tactico(mi_url)
    
    #time.sleep(3)
    
    # 2. Probamos el Heatmap
    # test_bloque_heatmap(mi_url, mi_jugador)  No funciona