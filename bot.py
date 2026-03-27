import feedparser
import requests
import re
import os
import time

# --- Configuración ---
RSS_URL = "https://www.chollometro.com/rss/hot" 
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") 
CACHE_FILE = "vistos.txt"
# Bajado a 250 para facilitar que encuentres cosas en el feed 'hot'
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

def get_direct_link(entry):
    """Extrae el enlace directo a la tienda desde el feed."""
    # Chollometro suele ponerlo en entry.link, pero para ir directo 
    # a veces necesitamos buscar la redirección en los parámetros del feed
    if 'link' in entry:
        # La mayoría de veces el RSS permite obtener el link de salida 
        # Si quieres el link que salta el aviso de Chollometro:
        return entry.link.replace("/ofertas/", "/visit/threaddesc/")
    return entry.link

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
    print(f"Feed cargado. Total entradas encontradas: {len(feed.entries)}")
except Exception as e:
    print(f"Error cargando RSS: {e}"); exit(1)

# --- 3. Procesar ---
enviados_en_esta_sesion = 0

for entry in reversed(feed.entries):
    id_chollo = entry.link
    temp = get_temp(entry.title)
    
    # Log de depuración para cada entrada
    print(f"Analizando: {entry.title[:40]}... | Temp: {temp}º")
    
    if id_chollo in vistos:
        print("  -> Ya publicado anteriormente (vistos.txt).")
        continue

    if temp < MIN_TEMP:
        print(f"  -> Temperatura insuficiente ({temp}º < {MIN_TEMP}º).")
        continue

    # Si pasa los filtros, preparamos el envío
enlace_directo = id_chollo.replace("/ofertas/", "/visit/threaddesc/")
        
        precio = get_price(entry.title)
        titulo_limpio = clean_title(entry.title)
        imagen_url = get_image(entry)
        tienda = get_merchant(entry)
    
    # --- DISEÑO ORDENADO ---
   embed = {
            "title": f"✨ {titulo_limpio}",
            "url": enlace_directo, # Título ahora lleva a la tienda
            "color": 0x2F3136,
            "fields": [
                {"name": "🌡️ Temperatura", "value": f"**{temp}º**", "inline": True},
                {"name": "💰 Precio", "value": f"**{precio}**", "inline": True},
                {"name": "🏪 Tienda", "value": f"**{tienda}**", "inline": True},
                {"name": "🔗 Enlace Directo", "value": f"[Ir a la tienda]({enlace_directo})", "inline": False}
            ],
        "footer": {"text": "Servidor para Españoles, chollito recién publicado"},
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

    if imagen_url:
        embed["image"] = {"url": imagen_url}

    datos_webhook = {
        "username": "Cazador de Chollos",
        "avatar_url": "https://i.imgur.com/8N88HQU.png", # He puesto una URL de ejemplo
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
            print(f"  ❌ Error Webhook ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"  ❌ Error de red: {e}")

# --- 4. Guardar Historial ---
print(f"--- Fin del proceso. Enviados hoy: {enviados_en_esta_sesion} ---")
with open(CACHE_FILE, "w") as f:
    # Mantenemos los últimos 200 vistos para evitar que el archivo crezca infinito
    f.write("\n".join(vistos[-200:]))
