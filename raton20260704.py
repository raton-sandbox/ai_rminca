# -*- coding: utf-8 -*-
"""
Orquestador Central: raton.py
Versión: 13.0.0 - Sincronización Total unbuffered, Mapeo Multimodal y Consola Interactiva
Timestamp: 2026-07-04T19:30:00-05:00
"""
import os
import json
import re
import datetime
import pandas as pd
from dotenv import load_dotenv
from groq import Groq


# Importación de la arquitectura Core e Interfaces Deterministas de Python
from core.geo_manager import CatalogoRutas
from handlers.origen_destino import buscar_rutas_origen_destino
from handlers.interes_zona import filtrar_por_interes_zona
from handlers.perfil_filtro import evaluar_esfuerzo_recreativo
from handlers.zona_info import obtener_info_navegacion_zona
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

#client = Groq(api_key=os.environ.get("GROQ_API_KEY"

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
    
    df_m = CatalogoRutas._conocimiento_maestro
    if df_m is not None and not df_m.empty:
        # 1. Obtener valores geográficos únicos combinando las zonas registradas (origen/destino)
        zonas_origen = df_m['zona_origen'].dropna().astype(str).str.strip().unique().tolist()
        zonas_destino = df_m['zona_destino'].dropna().astype(str).str.strip().unique().tolist()
        LISTA_AREAS_ESTATICAS = sorted(list(set(zonas_origen + zonas_destino)))
        
        # 2. Procesar la columna de intereses_tags extrayendo cada substring llanamente
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
    o estado de control diferente de "0" utilizando el glosario técnico.
    """
    print("\n🤖 [BOTV02]: No se encontraron opciones o trayectos que cumplan con tus expectativas, el motivo es:")
    
    # Intento defensivo de parsear la definición desde el glosario cargado en el singleton
    definiciones_dict = CatalogoRutas._definiciones
    motivo_real = None
    
    if isinstance(definiciones_dict, dict):
        errores_glosario = definiciones_dict.get("errores", {})
        motivo_real = errores_glosario.get(str(codigo_mensaje).strip())
        
    if motivo_real:
        print(f"💬 {motivo_real}")
    else:
        print(f"💬 Código de estado [{codigo_mensaje}] procesado sin descripción explícita en glosario.")
        
    print("Modifica tu petición o busca activamente la sección correspondiente en el sitio web.\n")

def renderizar_respuesta_usuario(lista_rutas: list, interes_modo: str, prompt_original: str):
    """
    Construye la interfaz conversacional final unificando de manera rigurosa
    las especificaciones técnicas de negocio (Nombres compuestos, Google Photos, Jornadas).
    """
    num_opciones = len(lista_rutas)
    print(f"\n🤖 [BOTV02]: Te tenemos {num_opciones} opciones que concuerdan con la petición que haces. Estas son:")
    print("=" * 85)
    
    df_m = CatalogoRutas._conocimiento_maestro
    if df_m is None or df_m.empty:
        return

    for id_ruta in lista_rutas:
        id_clean = str(id_ruta).strip()
        fila_df = df_m[df_m['id_ruta'] == id_clean]
        
        if not fila_df.empty:
            datos = fila_df.iloc[0].to_dict()
            
            # Regla de Negocio 4: El nombre de los senderos es la unión compuesta de sus extremos
            nombre_sendero = f"Desde {datos.get('zona_origen')} hasta {datos.get('zona_destino')}"
            
            # Determinación adaptativa del modo para render multimodal (Transporte vs Senderismo)
            es_vehicular = (
                str(datos.get('id_ruta')).startswith('LG') or 
                str(datos.get('grupo_conector')).upper() == 'VEHICULAR' or 
                str(datos.get('perfil_ruta')).lower() == 'carretera' or 
                str(datos.get('modo')).lower() == 'transporte publico'
            )
            
            # Regla de Negocio 6: Clasificación elástica de jornadas de caminata (9 Horas base)
            tiempo_str = datos.get('tiempo_min', '0')
            try:
                horas = float(tiempo_str) if tiempo_str else 0.0
            except ValueError:
                horas = 0.0
                
            if horas >= 9.0:
                jornada_txt = f"{horas} horas (Caminata larga, más de una jornada completa)"
            elif horas >= 4.0:
                jornada_txt = f"{horas} horas (Caminata media jornada)"
            else:
                jornada_txt = f"{horas} horas (Caminata corta recreativa con tiempos estimados esperados)"

            # -----------------------------------------------------------------
            # SUB-RENDERIZADOR A: Logística de Conectividad o Transporte Vehicular
            # -----------------------------------------------------------------
            if es_vehicular or interes_modo == "transporte":
                print(f"✈️ [GUÍA DE TRANSPORTE LOGÍSTICO]: Conexión regional para {nombre_sendero}")
                print(f"  • Medio de traslado: {datos.get('opcion_vehiculo', 'Bus / Colectivo Urbano')}")
                print(f"  • Distancia: {datos.get('distancia_km', 'N/A')} Km | Tiempo Estimado: {datos.get('tiempo_min', 'N/A')} Horas de viaje")
                print(f"  • Costo del Pasaje: {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Indicaciones UX: {datos.get('descripcion_ux', '')} {datos.get('descripcion_narrativa', '')}".strip())
                print(f"  • Ver mapa y guía completa en: {datos.get('url', 'N/A')}")
                
            # -----------------------------------------------------------------
            # SUB-RENDERIZADOR B: Rutas de Senderismo Recreativo o Local
            # -----------------------------------------------------------------
            else:
                # Regla de Negocio 5: Atributos obligatorios para la confirmación en el chat público
                print(f"🥾 [SENDERISMO]: {nombre_sendero}")
                if datos.get('nombre_variante'):
                    print(f"  • Variante/Atractivo: {datos.get('nombre_variante')}")
                print(f"  • Distancia total: {datos.get('distancia_km', 'N/A')} Km")
                print(f"  • Esfuerzo / Dificultad: {datos.get('dificultad', 'N/A')}")
                print(f"  • Duración calculada: {jornada_txt}")
                print(f"  • Desniveles: Ascenso +{datos.get('ascenso_mt', 'N/A')}m | Descenso -{datos.get('descenso_mt', 'N/A')}m")
                print(f"  • Soporte en la zona: {datos.get('opcion_vehiculo', 'N/A')}")
                print(f"  • Costos de acceso/Ingreso por persona: {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Descripción del Entorno: {datos.get('descripcion_ux', '')} {datos.get('descripcion_narrativa', '')}".strip())
                print(f"  • Álbum fotográfico y Mapas de referencia: {datos.get('url', 'N/A')}")
            
            print("-" * 85)

def procesar_con_ia_groq(texto_usuario: str) -> dict:
    """
    Enrutador analítico NLP con discriminador de intención pragmática 
    para extraer variables normalizadas orientadas a la base de datos de Pandas.
    """
    prompt_sistema = (
        "Eres el motor de traducción semántica y clasificador de intenciones del proyecto 'Raton de Minca'. "
        "Tu misión es mapear la petición libre del usuario hacia entidades parametrizadas exactas de nuestra base de datos.\n\n"
        
        f"--- LUGARES GEOGRÁFICOS REALES INDEXADOS EN MEMORIA RAM ---\n{json.dumps(LISTA_AREAS_ESTATICAS, ensure_ascii=False)}\n\n"
        f"--- SUBSTRINGS DE INTERES_TAGS REALES EN RAM ---\n{json.dumps(LISTA_TAGS_ESTATICOS, ensure_ascii=False)}\n\n"
        
        "REGLA DE DISTINCIÓN DE MODO (VEHICULAR / TRANSPORTE PÚBLICO VS SENDERISMO):\n"
        "1. Si el usuario pregunta de forma ambigua ('cómo ir de Minca a Bonda'), asume estrictamente que desea caminar, "
        "   clasificando el modo como Peatonal (Flujo Senderismo) y asignando 'tipo_flujo': 'origen_destino'.\n"
        "2. Si incluye explícitamente términos como 'viajar', 'moverse', 'bus', 'colectivo', 'taxi' o 'transporte público' "
        "   entre nodos geográficos: Clasifica el flujo como 'origen_destino' y coloca en el campo 'interes' el tag "
        "   específico 'transporte'. Esto obligará al backend a aislar las guías de conectividad vehicular globales.\n\n"
        
        "DICCIONARIO DE CONTROL SEMÁNTICO (ONTOLOGÍA SENDERISTA):\n"
        "Si el usuario indaga por cualquiera de los siguientes conceptos de la izquierda, debes considerarlos "
        "sinónimos directos y extraer estrictamente el término de control 'arqueologia' en el JSON final:\n"
        " - 'ruinas', 'caminos empedrados', 'caminos ancestrales', 'terrazas en piedra', 'vestigios' -> arqueologia\n\n"
        
        "REGLA CRÍTICA PERÍMETRO URBANO SANTA MARTA:\n"
        "Si el usuario pide explícitamente caminar 'dentro de la ciudad' o 'dentro de Santa Marta', debes mapear la entidad 'area' "
        "o el nodo al string oficial indexado: 'Santa Marta-Urbano' (mantén estrictamente el guion).\n\n"
        
        "CLASIFICACIÓN DEL 'TIPO_FLUJO':\n"
        " - 'origen_destino' si expresan deseo de trasladarse, viajar o caminar de un punto A a un punto B.\n"
        " - 'interes_zona' si buscan actividades, atracciones o tags en un área específica.\n"
        " - 'perfil_tecnico' si el usuario pide rutas filtradas netamente por su nivel de esfuerzo o dificultad.\n"
        " - 'zona_info' si pide información de navegación general, páginas o bloques independientes de un área.\n\n"
        
        "Regla de Oro: Prohibido inventar rutas que no existan en la matriz RAM. Devuelve EXCLUSIVAMENTE un objeto JSON válido con este formato:\n"
        "{\n"
        "  \"tipo_flujo\": \"origen_destino\" | \"interes_zona\" | \"perfil_tecnico\" | \"zona_info\",\n"
        "  \"origen\": string o null,\n"
        "  \"destino\": string o null,\n"
        "  \"area\": string o null,\n"
        "  \"interes\": string o null,\n"
        "  \"dificultad\": \"Facil\" | \"Media Baja\" | \"Media\" | \"Alta\" o null\n"
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
    Coordinador maestro de la arquitectura. Ejecuta el NLP sobre Groq, delega en
    los handlers analíticos de Pandas y guarda de forma persistente las métricas en JSONL.
    """
    entidades = procesar_con_ia_groq(texto_usuario)
    tipo_flujo = entidades.get("tipo_flujo", "desconocido")
    interes = entidades.get("interes")

    lista_retornada = []
    string_respuesta = "5"
    df_m = CatalogoRutas._conocimiento_maestro

    # Flujo 1: Trayectos punto a punto (Cubre senderos y Guías logísticas VEHICULAR)
    if tipo_flujo == "origen_destino":
        origen = entidades.get("origen")
        destino = entidades.get("destino")
        if origen and destino:
            resultado = buscar_rutas_origen_destino(origen, destino)
            lista_rutas_raw = resultado.get("rutas", [])
            
            # --- MECANISMO DE DESEMPATE MULTIMODAL EN PANDAS ---
            if df_m is not None and not df_m.empty:
                if interes == "transporte":
                    lista_retornada = [
                        idx for idx in lista_rutas_raw if (
                            str(df_m.loc[df_m['id_ruta'] == idx, 'id_ruta'].values[0]).startswith('LG') or
                            str(df_m.loc[df_m['id_ruta'] == idx, 'grupo_conector'].values[0]).upper() == 'VEHICULAR' or
                            str(df_m.loc[df_m['id_ruta'] == idx, 'modo'].values[0]).lower() == 'transporte publico'
                        )
                    ]
                else:
                    lista_retornada = [
                        idx for idx in lista_rutas_raw if not (
                            str(df_m.loc[df_m['id_ruta'] == idx, 'id_ruta'].values[0]).startswith('LG') or
                            str(df_m.loc[df_m['id_ruta'] == idx, 'grupo_conector'].values[0]).upper() == 'VEHICULAR' or
                            str(df_m.loc[df_m['id_ruta'] == idx, 'modo'].values[0]).lower() == 'transporte publico'
                        )
                    ]
                string_respuesta = "0" if lista_retornada else "2"

    # Flujo 2: Atractivos o intereses geolocalizados (LIKE / NOT LIKE)
    elif tipo_flujo == "interes_zona":
        area = entidades.get("area") or entidades.get("origen")
        if area and interes:
            es_positiva = detectar_asertividad(texto_usuario)
            resultado = filtrar_por_interes_zona(zona_usuario=area, interes_usuario=interes, es_positiva=es_positiva)
            lista_retornada = resultado.get("rutas", [])
            string_respuesta = resultado.get("resultado", "5")

    # Flujo 3: Filtro Técnico Paramétrico (Esfuerzo / Dificultad)
    elif tipo_flujo == "perfil_tecnico":
        dificultad = entidades.get("dificultad")
        if dificultad:
            resultado = evaluar_esfuerzo_recreativo(dificultad)
            lista_retornada = resultado.get("rutas", [])
            string_respuesta = resultado.get("resultado", "5")

    # Flujo 4: Mapeo de Bloques de Navegación del Sitio Web
    elif tipo_flujo == "zona_info":
        area = entidades.get("area") or entidades.get("origen")
        if area:
            info_web = obtener_info_navegacion_zona(area)
            if info_web.get("navegacion_bloques"):
                print(f"\nℹ️ [SITIO WEB RATON DE MINCA]: La zona macro '{info_web.get('area_confirmada')}' se administra en una sección independiente.")
                print(f"🔗 Puedes consultar el catálogo extendido directamente en: {info_web.get('url_referencia')}\n")
                string_respuesta = "0"

    # --- INTERCEPTADOR BLINDADO PERÍMETRO URBANO SANTA MARTA (SMR) ---
    area_normalizada = str(entidades.get("area", "")).replace("-", " ").strip().lower()
    origen_normalizado = str(entidades.get("origen", "")).replace("-", " ").strip().lower()
    
    if ("santa marta urbano" in [area_normalizada, origen_normalizado]) and string_respuesta != "0" and interes != "transporte":
        if df_m is not None and not df_m.empty:
            df_smr = df_m[(df_m['grupo_conector'].astype(str).str.strip().str.upper() == 'SMR') | 
                          (df_m['zona_origen'].astype(str).str.strip().str.lower() == 'santa marta-urbano')]
            if not df_smr.empty:
                lista_retornada = df_smr['id_ruta'].astype(str).str.strip().tolist()
                string_respuesta = "0"

    # Persistencia selectiva en archivo JSON Lines (.jsonl) para auditoría de interacciones
    registrar_interaccion(
        prompt_usuario=texto_usuario,
        entidades_dict=entidades,
        codigo_respuesta=string_respuesta,
        conteo_resultados=len(lista_retornada),
        lista_rutas_ids=lista_retornada,
        metadata_http=metadata_red
    )

    # Despacho de renders de salida finales hacia el widget de Google Sites
    if string_respuesta == "0" and tipo_flujo != "zona_info":
        renderizar_respuesta_usuario(lista_retornada, interes, texto_usuario)
    elif string_respuesta != "0":
        imprimir_error_handler(string_respuesta)

