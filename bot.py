import feedparser
import requests
import re
import os
import time

# --- Configuración ---
# Cambiado a 'hot' para que pueda captar chollos que realmente alcancen 250º
RSS_URL = "https://www.chollometro.com/rss/hot" 
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") 
CACHE_FILE = "vistos.txt"
MIN_TEMP = 300

def get_temp(title):
    """Busca patrones como "300º" o "350°" en el título."""
    match = re.search(r"(\d+)[º°]", title)
    if match:
        return int(match.group(1))
    return 0

def clean_title(title):
    """Limpia el título del RSS para quitar la temperatura inicial."""
    cleaned = re.sub(r"^\d+[º°]?\s*", "", title)
    return cleaned

# --- 1. Cargar IDs ya enviados (Caché) ---
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w") as f: f.write("")

with open(CACHE_FILE, "r") as f:
    vistos = f.read().splitlines()

# --- 2. Leer RSS de Chollometro ---
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

try:
    response_rss = requests.get(RSS_URL, headers=headers, timeout=10)
    response_rss.raise_for_status() 
    feed = feedparser.parse(response_rss.content)
except Exception as e:
    print(f"Error leyendo el RSS: {e}")
    exit(1)

# Procesar desde el más antiguo al más nuevo
for entry in reversed(feed.entries):
    # Usamos entry.link para que coincida exactamente con tu vistos.txt
    id_chollo = entry.link
    temp = get_temp(entry.title)
    
    # --- FILTRO ---
    if id_chollo not in vistos and temp >= MIN_TEMP:
        titulo_limpio = clean_title(entry.title)
        
        # --- 3. Formatear y enviar a Discord con Embed ---
        titulo_limpio = clean_title(entry.title)
        # Estructura del Embed para que se vea limpio y profesional
        embed = {
            "title": f"🔥 {titulo_limpio}",
            "url": entry.link,
            "color": 0xFF4500, # Naranja Chollometro
            "fields": [
                {
                    "name": "Temperatura",
                    "value": f"**{temp}º**",
                    "inline": True
                },
                {
                    "name": "Ir al chollo",
                    "value": f"[Haz clic aquí]({entry.link})",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Servidor para Españoles, chollito recién publicado"
            }
        }
        datos_webhook = {
            "embeds": [embed]
        }
        try:
            response = requests.post(WEBHOOK_URL, json=datos_webhook)
            time.sleep(1.2)
            if response.status_code == 204:
                print(f"Enviado con éxito: {titulo_limpio}")
                vistos.append(id_chollo)
            else:
                print(f"Error enviando a Discord: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error de red: {e}")

# --- 4. Guardar historial ---
with open(CACHE_FILE, "w") as f:
    f.write("\n".join(vistos[-100:]))
