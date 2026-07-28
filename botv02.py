# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
SERVIDOR PRINCIPAL: botv02.py (Edición de Diagnóstico Forzado)
"""
# IMPORTS CRÍTICOS NATIVOS PRIMERO (Para registrar el canal de salida de Windows)
import sys
import os
print("1. [DIAGNÓSTICO] Sistema operativo y canales base cargados.", file=sys.stderr, flush=True)

# Forzamos a Python a ignorar errores de hilos en segundos planos de librerías externas
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"

try:
    from flask import Flask, request, jsonify
    print("2. [DIAGNÓSTICO] Flask importado correctamente.", file=sys.stderr, flush=True)
except Exception as e:
    print(f"❌ Error al importar Flask: {e}", file=sys.stderr, flush=True)
    sys.exit(1)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("\n📥 [BOTv02] Nueva petición HTTP POST desde Dialogflow...", file=sys.stderr, flush=True)
    
    try:
        request_body = request.get_json(force=True)
        
        # 1. Extraemos el nombre exacto del Intent que se activó en Dialogflow
        intent_name = request_body.get("queryResult", {}).get("intent", {}).get("displayName", "").strip()
        print(f"🎯 [BOTv02] Intent recibido: '{intent_name}'", file=sys.stderr, flush=True)
        
        # Inicializamos la variable que guardará la respuesta del handler elegido
        respuesta_dict = {}

        # =====================================================================
        # MATRIZ DE ENRUTAMIENTO (Condicionales según el Intent)
        # =====================================================================
        
        # CASO 1: El usuario busca rutas filtrando por perfil, dificultad o tiempo
        if intent_name == "buscar_por_perfil_y_filtro":
            print("🔀 [BOTv02] Enrutando hacia -> handlers/perfil_filtro.py", file=sys.stderr, flush=True)
            from handlers.perfil_filtro import resolver_intencion
            respuesta_dict = resolver_intencion(request_body)
            
        # CASO 2: El usuario pregunta explícitamente por un trayecto de un punto A a un punto B
        elif intent_name == "buscar-origen-destino":
            print("🔀 [BOTv02] Enrutando hacia -> handlers/origen_destino.py", file=sys.stderr, flush=True)
            # Aquí importamos el handler específico que maneja trayectos (ejemplo de nombre de archivo y función)
            from handlers.origen_destino import resolver_intencion
            respuesta_dict = resolver_intencion(request_body)
            
        # CASO 3: El usuario quiere saber qué senderos hay disponibles en un área macro completa
        elif intent_name == "buscar_por_zona":
            print("🔀 [BOTv02] Enrutando hacia -> handlers/por_zona.py", file=sys.stderr, flush=True)
            # Aquí importamos el handler específico que busca por áreas geográficas macros
            from handlers.por_zona import resolver_busqueda_zona
            respuesta_dict = resolver_busqueda_zona(request_body)
        elif intent_name == "buscar_por_interes_zona":
            print("🔀 [BOTv02] Enrutando hacia -> handlers/interes_zona.py", file=sys.stderr, flush=True)
            # Aquí importamos el handler específico que busca por áreas geográficas macros
            from handlers.interes_zona import resolver_intencion
            respuesta_dict = resolver_intencion(request_body)    
        # CASO CONFIGURABLE: Por si Dialogflow activa un intent que olvidaste programar en Python
        else:
            print(f"⚠️ [BOTv02] Advertencia: El intent '{intent_name}' llegó al webhook pero no tiene un handler asignado en Python.", file=sys.stderr, flush=True)
            respuesta_dict = {
                "fulfillmentText": f"El sistema entendió tu intención ({intent_name}), pero la lógica de respuesta aún no está enlazada en el servidor local."
            }

        # Devolvemos la respuesta del handler seleccionado empaquetada en JSON
        return jsonify(respuesta_dict)
        
    except Exception as e:
        print(f"❌ [BOTv02] Error crítico en la ejecución del Webhook: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            "fulfillmentText": "Ocurrió un inconveniente de enrutamiento en el servidor del bot."
        })

# =====================================================================
# EL NUEVO ARRANQUE BLINDADO
# =====================================================================
if __name__ == "__main__":
    print("\n==================================================================", flush=True)
    print("⏳ [BOTv02] ARRANQUE: Iniciando inicialización...", flush=True)
    print("==================================================================", flush=True)
    
    # RETRASO DE IMPORTACIÓN: No importamos geo_manager arriba, lo hacemos 
    # únicamente dentro del bloque principal para aislar su espacio de memoria.
    try:
        print("⏳ [BOTv02] Intentando importar 'core.geo_manager' de forma aislada...", flush=True)
        from core.geo_manager import CatalogoRutas
        print("✅ [BOTv02] Módulo 'core.geo_manager' importado en memoria.", flush=True)
        
        print("⏳ [BOTv02] Invocando 'CatalogoRutas.cargar_componentes()'...", flush=True)
        
        # Ejecutamos el método
        base_datos_lista = CatalogoRutas.cargar_componentes()
        
        print(f"📊 [BOTv02] Retorno del método recibido. Valor: {base_datos_lista}", flush=True)
        
        if base_datos_lista:
            print("\n🚀 [BOTv02] Servidor Flask encendido en el puerto 5000...", flush=True)
            app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        else:
            print("\n❌ [BOTv02] La carga devolvió False.", flush=True)
            
    except BaseException as e:
        # Usamos BaseException para atrapar fallos del sistema que un Exception normal ignora
        print(f"\n💥 [CRASH DETECTADO] El proceso colapsó debido a: {type(e).__name__} - {str(e)}", flush=True)
        import traceback
        traceback.print_exc(file=sys.stdout)