# =========================================================================
# SECCIÓN PRINCIPAL: PROMPT ABIERTO EN BUCLE CONTINUO (UNBUFFERED)
# =========================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("      INITIALIZING BOTV02 PLATFORM - CORE ENGINE RAM 2026")
    print("="*70)
    print("🚀 Cargando diccionarios de datos del Framework...")
    
    if CatalogoRutas.cargar_componentes():
        # Inicialización de substrings estáticos sobre la memoria cargada
        inicializar_listas_analiticas_ram()
        
        print("✅ Todo el conocimiento analítico se encuentra indexado en memoria RAM.")
        print("💡 Los catálogos logísticos vehiculares y de senderos están sincronizados.")
        print("🚪 Para finalizar la interacción, escribe 'salir' o 'exit'.")
        print("="*70 + "\n")
        
        while True:
            try:
                prompt_usuario = input("👤 Usuario: ")
                
                if prompt_usuario.strip().lower() in ['salir', 'exit']:
                    print("\n🤖 [BOTV02]: Conexión cerrada con el Widget de Google Sites. ¡Buen viaje por la Sierra!")
                    break
                
                if not prompt_usuario.strip():
                    continue
                
                orquestar_pipeline(prompt_usuario)
                
                # Regla de Trazabilidad 7: Timestamp exacto en formato ISO/Local al final de la interacción
                print(f"🕒 [Control de Versión de Respuesta - ISO Local Timestamp]: {datetime.datetime.now().isoformat()}")
                print("."*85 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n🤖 [BOTV02]: Interrupción forzada. Saliendo del sistema...")
                break
            except Exception as e:
                print(f"\n❌ Se presentó un error inesperado en la captura: {e}\n")
    else:
        print("❌ Error crítico al levantar el Administrador Geográfico en memoria RAM.")