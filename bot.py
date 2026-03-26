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
    """Busca patrones como "300º" o "350°" en el título."""
    match = re.search(r"(\d+)[º°]", title)
    if match:
        return int(match.group(1))
    return 0

def clean_title(title):
    """Limpia el título del RSS para quitar la temperatura inicial."""
    cleaned = re.sub(r"^\d+[º°]?\s*", "", title)
    return cleaned

def get_image(entry):
    """Extrae la URL de la imagen del contenido del post."""
    # Intentamos buscar en el summary (HTML) la etiqueta <img>
    if 'summary' in entry:
        match = re.search(r'<img [^>]*src="([^"]+)"', entry.summary)
        if match:
            return match.group(1)
    return None

def get_merchant(entry):
    """Extrae el nombre de la tienda (Amazon, PcComponentes, etc)."""
    # Chollometro usa el namespace 'pepper:merchant' en su RSS
    if 'pepper_merchant' in entry:
        return entry['pepper_merchant']['name']
    return "Ver en web"

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
    id_chollo = entry.link
    temp = get_temp(entry.title)
    
    # --- FILTRO ---
    if id_chollo not in vistos and temp >= MIN_TEMP:
        titulo_limpio = clean_title(entry.title)
        imagen_url = get_image(entry)
        tienda = get_merchant(entry)
        
        # --- 3. Formatear y enviar a Discord con Embed ---
        embed = {
            "title": f"🔥 {titulo_limpio}",
            "url": entry.link,
            "color": 0xFF4500, # Naranja Chollometro
            "fields": [
                {
                    "name": "🏪 Tienda",
                    "value": f"**{tienda}**",
                    "inline": True
                },
                {
                    "name": "🌡️ Temperatura",
                    "value": f"**{temp}º**",
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
            }
        }

        # Añadimos la imagen principal si existe
        if imagen_url:
            embed["image"] = {"url": imagen_url}

        datos_webhook = {
            "embeds": [embed]
        }

        try:
            response = requests.post(WEBHOOK_URL, json=datos_webhook)
            time.sleep(1.2) # Respetar rate limits de Discord
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
