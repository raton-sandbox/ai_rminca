# -*- coding: utf-8 -*-
"""
Orquestador Central: raton.py
Versión: 24.3.0 - Control de Mensajes Triviales (Sin Interacción IA) y Canalización Única
Timestamp: 2026-07-28T12:10:00-05:00
"""
import os
import json
import re
import datetime

import pandas as pd
from dotenv import load_dotenv
from groq import Groq

# Carga las variables del archivo .env
load_dotenv()

# Importación de la arquitectura Core e Interfaces Deterministas de Python
from core.geo_manager import CatalogoRutas

# INYECTOR DE COMPATIBILIDAD GEOGRÁFICA (Monkey-Patching defensivo para Handlers Heredados)
if not hasattr(CatalogoRutas, 'obtener_sinonimos_directos'):
    def _obtener_sinonimos_directos(zona_input):
        return CatalogoRutas.normalizar_entidad_geografica(zona_input)
    CatalogoRutas.obtener_sinonimos_directos = _obtener_sinonimos_directos

if not hasattr(CatalogoRutas, 'obtener_toda_la_familia_descendiente'):
    def _obtener_toda_la_familia_descendiente(zona_padre):
        df_j = CatalogoRutas._hierarchy_data
        if df_j is not None and not df_j.empty:
            padre_clean = str(zona_padre).strip().lower()
            df_j['padre_clean'] = df_j['padre'].astype(str).str.strip().str.lower()
            df_j['zona_clean'] = df_j['zona'].astype(str).str.strip().str.lower()
            hijos = df_j[df_j['padre_clean'] == padre_clean]['zona_clean'].tolist()
            return [str(zona_padre).strip()] + hijos
        return [str(zona_padre).strip()]
    CatalogoRutas.obtener_toda_la_familia_descendiente = _obtener_toda_la_familia_descendiente

# Importaciones de Handlers manteniendo total compatibilidad intacta
from handlers.origen_destino import buscar_rutas_origen_destino
from handlers.interes_zona import filtrar_por_interes_zona
from handlers.perfil_filtro import filtrar_por_esfuerzo_y_perfil
from handlers.zona_info import obtener_enlaces_por_zona
from handlers.destino_puro import buscar_por_destino_puro 
# Importar para registro consultas de los usuarios
from logger_aprendizaje import registrar_interaccion

#  Módulo para inyección dinámica de definiciones/jerga desde GitHub ---
from loader_definiciones import cargar_definiciones_jerga, formatear_jerga_para_prompt

# Cargar glosario dinámico y construir el bloque del prompt una sola vez al arrancar
DATOS_JERGA = cargar_definiciones_jerga()
BLOQUE_GLOSARIO_PROMPT = formatear_jerga_para_prompt(DATOS_JERGA)

# Inicialización del cliente oficial de Groq
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("❌ No se encontró la variable de entorno GROQ_API_KEY")
client = Groq(api_key=api_key) 
#despues del igual=os.environ.get("GROQ_API_KEY"

LISTA_AREAS_ESTATICAS = []
LISTA_TAGS_ESTATICOS = []

# =========================================================================
# DICCIONARIO DE PATRONES PARA MENSAJES QUE NO REQUIEREN IA
# =========================================================================
DICCIONARIO_CORTESIA = {
    "10": [  # Mensajes de saludo / bienvenida / cortesía inicial
        r"^(hola+|buenas|buen(?:os)?\s+(?:dias|días|tardes|noches)|hey|que\s+tal|qué\s+tal|saludos|aló|alo)$",
        r"^(est(?:as|ás)\s+ahi|est(?:as|ás)\s+ahí|sigues\s+ahi|quien\s+eres|quién\s+eres)$"
    ],
    "11": [  # Mensajes de despedida / cierre / agradecimiento
        r"^(chao|adios|adiós|hasta\s+luego|nos\s+vemos|chaoo+|gracias|muchas\s+gracias|mil\s+gracias|vale|ok|listo)$"
    ]
}

