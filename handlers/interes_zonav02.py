# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
HANDLER: interes_zona.py
PROPÓSITO: Filtrar rutas con validación de zona y trazabilidad de memoria.
"""
import sys
from core.geo_manager import CatalogoRutas, sanitizar_cadena

def resolver_intencion(request_body):
    print("🚀 [INTERES_ZONA] Iniciando ejecución de lógica...", file=sys.stderr)
    
    try:
        # 1. Acceso a la RAM
        df = CatalogoRutas.obtener_matriz()
        if df.empty:
            print("❌ [INTERES_ZONA] Error: La matriz en RAM está vacía.", file=sys.stderr)
            return {"fulfillmentText": "Error: Base de datos no cargada."}

        # Volcado de depuración inicial
        print(f"🔍 [DEBUG] RAM total rutas: {len(df)}", file=sys.stderr)
        print(f"🔍 [DEBUG] Columnas disponibles: {df.columns.tolist()}", file=sys.stderr)
        
        # 2. Extracción de parámetros
        params = request_body.get("queryResult", {}).get("parameters", {})
        interes_input = sanitizar_cadena(params.get("Interes", ""))
        zona_param = sanitizar_cadena(params.get("Zona", "")) 
        
        print(f"🔍 [DEBUG] Parametros recibidos: Interes='{interes_input}', Zona='{zona_param}'", file=sys.stderr)

        # 3. Filtrado con seguimiento
        # Filtrado por Zona (Estricto, Case-Insensitive)
        if zona_param:
            df = df[df['area'].str.lower() == zona_param]
            print(f"📊 [DEBUG] Tras filtro Área ('{zona_param}'), quedan: {len(df)} registros.", file=sys.stderr)
        
        # Filtrado por Interés (LIKE sobre string plano)
        filtro_interes = df['intereses_tags'].str.contains(interes_input, case=False, na=False)
        df_resultado = df[filtro_interes]
        
        print(f"📊 [DEBUG] Tras filtro Interés ('{interes_input}'), quedan: {len(df_resultado)} resultados finales.", file=sys.stderr)

        if df_resultado.empty:
            return {"fulfillmentText": f"No encontré rutas para '{interes_input}' en la zona '{zona_param}'."}

        # 4. Construcción de respuesta
        nombres_dinamicos = [
            f"Sendero entre {row['zona_origen']} y {row['zona_destino']}" 
            for _, row in df_resultado.iterrows()
        ]
        
        mensaje = f"He encontrado: {', '.join(nombres_dinamicos[:3])}."
        print(f"✅ [INTERES_ZONA] Respuesta enviada: {mensaje}", file=sys.stderr)
        return {"fulfillmentText": mensaje}

    except Exception as e:
        print(f"❌ [ERROR CRÍTICO] {str(e)}", file=sys.stderr)
        return {"fulfillmentText": "Ocurrió un error interno durante la consulta."}