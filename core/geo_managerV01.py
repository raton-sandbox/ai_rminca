
# Ejecutar python D:/AI_RMinca/geo_manager.py
# 20260615
# Archivo excel de entrada D:/AI_RMinca/catalogo_rutas.xlsx
# Json D:/AI_RMinca/conocimiento_maestro.json
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
MÓDULO CORE: core/geo_manager.py
PROPÓSITO: Singleton de datos geográficos con conversión estricta a cadenas (String-Only)
           y soporte de consultas base para lógica elástica/LIKE.
"""
import os
import json
import pandas as pd
import unicodedata
import sys

def sanitizar_cadena(texto):
    if texto is None:
        return ""
    s = str(texto).strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

class CatalogoRutas:
    _df_maestro = pd.DataFrame()
    _df_jerarquia = pd.DataFrame()
    RAICES_PROHIBIDAS = {"santa marta", "cienaga", "dibulla"}

    @classmethod
    def cargar_componentes(cls):
        ruta_json = r"D:/AI_RMinca/conocimiento_maestro.json"
        ruta_excel = r"D:/AI_RMinca/catalogo_rutas.xlsx"
        
        try:
            # 1. Carga del Master JSON - Tratamiento radical como STRING sin validación de tipos
            if os.path.exists(ruta_json):
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    json_puro = json.load(f)
                
                filas_limpias = []
                
                for id_ruta, bloques in json_puro.items():
                    datos_raw = bloques.get("datos_excel", {})
                    
                    # Forzar de forma plana que toda Key y todo Valor sea estrictamente un String
                    datos_ruta = {str(k).lower().strip(): str(v).strip() for k, v in datos_raw.items()}
                    
                    # Inyectar campos de identificación y narrativas como strings nativos
                    datos_ruta["id_ruta"] = str(id_ruta).strip()
                    datos_ruta["descripcion_narrativa"] = str(bloques.get("contenido_web", {}).get("descripcion_narrativa", "")).strip()
                    
                    filas_limpias.append(datos_ruta)
                
                cls._df_maestro = pd.DataFrame(filas_limpias)
                
                # Asegurar la existencia de los 21 atributos fijos en el DataFrame como cadenas
                atributos_fijos = [
                    "id_ruta", "grupo_conector", "nombre_variante", "perfil_ruta", 
                    "zona_origen", "zona_destino", "modo", "distancia_km", "tiempo_min", 
                    "dificultad", "relieve_tipo", "ascenso_mt", "descenso_mt", "circular", 
                    "opcion_vehiculo", "conecta_con", "intereses_tags", "descripcion_ux", 
                    "url", "costo_estimado_cop_pp", "area", "descripcion_narrativa"
                ]
                
                for col in atributos_fijos:
                    if col not in cls._df_maestro.columns:
                        cls._df_maestro[col] = ""
                
                # REQUISITO PILAR 7: Imprimir en el log de Flask el total de rutas cargadas
                print(f"[GEO_MANAGER] Éxito: {len(cls._df_maestro)} rutas operativas cargadas en el Singleton desde el Master JSON.", file=sys.stderr)
            else:
                print(f"❌ [CRÍTICO] No existe el archivo maestro físico en: {ruta_json}", file=sys.stderr)
                cls._df_maestro = pd.DataFrame()

            # 2. Carga de la Jerarquía Geográfica (Catálogo Excel)
            if os.path.exists(ruta_excel):
                cls._df_jerarquia = pd.read_excel(ruta_excel, sheet_name="Jerarquia_Geografica")
                cls._df_jerarquia.columns = [str(c).lower().strip() for c in cls._df_jerarquia.columns]
            else:
                print(f"❌ [CRÍTICO] No existe el catálogo excel de jerarquías en: {ruta_excel}", file=sys.stderr)
                cls._df_jerarquia = pd.DataFrame()

            return True
        except Exception as e:
            print(f"❌ [FALLO EN CADENA DE CARGA] Imposible inicializar GeoManager: {str(e)}", file=sys.stderr)
            return False

    @classmethod
    def obtener_matriz(cls):
        return cls._df_maestro

    @classmethod
    def obtener_sinonimos_directos(cls, zona_usuario):
        if cls._df_jerarquia.empty or not zona_usuario:
            return zona_usuario
        entrada_clean = sanitizar_cadena(zona_usuario)
        for _, fila in cls._df_jerarquia.iterrows():
            nodo_zona = str(fila.get('zona', '')).strip()
            sinonimos_raw = str(fila.get('sinonimos', '')).strip()
            if sanitizar_cadena(nodo_zona) == entrada_clean:
                return nodo_zona
            lista_sinonimos = [sanitizar_cadena(s) for s in sinonimos_raw.split(',') if s.strip()]
            if entrada_clean in lista_sinonimos:
                return nodo_zona
        return zona_usuario

    @classmethod
    def obtener_padre_permitido(cls, nodo_id):
        if cls._df_jerarquia.empty or not nodo_id:
            return None
        nodo_clean = sanitizar_cadena(nodo_id)
        df_nodo = cls._df_jerarquia[cls._df_jerarquia['zona'].astype(str).apply(sanitizar_cadena) == nodo_clean]
        if not df_nodo.empty:
            padre_candidato = str(df_nodo.iloc[0].get('padre', '')).strip()
            if sanitizar_cadena(padre_candidato) in cls.RAICES_PROHIBIDAS:
                return None
            return padre_candidato if padre_candidato and padre_candidato.lower() != 'nan' else None
        return None

    @classmethod
    def obtener_toda_la_familia_descendiente(cls, zona_busqueda):
        bolsa_familia = set()
        if not zona_busqueda:
            return bolsa_familia
        zona_canonica = cls.obtener_sinonimos_directos(zona_busqueda)
        bolsa_familia.add(sanitizar_cadena(zona_canonica))
        if cls._df_jerarquia.empty:
            return bolsa_familia

        df_padre = cls._df_jerarquia[cls._df_jerarquia['zona'].astype(str).apply(sanitizar_cadena) == sanitizar_cadena(zona_canonica)]
        if not df_padre.empty:
            for s in str(df_padre.iloc[0].get('sinonimos', '')).split(','):
                if s.strip(): bolsa_familia.add(sanitizar_cadena(s))

        df_hijos = cls._df_jerarquia[cls._df_jerarquia['padre'].astype(str).apply(sanitizar_cadena) == sanitizar_cadena(zona_canonica)]
        for _, fila_hijo in df_hijos.iterrows():
            hijo_nombre = str(fila_hijo.get('zona', '')).strip()
            bolsa_familia.add(sanitizar_cadena(hijo_nombre))
            for s in str(fila_hijo.get('sinonimos', '')).split(','):
                if s.strip(): bolsa_familia.add(sanitizar_cadena(s))
        return bolsa_familia