def evaluar_conversacion_trivial(texto_usuario: str) -> str:
    """
    Evalúa mediante expresiones regulares si la entrada del usuario no requiere
    interacción con la IA por ser un saludo ('10') o una despedida ('11').
    Retorna el código de mensaje o None si la petición debe ser procesada por el LLM.
    """
    texto_clean = texto_usuario.lower().strip()
    texto_clean = re.sub(r"^[¡!¿?\s]+|[¡!¿?\s]+$", "", texto_clean)

    for codigo_estado, patrones in DICCIONARIO_CORTESIA.items():
        for patron in patrones:
            if re.search(patron, texto_clean):
                return codigo_estado
    return None

def inicializar_listas_analiticas_ram():
    global LISTA_AREAS_ESTATICAS, LISTA_TAGS_ESTATICOS
    df_m = CatalogoRutas._conocimiento_maestro
    if df_m is not None and not df_m.empty:
        zonas_origen = df_m['zona_origen'].dropna().astype(str).str.strip().unique().tolist()
        zonas_destino = df_m['zona_destino'].dropna().astype(str).str.strip().unique().tolist()
        LISTA_AREAS_ESTATICAS = sorted(list(set(zonas_origen + zonas_destino)))
        
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
    Rutina única centralizada para procesar y renderizar cualquier mensaje de control,
    error o respuesta trivial  consultando definiciones.json.
    """
    print("\n🤖 [Rata]: No se encontraron opciones que cumplan con tus expectativas, el motivo es:")
    df_glosario = CatalogoRutas._glosario
    motivo_real = None
    
    if df_glosario is not None and not df_glosario.empty:
        cond_entidad = df_glosario['entidad'].astype(str).str.upper() == 'ERROR'
        cond_categoria = df_glosario['categoria'].astype(str).str.strip() == str(codigo_mensaje).strip()
        df_error_especifico = df_glosario[cond_entidad & cond_categoria]
        
        if not df_error_especifico.empty:
            motivo_real = df_error_especifico.iloc[0]['definicion']
            
    if motivo_real:
        print(f"💬 {motivo_real}")
    else:
        print(f"💬 Código de estado [{codigo_mensaje}] procesado sin definición explícita en la matriz de errores.")
    print("Modifica tu petición o busca la sección correspondiente en el sitio web de ratondeminca.\n")

def renderizar_respuesta_usuario(lista_rutas: list, interes_modo: str, prompt_original: str):
    num_opciones = len(lista_rutas)
    print(f"\n🤖 [Rata]: Te tenemos {num_opciones} opciones que concuerdan con la petición que haces. Estas son:")
    print("=" * 85)
    
    df_m = CatalogoRutas._conocimiento_maestro
    if df_m is None or df_m.empty:
        return

    for id_ruta in lista_rutas:
        id_clean = str(id_ruta).strip()
        fila_df = df_m[df_m['id_ruta'] == id_clean]
        
        if not fila_df.empty:
            datos = fila_df.iloc[0].to_dict()
            nombre_sendero = f"Desde {datos.get('zona_origen')} hasta {datos.get('zona_destino')}"
            
            # --- 1. PROCESAMIENTO DEFENSIVO DE NODO SEGUNDO NIVEL (contenido_web) ---
            contenido_web = datos.get('contenido_web', {})
            if isinstance(contenido_web, str):
                try:
                    contenido_web = json.loads(contenido_web)
                except Exception:
                    contenido_web = {}
            elif not isinstance(contenido_web, dict):
                contenido_web = {}
                
            # Extracción segura de la narrativa
            desc_narrativa = contenido_web.get('descripcion_narrativa') or datos.get('descripcion_narrativa', '')
            desc_ux = datos.get('descripcion_ux', '')
            texto_descripcion = f"{desc_ux} {desc_narrativa}".strip()

            # --- 2. EXTRACCIÓN Y CONSOLIDACIÓN DE URLS ---
            # A. URL Oficial del registro (prioridad a contenido_web)
            url_oficial = contenido_web.get('url') or datos.get('url', '')
            
            # B. Extracción por Regex de URLs incrustadas en la descripcion_narrativa
            patron_url = r'https?://[^\s><"\'\)]+'
            urls_extraidas_narrativa = re.findall(patron_url, desc_narrativa)
            
            # C. Lista consolidada sin duplicados
            todas_las_urls = []
            if url_oficial and str(url_oficial).strip().upper() != 'N/A':
                todas_las_urls.append(str(url_oficial).strip())
            
            for u in urls_extraidas_narrativa:
                if u not in todas_las_urls:
                    todas_las_urls.append(u)
            
            # String de renderizado final para la URL
            url_render = " | ".join(todas_las_urls) if todas_las_urls else "N/A"
            # -------------------------------------------------------------------------

            es_vehicular = (
                str(datos.get('id_ruta')).startswith('LG') or 
                str(datos.get('grupo_conector')).upper() == 'VEHICULAR' or 
                str(datos.get('perfil_ruta')).lower() == 'carretera' or 
                str(datos.get('modo')).lower() == 'transporte publico'
            )
            
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

            if es_vehicular or interes_modo == "transporte":
                print(f"✈️ [GUÍA DE TRANSPORTE LOGÍSTICO]: Conexión regional para {nombre_sendero}")
                print(f"  • Medio de traslado: {datos.get('opcion_vehiculo', 'Bus / Colectivo Urbano')}")
                print(f"  • Distancia: {datos.get('distancia_km', 'N/A')} Km | Tiempo Estimado: {datos.get('tiempo_min', 'N/A')} Horas de viaje")
                print(f"  • Costo del Pasaje: {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Indicaciones UX: {texto_descripcion}")
                print(f"  • Ver mapa y guía completa en: {url_render}")
            else:
                print(f"🥾 [SENDERISMO]: {nombre_sendero}")
                if datos.get('nombre_variante'):
                    print(f"  • Variante: {datos.get('nombre_variante')}")
                print(f"  • Distancia total: {datos.get('distancia_km', 'N/A')} Km")
                print(f"  • Esfuerzo / Dificultad: {datos.get('dificultad', 'N/A')}")
                print(f"  • Duración calculada: {jornada_txt}")
                print(f"  • Desniveles: Ascenso +{datos.get('ascenso_mt', 'N/A')}m | Descenso -{datos.get('descenso_mt', 'N/A')}m")
                print(f"  • Soporte en la zona: {datos.get('opcion_vehiculo', 'N/A')}")
                print(f"  • Gasto estimado dia por persona transporte, otros cargos: {datos.get('costo_estimado_cop_pp', 'N/A')}")
                print(f"  • Lo destacado del recorrido: {texto_descripcion}")
                print(f"  • Fotografías y Mapas : {url_render}")
            
            print("-" * 85)

    try:
        if lista_rutas:
            id_ejemplo = lista_rutas[0]
            area_detectada = df_m.loc[df_m['id_ruta'] == id_ejemplo, 'area'].values[0]
            df_urls = df_m[df_m['area'].astype(str).str.upper() == str(area_detectada).upper()]
            
            # Extracción segura de URLs únicas del área tanto de la columna raíz como de contenido_web
            urls_unicas = []
            for _, fila in df_urls.iterrows():
                c_web = fila.get('contenido_web', {})
                if isinstance(c_web, str):
                    try:
                        c_web = json.loads(c_web)
                    except Exception:
                        c_web = {}
                u_val = c_web.get('url') or fila.get('url')
                if u_val and str(u_val).strip() not in ['', 'N/A', 'None'] and u_val not in urls_unicas:
                    urls_unicas.append(str(u_val).strip())
            
            if urls_unicas:
                print("\n💡 [RECOMENDACIÓN]: Para ver mapas interactivos, fotos y más detalles de esta zona, visita:")
                for url in urls_unicas:
                    print(f"🔗 {url}")
                print("Nota: Busca a lo largo de la página las secciones específicas del recorrido.\n")
    except Exception:
        pass

def procesar_con_ia_groq(texto_usuario: str) -> dict:
    prompt_sistema = (
        "## PERFIL Y ROL DE EJECUCIÓN\n"
        "Eres el motor de traducción semántica y clasificador de intenciones de 'RatondeMinca', un chatbot "
        "especializado en SENDERISMO, MONTAÑISMO y ECOTURISMO en la región de Santa Marta (Colombia) por lo que se incluyen municipios como ciénaga, pueblo bello, dibulla y aracataca.\n"
        "Tu ecosistema operativo son trochas, playas del Parque Tayrona, playas de santa marta, ríos, cafetales y senderos. "
        "Tu tarea principal es mapear el lenguaje natural del usuario (jerga de caminantes, turistas o montañistas) "
        "a los parámetros exactos requeridos por los handlers deterministas del backend.\n\n"
        #Inyección dinámica del glosario de jerga ---
        f"{BLOQUE_GLOSARIO_PROMPT}\n\n"
        "REGLAS CRÍTICAS DE MAPEO SEMÁNTICO:\n"
        "1. No te limites a coincidencias literales, singulares o plurales. Debes procesar SINÓNIMOS e INTENCIONES implícitas:\n"
        "   - Si el usuario dice 'lugares para bañarme', 'sitios para nadar' o 'charcos', mapea el tag de interés como 'balnearios'.\n"
        "   - Si dice 'cómo llego', 'colectivo', 'pasaje', 'transporte' o 'ir en carro', mapea el tag de interés como 'transporte'.\n"
        "2. Identifica con precisión la intención espacial (tipo_flujo):\n"
        "   - 'origen_destino': ÚNICAMENTE cuando se mencionen EXPLÍCITAMENTE dos puntos geográficos (de A hacia B, de A a B, cómo ir de A hasta B). "
        "¡PROHIBIDO! asumir o inventar que el origen es 'Minca' si el usuario no lo dijo por escrito.\n"
        "   - 'interes_zona': Cuando se busque una actividad, tag o sinónimo específico en una región (ej: Cascadas en Pozo Azul).\n"
        "   - 'perfil_tecnico': Cuando el usuario defina restricciones sobre su condición física o tiempo (ej: caminata fácil de 3 horas).\n"
        "   - 'zona_info': Preguntas generales sobre un área macro sin un interés parametrizado, o preguntas de un DESTINO PURO sin origen explícito "
        "(ej: '¿cómo llegar a chengue?', 'ir a pozo azul'). Si solo hay un destino, colócalo en 'destino', deja 'origen' como null y clasifica como 'zona_info'.\n"
        "     *CRÍTICO*: Si el usuario pregunta por un lugar específico contenido en un área macro con la estructura '[Lugar] en [Área]' "
        "(ej: 'como llegar a las terrazas del cacique en guachaca'), clasifica ESTRICTAMENTE como 'zona_info', mapeando el área macro "
        "en el campo 'area' y el lugar específico en el campo 'destino'.\n\n"
        "REGLA DE DISTINCIÓN DE MODO (VEHICULAR / TRANSPORTE PÚBLICO VS SENDERISMO):\n"
        "1. Si el usuario pregunta de forma explícita por trayectos de punto a punto ('cómo ir de Minca a Bonda') sin declarar transporte vehicular, "
        "asume estrictamente que desea caminar, clasificando el modo como Peatonal (Flujo Senderismo) y asignando 'tipo_flujo': 'origen_destino'.\n"
        "2. Si incluye explícitamente términos como 'viajar', 'moverse', 'bus', 'colectivo', 'taxi' o 'transporte público' "
        "entre nodos geográficos: Clasifica el flujo como 'origen_destino' y coloca en el campo 'interes' el tag "
        "específico 'transporte'. Esto obligará al backend a aislar las guías de conectividad vehicular globales.\n\n"
        "DICCIONARIO DE CONTROL SEMÁNTICO (ONTOLOGÍA SENDERISTA):\n"
        "Si el usuario indaga por cualquiera de los siguientes conceptos de la izquierda, debes considerarlos "
        "sinónimos directos y extraer strictly el término de control 'arqueologia' en el JSON final:\n"
        " - 'ruinas', 'caminos empedrados', 'caminos ancestrales', 'terrazas en piedra', 'vestigios' -> arqueologia\n\n"
        "REGLA CRÍTICA PERÍMETRO URBANO SANTA MARTA:\n"
        "Si el usuario pide explícitamente caminar 'dentro de la ciudad' o 'dentro de Santa Marta', debes mapear la entidad 'area' "
        "o el nodo al string oficial indexado: 'Santa Marta-Urbano' (mantén estrictamente el guion).\n\n"
        "CLASIFICACIÓN DEL 'TIPO_FLUJO':\n"
        " - 'origen_destino' si expresan deseo explícito de trasladarse de un punto A hacia un punto B.\n"
        " - 'interes_zona' si buscan actividades, atracciones o tags en un área específica.\n"
        " - 'perfil_tecnico' si el usuario pide rutas filtradas netamente por su nivel de esfuerzo o dificultad.\n"
        " - 'zona_info' si pide información de navegación general, páginas o un DESTINO SOLITARIO/PURO sin punto de partida definido.\n\n"
        f"--- LUGARES GEOGRÁFICOS REALES INDEXADOS EN MEMORIA RAM ---\n{json.dumps(LISTA_AREAS_ESTATICAS, ensure_ascii=False)}\n\n"
        f"--- SUBSTRINGS DE INTERES_TAGS REALES EN RAM ---\n{json.dumps(LISTA_TAGS_ESTATICOS, ensure_ascii=False)}\n\n"
        "Debes aproximar el origen, destino y área a los nombres más cercanos de la lista geográfica indexada.\n\n"
        "Devuelve EXCLUSIVAMENTE un objeto JSON válido con este formato:\n"
        "{\n"
        "  \"tipo_flujo\": \"origen_destino\" | \"interes_zona\" | \"perfil_tecnico\" | \"zona_info\",\n"
        "  \"origen\": string o null,\n"
        "  \"destino\": string o null,\n"
        "  \"area\": string o null,\n"
        "  \"interes\": string o null,\n"
        "  \"dificultad\": \"Facil\" | \"Media Baja\" | \"Media\" | \"Alta\" o null,\n"
        "  \"duracion_deseada\": \"corta\" | \"una jornada\" | \"larga\" o null\n"
        "}"
    )
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt_sistema}, {"role": "user", "content": texto_usuario}],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Error en canal Groq NLP: {e}")
        return {"tipo_flujo": "desconocido"}

def orquestar_pipeline(texto_usuario: str, metadata_red: dict = None):
    # 0. CONTROL DE MENSAJES QUE NO REQUIEREN IA (Guardián de Conversación Trivial)
    codigo_trivial = evaluar_conversacion_trivial(texto_usuario)
    if codigo_trivial:
        print(f"\n⚡ [ORQUESTADOR - CONTROL LOCAL]: Entrada trivial identificada ('{codigo_trivial}'). Omitiendo consulta a Groq.")
        registrar_interaccion(
            prompt_usuario=texto_usuario, entidades_dict={"tipo_flujo": "trivial"},
            codigo_respuesta=codigo_trivial, conteo_resultados=0, lista_rutas_ids=[], metadata_http=metadata_red
        )
        imprimir_error_handler(codigo_trivial)
        return

    # 1. PARSEO GLOBAL E INTERPRETACIÓN SEMÁNTICA (Vía Groq IA)
    entidades = procesar_con_ia_groq(texto_usuario)
    tipo_flujo = entidades.get("tipo_flujo", "desconocido")
    interes = entidades.get("interes")

    # TRAZA GLOBAL OBLIGATORIA DEL RESULTADO DEL PARSEO
    print(f"\n🧠 [ORQUESTADOR - TRAZA DE INTERPRETACIÓN SEMÁNTICA]")
    print(f" ├── Texto Original: '{texto_usuario}'")
    print(f" └── JSON Mapeado  : {json.dumps(entidades, ensure_ascii=False)}")

    lista_retornada = []
    string_respuesta = "12"  # Código de mensaje por defecto si la entrada no concuerda con ningún flujo válido
    df_m = CatalogoRutas._conocimiento_maestro

    # Flujo: Consultas generales por áreas macro, Destinos Puros o combinaciones (zona_info)
    if tipo_flujo == "zona_info":
        area = entidades.get("area") or entidades.get("origen")
        destino_especifico = entidades.get("destino")
        
        # CASO 1: Pregunta directa sobre un destino sin declarar área macro (Ej: "¿Cómo llego a Pozo Azul?")
        if destino_especifico and not area:
            print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: zona_info (Caso Destino Puro)")
            print(f" ├── Handler Invocado   : handlers.destino_puro.buscar_por_destino_puro")
            print(f" └── Argumentos Pasados : destino_usuario='{destino_especifico}'")
            
            resultado_puro = buscar_por_destino_puro(destino_especifico)
            lista_retornada = resultado_puro.get("rutas", [])
            string_respuesta = resultado_puro.get("resultado", "7")
            
        # CASO 2: Estructura combinada "Lugar en Área" (Ej: "Terrazas del Cacique en Guachaca")
        elif destino_especifico and area:
            print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: zona_info (Caso Intersección Semántica)")
            print(f" └── Estado             : Buscando combinación directa en Matriz Maestra antes de delegar.")
            
            area_oficial = CatalogoRutas.normalizar_entidad_geografica(area).strip().upper()
            destino_oficial = CatalogoRutas.normalizar_entidad_geografica(destino_especifico).strip().upper()
            
            cond_area = df_m['area'].astype(str).str.upper() == area_oficial
            cond_destino = df_m['zona_destino'].astype(str).str.upper() == destino_oficial
            df_coincidencias = df_m[cond_area & cond_destino]
            
            if not df_coincidencias.empty:
                lista_retornada = df_coincidencias['id_ruta'].dropna().unique().tolist()
                string_respuesta = "0"
                print(f" ✅ Coincidencia encontrada por atributos cruzados: {len(lista_retornada)} rutas.")
            else:
                print(f" ⚠️ Sin intersección exacta en matriz. Delegando al handler de enlaces por zona...")
                print(f" ├── Handler Invocado   : handlers.zona_info.obtener_enlaces_por_zona")
                print(f" └── Argumentos Pasados : area_usuario='{area}'")
                
                resultado_zona = obtener_enlaces_por_zona(area)
                lista_retornada = resultado_zona.get("rutas", [])
                string_respuesta = resultado_zona.get("resultado", "6")
                
        # CASO 3: Solo se especificó un área general macro (Ej: "Información de Minca")
        else:
            if area:
                print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: zona_info (Caso Área Macro)")
                print(f" ├── Handler Invocado   : handlers.zona_info.obtener_enlaces_por_zona")
                print(f" └── Argumentos Pasados : area_usuario='{area}'")
                
                resultado_zona = obtener_enlaces_por_zona(area)
                lista_retornada = resultado_zona.get("rutas", [])
                string_respuesta = resultado_zona.get("resultado", "6")

    # Flujo 1: Trayectos punto a punto (origen_destino)
    elif tipo_flujo == "origen_destino":
        origen = entidades.get("origen")
        destino = entidades.get("destino")
        area_contexto = entidades.get("area")
        
        if origen and destino:
            print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: origen_destino")
            print(f" ├── Handler Invocado   : handlers.origen_destino.buscar_rutas_origen_destino")
            print(f" └── Argumentos Pasados : origen_usuario='{origen}', destino_usuario='{destino}'")
            
            resultado = buscar_rutas_origen_destino(origen, destino)
            lista_rutas_raw = resultado.get("rutas", [])
            status_handler = resultado.get("resultado", "2")
            
            if df_m is not None and not df_m.empty and status_handler == "0":
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
            
            if not lista_retornada:
                print(" └── 🔍 [RE-ENRUTAMIENTO SEMÁNTICO]: Buscando rutas por intersección de Área y Destino...")
                zona_evaluar = area_contexto if area_contexto else origen
                area_oficial = CatalogoRutas.normalizar_entidad_geografica(zona_evaluar).strip().upper()
                destino_oficial = CatalogoRutas.normalizar_entidad_geografica(destino).strip().upper()
                
                cond_area = df_m['area'].astype(str).str.upper() == area_oficial
                cond_destino = df_m['zona_destino'].astype(str).str.upper() == destino_oficial
                df_coincidencias = df_m[cond_area & cond_destino]
                
                if not df_coincidencias.empty:
                    lista_retornada = df_coincidencias['id_ruta'].dropna().unique().tolist()
                    string_respuesta = "0"
                    print(f"     ✅ Intersección exitosa: {len(lista_retornada)} IDs de ruta consolidados.")
                else:
                    lista_retornada = []
                    string_respuesta = "6" if status_handler != "1" else "1"
            else:
                string_respuesta = "0"

    # Flujo 2: Atractivos o intereses geolocalizados (interes_zona)
    elif tipo_flujo == "interes_zona":
        area = entidades.get("area") or entidades.get("origen")
        if area and interes:
            es_positiva = detectar_asertividad(texto_usuario)
            
            print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: interes_zona")
            print(f" ├── Handler Invocado   : handlers.interes_zona.filtrar_por_interes_zona")
            print(f" └── Argumentos Pasados : zona_usuario='{area}', interes_usuario='{interes}', es_positiva={es_positiva}")
            
            resultado = filtrar_por_interes_zona(zona_usuario=area, interes_usuario=interes, es_positiva=es_positiva)
            lista_retornada = resultado.get("rutas", [])
            string_respuesta = resultado.get("resultado", "5")

    # Flujo 3: Perfiles físicos y técnicos (perfil_tecnico)
    elif tipo_flujo == "perfil_tecnico":
        dificultad = entidades.get("dificultad") or ""
        area = entidades.get("area") or entidades.get("origen") or "Minca"
        duracion = entidades.get("duracion_deseada") or "cualquiera"
        
        if dificultad or duracion != "cualquiera":
            print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: perfil_tecnico")
            print(f" ├── Handler Invocado   : handlers.perfil_filtro.filtrar_por_esfuerzo_y_perfil")
            print(f" └── Argumentos Pasados : zona='{area}', dificultad='{dificultad}', duracion_deseada='{duracion}'")
            
            resultado_perfil = filtrar_por_esfuerzo_y_perfil(zona=area, dificultad=dificultad, duracion_deseada=duracion)
            if resultado_perfil.get("status") == "exito":
                lista_retornada = [r["id_ruta"] for r in resultado_perfil.get("rutas", [])]
                string_respuesta = "0" if lista_retornada else "2"
            else:
                string_respuesta = "2"
                
    # Flujo de Excepción / Desconocido (Frases fuera del dominio de senderismo)
    else:
        print(f" ├── Componente Ejecutor: orquestar_pipeline -> flujo: DESCONOCIDO")
        print(f" └── Acción             : No se invocará ningún handler. Transmitiendo código '12'.")
        string_respuesta = "12"

    # --- INTERCEPTADOR PERÍMETRO URBANO SANTA MARTA (SMR) ---
    area_normalizada = str(entidades.get("area", "")).replace("-", " ").strip().lower()
    origen_normalizado = str(entidades.get("origen", "")).replace("-", " ").strip().lower()
    
    if ("santa marta urbano" in [area_normalizada, origen_normalizado]) and string_respuesta != "0" and interes != "transporte" and tipo_flujo != "zona_info":
        if df_m is not None and not df_m.empty:
            df_smr = df_m[(df_m['grupo_conector'].astype(str).str.strip().str.upper() == 'SMR') | 
                          (df_m['zona_origen'].astype(str).str.strip().str.lower() == 'santa marta-urbano')]
            if not df_smr.empty:
                lista_retornada = df_smr['id_ruta'].astype(str).str.strip().tolist()
                string_respuesta = "0"

    registrar_interaccion(
        prompt_usuario=texto_usuario, entidades_dict=entidades, codigo_respuesta=string_respuesta,
        conteo_resultados=len(lista_retornada), lista_rutas_ids=lista_retornada, metadata_http=metadata_red
    )

    if string_respuesta == "0":
        renderizar_respuesta_usuario(lista_retornada, interes, texto_usuario)
    else:
        imprimir_error_handler(string_respuesta)

if __name__ == "__main__":
    print("\n" + "="*70)
    print("      INITIALIZING BOTV02 PLATFORM - CORE ENGINE RAM 2026")
    print("="*70)
    
    if CatalogoRutas.cargar_componentes():
        inicializar_listas_analiticas_ram()
        print("Base de conocimiento indexada. Orquestador central operativo al 100%.\n")
        
        while True:
            try:
                prompt_usuario = input("👤 Usuario: ")
                if prompt_usuario.strip().lower() in ['salir', 'exit']:
                    imprimir_error_handler("11")
                    break
                if not prompt_usuario.strip():
                    continue
                orquestar_pipeline(prompt_usuario)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n❌ Error en ejecución: {e}\n")
