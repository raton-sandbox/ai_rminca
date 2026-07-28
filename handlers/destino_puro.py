# -*- coding: utf-8 -*-
"""
Handler de Destino Puro: handlers/destino_puro.py
Propósito: Resolver búsquedas directas basadas únicamente en la columna 'zona_destino'.
pregunta tipo como llegar a Pozo Azul?

Timestamp: 2026-07-05T11:45:00-05:00
"""
import pandas as pd
from core.geo_manager import CatalogoRutas

def buscar_por_destino_puro(destino_usuario: str) -> dict:
    """
    Busca un lugar revisando únicamente el ítem 'zona_destino' en conocimiento_maestro.
    
    Retorna:
        dict: {"rutas": list, "resultado": "0" | "7"}
    """
    df_m = CatalogoRutas._conocimiento_maestro
    lista_ids = []
    codigo_resultado = "7"

    if df_m is not None and not df_m.empty and destino_usuario:
        # Limpieza e igualación de cadenas
        destino_oficial = str(destino_usuario).strip().upper()
        
        # Filtrado directo en la columna de destino
        cond_destino = df_m['zona_destino'].astype(str).str.upper() == destino_oficial
        df_coincidencias = df_m[cond_destino]
        
        if not df_coincidencias.empty:
            lista_ids = df_coincidencias['id_ruta'].dropna().unique().tolist()
            codigo_resultado = "0"
            print(f"🎯 [HANDLER DESTINO PURO]: Coincidencia directa para '{destino_usuario}'. {len(lista_ids)} rutas encontradas.")
        else:
                      
            print(f"❌ [HANDLER DESTINO PURO]: Sin coincidencia en 'zona_destino' para '{destino_usuario}'.")

    return {
        "rutas": lista_ids,
        "resultado": codigo_resultado
    }