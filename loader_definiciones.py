# -*- coding: utf-8 -*-
"""
loader_definiciones.py

Módulo encargado de cargar, filtrar y formatear el catálogo de definiciones de jerga
y conceptos técnicos de senderismo desde el repositorio de GitHub:
  - Usuario: raton-sandbox
  - Repositorio: ai_rminca
  - Rama: main
  - Carpeta: core/
  - Archivo: definiciones.json

Timestamp de Generación / Actualización: 2026-07-31T12:25:38-05:00
"""

import json
import os
import requests
from datetime import datetime

# URL raw del archivo definiciones.json alojado en GitHub (rama main, carpeta core)
URL_DEFINICIONES_GITHUB = (
    "https://raw.githubusercontent.com/raton-sandbox/ai_rminca/main/core/definiciones.json"
)

# Ruta local fallback si se prefiere una copia en disco
PATH_LOCAL_DEFINICIONES = os.path.join("core", "definiciones.json")


def cargar_definiciones_jerga(url_github=URL_DEFINICIONES_GITHUB, path_local=PATH_LOCAL_DEFINICIONES):
    """
    Carga la lista de definiciones consumiendo directamente GitHub en tiempo de ejecución.
    Si falla la conexión de red, intenta hacer fallback al archivo local en `core/definiciones.json`.
    
    Filtra y suprime explícitamente todos los ítems cuya entidad sea "ERROR".

    Args:
        url_github (str): URL Raw de GitHub donde reside el JSON.
        path_local (str): Ruta relativa o absoluta local de respaldo.

    Returns:
        dict: Diccionario con la lista filtrada de elementos y el timestamp de carga.
    """
    datos_raw = None
    origen = ""
    timestamp_carga = datetime.now().isoformat()

    # 1. Intentar consumo remoto desde GitHub
    try:
        response = requests.get(url_github, timeout=10)
        if response.status_code == 200:
            datos_raw = response.json()
            origen = f"GitHub Remote ({url_github})"
        else:
            print(f"[WARN] GitHub devolvió HTTP {response.status_code}. Intentando carga local...")
    except Exception as e:
        print(f"[WARN] Falló la petición a GitHub ({e}). Intentando carga local...")

    # 2. Fallback a archivo local si la petición remota no obtuvo datos
    if datos_raw is None:
        if os.path.exists(path_local):
            try:
                with open(path_local, "r", encoding="utf-8") as f:
                    datos_raw = json.load(f)
                    origen = f"Archivo Local ({path_local})"
            except Exception as e:
                print(f"[ERROR] Error leyendo el archivo local {path_local}: {e}")
                return {"timestamp": timestamp_carga, "origen": "Error", "items": []}
        else:
            print(f"[ERROR] No se encontró el archivo local en {path_local}")
            return {"timestamp": timestamp_carga, "origen": "No encontrado", "items": []}

    # 3. Filtrar suprimiendo los elementos con "entidad": "SINONIMOS"
    definiciones_filtradas = [
        item for item in datos_raw 
        if item.get("entidad") == "SINONIMOS"
    ]

    print(f"[{timestamp_carga}] [OK] Carga exitosa desde {origen}.")
    print(f"[{timestamp_carga}] [OK] Se procesaron {len(definiciones_filtradas)} definiciones válidas (suprimidos {len(datos_raw) - len(definiciones_filtradas)} errores).")

    return {
        "timestamp": timestamp_carga,
        "origen": origen,
        "items": definiciones_filtradas
    }


def formatear_jerga_para_prompt(resultado_carga):
    """
    Transforma el resultado de la carga en un bloque de texto estructurado y ordenado por entidad, listo para ser inyectado en el System Prompt del orquestador.

    Args:
        resultado_carga (dict): Retorno de `cargar_definiciones_jerga()`.

    Returns:
        str: Texto estructurado con encabezado, timestamp y glosario.
    """
    items = resultado_carga.get("items", [])
    if not items:
        return ""

    # Agrupar por tipo de entidad
    agrupado = {}
    for item in items:
        entidad = item.get("entidad", "General")
        if entidad not in agrupado:
            agrupado[entidad] = []
        agrupado[entidad].append(item)

    timestamp_str = resultado_carga.get("timestamp", "")
    lineas = [
        f"GLOSARIO Y CONCEPTOS TECNICOS DE SENDERISMO (RATON DE MINCA) [Cargado: {timestamp_str}]:"
    ]

    for entidad, lista_items in agrupado.items():
        lineas.append(f"\n### {entidad}:")
        for item in lista_items:
            cat = str(item.get("categoria", "")).strip()
            def_text = str(item.get("definicion", "")).strip()
            #horas = str(item.get("horas_limite", "")).strip()

            linea_item = f"- **{cat}**: {def_text}"
            #if horas and horas not in ["0.0", ""]:
            #    linea_item += f" *(Límite aprox: {horas}h)*"

            lineas.append(linea_item)

    return "\n".join(lineas)