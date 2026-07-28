# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
MÓDULO HANDLERS: handlers/origen_destino.py
PROPÓSITO: Buscador analítico bidireccional (A -> B o B -> A) con inversión 
           dinámica de vectores de desnivel (ascenso/descenso) y generación
           de nombre sintáctico estructurado utilizando 'nombre_variante' como sufijo.
           Actúa como una Tool nativa calificada para el SDK de Gemini.
"""
import sys
import pandas as pd
from typing import Dict, Any, List, Optional
from core.geo_manager import CatalogoRutas, sanitizar_cadena

def _construir_nombre_ruta(origen: str, destino: str, nombre_variante_raw: Any) -> str:
    """
    Función helper interna para unificar la regla de nomenclatura:
    'Desde Origen hasta Destino' y opcionalmente ' - [Sufijo de Variante]' 
    si la columna 'nombre_variante' contiene un valor válido y no genérico.
    """
    base = f"Desde {origen} hasta {destino}"
    
    # Validación defensiva del contenido de la columna nombre_variante
    if pd.notna(nombre_variante_raw):
        v_str = str(nombre_variante_raw).strip()
        # Si tiene contenido real y no es un marcador genérico por defecto
        if v_str and v_str.lower() not in ['nan', 'none', '', 'trayecto general', 'general', 'default']:
            return f"{base} - {v_str}"
            
    return base

def buscar_trayecto_origen_destino(
    origen: str,
    destino: str
) -> Dict[str, Any]:
    """
    Busca de forma analítica y bidireccional rutas en el catálogo que conecten 
    dos puntos geográficos. Invierte dinámicamente los desniveles y reconstruye 
    el nombre del sendero siguiendo la estructura 'Desde [Origen] hasta [Destino] - [nombre_variante]'.

    Args:
        origen: Nombre del lugar, vereda o hito geográfico de partida (ej. 'Minca', 'Gaira').
        destino: Nombre del lugar o atractivo natural de llegada (ej. 'Gaira', 'Minca').

    Returns:
        Dict[str, Any]: Estructura de datos con las rutas adaptadas vectorialmente y nombres dinámicos.
    """
    print(f"⚡ [LOG LOCAL] Invocando 'buscar_trayecto_origen_destino' (Key: nombre_variante)", file=sys.stderr, flush=True)
    print(f"🔍 [PARÁMETROS] Solicitado: '{origen}' -> '{destino}'", file=sys.stderr, flush=True)

    df_maestro = CatalogoRutas.obtener_matriz()
    if df_maestro.empty:
        return {"estado": "vacio", "datos": []}

    origen_clean = sanitizar_cadena(origen)
    destino_clean = sanitizar_cadena(destino)

    if not origen_clean or not destino_clean:
        return {"estado": "vacio", "datos": []}

    # 1. NORMALIZACIÓN DE COLUMNAS PARA COMPARACIÓN VECTORIAL
    series_origen_db = df_maestro['zona_origen'].astype(str).apply(sanitizar_cadena)
    series_destino_db = df_maestro['zona_destino'].astype(str).apply(sanitizar_cadena)

    # ESPACIO VECTORIAL DE BÚSQUEDA (Directo e Inverso)
    mascara_sentido_directo = (series_origen_db.str.contains(origen_clean, regex=False)) & \
                              (series_destino_db.str.contains(destino_clean, regex=False))

    mascara_sentido_inverso = (series_origen_db.str.contains(destino_clean, regex=False)) & \
                              (series_destino_db.str.contains(origen_clean, regex=False))

    # 2. FILTRADO COLECTIVO EN RAM
    df_directo = df_maestro[mascara_sentido_directo].copy()
    df_inverso = df_maestro[mascara_sentido_inverso].copy()

    rutas_formateadas = []

    # 3. PROCESAMIENTO DE RUTAS EN SENTIDO DIRECTO
    for _, fila in df_directo.iterrows():
        zo_tit = str(fila.get("zona_origen", "")).title()
        zd_tit = str(fila.get("zona_destino", "")).title()
        
        # Pasamos el valor original de la columna nombre_variante al constructor de nombres
        nombre_dinamico = _construir_nombre_ruta(zo_tit, zd_tit, fila.get("nombre_variante"))

        rutas_formateadas.append({
            "id_ruta": str(fila.get("id_ruta", "")),
            "nombre_variante": nombre_dinamico, # Aquí Gemini recibe el nombre UX estructurado completo
            "zona_origen": zo_tit,
            "zona_destino": zd_tit,
            "area": str(fila.get("area", "")).title(),
            "modo": str(fila.get("modo", "Hiking")),
            "distancia_km": str(fila.get("distancia_km", "0")),
            "tiempo_min": str(fila.get("tiempo_min", "0")),
            "dificultad": str(fila.get("dificultad", "Media")),
            "ascenso_mt": str(fila.get("ascenso_mt", "0")),
            "descenso_mt": str(fila.get("descenso_mt", "0")),
            "costo_estimado_cop_pp": str(fila.get("costo_estimado_cop_pp", "Ninguno")),
            "descripcion_ux": str(fila.get("descripcion_ux", "")),
            "url": str(fila.get("url", "")),
            "descripcion_narrativa": str(fila.get("descripcion_narrativa", ""))
        })

    # 4. PROCESAMIENTO DE RUTAS EN SENTIDO INVERSO (Espejo y transposición)
    for _, fila in df_inverso.iterrows():
        zo_original_tit = str(fila.get("zona_origen", "")).title()
        zd_original_tit = str(fila.get("zona_destino", "")).title()
        
        # En sentido inverso, invertimos origen y destino en el texto base, pero mantenemos su variante original
        nombre_dinamico_inverso = _construir_nombre_ruta(zd_original_tit, zo_original_tit, fila.get("nombre_variante"))

        # Transposición física de desniveles
        ascenso_original = str(fila.get("ascenso_mt", "0"))
        descenso_original = str(fila.get("descenso_mt", "0"))

        rutas_formateadas.append({
            "id_ruta": str(fila.get("id_ruta", "")),
            "nombre_variante": nombre_dinamico_inverso,
            "zona_origen": zd_original_tit,  
            "zona_destino": zo_original_tit, 
            "area": str(fila.get("area", "")).title(),
            "modo": str(fila.get("modo", "Hiking")),
            "distancia_km": str(fila.get("distancia_km", "0")),
            "tiempo_min": str(fila.get("tiempo_min", "0")), 
            "dificultad": str(fila.get("dificultad", "Media")),
            "ascenso_mt": descenso_original, 
            "descenso_mt": ascenso_original, 
            "costo_estimado_cop_pp": str(fila.get("costo_estimado_cop_pp", "Ninguno")),
            "descripcion_ux": str(fila.get("descripcion_ux", "")),
            "url": str(fila.get("url", "")),
            "descripcion_narrativa": f"Trayecto consultado en sentido inverso. {str(fila.get('descripcion_narrativa', ''))}"
        })

    total_total = len(rutas_formateadas)
    print(f"📊 [MÉTRICA RAM] Trayectos mapeados con sufijo 'nombre_variante': {total_total}", file=sys.stderr, flush=True)

    if not rutas_formateadas:
        return {"estado": "vacio", "datos": []}

    return {
        "estado": "exitoso",
        "datos": rutas_formateadas
    }