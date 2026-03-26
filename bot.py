import feedparser
import requests
import re
import os
import time

# --- Configuración ---
RSS_URL = "https://www.chollometro.com/rss/hot" 
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") 
CACHE_FILE = "vistos.txt"
MIN_TEMP = 350

def get_temp(title):
    match = re.search(r"(\d+)[º°]", title)
    return int(match.group(1)) if match else 0

def get_price(title):
    """Extrae el precio del título (ej: 19,99€)."""
    match = re.search(r"(\d+(?:[.,]\d+)?€)", title)
    return match.group(1) if match else "Ver en web"

def clean_title(title):
    """Limpia el título quitando temperatura y precio inicial."""
    # Quita "350º" o "350°"
    cleaned = re.sub(r"^\d+[º°]?\s*", "", title)
    # Quita el precio si está al principio (ej: "199€ Samsung...")
    cleaned = re.sub(r"^\d+(?:[.,]\d+)?€\s*", "", cleaned)
    return cleaned.strip()

def get_image(entry):
    if 'summary' in entry:
        match = re.search(r'<img [^>]*src="([^"]+)"', entry.summary)
        return match.group(1) if match else None
    return None

def get_merchant(entry):
    if 'pepper_merchant' in entry:
        return entry['pepper_merchant']['name']
    return "Tienda desconocida"

# --- 1. Cargar IDs ---
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w") as f: f.write("")
with open(CACHE_FILE, "r") as f:
    vistos = f.read().splitlines()

# --- 2. Leer RSS ---
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
try:
    response_rss = requests.get(RSS_URL, headers=headers, timeout=10)
    feed = feedparser.parse(response_rss.content)
except Exception as e:
    print(f"Error: {e}"); exit(1)

# --- 3. Procesar ---
for entry in reversed(feed.entries):
    id_chollo = entry.link
    temp = get_temp(entry.title)
    
    if id_chollo not in vistos and temp >= MIN_TEMP:
        precio = get_price(entry.title)
        titulo_limpio = clean_title(entry.title)
        imagen_url = get_image(entry)
        tienda = get_merchant(entry)
        
        # --- NUEVO DISEÑO DE EMBED ---
        embed = {
            "title": f"✨ {titulo_limpio}",
            "url": entry.link,
            "color": 0x2F3136, # Color oscuro elegante (puedes cambiarlo a 0xFF4500 para naranja)
            "fields": [
                {
                    "name": "🌡️ Temperatura",
                    "value": f"**{temp}º**",
                    "inline": True
                },
                {
                    "name": "💰 Precio",
                    "value": f"**{precio}**",
                    "inline": True
                },
                {
                    "name": "🏪 Tienda",
                    "value": f"**{tienda}**",
                    "inline": True
                },
                {
                    "name": "🔗 Enlace",
                    "value": f"[Ir al chollo]({entry.link})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "Servidor para Españoles, chollito recién publicado"
            },
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        }

        if imagen_url:
            embed["image"] = {"url": imagen_url}

        datos_webhook = {
            "username": "Cazador de Chollos",
            "avatar_url": "URL_DE_TU_NUEVO_LOGO", # Aquí puedes pegar la URL del logo que generamos antes
            "embeds": [embed]
        }

        try:
            requests.post(WEBHOOK_URL, json=datos_webhook)
            vistos.append(id_chollo)
            time.sleep(1.2)
        except Exception as e:
            print(f"Error: {e}")

# --- 4. Guardar ---
with open(CACHE_FILE, "w") as f:
    f.write("\n".join(vistos[-100:]))
