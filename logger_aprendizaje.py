# -*- coding: utf-8 -*-
"""
Módulo Independiente: logger_aprendizaje.py
Versión: 1.0.0 - Persistencia de Interacciones Reales y Filtrado Defensivo Anti-Spam
Timestamp: 2026-07-03T12:05:00-05:00
"""
import os
import json
from datetime import datetime

# Ruta absoluta hacia el archivo de acumulación analítica
# Obtiene la ruta del directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = "D:/AI_RMinca/logs/interacciones_aprendizaje.jsonl"

# Lista negra de palabras clave de control para detener saludos triviales o spam publicitario
SALUDOS_Y_SPAM_KEYWORDS = [
    "hola", "hi", "bye","buenos dias", "buenas tardes", "buenas noches", "adios", 
    "chao", "test", "prueba", "http", "www", "click aqui", "buy now"
]

def registrar_interaccion(
    prompt_usuario: str, 
    entidades_dict: dict, 
    codigo_respuesta: str, 
    conteo_resultados: int,
    lista_rutas_ids: list,
    metadata_http: dict = None
) -> bool:
    """
    Evalúa, limpia y persiste una interacción real en el archivo de registro estructurado.
    Excluye activamente saludos, spam e inyecciones de publicidad que degraden el dataset.
    
    Parámetros:
    -----------
    prompt_usuario : str -> El texto crudo enviado por el caminante.
    entidades_dict : dict -> El objeto JSON de entidades extraído por Groq.
    codigo_respuesta : str -> El string de control devuelto por el flujo analítico ("0", "4", etc.).
    conteo_resultados : int -> Número de rutas finales que hicieron match en Pandas.
    lista_rutas_ids : list -> IDs alfanuméricos de las rutas devueltas.
    metadata_http : dict -> Diccionario opcional con el User-Agent y la IP procesada por el frontend.
    """
    texto_clean = prompt_usuario.strip().lower()
    
    # =========================================================================
    # REGLA DE FILTRADO 1: Exclusión por Longitud Mínima e Expresiones Triviales
    # =========================================================================
    palabras = texto_clean.split()
    if len(palabras) <= 1:
        # Ignora palabras sueltas como "hola", "ok", "?", "Minca" sin contexto
        return False
        
    # Validar si el texto coincide exactamente con algún saludo o contiene enlaces sospechosos
    if any(keyword in texto_clean for keyword in SALUDOS_Y_SPAM_KEYWORDS) and len(palabras) <= 3:
        # Deja pasar frases largas complejas, pero bloquea saludos cortos tipo "Hola buenos dias"
        return False

    # =========================================================================
    # REGLA DE FILTRADO 2: Exclusión de Consultas Sin Sentido (Ruido de Ejecución)
    # =========================================================================
    tipo_flujo = entidades_dict.get("tipo_flujo", "desconocido")
    
    # Si el orquestador no pudo clasificar el flujo y Pandas no encontró estructura válida, es basura
    if tipo_flujo == "desconocido" or str(codigo_respuesta).strip() == "5":
        return False

    # =========================================================================
    # CONSTRUCCIÓN DEL REGISTRO DE APRENDIZAJE (LOG SCHEMA)
    # =========================================================================
    # Extracción higiénica de metadata técnica enviada por el navegador
    meta_interna = metadata_http if metadata_http is not None else {}
    ip_origen = meta_interna.get("ip_origen", "127.0.0.1")
    
    # Anonimización mandatoria del último octeto de la IP para cumplir con privacidad de datos
    partes_ip = ip_origen.split('.')
    if len(partes_ip) == 4:
        ip_anonima = f"{partes_ip[0]}.{partes_ip[1]}.{partes_ip[2]}.XX"
    else:
        ip_anonima = "IP_ANONIMA"

    # Procesar indicadores de contexto temporal
    ahora = datetime.now()
    es_fin_de_semana = ahora.weekday() in [5, 6]  # 5 = Sábado, 6 = Domingo
    
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
            "es_fin_de_semana_o_festivo": es_fin_de_semana,
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
    # PERSISTENCIA SEGURA EN DISCO LOCAL (JSON Lines APPEND MODE)
    # =========================================================================
    try:
        # Asegurar de forma defensiva la existencia de la carpeta de logs
        os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        print(f"📊 [LOGGER]: Interacción real indexada de forma exitosa en el escalón de aprendizaje (.jsonl).")
        return True
    except Exception as e:
        print(f"⚠️ [LOGGER]: No se pudo escribir el log analítico en disco: {e}")
        return False