# -*- coding: utf-8 -*-
"""
ORQUESTADOR CONVERSACIONAL: raton_directo.py
PROPÓSITO: Entorno de pruebas local para Botv02 (Proyecto AI_RMinca).
           Utiliza el SDK moderno 'google.genai' con soporte de Tools
           y control estricto de vocabulario en RAM estática.
LOGS: Ejecución unbuffered (-u) con trazabilidad total en la consola de comandos.
ÚLTIMA MODIFICACIÓN: 2026-06-23T19:42:00-05:00
"""
import os
import sys
from google import genai
from google.genai import types

# Importación nativa de la estructura real diseñada en core/
from core.geo_manager import CatalogoRutas
from handlers.interes_zona import buscar_rutas_por_interes_y_zona

# Forzar salida no bufferizada para monitoreo en tiempo real
sys.stdout.reconfigure(line_buffering=True)

# =====================================================================
# 1. INITIALIZATION DE LA MATRIZ DE CONOCIMIENTO (RAM ESTÁTICA)
# =====================================================================
# Forzamos la carga analítica del JSON maestro y el Excel antes de llamar a la API
carga_exitosa = CatalogoRutas.cargar_componentes()

if not carga_exitosa:
    print("❌ [ERROR CRÍTICO]: No se pudieron cargar los componentes en la RAM. Abortando.", file=sys.stderr, flush=True)
    sys.exit(1)

# Recuperamos la matriz ya aplanada para verificar la consistencia del laboratorio
df_verificacion = CatalogoRutas.obtener_matriz()
if df_verificacion.empty:
    print("⚠️ [ALERTA]: La matriz de CatalogoRutas se encuentra vacía tras la inicialización.", flush=True)

# =====================================================================
# 2. CONFIGURACIÓN DEL CLIENTE API GEMINI (SDK MODERNO)
# =====================================================================
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("❌ [ERROR CRÍTICO]: La variable de entorno GEMINI_API_KEY no está definida.", file=sys.stderr, flush=True)
    sys.exit(1)

# Inicialización estándar del cliente global
client = genai.Client(api_key=API_KEY)

system_instruction = (
    "Eres 'ratondeminca' (Botv02), un Ingeniero de Guianza de Inteligencia Artificial experto en la Sierra Nevada.\n"
    "Tu objetivo es guiar al usuario utilizando un vocabulario controlado basado estrictamente en el retorno de tus herramientas.\n\n"
    
    "PROHIBICIÓN ABSOLUTA:\n"
    "No inventes, deduzcas ni presupongas rutas, tags o corregimientos que no estén explícitamente en el JSON devuelto por Python.\n\n"
    
    "REGLA DE INYECCIÓN MAPA INTERACTIVO (UX FLUIDA):\n"
    "Cada vez que la herramienta 'buscar_rutas_por_interes_y_zona' te responda con los estados:\n"
    "'radiografia_completa', 'requieres_interes' o 'no_coincide_carta',\n"
    "significa que el usuario está explorando o no conoce los límites del territorio.\n"
    "Estás OBLIGADO a incluir textualmente en tu respuesta el enlace del mapa de sectores oficial:\n"
    "https://sites.google.com/site/ratondeminca/lugares-places (etiquétalo de forma natural como 'Mapa de Sectores Oficial').\n\n"
    
    "MANEJO DE ESTADOS DE LA CARTA (EL RESTAURANTE):\n"
    "1. Si estado == 'radiografia_completa': Recibirás el diccionario 'carta_territorial'. Organiza una respuesta elegante "
    "y estructurada por corregimientos (ej: En BONDA puedes realizar..., mientras que en MINCA encontrarás...). Muestra el "
    "Mapa de Sectores Oficial para que el usuario haga clic, se ubique visualmente y elija su zona.\n"
    "2. Si estado == 'requiere_interes' o 'no_coincide_carta': Explica amablemente que para la zona elegida, la 'carta real' "
    "de atractivos se limita a los elementos de 'carta_disponible'. Despliégalos con viñetas claras y emojis. "
    "Recuérdale explícitamente al turista que puede seleccionar un ítem, combinar varios o pedirlos TODOS para su caminata.\n\n"
    
    "REGLAS DE HOMOLOGACIÓN SEMÁNTICA:\n"
    "Si el usuario usa frases complejas o adjetivos de antigüedad (ej: 'caminos ancestrales', 'caminos de piedra', 'ruinas indigenas'), "
    "debes mapear esos conceptos directamente al token controlado: 'arqueologia'.\n"
    "Si detectas exclusiones o vedas explícitas (ej: 'pero NO de montaña', 'sin ir al tayrona', 'que no sea playa'), "
    "inyecta el núcleo de la negación en minúsculas y sin tildes en el parámetro 'excluir'."
)

# Configuración combinada bajo el estándar estricto de google.genai
config = types.GenerateContentConfig(
    temperature=0.2,
    top_p=0.95,
    system_instruction=system_instruction,
    tools=[buscar_rutas_por_interes_y_zona],
)

# Forzamos el uso de la versión de última generación de Flash
chat = client.chats.create(model="gemini-2.5-flash", config=config)

# =====================================================================
# 3. BUCLE PRINCIPAL DE INTERACCIÓN (LABORATORIO DE ESTRÉS)
# =====================================================================
print("=====================================================================", flush=True)
print("🤖 Botv02 (ratondeminca) EN LÍNEA - MOTOR GEMINI 2.5 FLASH", flush=True)
print("   Escribe 'salir' para cerrar el entorno de pruebas local.", flush=True)
print("=====================================================================\n", flush=True)

while True:
    try:
        user_input = input("👤 Usuario: ")
        if user_input.strip().lower() == "salir":
            print("\n👋 Cerrando el laboratorio de pruebas local. ¡Cambio y fuera!", flush=True)
            break
            
        if not user_input.strip():
            continue

        response = chat.send_message(user_input)
        print(f"\n🤖 Botv02: {response.text}")
        print("-" * 70 + "\n", flush=True)

    except KeyboardInterrupt:
        print("\n\n👋 Interrupción detectada. Saliendo del laboratorio...", flush=True)
        break
    except Exception as e:
        print(f"\n❌ [ERROR EN CICLO DE CHAT]: {str(e)}\n", file=sys.stderr, flush=True)