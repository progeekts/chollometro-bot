import feedparser
import requests
import re
import os

# --- Configuración ---
RSS_URL = "https://www.chollometro.com/rss/nuevos" # Usamos nuevos para captarlos todos
# Asegúrate de tener este Secret configurado en GitHub -> Settings -> Secrets and variables -> Actions
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") 
CACHE_FILE = "vistos.txt"
MIN_TEMP = 300 # Umbral de temperatura

def get_temp(title):
    """Busca patrones como "350°" o "350º" en el título."""
    match = re.search(r"(\d+)º", title)
    if match:
        return int(match.group(1))
    return 0

def clean_title(title):
    """Limpia el título del RSS para quitar la temperatura inicial."""
    # Elimina patrones como "350º ", "350° ", "350 " al principio del texto
    cleaned = re.sub(r"^\d+[º°]?\s*", "", title)
    return cleaned

# --- 1. Cargar IDs ya enviados (Caché) ---
if not os.path.exists(CACHE_FILE):
    # Crea el archivo si no existe
    with open(CACHE_FILE, "w") as f: f.write("")

with open(CACHE_FILE, "r") as f:
    # Lee todas las líneas y quita espacios en blanco
    vistos = f.read().splitlines()

# --- 2. Leer RSS de Chollometro ---
try:
    feed = feedparser.parse(RSS_URL)
except Exception as e:
    print(f"Error leyendo el RSS: {e}")
    exit(1)

# Procesar desde el más antiguo al más nuevo para mantener el orden
for entry in reversed(feed.entries):
    id_chollo = entry.id
    temp = get_temp(entry.title)
    
    # --- FILTRO: No visto antes Y temperatura mayor o igual a MIN_TEMP ---
    if id_chollo not in vistos and temp >= MIN_TEMP:
        
        # Limpiamos el título para que no se repita la temperatura
        titulo_limpio = clean_title(entry.title)
        
        # --- 3. Formatear y enviar a Discord ---
        # Definimos el mensaje con el formato exacto solicitado
        mensaje_formateado = (
            f"🔥 **¡NUEVO CHOLLO!** 🔥 ({temp}º)\n\n"
            f"✨ **Producto:** {titulo_limpio}\n"
            f"🔗 **Link:** {entry.link}"
        )
        
        datos_webhook = {
            "content": mensaje_formateado
        }
        
        try:
            response = requests.post(WEBHOOK_URL, json=datos_webhook)
            if response.status_code == 204:
                print(f"Enviado con éxito: {titulo_limpio}")
                # Solo añadimos a vistos si se envió correctamente
                vistos.append(id_chollo)
            else:
                print(f"Error enviando a Discord: {response.status_code}, {response.text}")
        except Exception as e:
            print(f"Error de red: {e}")

# --- 4. Guardar historial (limitado a los últimos 100 para no pesar mucho) ---
with open(CACHE_FILE, "w") as f:
    f.write("\n".join(vistos[-100:]))
