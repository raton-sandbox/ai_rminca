# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Orquestador Central: raton.py
Versión: 12.0.0 - Sincronización Santa Marta-Urbano y Desempate Vehicular Integrado
Timestamp: 2026-07-03T20:36:00-05:00
"""
import os
import json
import re
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

from core.geo_manager import CatalogoRutas
from handlers.origen_destino import buscar_rutas_origen_destino
from handlers.interes_zona import filtrar_por_interes_zona
from logger_aprendizaje import registrar_interaccion
# Carga las variables del archivo .env si existe en el entorno local
load_dotenv()
# Inicialización del cliente oficial de Groq
# Obtiene la clave de las variables de entorno del sistema o del archivo .env
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("❌ No se encontró la variable de entorno GROQ_API_KEY")

# Inicializa el cliente pasando la variable
client = Groq(api_key=api_key)


# =========================================================================
# VARIABLES GLOBALES DE CONTROL SEMÁNTICO (Cargadas una sola vez en el Engine)
# =========================================================================
LISTA_AREAS_ESTATICAS = []
LISTA_TAGS_ESTATICOS = []

def inicializar_listas_analiticas_ram():
    """
    Extrae de forma unbuffered y por única vez los substrings de control
    geográfico e intereses desde la RAM del Singleton.
    """
    global LISTA_AREAS_ESTATICAS, LISTA_TAGS_ESTATICOS
    
    df_m = CatalogoRutas._conocimiento_maestro.copy()
    
    # 1. Obtener valores geográficos únicos combinando las zonas registradas (origen/destino)
    zonas_origen = df_m['zona_origen'].dropna().astype(str).str.strip().unique().tolist()
    zonas_destino = df_m['zona_destino'].dropna().astype(str).str.strip().unique().tolist()
    LISTA_AREAS_ESTATICAS = sorted(list(set(zonas_origen + zonas_destino)))
    
    # 2. Procesar la columna de intereses_tags extrayendo cada substring individual único
    tags_crudos = df_m['intereses_tags'].dropna().astype(str).tolist()
    set_substrings_tags = set()
    for fila_tags in tags_crudos:
        for item in fila_tags.split(','):
            tag_limpio = item.strip()
            if tag_limpio:
                set_substrings_tags.add(tag_limpio)
    LISTA_TAGS_ESTATICOS = sorted(list(set_substrings_tags))
    
    print("📊 [ENGINE RAM]: Listas analíticas estáticas consolidadas en el encabezado global.")


def detectar_asertividad(texto_usuario: str) -> bool:
    """
    Analiza lingüísticamente la petición del usuario para determinar si solicita
    una inclusión (True) o una exclusión del elemento de interés (False).
    """
    patrones_negacion = [
        r"\bno\s+tenga\b", r"\bsin\b", r"\bque\s+no\s+haya\b", 
        r"\bno\s+tengan\b", r"\bevitando\b", r"\bmenos\s+", r"\bno\s+quiero\s+ver\b"
    ]
    texto_clean = texto_usuario.lower().strip()
    for patron in patrones_negacion:
        if re.search(patron, texto_clean):
            return False
    return True

def imprimir_error_handler(codigo_mensaje: str):
    """
    Procesa y renderiza de forma homogénea cualquier respuesta de error 
    o estado de control diferente de "0" utilizando el glosario.
    """
    print("\nNo se encontraron opciones o trayectos que cumplan con tus expectativas, el motivo es:")
    
    df_g = CatalogoRutas._glosario.copy()
    df_g['entidad_clean'] = df_g['entidad'].astype(str).str.strip().str.upper()
    df_g['categoria_clean'] = df_g['categoria'].astype(str).str.strip()
    
    filtro_error = (df_g['entidad_clean'] == 'ERROR') & (df_g['categoria_clean'] == str(codigo_mensaje).strip())
    match_definicion = df_g[filtro_error]
    
    if not match_definicion.empty:
        motivo_real = match_definicion.iloc[0]['definicion']
        print(f"💬 {motivo_real}")
    else:
        print(f"💬 Código de estado [{codigo_mensaje}] procesado sin descripción explícita en glosario.")
        
    print("Modifica tu petición o busca activamente la sección correspondiente en el sitio web.\n")

def formatear_y_renderizar_exito(lista_rutas: list):
    """
    Formatea y discrimina dinámicamente si el resultado es una ruta de senderismo
    o una guía de logística global de transporte vehicular (Tiempos en horas).
    """
    num_opciones = len(lista_rutas)
    print(f"\nTe tenemos {num_opciones} opciones que concuerdan con la petición que haces. Estas son:")
    print("=" * 75)
    
    df_m = CatalogoRutas._conocimiento_maestro.copy()
    df_m['id_ruta_temp'] = df_m['id_ruta'].astype(str).str.strip()

    for id_ruta in lista_rutas:
        id_clean = str(id_ruta).strip()
        fila_df = df_m[df_m['id_ruta_temp'] == id_clean]
        
        if not fila_df.empty:
            datos = fila_df.iloc[0].to_dict()
            grupo = datos.get('grupo_conector', '').strip().upper()
            
            origen = datos.get('zona_origen', '').strip()
            destino = datos.get('zona_destino', '').strip()
            encabezado_ruta = f"Desde {origen} hasta {destino}"
            
            nombre_variante = datos.get('nombre_variante')
            if pd.notna(nombre_variante) and str(nombre_variante).strip() and str(nombre_variante).strip().lower() != 'nan':
                encabezado_ruta += f" por {str(nombre_variante).strip()}"
            
            # -----------------------------------------------------------------
            # SUB-RENDERIZADOR A: Logística de Conectividad o Transporte Vehicular
            # -----------------------------------------------------------------
            if grupo == 'VEHICULAR':
                print(f"✈️ [GUÍA DEL VIAJERO]: {encabezado_ruta}")
                print(f"  • Distancia aproximada: {datos.get('distancia_km', 'N/A')} Km")
                print(f"  • Tiempo estimado de viaje: {datos.get('tiempo_min', 'N/A')} horas (aproximadas)")
                print(f"  • Medios de transporte o apoyo: {datos.get('opcion_vehiculo', 'N/A')}")
                
                desc_ux = datos.get('descripcion_ux', '').strip()
                desc_web = datos.get('descripcion_web', '').strip()
                print(f"  • Indicaciones logísticas: {desc_ux} {desc_web}".strip())
                print(f"  • Costo estimado / Pasaje aproximado: COP {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Ver mapa y guía completa en: {datos.get('url', 'N/A')}")
                
            # -----------------------------------------------------------------
            # SUB-RENDERIZADOR B: Rutas de Senderismo Recreativo o Local
            # -----------------------------------------------------------------
            else:
                print(f"🥾 [SENDERISMO]: {encabezado_ruta}")
                print(f"  • Distancia en Km: {datos.get('distancia_km', 'N/A')}")
                print(f"  • Tiempo estimado recreacional: {datos.get('tiempo_min', 'N/A')} horas")
                print(f"  • Nivel de Dificultad: {datos.get('dificultad', 'N/A')}")
                print(f"  • Terreno predominante: {datos.get('relieve_tipo', 'N/A')}")
                print(f"  • Desnivel: Ascenso +{datos.get('ascenso_mt', 'N/A')}m | Descenso -{datos.get('descenso_mt', 'N/A')}m")
                print(f"  • Logística vehicular: {datos.get('opcion_vehiculo', 'N/A')}")
                
                desc_ux = datos.get('descripcion_ux', '').strip()
                desc_web = datos.get('descripcion_web', '').strip()
                print(f"  • Descripción técnica: {desc_ux} {desc_web}".strip())
                print(f"  • Costos de acceso/ingresos: COP {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Página web de referencia: {datos.get('url', 'N/A')}")
            
            print("-" * 75)

def procesar_con_ia_groq(texto_usuario: str) -> dict:
    """
    Enrutador analítico NLP con discriminador de intención pragmática 
    para diferenciar transporte interurbano (VEHICULAR) de rutas a pie.
    """
    prompt_sistema = (
        "Eres el enrutador analítico y motor de traducción semántica de BOTV02. Tu objetivo es mapear "
        "las expresiones, sinónimos y peticiones coloquiales del usuario hacia los elementos exactos del catálogo de senderos,  localidades y ciudades.\n\n"
        
        f"--- LUGARES GEOGRÁFICOS Y NODOS REALES EN RAM ---\n{json.dumps(LISTA_AREAS_ESTATICAS, ensure_ascii=False)}\n\n"
        f"--- SUBSTRINGS DE INTERES_TAGS REALES EN RAM ---\n{json.dumps(LISTA_TAGS_ESTATICOS, ensure_ascii=False)}\n\n"
        
        "DICCIONARIO DE CONTROL SEMÁNTICO (ONTOLOGÍA SENDERISTA):\n"
        "Si el usuario indaga por cualquiera de los siguientes conceptos de la izquierda, debes considerarlos "
        "sinónimos directos y extraer estrictamente el término de control 'arqueologia' en el JSON final:\n"
        " - 'ruinas' -> arqueologia\n"
        " - 'caminos empedrados' o 'caminos empedrado' -> arqueologia\n"
        " - 'caminos ancestrales' -> arqueologia\n"
        " - 'terrazas en piedra' o 'terrazas taironas' -> arqueologia\n"
        " - 'asentamientos precolombinos' o 'indigenas antiguos' -> arqueologia\n"
        " - 'vestigios' -> arqueologia\n\n"
        
        "REGLA CRÍTICA PERÍMETRO URBANO SANTA MARTA:\n"
        "Si el usuario pide explícitamente caminar 'dentro de la ciudad', 'en el casco urbano', 'dentro de Santa Marta' "
        "o hace referencia a rutas estrictamente urbanas locales de Santa Marta, debes mapear la entidad 'area' "
        "o el nodo al string oficial indexado: 'Santa Marta-Urbano' (mantén estrictamente el guion).\n\n"
        
        "REGLA DE ORO DE DISCRIMINACIÓN (VEHICULAR VS SENDERISMO):\n"
        "Si el usuario incluye en su pregunta terminos como 'viajar', 'moverse', o pide 'transporte', 'colectivos', 'buses', 'taxi' "
        "entre nodos principales (ej. de Santa Marta a Minca, de Santa Marta a Bonda, o desde Barranquilla/Aracataca):\n"
        "1. Clasifica el flujo STRICTAMENTE como 'tipo_flujo': 'origen_destino'.\n"
        "2. Identifica los nodos de origen y destino correspondientes.\n"
        "3. Coloca en el campo 'interes' el tag específico 'transporte'. Esto es VITAL para que los handlers de "
        "   Pandas filtren únicamente la guía logística vehicular y no mezclen los senderos peatonales de la zona.\n\n"
        
        "REGLAS ESTRICTAS DE EVALUACIÓN SEMÁNTICA:\n"
        "1. Para el campo 'interes' (Flujo interes_zona):\n"
        "   - Analiza la intención conceptual. Aplica el Diccionario Semántico si aplica para mapear a términos en RAM.\n"
        "2. Para los campos 'area', 'origen' y 'destino':\n"
        "   - Evalúa contra la lista de LUGARES GEOGRÁFICOS en RAM. Corrige errores ortográficos aproximándolos "
        "     al nombre oficial (ej: 'vonda' -> 'Bonda'; 'minka' -> 'Minca'; 'santa marta urbano' -> 'Santa Marta-Urbano').\n"
        "3. Clasificación del 'tipo_flujo':\n"
        "   - 'origen_destino' si expresan deseo de trasladarse, viajar o caminar de un punto A a un punto B.\n"
        "   - 'interes_zona' si buscan actividades, atracciones o tags en un área específica.\n\n"
        
        "Devuelve ÚNICAMENTE un objeto JSON válido con la siguiente estructura:\n"
        "{\n"
        "  \"tipo_flujo\": \"origen_destino\" | \"interes_zona\",\n"
        "  \"origen\": string o null,\n"
        "  \"destino\": string o null,\n"
        "  \"area\": string o null,\n"
        "  \"interes\": string o null\n"
        "}"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": texto_usuario}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Error en canal Groq NLP: {e}")
        return {"tipo_flujo": "desconocido"}

def orquestar_pipeline(texto_usuario: str, metadata_red: dict = None):
    """
    Coordinador maestro del ecosistema. Ejecuta NLP, delega a los handlers deterministas 
    de Pandas, resuelve desempates vehiculares y guarda trazas en el log de aprendizaje.
    """
    entidades = procesar_con_ia_groq(texto_usuario)
    tipo_flujo = entidades.get("tipo_flujo", "desconocido")
    interes = entidades.get("interes")

    lista_retornada = []
    string_respuesta = "5"

    # Flujo 1: Trayectos punto a punto (Cubre senderos y Guías logísticas VEHICULAR)
    if tipo_flujo == "origen_destino":
        origen = entidades.get("origen")
        destino = entidades.get("destino")
        if origen and destino:
            resultado = buscar_rutas_origen_destino(origen, destino)
            lista_rutas_raw = resultado.get("rutas", [])
            
            # --- MECANISMO DE DESEMPATE ANALÍTICO EN PANDAS ---
            df_m = CatalogoRutas._conocimiento_maestro
            if interes == "transporte":
                # Aislamos los tips de transporte interurbano (VEHICULAR)
                lista_retornada = [
                    idx for idx in lista_rutas_raw 
                    if str(df_m.loc[df_m['id_ruta'] == idx, 'grupo_conector'].values[0]).strip().upper() == 'VEHICULAR'
                ]
            else:
                # Excluimos los tips de transporte para no ensuciar los senderos peatonales
                lista_retornada = [
                    idx for idx in lista_rutas_raw 
                    if str(df_m.loc[df_m['id_ruta'] == idx, 'grupo_conector'].values[0]).strip().upper() != 'VEHICULAR'
                ]
            string_respuesta = "0" if lista_retornada else "2"

    # Flujo 2: Atractivos o intereses geolocalizados
    elif tipo_flujo == "interes_zona":
        area = entidades.get("area") or entidades.get("origen")
        if area and interes:
            es_positiva = detectar_asertividad(texto_usuario)
            resultado = filtrar_por_interes_zona(zona_usuario=area, interes_usuario=interes, es_positiva=es_positiva)
            lista_retornada = resultado.get("rutas", [])
            string_respuesta = resultado.get("resultado", "5")

    # --- INTERCEPTADOR BLINDADO PERÍMETRO URBANO SANTA MARTA (SMR) ---
    area_normalizada = str(entidades.get("area", "")).replace("-", " ").strip().lower()
    origen_normalizado = str(entidades.get("origen", "")).replace("-", " ").strip().lower()
    
    if ("santa marta urbano" in [area_normalizada, origen_normalizado]) and string_respuesta != "0" and interes != "transporte":
        df_m = CatalogoRutas._conocimiento_maestro.copy()
        df_smr = df_m[(df_m['grupo_conector'].astype(str).str.strip().str.upper() == 'SMR') | 
                      (df_m['zona_origen'].astype(str).str.strip().str.lower() == 'santa marta-urbano')]
        if not df_smr.empty:
            lista_retornada = df_smr['id_ruta'].astype(str).str.strip().tolist()
            string_respuesta = "0"

    # Persistencia selectiva en el archivo JSON Lines (.jsonl) para el aprendizaje continuo
    registrar_interaccion(
        prompt_usuario=texto_usuario,
        entidades_dict=entidades,
        codigo_respuesta=string_respuesta,
        conteo_resultados=len(lista_retornada),
        lista_rutas_ids=lista_retornada,
        metadata_http=metadata_red
    )

    # Despacho de renders corporativos finales
    if string_respuesta == "0":
        formatear_y_renderizar_exito(lista_retornada)
    else:
        imprimir_error_handler(string_respuesta)


# =========================================================================
# SECCIÓN PRINCIPAL: PROMPT ABIERTO EN BUCLE CONTINUO (UNBUFFERED)
# =========================================================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("      INITIALIZING BOTV02 PLATFORM - CORE ENGINE RAM")
    print("="*60)
    print("🚀 Cargando diccionarios de datos del Framework...")
    
    if CatalogoRutas.cargar_componentes():
        # Ejecución única global al arrancar el proceso de ejecución
        inicializar_listas_analiticas_ram()
        
        print("✅ Todo el conocimiento analítico se encuentra indexado en memoria RAM.")
        print("💡 Los catálogos logísticos vehiculares y de senderos están sincronizados.")
        print("🚪 Para finalizar la interacción, escribe 'salir' o 'exit'.")
        print("="*60 + "\n")
        
        while True:
            try:
                prompt_usuario = input("👤 Usuario: ")
                
                if prompt_usuario.strip().lower() in ['salir', 'exit']:
                    print("\n🤖 [BOTV02]: Conexión cerrada. ¡Buen viaje viajero!")
                    break
                
                if not prompt_usuario.strip():
                    continue
                
                orquestar_pipeline(prompt_usuario)
                
            except KeyboardInterrupt:
                print("\n\n🤖 [BOTV02]: Interrupción forzada. Saliendo del sistema...")
                break
            except Exception as e:
                print(f"\n❌ Se presentó un error inesperado en la captura: {e}\n")
    else:
        print("❌ Error crítico al levantar el Administrador Geográfico en memoria RAM.")