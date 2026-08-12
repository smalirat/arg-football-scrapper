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
CHECKPOINT_FILE = os.path.join(BASE_PATH, "checkpoint.json")

async def obtener_json_seguro(page):
    """Extrae el JSON y detecta si es necesario el desbloqueo humano."""
    await asyncio.sleep(1) 
    while True:
        try:
            raw_text = await page.evaluate("document.body.innerText")
            data = json.loads(raw_text)
            if isinstance(data, dict) and (data.get("code") == "TURNSTILE_REQUIRED" or "Verification" in str(data)):
                print("\n🚫 BLOQUEO: Turnstile detectado.")
                input("Acción: Resuelve el captcha en Chrome y presiona ENTER aquí...")
                return "REINTENTAR"
            return data
        except Exception:
            print(f"\n⚠️ CONTENIDO NO VÁLIDO (Bloqueo silencioso).")
            input("Acción: Interactúa con el navegador y presiona ENTER aquí...")
            continue

async def descargar_por_goteo():
    for sub in ["leagues", "matches"]:
        os.makedirs(os.path.join(BASE_PATH, sub), exist_ok=True)
    checkpoint = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f: 
            checkpoint = json.load(f)

    print(f"🚀 Iniciando con perfil: {CHROME_PROFILE_PATH}")
    browser = await uc.start(
        user_data_dir=CHROME_PROFILE_PATH,
        no_sandbox=True,
        browser_args=["--disable-gpu", "--no-first-run"]
    )
    tarea_completada = False

    try:
        for l_id, info in FOTMOB_CONFIG["ligas"].items():
            if tarea_completada: break
            for anio in info["años"]:
                progreso = checkpoint.get(str(l_id), {})
                if progreso == "COMPLETO" or (isinstance(progreso, dict) and progreso.get("estado") == "COMPLETO"):
                    continue
                if isinstance(progreso, dict) and progreso.get("anio") and progreso.get("anio") != anio:
                    continue

                print(f"🎯 Tarea actual: {info['nombre']} - {anio}")
                url_league = f"https://www.fotmob.com/api/data/leagues?id={l_id}&season={anio}"
                page = await browser.get(url_league)
                data_l = await obtener_json_seguro(page)
                if data_l == "REINTENTAR": return

                with open(os.path.join(BASE_PATH, "leagues", f"league_{l_id}_{anio.replace('/', '_')}.json"), "w", encoding="utf-8") as f:
                    json.dump(data_l, f, indent=4)

                matches = data_l.get('fixtures', {}).get('allMatches', []) or data_l.get('leagueOverviewMatches', [])
                ultimo_match_id = progreso.get("ultimo_match_id") if isinstance(progreso, dict) else None
                encontrado_puntero = False if ultimo_match_id else True

                for m in matches:
                    m_id = str(m.get('id'))
                    if not encontrado_puntero:
                        if m_id == ultimo_match_id:
                            encontrado_puntero = True
                        continue 

                    m_path = os.path.join(BASE_PATH, "matches", f"match_{m_id}.json")
                    espera = random.uniform(8, 15)
                    print(f"   ∟ 🏟️ Partido {m_id} (esperando {espera:.1f}s)...")
                    await asyncio.sleep(espera)
                    url_match = f"https://www.fotmob.com/api/data/matchDetails?matchId={m_id}"
                    page_m = await browser.get(url_match)
                    data_m = await obtener_json_seguro(page_m)
                    if data_m == "REINTENTAR": return

                    if isinstance(data_m, dict):
                        with open(m_path, "w", encoding="utf-8") as f:
                            json.dump(data_m, f, indent=4)
                        checkpoint[str(l_id)] = {
                            "anio": anio,
                            "ultimo_match_id": m_id,
                            "estado": "EN_PROGRESO"
                        }
                        with open(CHECKPOINT_FILE, "w") as f:
                            json.dump(checkpoint, f, indent=4)

                checkpoint[str(l_id)] = {"anio": anio, "estado": "COMPLETO"}
                with open(CHECKPOINT_FILE, "w") as f:
                    json.dump(checkpoint, f, indent=4)
                print(f"✅ Temporada {anio} finalizada.")
                tarea_completada = True
                break

    finally:
        print("\n👋 Proceso en pausa. El navegador sigue abierto.")
        while True:
            await asyncio.sleep(10)

if __name__ == "__main__":
    uc.loop().run_until_complete(descargar_por_goteo())