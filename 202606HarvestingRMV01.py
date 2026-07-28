# Harvesting Raton de Minca
# 2026-JN-03
# Ejecutar python D:/AI_RMinca/202606HarvestingRMV01.py
# Archivos Txt de salida
# Archivo excel de entrada D:/AI_RMinca/catalogo_rutas.xlsx



import os
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook


# =====================================================================
# CONDICIÓN 5: DIRECTORIÓ Y RUTAS CONFIGURABLES POR EL USUARIO
# =====================================================================
RUTA_EXCEL = "D:/AI_RMinca/catalogo_rutas.xlsx"       
DIRECTORIO_DESTINO = "D:/AI_RMinca" 

# Asegurar la existencia del directorio de destino
os.makedirs(DIRECTORIO_DESTINO, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =====================================================================
# CONDICIÓN 1: PROCESAMIENTO DE EXCEL Y ELIMINACIÓN DE DUPLICADOS
# =====================================================================
try:
    df_catalogo = pd.read_excel(RUTA_EXCEL, sheet_name="CATALOGO")
    df_catalogo.columns = df_catalogo.columns.str.strip()
    
    if 'URL' not in df_catalogo.columns or 'AREA' not in df_catalogo.columns:
        raise ValueError("El archivo Excel debe contener las columnas 'URL' y 'AREA' en la hoja 'CATALOGO'.")
    
    # Quedarse únicamente con URLs únicas para evitar repetir el scrapping
    df_unicos = df_catalogo.drop_duplicates(subset=['URL']).copy()
    print(f"--> Excel procesado. Se realizaría el scraping sobre {len(df_unicos)} URLs únicas.")
except Exception as e:
    print(f"Error al procesar el archivo Excel: {e}")
    df_unicos = pd.DataFrame()

# =====================================================================
# FUNCIÓN AUXILIAR: GENERACIÓN DEL ARCHIVO TXT (CONDICIONES 2, 4 Y 5)
# =====================================================================
def guardar_archivo_txt(directorio, url_fuente, area, sendero, lineas_texto, enlaces_multimedia):
    # Condición 2: ID obtenido de los primeros 6 caracteres del h3
    id_seccion = sendero[:6].strip()
    if not id_seccion:
        id_seccion = "S_ID"
        
    # Condición 4: Primeros 16 caracteres del subtítulo h3 reemplazando espacios por '_'
    nombre_limpio = re.sub(r'[\\/*?:"<>|]', "", sendero) # Remover caracteres prohibidos por SO
    nombre_archivo_base = nombre_limpio[:16].strip().replace(" ", "_")
    
    if not nombre_archivo_base:
        nombre_archivo_base = "seccion_anonima"
        
    nombre_completo_archivo = f"{nombre_archivo_base}.txt"
    ruta_final_archivo = os.path.join(directorio, nombre_completo_archivo)
    
    contenido_archivo = []
    
    # Construcción del Encabezado (Condición 2)
    contenido_archivo.append(f"ID: {id_seccion}")
    contenido_archivo.append(f"URL_FUENTE: {url_fuente}")
    contenido_archivo.append(f"Area: {area}")
    contenido_archivo.append(f"Sendero: {sendero}")
    contenido_archivo.append("-" * 60)
    
    # Párrafo de texto o listas que siguen al subtítulo
    if lineas_texto:
        contenido_archivo.append("\n".join(lineas_texto))
    else:
        contenido_archivo.append("[Esta sección h3 no contiene texto o listas posteriores]")
        
    # Condición 3: Inyección de URLs de Mapas y Fotos rescatadas al final de la sección h3 respectiva
    if enlaces_multimedia:
        # Remover duplicados exactos preservando el orden
        enlaces_unicos = list(dict.fromkeys(enlaces_multimedia))
        contenido_archivo.append("\n" + "=" * 40)
        contenido_archivo.append("ENLACES MULTIMEDIA RESCATADOS EN ESTA SECCIÓN:")
        contenido_archivo.append("=" * 40)
        contenido_archivo.append("\n".join(enlaces_unicos))
        
    try:
        with open(ruta_final_archivo, "w", encoding="utf-8") as txt_file:
            txt_file.write("\n".join(contenido_archivo))
        print(f"   [Archivo Guardado]: {nombre_completo_archivo}")
    except IOError as io_err:
        print(f"   Error al guardar el archivo {nombre_completo_archivo}: {io_err}")

# =====================================================================
# PROCESO PRINCIPAL DE HARVESTING LINEAL (MÁQUINA DE ESTADOS)
# =====================================================================
for index, fila in df_unicos.iterrows():
    url_objetivo = fila['URL']
    area_objetivo = fila['AREA']
    
    print(f"\nIniciando harvesting de la URL: {url_objetivo}")
    
    try:
        response = requests.get(url_objetivo, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Enfocar la búsqueda en el cuerpo o contenedor principal de la página
        main_content = soup.find('main') or soup.find('body')
        if not main_content:
            print(f"No se detectó un cuerpo de contenido en {url_objetivo}")
            continue

        seccion_activa = False
        subtitulo_texto = ""
        contenido_bloque = []
        urls_mapas_fotos = []

        # Recorrido secuencial estricto de etiquetas hijas / hermanos HTML
        for elemento in main_content.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'iframe', 'a']):
            
            # CONDICIÓN 0: Si aparece un H1 o H2, actúa como frontera y corta la captura del H3 anterior
            if elemento.name in ['h1', 'h2']:
                if seccion_activa:
                    # Guardamos la sección h3 que se acaba de cerrar si acumuló datos
                    if len(contenido_bloque) > 0 or len(urls_mapas_fotos) > 0:
                        guardar_archivo_txt(DIRECTORIO_DESTINO, url_objetivo, area_objetivo, subtitulo_texto, contenido_bloque, urls_mapas_fotos)
                # Resetear estados por completo debido a la frontera
                seccion_activa = False
                subtitulo_texto = ""
                contenido_bloque = []
                urls_mapas_fotos = []
                continue

            # DETECCIÓN DE SUBTÍTULO (H3): Inicia o cambia de bloque de captura
            if elemento.name == 'h3':
                # Si ya veníamos capturando un H3 previo y aparece otro consecutivo, cerramos y guardamos el anterior
                if seccion_activa and (len(contenido_bloque) > 0 or len(urls_mapas_fotos) > 0):
                    guardar_archivo_txt(DIRECTORIO_DESTINO, url_objetivo, area_objetivo, subtitulo_texto, contenido_bloque, urls_mapas_fotos)
                
                # Activar nueva sección con los datos actuales
                seccion_activa = True
                subtitulo_texto = elemento.get_text(strip=True)
                contenido_bloque = []
                urls_mapas_fotos = []
                continue

            # CAPTURA INTERNA DE ELEMENTOS (Solo si estamos situados bajo un H3 activo)
            if seccion_activa:
                
                # CONDICIÓN 3: Rescate en secciones <iframe> (Específico para Google Maps)
                if elemento.name == 'iframe' and elemento.has_attr('src'):
                    src = elemento['src']
                    # Filtra si la URL del iframe apunta a dominios de mapas de Google o contenido de usuario de Google
                    if any(p in src.lower() for p in ["maps.google", "googleusercontent.com", "google.com/maps"]):
                        urls_mapas_fotos.append(f"[Google Maps - iframe]: {src}")
                
                # CONDICIÓN 3: Rescate en marcadores de hipervínculo <a> (Específico para Google Photos o enlaces directos a mapas)
                elif elemento.name == 'a' and elemento.has_attr('href'):
                    href = elemento['href']
                    
                    # Comprobación para Google Photos
                    if any(p in href.lower() for p in ["goo.gl/photos", "photos.google", "photos.app.goo.gl"]):
                        urls_mapas_fotos.append(f"[Google Photos - Enlace]: {href}")
                    
                    # Salvaguarda: por si un mapa fue ingresado como enlace convencional en lugar de iframe
                    elif any(p in href.lower() for p in ["maps.google", "google.com/maps"]):
                        urls_mapas_fotos.append(f"[Google Maps - Enlace]: {href}")

                # Extracción clásica de textos de tipo párrafo
                elif elemento.name == 'p':
                    texto_p = elemento.get_text(strip=True)
                    if texto_p:
                        contenido_bloque.append(texto_p)
                        
                # Extracción de textos estructurados como listas (ul, ol)
                elif elemento.name in ['ul', 'ol']:
                    for item in elemento.find_all('li'):
                        texto_item = item.get_text(strip=True)
                        if texto_item:
                            contenido_bloque.append(f"- {texto_item}")

        # Guardar la última sección h3 del documento si quedó abierta tras terminar el ciclo
        if seccion_activa and (len(contenido_bloque) > 0 or len(urls_mapas_fotos) > 0):
            guardar_archivo_txt(DIRECTORIO_DESTINO, url_objetivo, area_objetivo, subtitulo_texto, contenido_bloque, urls_mapas_fotos)

    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con la URL {url_objetivo}: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado al procesar {url_objetivo}: {e}")