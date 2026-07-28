# -*- coding: utf-8 -*-
"""
Módulo de Herramienta: Filtro por Origen y Destino Geográfico (Algoritmo Bidireccional)
Versión: 4.8.0 - Lógica de Expansión Basada en Estructura Real de Dos Niveles
Timestamp: 2026-06-27T13:28:00-05:00
"""
import pandas as pd
from core.geo_manager import CatalogoRutas

def buscar_rutas_origen_destino(origen_usuario: str, destino_usuario: str) -> dict:
    """
    Handler determinista para dos niveles geográficos. Si la zona consultada
    posee subzonas asociadas en la columna 'padre', expande la búsqueda a sus hijos.
    """
    zona_orig_clean = CatalogoRutas.normalizar_entidad_geografica(origen_usuario).strip().lower()
    zona_dest_clean = CatalogoRutas.normalizar_entidad_geografica(destino_usuario).strip().lower()

    if zona_orig_clean == zona_dest_clean:
        return {"resultado": "1", "rutas": []}

    df_j = CatalogoRutas._hierarchy_data.copy()
    df_m = CatalogoRutas._conocimiento_maestro.copy()

    # Normalización higiénica para comparación en Pandas
    df_j['zona_clean'] = df_j['zona'].astype(str).str.strip().str.lower()
    df_j['padre_clean'] = df_j['padre'].astype(str).str.strip().str.lower()
    df_j['sinonimos_clean'] = df_j['sinonimos'].astype(str).str.strip().str.lower()

    # Buscar los registros de origen y destino en el dataframe de jerarquías
    match_origen = df_j[df_j['zona_clean'] == zona_orig_clean]
    if match_origen.empty:
        match_origen = df_j[df_j['sinonimos_clean'].str.contains(zona_orig_clean, na=False, regex=False)]

    match_destino = df_j[df_j['zona_clean'] == zona_dest_clean]
    if match_destino.empty:
        match_destino = df_j[df_j['sinonimos_clean'].str.contains(zona_dest_clean, na=False, regex=False)]

    if match_origen.empty or match_destino.empty:
        return {"resultado": "2", "rutas": []}

    # -------------------------------------------------------------------------
    # REGLA b: Procesamiento e Inyección del Nodo Origen e Hijos
    # -------------------------------------------------------------------------
    nodos_origen = []
    zona_origen_base = str(match_origen.iloc[0]['zona_clean']).strip()
    nodos_origen.append(zona_origen_base)

    # REGLA LOGICA DE DOS NIVELES: Buscamos si la zona actual es 'padre' de subzonas
    hijos_origen = df_j[df_j['padre_clean'] == zona_origen_base]['zona_clean'].tolist()
    for hijo in hijos_origen:
        if hijo not in nodos_origen:
            nodos_origen.append(hijo)

    # -------------------------------------------------------------------------
    # REGLA c: Procesamiento e Inyección del Nodo Destino e Hijos
    # -------------------------------------------------------------------------
    nodos_destino = []
    zona_destino_base = str(match_destino.iloc[0]['zona_clean']).strip()
    nodos_destino.append(zona_destino_base)

    # Buscamos si la zona destino actúa como padre en el catálogo
    hijos_destino = df_j[df_j['padre_clean'] == zona_destino_base]['zona_clean'].tolist()
    for hijo in hijos_destino:
        if hijo not in nodos_destino:
            nodos_destino.append(hijo)

    # -------------------------------------------------------------------------
    # FILTRADO MATRICIAL EN CONOCIMIENTO MAESTRO
    # -------------------------------------------------------------------------
    df_m['zona_origen_clean'] = df_m['zona_origen'].astype(str).str.strip().str.lower()
    df_m['zona_destino_clean'] = df_m['zona_destino'].astype(str).str.strip().str.lower()
    df_m['id_ruta_clean'] = df_m['id_ruta'].astype(str).str.strip()

    # Evaluación cruzada bidireccional empleando conjuntos calculados (.isin)
    mascara_directa = (df_m['zona_origen_clean'].isin(nodos_origen)) & (df_m['zona_destino_clean'].isin(nodos_destino))
    interseccion_final = df_m[mascara_directa]['id_ruta_clean'].tolist()

    mascara_inversa = (df_m['zona_origen_clean'].isin(nodos_destino)) & (df_m['zona_destino_clean'].isin(nodos_origen))
    interseccion_inversa = df_m[mascara_inversa]['id_ruta_clean'].tolist()
    
    rutas_totales = list(set(interseccion_final + interseccion_inversa))

    if len(rutas_totales) == 0:
        return {"resultado": "2", "rutas": []}
    else:
        return {"resultado": "0", "rutas": rutas_totales}