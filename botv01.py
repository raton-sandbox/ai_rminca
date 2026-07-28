#webhook captura parametros enviados por los intents de dialogflow es
#202060614
#crea servidor with Flask
#ir a la carpeta del proyecto en D
# aplicamos una operación matemática de matrices llamada Transposición (.T). Esto voltea la tabla de Pandas de forma inmediata en la memoria RAM: las filas se convierten en columnas y las columnas en filas. De esta manera, zona_origen, zona_destino y tus otros 21 atributos pasan a ser las columnas oficiales de consulta.

#Ejecutar python D:/AI_RMinca/botv01.py
# datos en D:/AI_RMinca/conocimiento_maestro.json
# Incluiye la lógica básica de filtrado, control de errores, sanitización de strings y diseño de experiencia de usuario UX).
#en consola aparte previo debe estar ejecutandose el servidor ngrok
#Para cada intent debe estar habilidato el fulfillment con la url de forwining con la carpeta webhook

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MÓDULO: botv01.py
DESCRIPCIÓN: Webhook para Dialogflow ES - Proyecto Ratón de Minca.
OPTIMIZACIÓN: Soporte para Múltiples Nodos Maestros y marcas explícitas en Excel.
"""

import os
import sys
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify

# ==============================================================================
# CONFIGURACIÓN GLOBAL DE ARCHIVOS DE ENTRADA
# ==============================================================================
RUTA_MAESTRA = r"D:\AI_RMinca\conocimiento_maestro.json"
RUTA_JERARQUIA_EXCEL = r"D:\AI_RMinca\catalogo_rutas.xlsx"
HOJA_JERARQUIA = "Jerarquia_Geografica"

# 🔥 TU NUEVA LISTA NEGRA MULTI-MASTER (Normalizada en minúsculas y sin acentos críticos)
NODOS_MAESTROS_SISTEMA = {
    "santa marta", 
    "dibulla", 
    "cienaga", 
    "ciénaga", 
    "nabusimake", 
    "nabusímake", 
    "pueblo bello"
}

app = Flask(__name__)

# ==============================================================================
# CARGA E INGESTIÓN DE LA ONTOLOGÍA GEOGRÁFICA
# ==============================================================================
def cargar_ontologia_geografica_desde_excel():
    if not os.path.exists(RUTA_JERARQUIA_EXCEL):
        print(f"⚠️ ADVERTENCIA: No se encontró el catálogo en {RUTA_JERARQUIA_EXCEL}.")
        return {}

    try:
        df_geo = pd.read_excel(RUTA_JERARQUIA_EXCEL, sheet_name=HOJA_JERARQUIA)
        df_geo['zona'] = df_geo['zona'].astype(str).str.strip().str.lower()
        df_geo['padre'] = df_geo['padre'].fillna("").astype(str).str.strip().str.lower()
        df_geo['sinonimos'] = df_geo['sinonimos'].fillna("").astype(str).str.strip().str.lower()

        diccionario_jerarquia = {}

        for _, fila in df_geo.iterrows():
            zona_id = fila['zona']
            padre_id = fila['padre']
            
            if not zona_id or zona_id == "nan":
                continue
            
            # Normalización defensiva: Si en Excel dice "master" o "raiz", o si el ID está en la lista
            es_master = (padre_id in ["master", "raiz", "", "nan"]) or (zona_id in NODOS_MAESTROS_SISTEMA)
            
            lista_sinonimos = [s.strip() for s in fila['sinonimos'].split(',') if s.strip()]
            if zona_id not in lista_sinonimos:
                lista_sinonimos.append(zona_id)

            diccionario_jerarquia[zona_id] = {
                # Guardamos "master" de forma estándar si es una raíz geográfica
                "padre": "master" if es_master else padre_id,
                "sinonimos": lista_sinonimos
            }

        print(f"✅ Ontología procesada: {len(diccionario_jerarquia)} nodos cargados en memoria.")
        return diccionario_jerarquia

    except Exception as e:
        print(f"❌ CRÍTICO: Error al digerir la pestaña {HOJA_JERARQUIA}: {str(e)}")
        return {}

# ==============================================================================
# CARGA Y NORMALIZACIÓN DEL ARCHIVO CONOCIMIENTO MAESTRO
# ==============================================================================
def inicializar_fuente_verdad():
    if not os.path.exists(RUTA_MAESTRA):
        print(f"⚠️ ADVERTENCIA: No se encontró la fuente de verdad en {RUTA_MAESTRA}.")
        return pd.DataFrame()
    try:
        df_raw = pd.read_json(RUTA_MAESTRA)
        if 'datos_excel' not in df_raw.columns:
            df_raw = df_raw.T

        if 'datos_excel' in df_raw.columns:
            df_validos = df_raw[df_raw['datos_excel'].apply(lambda x: isinstance(x, dict))]
            df_final = pd.DataFrame(df_validos['datos_excel'].tolist(), index=df_validos.index)
            if 'contenido_web' in df_raw.columns:
                df_final['contenido_web'] = df_raw['contenido_web']
        else:
            df_final = df_raw

        columnas_numericas = ['distancia_km', 'tiempo_min', 'ascenso_mt', 'descenso_mt']
        for col in columnas_numericas:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')

        print(f"✅ Base de conocimiento de rutas lista ({len(df_final)} variantes).")
        return df_final
    except Exception as error:
        print(f"❌ CRÍTICO: Error en ingeniería de datos JSON: {str(error)}")
        return pd.DataFrame()

# Inicialización única de estructuras en memoria RAM
JERARQUIA_GEOGRAFICA = cargar_ontologia_geografica_desde_excel()
df_master = inicializar_fuente_verdad()

# ==============================================================================
# HELPERS DE NAVEGACIÓN DE GRAFOS GEOGRÁFICOS
# ==============================================================================
def obtener_sinonimos_directos(zona_raw: str):
    zona = zona_raw.strip().lower()
    for nodo_id, data in JERARQUIA_GEOGRAFICA.items():
        if zona == nodo_id or zona in data["sinonimos"]:
            return nodo_id, data["sinonimos"]
    return zona, [zona]

def obtener_padre_permitido(nodo_id: str):
    """
    🛡️ EL ESCUDO MULTI-MASTER: 
    Retorna el padre y sus sinónimos ÚNICAMENTE si no colisiona con un nodo maestro.
    """
    if nodo_id in JERARQUIA_GEOGRAFICA:
        padre_id = JERARQUIA_GEOGRAFICA[nodo_id]["padre"]
        
        # Intercepción por marca explícita o por pertenencia a la lista negra
        if not padre_id or padre_id in ["master", "raiz", "", "nan"]:
            return None, []
            
        if padre_id in NODOS_MAESTROS_SISTEMA:
            print(f"🛑 Contención activada: Se bloqueó el ascenso hacia el Nodo Maestro: '{padre_id}'")
            return None, [] 
            
        if padre_id in JERARQUIA_GEOGRAFICA:
            return padre_id, JERARQUIA_GEOGRAFICA[padre_id]["sinonimos"]
            
    return None, []

# ==============================================================================
# MOTOR CORE DE BÚSQUEDA POR TIERS
# ==============================================================================
def ejecutar_busqueda_en_base_datos(lista_origen, lista_destino):
    regex_origen = "|".join(lista_origen)
    regex_destino = "|".join(lista_destino)

    # TIER 1: Coincidencia Estructural Directa
    df_res = df_master[
        df_master['zona_origen'].astype(str).str.lower().str.contains(regex_origen, regex=True, na=False) &
        df_master['zona_destino'].astype(str).str.lower().str.contains(regex_destino, regex=True, na=False)
    ]
    if not df_res.empty: return df_res, "directo"

    # TIER 2: Coincidencia Estructural Inversa
    df_res = df_master[
        df_master['zona_origen'].astype(str).str.lower().str.contains(regex_destino, regex=True, na=False) &
        df_master['zona_destino'].astype(str).str.lower().str.contains(regex_origen, regex=True, na=False)
    ]
    if not df_res.empty: return df_res, "inverso"

    # TIER 3: Escaneo Cruzado Global
    bloque_conocimiento = (
        df_master['nombre_variante'].astype(str).str.lower() + " " +
        df_master['zona_origen'].astype(str).str.lower() + " " +
        df_master['zona_destino'].astype(str).str.lower() + " " +
        df_master['descripcion_ux'].astype(str).str.lower()
    )
    if 'contenido_web' in df_master.columns:
        bloque_conocimiento += " " + df_master['contenido_web'].astype(str).str.lower()

    df_res = df_master[
        bloque_conocimiento.str.contains(regex_origen, regex=True, na=False) &
        bloque_conocimiento.str.contains(regex_destino, regex=True, na=False)
    ]
    if not df_res.empty: return df_res, "global"

    return pd.DataFrame(), ""

# ==============================================================================
# LÓGICA LOGÍSTICA DEL WEBHOOK
# ==============================================================================
def procesar_intent_origen_destino(parameters):
    origen_raw = str(parameters.get('Origen') or '').strip().lower()
    destino_raw = str(parameters.get('Destino') or '').strip().lower()
    
    if not origen_raw or not destino_raw:
        return "Por favor, confírmame desde qué lugar partes y hacia cuál te diriges."

    id_orig, syn_orig = obtener_sinonimos_directos(origen_raw)
    id_dest, syn_dest = obtener_sinonimos_directos(destino_raw)

    es_busqueda_fallback = False

    # FASE 1: Nivel Jerárquico Exacto
    df_resultado, tier_exito = ejecutar_busqueda_en_base_datos(syn_orig, syn_dest)

    # FASE 2: Escalabilidad Controlada (Fallback)
    if df_resultado.empty:
        padre_orig_id, padre_orig_syn = obtener_padre_permitido(id_orig)
        padre_dest_id, padre_dest_syn = obtener_padre_permitido(id_dest)

        if padre_orig_id or padre_dest_id:
            fallback_orig = padre_orig_syn if padre_orig_id else syn_orig
            fallback_dest = padre_dest_syn if padre_dest_id else syn_dest
            
            df_resultado, tier_exito = ejecutar_busqueda_en_base_datos(fallback_orig, fallback_dest)
            if not df_resultado.empty:
                es_busqueda_fallback = True

    # GENERADOR DE OUTPUT MULTI-RUTA
    if not df_resultado.empty:
        total_rutas = len(df_resultado)
        
        if es_busqueda_fallback:
            texto_ux = f"🧭 *No encontré tracks específicos para ese punto exacto, pero aquí tienes {total_rutas} alternativas en el sector:* \n\n"
        elif tier_exito == "directo":
            texto_ux = f"🗺️ *He encontrado {total_rutas} alternativas de transporte e indicaciones para ir desde {origen_raw.title()} hacia {destino_raw.title()}:*\n\n"
        elif tier_exito == "inverso":
            texto_ux = f"🔄 *Nota:* Rutas calculadas en sentido inverso. {total_rutas} opciones disponibles para el trayecto:\n\n"
        else:
            texto_ux = f"✨ *Información de rutas referenciales detectadas ({total_rutas} opciones):*\n\n"

        for indice, (_, registro) in enumerate(df_resultado.iterrows(), 1):
            nombre = registro.get('nombre_variante', f'Variante {indice}')
            origen_fijo = registro.get('zona_origen', 'Origen')
            destino_fijo = registro.get('zona_destino', 'Destino')
            modo = registro.get('modo', 'No especificado')
            distancia = registro.get('distancia_km', 'N/A')
            
            tiempo_raw = registro.get('tiempo_min', np.nan)
            tiempo = f"{int(tiempo_raw)} min" if pd.notna(tiempo_raw) and str(tiempo_raw).replace('.0','').isdigit() else "Tiempo no registrado"
            
            dificultad = registro.get('dificultad', 'Moderada')
            descripcion = registro.get('descripcion_ux', '')
            url_mapa = registro.get('url', '')

            texto_ux += f"--- 🗺️ *Opción {indice}: {nombre}* ---\n"
            texto_ux += f"📍 *Eje Geográfico:* {origen_fijo} ➡️ {destino_fijo}\n"
            texto_ux += f"🚗 *Modo:* {modo} | 📏 *Distancia:* {distancia} KM | ⏱️ *Duración:* {tiempo}\n"
            texto_ux += f"🥾 *Dificultad:* {dificultad}\n"
            texto_ux += f"📝 *Indicaciones:* {descripcion}\n"
            
            if url_mapa and str(url_mapa).strip() and url_mapa != "nan":
                texto_ux += f"🔗 *Ver mapa:* {url_mapa}\n"
            texto_ux += "\n"

        return texto_ux.strip()
    else:
        return f"Lo siento, no tengo registrada ninguna conexión o ruta logística entre '{origen_raw}' y '{destino_raw}' en el catálogo actual."

@app.route('/webhook', methods=['POST'])
def procesamiento_intents():
    try:
        payload = request.get_json(silent=True, force=True) or {}
        query_result = payload.get('queryResult', {})
        intent_name = query_result.get('intent', {}).get('displayName', '')
        parameters = query_result.get('parameters', {})
        
        if intent_name == "buscar-origen-destino":
            respuesta_final = procesar_intent_origen_destino(parameters)
        else:
            respuesta_final = "Webhook activo y respondiendo."

        return jsonify({"fulfillmentText": respuesta_final})
    except Exception as e:
        return jsonify({"fulfillmentText": f"⚙️ Error interno en el servidor: {str(e)}."})

if __name__ == '__main__':
    app.run(port=5000, debug=True)