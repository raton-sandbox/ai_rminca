# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
MÓDULO HANDLERS: handlers/origen_destino.py
PROPÓSITO: Resolver la intención de búsqueda por origen-destino implementando
           un filtrado elástico basado en subcadenas (Lógica difusa tipo LIKE)
           operando con strings puros sin validación de tipos.
"""
import sys
import pandas as pd
from core.geo_manager import CatalogoRutas, sanitizar_cadena

def buscar_rutas_like(origen_usuario, destino_usuario):
    """
    Realiza una búsqueda elástica estilo SQL LIKE de los términos de origen y destino 
    sobre la matriz de datos, combinando las bolsas geográficas expandidas.
    """
    df_maestro = CatalogoRutas.obtener_matriz()
    if df_maestro.empty:
        return []

    # Generar bolsas de expansión geográficas (Nodos + Hijos + Sinónimos)
    bolsa_origen = CatalogoRutas.obtener_toda_la_familia_descendiente(origen_usuario)
    bolsa_destino = CatalogoRutas.obtener_toda_la_familia_descendiente(destino_usuario)

    # Inicializar máscaras booleanas en falso usando el índice del DataFrame
    mascara_origen_like = pd.Series(False, index=df_maestro.index)
    mascara_destino_like = pd.Series(False, index=df_maestro.index)

    # LÓGICA DIFUSA LIKE (OR Iterativo de subcadenas parciales contenidas en la celda)
    for miembro in bolsa_origen:
        miembro_clean = sanitizar_cadena(miembro)
        if miembro_clean:
            mascara_origen_like |= df_maestro['zona_origen'].astype(str).apply(sanitizar_cadena).str.contains(miembro_clean, regex=False)

    for miembro in bolsa_destino:
        miembro_clean = sanitizar_cadena(miembro)
        if miembro_clean:
            mascara_destino_like |= df_maestro['zona_destino'].astype(str).apply(sanitizar_cadena).str.contains(miembro_clean, regex=False)

    # INTERSECCIÓN ELÁSTICA (AND de ambas condiciones vectoriales tipo LIKE)
    df_resultado = df_maestro[mascara_origen_like & mascara_destino_like]
    
    return df_resultado.to_dict(orient="records")

def resolver_intencion(request_body):
    """
    Parsea los parámetros del intent de Dialogflow ES, ejecuta el emparejamiento 
    de cadenas y construye el flujo narrativo de salida enriquecido.
    """
    try:
        query_result = request_body.get("queryResult", {})
        parameters = query_result.get("parameters", {})
        
        # Extracción plana forzando conversión a string puro sin verificar tipos
        origen_raw = parameters.get("zona_origen", "")
        destino_raw = parameters.get("zona_destino", "")
        
        if isinstance(origen_raw, list): 
            origen_raw = origen_raw[0] if origen_raw else ""
        if isinstance(destino_raw, list): 
            destino_raw = destino_raw[0] if destino_raw else ""
            
        origen = str(origen_raw).strip()
        destino = str(destino_raw).strip()

        if not origen or not destino:
            return {
                "fulfillmentText": "Para poder recomendarte la mejor alternativa, confírmame detalladamente tu punto de partida y a qué lugar deseas llegar."
            }

        # Ejecución de la consulta elástica LIKE sobre la matriz RAM
        rutas_encontradas = buscar_rutas_like(origen, destino)

        # TIERS DE CONTINGENCIA GEOGRÁFICA CON ENFOQUE LIKE SI NO HAY RUTA DIRECTA
        if not rutas_encontradas:
            df_maestro = CatalogoRutas.obtener_matriz()
            bolsa_origen = CatalogoRutas.obtener_toda_la_familia_descendiente(origen)
            
            mascara_fallback = pd.Series(False, index=df_maestro.index)
            for miembro in bolsa_origen:
                miembro_clean = sanitizar_cadena(miembro)
                if miembro_clean:
                    mascara_fallback |= df_maestro['zona_origen'].astype(str).apply(sanitizar_cadena).str.contains(miembro_clean, regex=False)
            
            df_alternativas = df_maestro[mascara_fallback]
            
            if not df_alternativas.empty:
                destinos_viables = df_alternativas['zona_destino'].unique()
                sugerencias_str = ", ".join(list(str(d) for d in destinos_viables)[:4])
                
                texto_fallback = (
                    f"No tengo registrada una ruta directa entre '{origen}' y '{destino}'. "
                    f"Sin embargo, veo que desde '{origen}' puedes conectar con estos otros sectores: {sugerencias_str}. "
                    f"¿Te interesaría explorar alguna de estas opciones?"
                )
            else:
                texto_fallback = f"Por el momento no tengo rutas cargadas que inicien en '{origen}' o vayan hacia '{destino}' en mi base de datos."
            
            return {"fulfillmentText": texto_fallback}

        # CONSTRUCCIÓN DEL TEXTO DE RESPUESTA CON VERIFICACIÓN STRING-ONLY
        texto_fulfillment = f"¡Encontré {len(rutas_encontradas)} opción(es) ideales para tu viaje desde {origen} hacia {destino}!\n\n"
        
        for i, ruta in enumerate(rutas_encontradas, 1):
            variante = ruta.get("nombre_variante", "Trayecto General")
            modo = ruta.get("modo", "No especificado")
            distancia = ruta.get("distancia_km", "?")
            dificultad = ruta.get("dificultad", "No especificada")
            costo = ruta.get("costo_estimado_cop_pp", "No determinado")
            descripcion_ux = ruta.get("descripcion_ux", "")
            narrativa = ruta.get("descripcion_narrativa", "")
            
            texto_fulfillment += f"📍 Opción {i}: {variante} ({modo})\n"
            texto_fulfillment += f"   • Trayecto: {ruta.get('zona_origen')} ➡️ {ruta.get('zona_destino')}\n"
            texto_fulfillment += f"   • Info Técnica: {distancia} km | Dificultad: {dificultad} | Costo: {costo}\n"
            
            # Incorporar riqueza empírica y narrativa si existe contenido (tratados como texto puro)
            if descripcion_ux:
                texto_fulfillment += f"   • Resumen logístico: {descripcion_ux}\n"
            if narrativa and narrativa.lower() != "nan" and narrativa != "":
                resumen_historico = narrativa[:180] + "..." if len(narrativa) > 180 else narrativa
                texto_fulfillment += f"   • Detalles del entorno: {resumen_historico}\n"
                
            texto_fulfillment += "\n"

        return {
            "fulfillmentText": texto_fulfillment.strip()
        }

    except Exception as error:
        print(f"❌ [FALLO CONTROLADO] Error en handlers/origen_destino.py (Módulo LIKE): {str(error)}", file=sys.stderr)
        return {
            "fulfillmentText": "Surgió un inconveniente en el servidor al procesar la búsqueda parcial de zonas. ¿Podrías indicarme los puntos de nuevo?"
        }