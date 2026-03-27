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
    cleaned = re.sub(r"^\d+[º°]?\s*", "", title)
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

def get_direct_link(entry_link):
    """Transforma el link de Chollometro en link de redirección directa."""
    return entry_link.replace("/ofertas/", "/visit/threaddesc/")

# --- 1. Cargar IDs ---
if not os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "w") as f: f.write("")
with open(CACHE_FILE, "r") as f:
    vistos = f.read().splitlines()

# --- 2. Leer RSS ---
print(f"--- Iniciando búsqueda en {RSS_URL} ---")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
try:
    response_rss = requests.get(RSS_URL, headers=headers, timeout=10)
    feed = feedparser.parse(response_rss.content)
    print(f"Feed cargado. Total entradas: {len(feed.entries)}")
except Exception as e:
    print(f"Error cargando RSS: {e}"); exit(1)

# --- 3. Procesar ---
enviados_en_esta_sesion = 0

for entry in reversed(feed.entries):
    id_chollo = entry.link
    temp = get_temp(entry.title)
    
    print(f"Analizando: {entry.title[:40]}... | Temp: {temp}º")
    
    if id_chollo in vistos:
        print("  -> Ya en vistos.txt")
        continue

    if temp < MIN_TEMP:
        print(f"  -> Temp insuficiente ({temp}º)")
        continue

    # --- TODO ESTE BLOQUE DEBE TENER LA MISMA SANGRÍA ---
    enlace_directo = get_direct_link(id_chollo)
    precio = get_price(entry.title)
    titulo_limpio = clean_title(entry.title)
    imagen_url = get_image(entry)
    tienda = get_merchant(entry)
    
    embed = {
        "title": f"✨ {titulo_limpio}",
        "url": enlace_directo,
        "color": 0x2F3136,
        "fields": [
            {"name": "🌡️ Temperatura", "value": f"**{temp}º**", "inline": True},
            {"name": "💰 Precio", "value": f"**{precio}**", "inline": True},
            {"name": "🏪 Tienda", "value": f"**{tienda}**", "inline": True},
            {"name": "🔗 Enlace Directo", "value": f"[Ir a la tienda]({enlace_directo})", "inline": False}
        ],
        "footer": {"text": "Chollito recién publicado"},
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

    if imagen_url:
        embed["image"] = {"url": imagen_url}

    datos_webhook = {
        "username": "Cazador de Chollos",
        "avatar_url": "https://i.imgur.com/8N88HQU.png",
        "embeds": [embed]
    }

    try:
        res = requests.post(WEBHOOK_URL, json=datos_webhook)
        if res.status_code == 204:
            print(f"  ✅ ENVIADO: {titulo_limpio}")
            vistos.append(id_chollo)
            enviados_en_esta_sesion += 1
            time.sleep(1.2)
        else:
            print(f"  ❌ Error Webhook: {res.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

# --- 4. Guardar ---
print(f"--- Fin. Enviados sesión: {enviados_en_esta_sesion} ---")
with open(CACHE_FILE, "w") as f:
    f.write("\n".join(vistos[-200:]))
