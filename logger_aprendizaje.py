# -*- coding: utf-8 -*-
"""
Módulo Independiente: logger_aprendizaje.py
Versión: 2.1.0 - Persistencia remota vía GitHub REST API sobre rama aislada 'data-logs'
Timestamp: 2026-07-28T20:29:50-05:00

"""
import os
import json
import base64
import requests
from datetime import datetime

# =========================================================================
# CONFIGURACIÓN DE CONEXIÓN A GITHUB VIA API
# =========================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Nombre de usuario y repositorio de GitHub:
GITHUB_REPO = "raton-sandbox/ai-rminca"

# Ruta del archivo dentro de la rama 'data-logs'
LOG_FILE_PATH_IN_REPO = "interacciones_aprendizaje.jsonl"

# Lista negra de palabras clave de control para detener saludos triviales o spam publicitario
SALUDOS_Y_SPAM_KEYWORDS = [
    "hola", "hi", "bye", "buenos dias", "buenas tardes", "buenas noches", "adios", 
    "chao", "test", "prueba", "http", "www", "click aqui", "buy now"
]

def enviar_log_a_github(log_entry: dict) -> bool:
    """
    Obtiene el contenido actual del archivo .jsonl desde la rama 'data-logs', 
    concatena la nueva línea JSON y ejecuta un commit automático vía REST API.
    """
    if not GITHUB_TOKEN:
        print("⚠️ [LOGGER]: Variable GITHUB_TOKEN no configurada en Render. Omitiendo persistencia remota.")
        return False

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{LOG_FILE_PATH_IN_REPO}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        nueva_linea = json.dumps(log_entry, ensure_ascii=False) + "\n"
        
        # 1. Consultar si el archivo ya existe EN LA RAMA 'data-logs' para obtener su contenido y SHA
        url_get = f"{url}?ref=data-logs"
        response = requests.get(url_get, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            sha = data["sha"]
            contenido_actual = base64.b64decode(data["content"]).decode("utf-8")
            contenido_actualizado = contenido_actual + nueva_linea
        elif response.status_code == 404:
            # Si el archivo aún no existe en data-logs, se inicializa por primera vez
            sha = None
            contenido_actualizado = nueva_linea
        else:
            print(f"⚠️ [LOGGER]: Error al consultar GitHub API: Status Code {response.status_code}")
            return False

        # 2. Codificar en Base64 (Requisito estricto de la API de contenidos de GitHub)
        contenido_b64 = base64.b64encode(contenido_actualizado.encode("utf-8")).decode("utf-8")

        # 3. Construir el payload para el commit hacia la rama 'data-logs'
        payload = {
            "message": f"Analytics: registro de interacción {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": contenido_b64,
            "branch": "data-logs"
        }
        if sha:
            payload["sha"] = sha

        # 4. Enviar actualización a GitHub (PUT)
        put_response = requests.put(url, headers=headers, json=payload)

        if put_response.status_code in [200, 201]:
            print("📊 [LOGGER]: Interacción real indexada de forma exitosa en GitHub (.jsonl).")
            return True
        else:
            print(f"⚠️ [LOGGER]: Falló el commit en GitHub: {put_response.json()}")
            return False

    except Exception as e:
        print(f"⚠️ [LOGGER]: Excepción al conectar con la API de GitHub: {e}")
        return False


def registrar_interaccion(
    prompt_usuario: str, 
    entidades_dict: dict, 
    codigo_respuesta: str, 
    conteo_resultados: int,
    lista_rutas_ids: list,
    metadata_http: dict = None
) -> bool:
    """
    Evalúa, limpia y persiste una interacción real en el repositorio de GitHub.
    Mantendremos intacta la firma y lógica de filtrado defensivo original.
    """
    texto_clean = prompt_usuario.strip().lower()
    
    # =========================================================================
    # REGLA DE FILTRADO 1: Exclusión por Longitud Mínima e Expresiones Triviales
    # =========================================================================
    palabras = texto_clean.split()
    if len(palabras) <= 1:
        return False
        
    if any(keyword in texto_clean for keyword in SALUDOS_Y_SPAM_KEYWORDS) and len(palabras) <= 3:
        return False

    # =========================================================================
    # REGLA DE FILTRADO 2: Exclusión de Consultas Sin Sentido (Ruido de Ejecución)
    # =========================================================================
    tipo_flujo = entidades_dict.get("tipo_flujo", "desconocido")
    if tipo_flujo == "desconocido" or str(codigo_respuesta).strip() == "5":
        return False

    # =========================================================================
    # CONSTRUCCIÓN DEL REGISTRO DE APRENDIZAJE (LOG SCHEMA)
    # =========================================================================
    meta_interna = metadata_http if metadata_http is not None else {}
    ip_origen = meta_interna.get("ip_origen", "127.0.0.1")
    
    partes_ip = ip_origen.split('.')
    if len(partes_ip) == 4:
        ip_anonima = f"{partes_ip[0]}.{partes_ip[1]}.{partes_ip[2]}.XX"
    else:
        ip_anonima = "IP_ANONIMA"

    ahora = datetime.now()
    
    log_entry = {
        "timestamp": ahora.isoformat(),
        "prompt_usuario_original": prompt_usuario.strip(),
        "metadata_tecnica": {
            "ip_origen_anonimizada": ip_anonima,
            "dispositivo_tipo": meta_interna.get("dispositivo_tipo", "No detectado"),
            "sistema_operativo": meta_interna.get("sistema_operativo", "No detectado"),
            "navegador": meta_interna.get("navegador", "No detectado")
        },
        "indicadores_contextuales": {
            "es_fin_de_semana_o_festivo": ahora.weekday() in [5, 6],
            "hora_del_dia": ahora.strftime("%H:%M"),
            "mes_operacion": ahora.strftime("%B")
        },
        "analisis_orquestador": {
            "tipo_flujo": tipo_flujo,
            "area_mapeada": entidades_dict.get("area"),
            "interes_mapeado": entidades_dict.get("interes"),
            "origen_mapeado": entidades_dict.get("origen"),
            "destino_mapeado": entidades_dict.get("destino")
        },
        "resultado_ejecucion": {
            "codigo_respuesta_pandas": str(codigo_respuesta).strip(),
            "conteo_resultados": conteo_resultados,
            "rutas_devueltas_ids": lista_rutas_ids
        }
    }

    # =========================================================================
    # PERSISTENCIA REMOTA EN GITHUB
    # =========================================================================
    return enviar_log_a_github(log_entry)