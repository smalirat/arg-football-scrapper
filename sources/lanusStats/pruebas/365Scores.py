import LanusStats as ls
import pandas as pd
from PIL import Image

threesix = ls.ThreeSixFiveScores()

def laboratorio_365_profesional():
    print("--- 📱 REFINANDO DATA DE 365SCORES ---")
    
    match_url = "https://www.365scores.com/es-mx/football/match/copa-de-la-liga-profesional-7214/lanus-union-santa-fe-869-7206-7214#id=4033824"

    # 1. SHOTMAP (Limpieza de Coordenadas)
    print("\n[1] Procesando Shotmap (Normalización para DB)")
    try:
        shotmap = threesix.get_match_shotmap(match_url)
        if not shotmap.empty:
            # Reemplazamos NaN por 0 para que tu SQL no explote
            shotmap[['x', 'y']] = shotmap[['x', 'y']].fillna(0)
            print(f"✅ {len(shotmap)} tiros normalizados.")
            # Las columnas que realmente te sirven para la tabla 'eventos_tiros'
            print(shotmap[['xg', 'x', 'y', 'shot_outcome']].head(3))
    except Exception as e:
        print(f"❌ Error en Shotmap: {e}")

    # 2. INFO DE JUGADORES (Mapeo de IDs)
    print("\n[2] Extrayendo IDs para Mapeo de Proveedores")
    try:
        p_info = threesix.get_players_info(match_url)
        if not p_info.empty:
            # En tu DB, guardá el 'athleteId' como 'id_365scores'
            print("✅ Muestra de IDs de jugadores encontrados:")
            print(p_info[['name', 'athleteId']].head(3))
    except Exception as e:
        print(f"❌ Error en Info: {e}")

    # 3. HEATMAP (Manejo de Imagen)
    print("\n[3] Generando Heatmap (Formato Imagen)")
    try:
        # IMPORTANTE: Aquí la librería devuelve un objeto de imagen WebP
        img_heatmap = threesix.get_player_heatmap_match(player="Walter Bou", match_url=match_url)
        
        if img_heatmap:
            print("✅ Heatmap obtenido correctamente como objeto de imagen.")
            # Si querés guardarlo en tu carpeta de assets del proyecto:
            # img_heatmap.save("heatmap_bou.webp")
        else:
            print("⚠️ No se pudo generar la imagen del heatmap.")
    except Exception as e:
        print(f"❌ Error en Heatmap: {e}")

if __name__ == "__main__":
    laboratorio_365_profesional()