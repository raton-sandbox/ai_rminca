## -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Módulo de Herramienta: Filtro por Área Geográfica e Intereses/Actividades (Operadores LIKE / NOT LIKE)
Versión: 1.0.0 - Cumplimiento Estricto de Reglas de Asertividad A-F
Timestamp: 2026-06-27T14:05:00-05:00
"""
import pandas as pd
from core.geo_manager import CatalogoRutas

def filtrar_por_interes_zona(zona_usuario: str, interes_usuario: str, es_positiva: bool = True) -> dict:
    """
    Handler analítico para discriminar rutas según el área geográfica y tags de interés.
    Soporta peticiones asertivas positivas (LIKE) y negativas (NOT LIKE).
    
    Parámetros:
    -----------
    zona_usuario : str -> El área por la que indaga el usuario.
    interes_usuario : str -> El tag o actividad enviado por el orquestador.
    es_positiva : bool -> True para inclusión (LIKE), False para exclusión (NOT LIKE).
    """
    # Garantizar la existencia y copia limpia de la base de datos maestra en RAM
    df_m = CatalogoRutas._conocimiento_maestro.copy()
    
    # Normalización higiénica para las columnas de comparación
    df_m['area_clean'] = df_m['area'].astype(str).str.strip().str.lower() if 'area' in df_m.columns else df_m['perfil_ruta'].astype(str).str.strip().str.lower()
    df_m['intereses_tags_clean'] = df_m['intereses_tags'].astype(str).str.strip().str.lower()
    df_m['id_ruta_clean'] = df_m['id_ruta'].astype(str).str.strip()

    zona_clean = zona_usuario.strip().lower()
    interes_clean = interes_usuario.strip().lower()

    # =========================================================================
    # REGLA a: Validación del Área Geográfica Reconocida
    # =========================================================================
    areas_unicas = sorted(df_m['area_clean'].unique())
    
    if zona_clean not in areas_unicas:
        # Imprimir en consola las áreas geográficas únicas en orden alfabético
        areas_print = [a.capitalize() for a in areas_unicas]
        print(f"📊 Areas geograficas reconocidas: {areas_print}")
        return {"resultado": "5", "rutas": []}

    # =========================================================================
    # REGLA b: Segmentación de la Petición Asertiva
    # =========================================================================
    # Filtrar primero la matriz del maestro únicamente por la zona validada
    df_zona = df_m[df_m['area_clean'] == zona_clean]

    if es_positiva:
        # ---------------------------------------------------------------------
        # REGLAS c y d: Petición Positiva - Operador LIKE
        # ---------------------------------------------------------------------
        mascara_like = df_zona['intereses_tags_clean'].str.contains(interes_clean, na=False, regex=False)
        df_resultado = df_zona[mascara_like]
        
        if not df_resultado.empty:
            rutas_validas = df_resultado['id_ruta_clean'].tolist()
            return {"resultado": "0", "rutas": rutas_validas}
        else:
            # -----------------------------------------------------------------
            # REGLA e: Petición Positiva - String NO encontrado (Sugerir conocidos)
            # -----------------------------------------------------------------
            # Extraer, limpiar y ordenar alfabéticamente todos los tags únicos de la zona filtrada
            tags_set = set()
            for row in df_zona['intereses_tags'].dropna():
                sub_tags = [t.strip().capitalize() for t in str(row).split(',') if t.strip()]
                tags_set.update(sub_tags)
            
            tags_ordenados = sorted(list(tags_set))
            
            print(f"⚠️ Para el area que quieres visitar, no se encuentran actividades relevantes de tu interes, etas son las actividades de interes conocidas: {tags_ordenados}")
            return {"resultado": "4", "rutas": []}

    else:
        # ---------------------------------------------------------------------
        # REGLA f: Petición Negativa - Operador NOT LIKE (Ej. "que no tenga rio")
        # ---------------------------------------------------------------------
        mascara_not_like = ~df_zona['intereses_tags_clean'].str.contains(interes_clean, na=False, regex=False)
        df_resultado = df_zona[mascara_not_like]
        
        if not df_resultado.empty:
            rutas_validas = df_resultado['id_ruta_clean'].tolist()
            return {"resultado": "0", "rutas": rutas_validas}
        else:
            # No quedaron rutas tras la exclusión (Ej: pedir exclusión de bosques en una zona donde todo es bosque)
            return {"resultado": "3", "rutas": []}