import feedparser
import requests
import re
import os

# Configuración
RSS_URL = "https://www.chollometro.com/rss/nuevos" # Usamos nuevos para captarlos todos
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
CACHE_FILE = "vistos.txt"
MIN_TEMP = 300

def get_temp(title):
    # Busca patrones como "350°" o "350º"
    match = re.search(r"(\d+)º", title)
    if match:
        return int(match.group(1))
    return 0

# 1. Cargar IDs ya enviados
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w") as f: f.write("")

with open(CACHE_FILE, "r") as f:
    vistos = f.read().splitlines()

# 2. Leer RSS
feed = feedparser.parse(RSS_URL)
nuevos_vistos = []

for entry in reversed(feed.entries): # Del más antiguo al más nuevo
    id_chollo = entry.id
    temp = get_temp(entry.title)
    
    if id_chollo not in vistos and temp >= MIN_TEMP:
        # Enviar a Discord
        mensaje = {
            "content": f"🔥 **¡CHOLLAZO {temp}º!**\n{entry.title}\n{entry.link}"
        }
        requests.post(WEBHOOK_URL, json=mensaje)
        vistos.append(id_chollo)

# 3. Guardar historial (limitado a los últimos 100 para no pesar mucho)
with open(CACHE_FILE, "w") as f:
    f.write("\n".join(vistos[-100:]))
