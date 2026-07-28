
# Ejecutar python D:/AI_RMinca/geo_manager.py
# 20260615
# Archivo excel de entrada D:/AI_RMinca/catalogo_rutas.xlsx
# Json D:/AI_RMinca/conocimiento_maestro.json
# -*- coding: utf-8 -*-
"""
ARCHIVO: core/geo_manager.py
PROPÓSITO: Singleton centralizado para la gestión de la base de conocimiento maestra.
           Edición con trazabilidad quirúrgica paso a paso para detectar congelamientos.
"""
import pandas as pd
import json
import sys
import os

print(f"🚀 caspsss DEBUG")
def sanitizar_cadena(valor):
    # Forzamos flush=True para asegurarnos de que el mensaje salga instantáneamente a la consola
    print(f"🚀 [GEO_MANAGER] DEBUG: Ejecutando utilidad 'sanitizar_cadena' para el valor: '{valor}'", file=sys.stderr, flush=True)
    return str(valor).strip().lower() if valor else ""
print(f"🚀 Klasspsss DEBUG")
class CatalogoRutas:
    _matriz = pd.DataFrame()     
    _jerarquia = pd.DataFrame()  
    _glosario = pd.DataFrame()   
    print(f"🚀 Por ti asspsss DEBUG")
    @classmethod
    def cargar_componentes(cls):
        print("🔍 [GEO_MANAGER] DEBUG: Entrando al método 'cargar_componentes'", file=sys.stderr, flush=True)
        try:
            # ==========================================================
            # DIAGNÓSTICO 1: VALIDACIÓN DE RUTAS FÍSICAS
            # ==========================================================
            ruta_json = 'D:/AI_RMinca/conocimiento_maestro.json'
            ruta_excel = 'D:/AI_RMinca/catalogo_rutas.xlsx'
            
            print(f"📁 [GEO_MANAGER] DEBUG: Verificando archivos. ¿Existe JSON?: {os.path.exists(ruta_json)} | ¿Existe Excel?: {os.path.exists(ruta_excel)}", file=sys.stderr, flush=True)

            # ==========================================================
            # DIAGNÓSTICO 2: CARGA DEL JSON MAESTRO
            # ==========================================================
            print("⏳ [GEO_MANAGER] DEBUG: Intentando abrir archivo JSON...", file=sys.stderr, flush=True)
            with open(ruta_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ [GEO_MANAGER] DEBUG: JSON cargado con éxito. Elementos detectados: {len(data)}", file=sys.stderr, flush=True)
            
            print("⏳ [GEO_MANAGER] DEBUG: Iniciando aplanamiento del JSON...", file=sys.stderr, flush=True)
            lista_plana = []
            for id_ruta, contenido in data.items():
                fila = {"id_ruta": id_ruta}
                fila.update(contenido.get('datos_excel', {}))
                fila.update(contenido.get('contenido_web', {}))
                
                for key, val in fila.items():
                    if isinstance(val, list):
                        fila[key] = ", ".join(map(str, val))
                    else:
                        fila[key] = str(val)
                lista_plana.append(fila)
            
            df_json = pd.DataFrame(lista_plana)
            df_json.columns = df_json.columns.str.lower().str.strip()
            cls._matriz = df_json.astype(str).replace('nan', '', regex=True)
            print(f"✅ [GEO_MANAGER] DEBUG: Matriz de rutas aplanada en DataFrame. Forma: {cls._matriz.shape}", file=sys.stderr, flush=True)
            
            # ==========================================================
            # DIAGNÓSTICO 3: CARGA DEL EXCEL - HOJA JERARQUÍA
            # ==========================================================
            print(f"⏳ [GEO_MANAGER] DEBUG: Intentando invocar pd.read_excel para la hoja 'Jerarquia_Geografica'...", file=sys.stderr, flush=True)
            print("⚠️ [ADVERTENCIA] Si el script se detiene AQUÍ, significa que tienes el archivo Excel abierto en tu computadora. ¡Ciérralo!", file=sys.stderr, flush=True)
            
            cls._jerarquia = pd.read_excel(ruta_excel, sheet_name='Jerarquia_Geografica')
            print(f"✅ [GEO_MANAGER] DEBUG: Hoja 'Jerarquia_Geografica' leída con éxito. Registros: {len(cls._jerarquia)}", file=sys.stderr, flush=True)
            
            for col in cls._jerarquia.columns:
                cls._jerarquia[col] = cls._jerarquia[col].astype(str).str.strip().str.lower()
            print("✅ [GEO_MANAGER] DEBUG: Columnas de jerarquía normalizadas.", file=sys.stderr, flush=True)

            # ==========================================================
            # DIAGNÓSTICO 4: CARGA DEL EXCEL - HOJA DEFINICIONES
            # ==========================================================
            print("⏳ [GEO_MANAGER] DEBUG: Intentando leer la hoja 'Definiciones'...", file=sys.stderr, flush=True)
            df_glosario_raw = pd.read_excel(ruta_excel, sheet_name='Definiciones')
            print(f"✅ [GEO_MANAGER] DEBUG: Hoja 'Definiciones' leída. Filas iniciales: {len(df_glosario_raw)}", file=sys.stderr, flush=True)
            
            df_glosario_raw.columns = df_glosario_raw.columns.str.lower().str.strip()
            
            for col in ['entidad', 'categoria', 'definicion']:
                if col in df_glosario_raw.columns:
                    df_glosario_raw[col] = df_glosario_raw[col].astype(str).str.strip()
            
            print("⏳ [GEO_MANAGER] DEBUG: Procesando columna numérica 'horas_limite'...", file=sys.stderr, flush=True)
            if 'horas_limite' in df_glosario_raw.columns:
                df_glosario_raw['horas_limite'] = pd.to_numeric(df_glosario_raw['horas_limite'], errors='coerce').fillna(0.0)
            else:
                df_glosario_raw['horas_limite'] = 0.0
                print("⚠️ [GEO_MANAGER] ADVERTENCIA: La columna 'horas_limite' no existía en el Excel.", file=sys.stderr, flush=True)
            
            cls._glosario = df_glosario_raw
            print("✅ [GEO_MANAGER] DEBUG: Columna 'horas_limite' parseada con éxito.", file=sys.stderr, flush=True)
            
            print(f"🎉 [GEO_MANAGER] FINALIZADO CON ÉXITO: Rutas={len(cls._matriz)} | Jerarquías={len(cls._jerarquia)} | Glosario={len(cls._glosario)}", file=sys.stderr, flush=True)
            return True
            
        except Exception as e:
            print(f"❌ [GEO_MANAGER] ERROR CRÍTICO FATAL EN CARGA: {str(e)}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return False

    @classmethod
    def obtener_matriz(cls):
        return cls._matriz

    @classmethod
    def obtener_glosario(cls):
        return cls._glosario

    @classmethod
    def obtener_definicion(cls, entidad, categoria):
        if cls._glosario.empty:
            return ""
        filtro = (cls._glosario['entidad'].str.lower() == entidad.lower()) & \
                 (cls._glosario['categoria'].str.lower() == categoria.lower())
        sub_df = cls._glosario[filtro]
        if not sub_df.empty:
            return sub_df.iloc[0]['definicion']
        return ""

    @classmethod
    def obtener_sinonimos_directos(cls, zona):
        zona_sanitizada = sanitizar_cadena(zona)
        if cls._jerarquia.empty:
            return [zona_sanitizada]
        filtro = (cls._jerarquia['zona'] == zona_sanitizada) | (cls._jerarquia['sinonimos'].str.contains(zona_sanitizada, na=False))
        sub_df = cls._jerarquia[filtro]
        resultados = {zona_sanitizada}
        for _, row in sub_df.iterrows():
            resultados.add(row['zona'])
            if row['sinonimos'] and row['sinonimos'] != 'nan':
                for s in row['sinonimos'].split(','):
                    if s.strip():
                        resultados.add(s.strip())
        return list(resultados)

    @classmethod
    def obtener_padre_permitido(cls, nodo_id):
        nodo_sanitizado = sanitizar_cadena(nodo_id)
        if cls._jerarquia.empty:
            return None
        raices_bloqueadas = {'santa marta', 'ciénaga', 'dibulla', 'bonda', 'minca', 'guachaca', 'palomino'}
        filtro = cls._jerarquia['zona'] == nodo_sanitizado
        sub_df = cls._jerarquia[filtro]
        if not sub_df.empty:
            padre = sub_df.iloc[0]['padre']
            if padre and padre != 'nan' and padre not in raices_bloqueadas:
                return padre
        return None

    @classmethod
    def obtener_toda_la_familia_descendiente(cls, zona):
        zona_sanitizada = sanitizar_cadena(zona)
        familia = set(cls.obtener_sinonimos_directos(zona_sanitizada))
        if cls._jerarquia.empty:
            return list(familia)
        filtro_hijos = cls._jerarquia['padre'] == zona_sanitizada
        hijos_df = cls._jerarquia[filtro_hijos]
        for _, row in hijos_df.iterrows():
            hijo = row['zona']
            familia.add(hijo)
            if row['sinonimos'] and row['sinonimos'] != 'nan':
                for s in row['sinonimos'].split(','):
                    if s.strip():
                        familia.add(s.strip())
        return list(familia)