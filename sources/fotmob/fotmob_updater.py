import json
import os
import time
import sys
import random
import asyncio
import nodriver as uc

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from configs.config import FOTMOB_CONFIG

CHROME_PROFILE_PATH = r"D:\Argstats\chrome_profile"
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "jsons", "fotmob"))

async def obtener_json_seguro(page):
    """Extrae el JSON y detecta si es necesario el desbloqueo humano."""
    await asyncio.sleep(1)
    
    while True:
        try:
            raw_text = await page.evaluate("document.body.innerText")
            data = json.loads(raw_text)
            
            if isinstance(data, dict) and (data.get("code") == "TURNSTILE_REQUIRED" or "Verification" in str(data)):
                print("\n⚠️ BLOQUEO: Turnstile detectado.")
                input("Acción: Resuelve el captcha en Chrome y presiona ENTER aquí...")
                return "REINTENTAR"
                
            return data
        except Exception:
            print(f"\n⚠️ CONTENIDO NO VÁLIDO (Bloqueo silencioso).")
            input("Acción: Interactúa con el navegador y presiona ENTER aquí...")
            continue

async def actualizar_liga_especifica(liga_id, anio):
    """
    Fuerza la actualización de un torneo específico, saltando los partidos
    que ya se encuentran descargados en formato JSON.
    """
    for sub in ["leagues", "matches"]:
        os.makedirs(os.path.join(BASE_PATH, sub), exist_ok=True)
        
    print(f"🚀 Iniciando con perfil: {CHROME_PROFILE_PATH}")
    
    browser = await uc.start(
        user_data_dir=CHROME_PROFILE_PATH,
        no_sandbox=True,
        browser_args=["--disable-gpu", "--no-first-run"]
    )
    
    try:
        print(f"🎯 Forzando actualización para Liga ID: {liga_id} - Año: {anio}")
        
        url_league = f"https://www.fotmob.com/api/data/leagues?id={liga_id}&season={anio}"
        page = await browser.get(url_league)
        data_l = await obtener_json_seguro(page)
        
        if data_l == "REINTENTAR": return
        
        # Guardar la info actualizada de la liga
        with open(os.path.join(BASE_PATH, "leagues", f"league_{liga_id}_{anio.replace('/', '_')}.json"), "w", encoding="utf-8") as f:
            json.dump(data_l, f, indent=4)
            
        matches = data_l.get('fixtures', {}).get('allMatches', []) or data_l.get('leagueOverviewMatches', [])
        
        partidos_descargados = 0
        partidos_saltados = 0
        
        for m in matches:
            m_id = str(m.get('id'))
            m_path = os.path.join(BASE_PATH, "matches", f"match_{m_id}.json")
            
            # Si el JSON del partido ya existe, no lo volvemos a bajar.
            # (Si quisieras actualizar partidos YA descargados porque cambiaron las stats, elimina este if)
            if os.path.exists(m_path):
                partidos_saltados += 1
                continue
                
            espera = random.uniform(8, 15)
            print(f"⬇️ Descargando Partido {m_id} (esperando {espera:.1f}s)...")
            await asyncio.sleep(espera)
            
            url_match = f"https://www.fotmob.com/api/data/matchDetails?matchId={m_id}"
            page_m = await browser.get(url_match)
            data_m = await obtener_json_seguro(page_m)
            
            if data_m == "REINTENTAR": return
            
            if isinstance(data_m, dict):
                with open(m_path, "w", encoding="utf-8") as f:
                    json.dump(data_m, f, indent=4)
                partidos_descargados += 1
                    
        print(f"✅ Actualización finalizada. Descargados: {partidos_descargados}. Ya existían: {partidos_saltados}.")

    finally:
        print("\n👋 Proceso en pausa. El navegador sigue abierto.")
        while True:
            await asyncio.sleep(10)

if __name__ == "__main__":
    # Configura aquí qué torneo exacto quieres forzar a descargar.
    # 112 = Liga Profesional, 10007 = Copa de la Liga Profesional
    LIGA_OBJETIVO = "112" 
    ANIO_OBJETIVO = "2026"
    
    uc.loop().run_until_complete(actualizar_liga_especifica(LIGA_OBJETIVO, ANIO_OBJETIVO))