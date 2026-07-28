# -*- coding: utf-8 -*-
"""
HANDLER: handlers/perfil_filtro.py
PROPÓSITO: Procesar intenciones de búsqueda por perfil, trayecto o zona geográfica.
           Implementa blindaje contra contextos corruptos de Dialogflow, filtros 
           matemáticos de tiempo basados en Excel y enriquecimiento dinámico de respuestas.
"""
import sys
import pandas as pd
from core.geo_manager import CatalogoRutas, sanitizar_cadena

def resolver_intencion(request_body):
    print("🚀 [PERFIL_FILTRO] Iniciando ejecución de 'resolver_intencion'...", file=sys.stderr)
    
    try:
        # Extraemos la matriz de rutas y el glosario desde el Singleton en RAM
        df = CatalogoRutas.obtener_matriz()
        df_glosario = CatalogoRutas.obtener_glosario()
        
        if df.empty:
            print("❌ [PERFIL_FILTRO] Error: La matriz de rutas está vacía en RAM.", file=sys.stderr)
            return {"fulfillmentText": "Lo siento, la base de datos de rutas no se encuentra disponible en este momento."}

        # 1. Recuperación del texto original del usuario para validaciones defensivas
        query_text = request_body.get("queryResult", {}).get("queryText", "").lower()
        params = request_body.get("queryResult", {}).get("parameters", {})
        
        # 2. Escudo contra el arrastre de parámetros geográficos en formato de lista
        zona_raw = params.get("Zona", "")
        origen = sanitizar_cadena(params.get("Origen", ""))
        destino = sanitizar_cadena(params.get("Zona_destino", params.get("Destino", "")))
        zona = ""

        if isinstance(zona_raw, list):
            print(f"📥 [PERFIL_FILTRO] Detectada estructura de lista en parámetro Zona: {zona_raw}", file=sys.stderr)
            if len(zona_raw) == 1:
                # Caso: Residuo de contexto previo (Aplanamos la lista a un string tradicional)
                zona = sanitizar_cadena(zona_raw[0])
                print(f"🧹 [PERFIL_FILTRO] Lista de un elemento normalizada a string: '{zona}'", file=sys.stderr)
            elif len(zona_raw) >= 2:
                # Caso: Pregunta implícita de trayecto (ej: '¿Es sencillo ir de Bonda a Minca?')
                if not origen:
                    origen = sanitizar_cadena(zona_raw[0])
                if not destino:
                    destino = sanitizar_cadena(zona_raw[1])
                print(f"🔀 [PERFIL_FILTRO] Lista desglosada con éxito -> Origen: '{origen}', Destino: '{destino}'", file=sys.stderr)
        else:
            # Caso estándar: Viene como un string plano
            zona = sanitizar_cadena(zona_raw)

        # 3. Escudo contra parámetros fantasma de duración (Arrastrados por persistencia de contexto)
        duracion_raw = params.get("duration", "")
        duracion_param = ""
        
        # Lista de control de palabras clave que demuestran intención de tiempo real en el turno actual
        palabras_tiempo = ['hora', 'hr', 'minut', 'corto', 'jornada', 'larga', 'tiempo', 'durac']
        
        if duracion_raw:
            if isinstance(duracion_raw, str) and duracion_raw != "":
                # Si es una categoría textual, verificamos que el usuario realmente la haya escrito ahora
                if any(p in query_text for p in palabras_tiempo) or any(p in duracion_raw.lower() for p in palabras_tiempo):
                    duracion_param = duracion_raw
                else:
                    print("🧹 [PERFIL_FILTRO] Escudo activado: Se descartó 'duration' string por arrastre fantasma.", file=sys.stderr)
            
            elif isinstance(duracion_raw, dict) and duracion_raw.get('amount'):
                # Si es el objeto sys.duration de Dialogflow, comprobamos su presencia en la frase actual
                if any(p in query_text for p in palabras_tiempo) or str(duracion_raw.get('amount')) in query_text:
                    duracion_param = duracion_raw
                else:
                    print("🧹 [PERFIL_FILTRO] Escudo activado: Se descartó objeto 'sys.duration' por arrastre fantasma.", file=sys.stderr)

        # Extracción estándar del resto de entidades sanitizadas
        perfil = sanitizar_cadena(params.get("Perfil", ""))
        dificultad = sanitizar_cadena(params.get("Dificultad", ""))

        print(f"🔍 [PERFIL_FILTRO] Parámetros Finales: Origen='{origen}', Destino='{destino}', Zona='{zona}', Dificultad='{dificultad}', Duración='{duracion_param}'", file=sys.stderr)

        # Copia de trabajo para aplicar los filtros sucesivos
        df_filtrado = df.copy()

        # =====================================================================
        # APLICACIÓN DE FILTROS SUCESIVOS (Matriz de Decisiones Relacionales)
        # =====================================================================
        
        # Filtro 1: Criterios Geográficos (Trayecto exacto vs. Área Macro)
        if origen and destino:
            df_filtrado = df_filtrado[(df_filtrado['zona_origen'].str.lower() == origen) & 
                                      (df_filtrado['zona_destino'].str.lower() == destino)]
        elif zona:
            df_filtrado = df_filtrado[df_filtrado['area'].str.lower() == zona]

        # Filtro 2: Dificultad Técnica Homologada
        if dificultad:
            df_filtrado = df_filtrado[df_filtrado['dificultad'].str.lower() == dificultad]
        
        # Filtro 3: Perfil Semántico o Tags de Interés
        if perfil:
            df_filtrado = df_filtrado[df_filtrado['perfil_ruta'].str.contains(perfil, case=False, na=False)]

        # Filtro 4: Operaciones Matemáticas de Duración (Categorías vs. sys.duration)
        if duracion_param and not df_glosario.empty:
            # Forzamos numérico el tiempo de la ruta registrado originalmente en minutos
            minutos_ruta = pd.to_numeric(df_filtrado['tiempo_min'], errors='coerce').fillna(0)
            
            # SUB-CASO 4.1: Filtrado por Categorías Fijas mapeadas del Excel
            if isinstance(duracion_param, str) and duracion_param in ['corta', 'jornada', 'larga']:
                limite_corto = df_glosario[(df_glosario['entidad'].str.lower() == 'duracion') & (df_glosario['categoria'].str.lower() == 'corta')]['horas_limite'].max()
                limite_jornada = df_glosario[(df_glosario['entidad'].str.lower() == 'duracion') & (df_glosario['categoria'].str.lower() == 'jornada')]['horas_limite'].max()
                
                # Conversión defensiva a minutos con respaldos rígidos en caso de error
                min_corto = (limite_corto if limite_corto > 0 else 4.0) * 60
                min_jornada = (limite_jornada if limite_jornada > 0 else 9.0) * 60
                
                if duracion_param == 'corta':
                    df_filtrado = df_filtrado[minutos_ruta <= min_corto]
                elif duracion_param == 'jornada':
                    df_filtrado = df_filtrado[(minutos_ruta > min_corto) & (minutos_ruta <= min_jornada)]
                elif duracion_param == 'larga':
                    df_filtrado = df_filtrado[minutos_ruta > min_jornada]
                
                print(f"📊 [PERFIL_FILTRO] Filtro aplicado por categoría de tiempo: '{duracion_param}'", file=sys.stderr)
            
            # SUB-CASO 4.2: Filtrado por Ventana Numérica de Aproximación (sys.duration)
            else:
                try:
                    horas_solicitadas = 0.0
                    if isinstance(duracion_param, dict):
                        amount = duracion_param.get('amount', 0)
                        unit = str(duracion_param.get('unit', 'hora')).lower()
                        # Normalización de escala temporal (Minutos a Horas flotantes)
                        horas_solicitadas = float(amount) / 60.0 if 'min' in unit else float(amount)
                    else:
                        texto_limpio = ''.join(c for c in str(duracion_param) if c.isdigit() or c == '.')
                        if texto_limpio:
                            horas_solicitadas = float(texto_limpio)
                    
                    if horas_solicitadas > 0:
                        minutos_solicitados = horas_solicitadas * 60
                        # DEFENSA UX: Ventana de tolerancia de +/- 1 hora (+/- 60 minutos)
                        umbral_tolerancia = 60
                        min_bajo = max(0, minutos_solicitados - umbral_tolerancia)
                        min_alto = minutos_solicitados + umbral_tolerancia
                        
                        df_filtrado = df_filtrado[(minutos_ruta >= min_bajo) & (minutos_ruta <= min_alto)]
                        print(f"📊 [PERFIL_FILTRO] Ventana matemática aplicada: [{min_bajo} a {min_alto}] min. Quedan: {len(df_filtrado)} rutas.", file=sys.stderr)
                        
                        # Reasignamos de manera inversa para la posterior consulta estética del glosario
                        if horas_solicitadas <= 4:
                            duracion_param = "corta"
                        elif horas_solicitadas <= 9:
                            duracion_param = "jornada"
                        else:
                            duracion_param = "larga"
                
                except (ValueError, TypeError) as e:
                    print(f"⚠️ [PERFIL_FILTRO] Error analítico en duración numérica: {e}. Fallback a LIKE.", file=sys.stderr)
                    df_filtrado = df_filtrado[df_filtrado['tiempo_min'].str.contains(str(duracion_param), case=False, na=False)]

        # Validación final de registros resultantes
        if df_filtrado.empty:
            print("⚠️ [PERFIL_FILTRO] La consulta arrojó cero resultados tras aplicar los filtros.", file=sys.stderr)
            return {"fulfillmentText": "No encontré senderos registrados en el catálogo que cumplan exactamente con todas las condiciones propuestas."}

        # =====================================================================
        # CONSTRUCCIÓN DE LA RESPUESTA ENRIQUECIDA (UX TEXT)
        # =====================================================================
        encabezado = "Estan son los senderos que se consideran apropiados para las condiciones que se proponen.\n\n"
        bloques_senderos = []

        # Extraemos un máximo de 3 senderos para no saturar la interfaz del chat
        for _, row in df_filtrado.head(3).iterrows():
            texto_sendero = f"📍 Sendero entre {row['zona_origen']} and {row['zona_destino']} en el area de {row['area']}"
            
            # Recuperamos los campos extendidos garantizando textos limpios
            desc_ux = str(row.get('descripcion_ux', '')).strip()
            desc_web = str(row.get('contenido_web_text', row.get('descripcion_web', ''))).strip()
            tags = str(row.get('intereses_tags', '')).strip()
            variante = str(row.get('variante', row.get('nombre_variante', ''))).strip()

            if desc_ux and desc_ux.lower() != 'nan':
                texto_sendero += f"\n   • Resumen: {desc_ux}"
            if desc_web and desc_web.lower() != 'nan':
                texto_sendero += f"\n   • Detalle Web: {desc_web}"
            if tags and tags.lower() != 'nan':
                texto_sendero += f"\n   • Intereses asociados: {tags}"
            if variante and variante.lower() != 'nan' and variante != "":
                texto_sendero += f"\n   • Variante disponible: {variante}"
            
            bloques_senderos.append(texto_sendero)

        mensaje_final = encabezado + "\n\n".join(bloques_senderos)

        # =====================================================================
        # INYECCIÓN DINÁMICA DE DEFINICIONES (GLOSARIO DEL EXCEL)
        # =====================================================================
        notas_glosario = []
        
        if dificultad:
            def_dificultad = CatalogoRutas.obtener_definicion('dificultad', dificultad)
            if def_dificultad:
                notas_glosario.append(f"• Categoría {dificultad.capitalize()}: {def_dificultad}")

        if duracion_param and isinstance(duracion_param, str):
            def_duracion = CatalogoRutas.obtener_definicion('duracion', duracion_param)
            if def_duracion:
                notas_glosario.append(f"• Duración {duracion_param.capitalize()}: {def_duracion}")

        # Si se recuperaron aclaraciones del glosario, se anexan limpiamente abajo del todo
        if notas_glosario:
            mensaje_final += "\n\n📖 *Información técnica complementaria:* \n" + "\n".join(notas_glosario)

        print("✅ [PERFIL_FILTRO] Ejecución completada de forma exitosa.", file=sys.stderr)
        return {"fulfillmentText": mensaje_final}

    except Exception as e:
        print(f"❌ [PERFIL_FILTRO] Error crítico en tiempo de ejecución: {str(e)}", file=sys.stderr)
        return {"fulfillmentText": "Ocurrió un error interno al intentar procesar los filtros descriptivos del trayecto."}