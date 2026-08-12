import json
import os
import logging

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "jsons", "fotmob"))

def cargar_json(subfolder, filename):
    path = os.path.join(BASE_PATH, subfolder, filename)
    if not os.path.exists(path): return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def auditar_local():
    print(f"🔍 AUDITANDO ARCHIVOS EN: {BASE_PATH}")
    
    match_dir = os.path.join(BASE_PATH, "matches")
    if os.path.exists(match_dir):
        files = [f for f in os.listdir(match_dir) if f.endswith('.json')]
        print(f"✅ Partidos encontrados: {len(files)}")

    player_dir = os.path.join(BASE_PATH, "players")
    if os.path.exists(player_dir):
        files = [f for f in os.listdir(player_dir) if f.endswith('.json')]
        print(f"✅ Jugadores encontrados: {len(files)}")

if __name__ == "__main__":
    auditar_local()