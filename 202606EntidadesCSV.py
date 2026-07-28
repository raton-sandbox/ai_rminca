# Trasladar entidades desde hoja excel Raton de Minca
# 2026-JN-10
# Ejecutar python D:/AI_RMinca/202606EntidadesCSV.py
# Archivos Txt de salida
# Archivo excel de entrada D:/AI_RMinca/catalogo_rutas.xlsx

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MÓDULO: botv01.py
DESCRIPCIÓN: Webhook central en Flask para Dialogflow ES - Proyecto Ratón de Minca.
ARQUITECTURA: Procesamiento vectorial defensivo e in-memory con Pandas.
PRESIÓN DE DATOS: Carga ~200 ítems desde el catálogo de rutas externo (Excel).
"""

import os
import sys
import traceback
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify

# ==============================================================================
# CONFIGURACIÓN GLOBAL DE ARCHIVOS DE ENTRADA (FUENTES DE VERDAD)
# ==============================================================================
RUTA_MAESTRA = r"D:\AI_RMinca\conocimiento_maestro.json"
RUTA_JERARQUIA_EXCEL = r"D:\AI_RMinca\catalogo_rutas.xlsx"
HOJA_JERARQUIA = "Jerarquia_Geografica"

app = Flask(__name__)

# ==============================================================================
# CARGA E INGESTIÓN DE LA ONTOLOGÍA GEOGRÁFICA (EXCEL)
# ==============================================================================
def cargar_ontologia_geografica_desde_excel():
    """
    Lee la pestaña 'Jerarquia_Geografica' del catálogo de rutas en Excel
    y construye dinámicamente el árbol jerárquico de nodos en la RAM.
    """
    print(f"📁 Cargando catálogo geográfico desde: {RUTA_JERARQUIA_EXCEL} [{HOJA_JERARQUIA}]...")
    if not os.path.exists(RUTA_JERARQUIA_EXCEL):
        print(f"⚠️ ADVERTENCIA: No se encontró el catálogo en {RUTA_JERARQUIA_EXCEL}. Jerarquía desactivada.")
        return {}

    try:
        # Carga explícita apuntando a la pestaña solicitada
        df_geo = pd.read_excel(RUTA_JERARQUIA_EXCEL, sheet_name=HOJA_JERARQUIA)
        
        # Sanitización estricta de strings para evitar fallos por espacios o mayúsculas
        df_geo['zona'] = df_geo['zona'].astype(str).str.strip().str.lower()
        df_geo['padre'] = df_geo['padre'].fillna("").astype(str).str.strip().str.lower()
        df_geo['sinonimos'] = df_geo['sinonimos'].fillna("").astype(str).str.strip().str.lower()

        diccionario_jerarquia = {}

        # Paso 1: Mapear IDs de zonas y sus sinónimos vectoriales
        for _, fila in df_geo.iterrows():
            zona_id = fila['zona']
            if not zona_id or zona_id == "nan":
                continue
                
            # Convertimos la celda de sinónimos en una lista limpia
            lista_sinonimos = [s.strip() for s in fila['sinonimos'].split(',') if s.strip()]
            if zona_id not in lista_sinonimos:
                lista_sinonimos.append(zona_id)

            diccionario_jerarquia[zona_id] = {
                "padre": fila['padre'] if fila['padre'] != "" and fila['padre'] != "nan" else None,
                "sinonimos": lista_sinonimos,
                "hijos": []
            }

        # Paso 2: Tejer la red de dependencias (Padres -> Hijos)
        for zona_id, metadata in diccionario_jerarquia.items():
            padre_id = metadata["padre"]
            if padre_id and padre_id in diccionario_jerarquia:
                diccionario_jerarquia[padre_id]["hijos"].append(zona_id)

        print(f"✅ Ontología procesada: {len(diccionario_jerarquia)} nodos geográficos cargados en memoria.")
        return diccionario_jerarquia

    except Exception as e:
        print(f"❌ CRÍTICO: Error al digerir la pestaña {HOJA_JERARQUIA}: {str(e)}")
        traceback.print_exc()
        return {}

# ==============================================================================
# CARGA Y NORMALIZACIÓN DEL ARCHIVO CONOCIMIENTO MAESTRO (JSON)
# ==============================================================================
def inicializar_fuente_verdad():
    """
    Carga el JSON maestro de rutas y normaliza tipos de datos mixtos en RAM.
    """
    print("🚀 Inicializando el Motor de Datos de Rutas...")
    if not os.path.exists(RUTA_MAESTRA):
        print(f"❌ CRÍTICO: No se encontró el archivo maestro en: {RUTA_MAESTRA}")
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

        # Inmunización de tipados
        columnas_numericas = ['distancia_km', 'tiempo_min', 'ascenso_mt', 'descenso_mt']
        for col in columnas_numericas:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')

        if 'circular' in df_final.columns:
            df_final['circular'] = df_final['circular'].replace("", False).astype(bool)

        if 'conecta_con' in df_final.columns:
            df_final['conecta_con'] = df_final['conecta_con'].apply(lambda x: [] if x == "" else (x if isinstance(x, list) else [str(x)]))

        if 'descripcion_ux' in df_final.columns:
            df_final['descripcion_ux'] = df_final['descripcion_ux'].fillna("").str.strip()
            df_final.loc[df_final['descripcion_ux'] == "", 'descripcion_ux'] = "Detalles logísticos de este sendero en proceso de actualización."

        print(f"✅ ÉXITO: Base de conocimiento de rutas lista ({len(df_final)} variantes).")
        return df_final

    except Exception as error:
        print(f"❌ CRÍTICO: Error en ingeniería de datos del JSON: {str(error)}")
        return pd.DataFrame()

# Carga e inmunización única en el arranque del servidor local
JERARQUIA_GEOGRAFICA = cargar_ontologia_geografica_desde_excel()
df_master = inicializar_fuente_verdad()

# ==============================================================================
# ASISTENTE DE EXPANSIÓN GEOGRÁFICA
# ==============================================================================
def obtener_linaje_geografico(zona_solicitada: str) -> list:
    zona = zona_solicitada.strip().lower()
    terminos_finales = [zona]
    nodo_encontrado = None

    # Identificar el nodo raíz correspondiente por sinónimo
    for nodo_id, data in JERARQUIA_GEOGRAFICA.items():
        if zona in data["sinonimos"] or zona == nodo_id:
            nodo_encontrado = nodo_id
            terminos_finales.extend(data["sinonimos"])
            break

    # Resolver descendencia (Hijos y Nietos) para abarcar el catálogo extendido
    if nodo_encontrado:
        hijos_directos = JERARQUIA_GEOGRAFICA[nodo_encontrado]["hijos"]
        for hijo in hijos_directos:
            if hijo in JERARQUIA_GEOGRAFICA:
                terminos_finales.extend(JERARQUIA_GEOGRAFICA[hijo]["sinonimos"])
                nietos = JERARQUIA_GEOGRAFICA[hijo]["hijos"]
                for nieto in nietos:
                    if nieto in JERARQUIA_GEOGRAFICA:
                        terminos_finales.extend(JERARQUIA_GEOGRAFICA[nieto]["sinonimos"])

    return list(dict.fromkeys([t for t in terminos_finales if t]))

# ==============================================================================
# LÓGICA DE CONSULTA POR DIALOGFLOW
# ==============================================================================
def procesar_intent_origen_destino(parameters):
    origen_raw = str(parameters.get('origen') or parameters.get('Zona_origen') or '').strip().lower()
    destino_raw = str(parameters.get('destino') or parameters.get('Zona_destino') or '').strip().lower()
    
    if not origen_raw or not destino_raw:
        return "Por favor, confírmame tu punto de partida y a dónde deseas ir."

    origen_expandido = obtener_linaje_geografico(origen_raw)
    destino_expandido = obtener_linaje_geografico(destino_raw)
    
    regex_origen = "|".join(origen_expandido)
    regex_destino = "|".join(destino_expandido)

    df_resultado = pd.DataFrame()
    es_ruta_inversa = False
    tier_exito = ""

    # TIER 1: Coincidencia Estructural Directa
    df_resultado = df_master[
        df_master['zona_origen'].astype(str).str.lower().str.contains(regex_origen, regex=True, na=False) &
        df_master['zona_destino'].astype(str).str.lower().str.contains(regex_destino, regex=True, na=False)
    ]
    if not df_resultado.empty: tier_exito = "directo"

    # TIER 2: Coincidencia Estructural Inversa
    if df_resultado.empty:
        df_resultado = df_master[
            df_master['zona_origen'].astype(str).str.lower().str.contains(regex_destino, regex=True, na=False) &
            df_master['zona_destino'].astype(str).str.lower().str.contains(regex_origen, regex=True, na=False)
        ]
        if not df_resultado.empty:
            es_ruta_inversa = True
            tier_exito = "inverso"

    # TIER 3: Escaneo Cruzado en Bloques de Texto Completos
    if df_resultado.empty:
        bloque_conocimiento = (
            df_master['nombre_variante'].astype(str).str.lower() + " " +
            df_master['zona_origen'].astype(str).str.lower() + " " +
            df_master['zona_destino'].astype(str).str.lower() + " " +
            df_master['descripcion_ux'].astype(str).str.lower()
        )
        if 'contenido_web' in df_master.columns:
            bloque_conocimiento += " " + df_master['contenido_web'].astype(str).str.lower()

        df_resultado = df_master[
            bloque_conocimiento.str.contains(regex_origen, regex=True, na=False) &
            bloque_conocimiento.str.contains(regex_destino, regex=True, na=False)
        ]
        if not df_resultado.empty: tier_exito = "global"

    # OUTPUT GENERATOR
    if not df_resultado.empty:
        registro = df_resultado.iloc[0]
        nombre = registro.get('nombre_variante', 'Variante General')
        origen_fijo = registro.get('zona_origen', 'Origen')
        destino_fijo = registro.get('zona_destino', 'Destino')
        modo = registro.get('modo', 'No especificado')
        distancia = registro.get('distancia_km', 'N/A')
        tiempo_raw = registro.get('tiempo_min', np.nan)
        tiempo = f"{int(tiempo_raw)} min" if pd.notna(tiempo_raw) and str(tiempo_raw).replace('.0','').isdigit() else "Tiempo estimado no registrado"
        dificultad = registro.get('dificultad', 'Moderada')
        descripcion = registro.get('descripcion_ux', '')
        url_mapa = registro.get('url', '')

        if tier_exito == "directo":
            encabezado = f"📍 *{nombre}*\n🗺️ *Trayecto:* {origen_fijo} ➡️ {destino_fijo}\n"
        elif tier_exito == "inverso":
            encabezado = f"📍 *{nombre}*\n🔄 *Nota:* Trayecto calculado en sentido inverso.\n🗺️ *Trayecto:* {origen_fijo} ➡️ {destino_fijo}\n"
        else:
            encabezado = f"✨ *Información Logística Encontrada:* {nombre}\n🗺️ *Eje de Conexión:* {origen_fijo} ➡️ {destino_fijo}\n"

        texto_ux = (f"{encabezado}🚗 *Modo:* {modo}\n📏 *Distancia:* {distancia} KM\n⏱️ *Duración:* {tiempo}\n🥾 *Dificultad:* {dificultad}\n\n📝 *Indicaciones:*\n{descripcion}")
        if url_mapa and str(url_mapa).strip() and url_mapa != "nan":
            texto_ux += f"\n\n🔗 Ver mapa de referencia: {url_mapa}"
        return texto_ux
    else:
        return f"No tengo registrada una ruta directa o conexiones lógicas entre '{origen_raw}' y '{destino_raw}' en el catálogo actual."

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
            respuesta_final = "Webhook activo, listo para servir consultas de rutas."

        return jsonify({"fulfillmentText": respuesta_final})
    except Exception as e:
        return jsonify({"fulfillmentText": f"⚙️ Error interno en el servidor: {str(e)}."})

if __name__ == '__main__':
    app.run(port=5000, debug=True)