# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Manejador Analítico: Consultor de Rutas por Área Macro
Versión: 3.0.0 - Estandarización de Firmas e Identificadores de Ruta (ID_Ruta)
Timestamp: 2026-07-04T21:42:00-05:00
"""
from core.geo_manager import CatalogoRutas

def obtener_enlaces_por_zona(area_usuario: str) -> dict:
    """
    Filtra el DataFrame Maestro en RAM por la columna 'area' tras normalizar 
    las sinonimias y extrae los IDs de ruta correspondientes.
    
    Args:
        area_usuario (str): Nombre del área o corregimiento consultado por el usuario.
        
    Returns:
        dict: Estructura estandarizada con la lista de id_ruta y el código de control.
              {
                "status": "exito" | "vacio",
                "rutas": list,  # Lista de id_ruta (strings)
                "resultado": "0" | "6"
              }
    """
    # 1. Normalizar la entrada del usuario usando el Singleton Geográfico para resolver sinónimos
    area_oficial = CatalogoRutas.obtener_sinonimos_directos(area_usuario).strip().upper()
    
    df_maestro = CatalogoRutas._conocimiento_maestro
    lista_rutas = []
    
    if df_maestro is not None and not df_maestro.empty:
        # 2. Ejecutar el filtrado matricial en Pandas sobre la columna 'area'
        df_filtrado = df_maestro[df_maestro['area'].astype(str).str.upper() == area_oficial]
        
        # 3. Extraer los IDs únicos de las rutas que pertenecen a dicha área
        if not df_filtrado.empty:
            lista_rutas = df_filtrado['id_ruta'].dropna().unique().tolist()
    
    # Imprimir métricas analíticas en la consola para trazabilidad técnica
    print(f"\n[LOG HANDLER - ZONA INFO]")
    print(f" -> Área solicitada: '{area_usuario}' | Resuelta como: '{area_oficial}'")
    print(f" -> IDs de ruta consolidados: {len(lista_rutas)}")
    
    # 4. Despacho homogeneizado de respuestas y códigos de control del Framework
    if lista_rutas:
        return {
            "status": "exito",
            "rutas": lista_rutas,
            "resultado": "0"
        }
    else:
        return {
            "status": "vacio",
            "rutas": [],
            "resultado": "6"
        }