
# Ejecutar python D:/AI_RMinca/geo_manager.py
# 20260615
# Archivo excel de entrada D:/AI_RMinca/catalogo_rutas.xlsx
# Json D:/AI_RMinca/conocimiento_maestro.json
# -*- coding: utf-8 -*-
"""
Módulo Core: Administrador de Catálogos Geográficos y Datos Maestros
Versión: 2.2.0 - Sincronización de Glosario Matricial de Errores
Timestamp: 2026-07-05T09:35:00-05:00
"""
import os
import json
import re
import os
import difflib
import pandas as pd

class CatalogoRutas:
    # Atributos de clase para persistencia en memoria RAM
    _hierarchy_data = None      # DataFrame de jerarquia_geografica.json
    _conocimiento_maestro = None # DataFrame de conocimiento_maestro.json
    _glosario = None            # DataFrame de definiciones.json / glosario

    @classmethod
    @classmethod
    def cargar_componentes(cls) -> bool:
        """
        Carga de manera segura todos los archivos JSON del sistema a la memoria RAM.
        Devuelve True si la inicialización de vectores fue exitosa.
        """
        # Obtiene la ruta del directorio base del proyecto
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        #path_jerarquia = 'D:/AI_RMinca/jerarquia_geografica.json'
        #path_maestro =   'D:/AI_RMinca/conocimiento_maestro.json'
        #path_glosario = 'D:/AI_RMinca/definiciones.json' 
        path_jerarquia = os.path.join(BASE_DIR, 'jerarquia_geografica.json')
        path_maestro   = os.path.join(BASE_DIR, 'conocimiento_maestro.json')
        path_glosario  = os.path.join(BASE_DIR, 'definiciones.json')

        try:
            # 1. Cargar Jerarquía Territorial
            if os.path.exists(path_jerarquia):
                with open(path_jerarquia, 'r', encoding='utf-8') as f:
                    cls._hierarchy_data = pd.DataFrame(json.load(f))
            else:
                print(f"❌ Archivo no encontrado: {path_jerarquia}")
                return False

            # 2. Cargar Conocimiento Maestro (Estructura compleja de bloques)
            if os.path.exists(path_maestro):
                with open(path_maestro, 'r', encoding='utf-8') as f:
                    maestro_raw = json.load(f)
                lista_rutas = []
                for id_ruta, bloques in maestro_raw.items():
                    row = bloques.get('datos_excel', {}).copy()
                    
                    # CORRECCIÓN: Mantener la URL de 'datos_excel' si existe.
                    # Si no está presente, buscar en 'contenido_web' o 'datos_web' como fallback.
                    url_excel = row.get('url', '')
                    url_web = (
                        bloques.get('contenido_web', {}).get('url_referencia', '') or 
                        bloques.get('datos_web', {}).get('url_referencia', '')
                    )
                    row['url'] = (url_excel or url_web).strip()
                    row['id_ruta'] = str(id_ruta).strip()
                    lista_rutas.append(row)

                cls._conocimiento_maestro = pd.DataFrame(lista_rutas)

                # CONTROL Y DEPURACIÓN
                print("\n================ DEPURACIÓN: CONOCIMIENTO MAESTRO ================")
                print(f"📊 Cantidad total de filas cargadas: {len(cls._conocimiento_maestro)}")
                print("🔍 Muestra de las primeras 10 filas (id_ruta, area, url):")
                columns_to_show = [col for col in ['id_ruta', 'area', 'url'] if col in cls._conocimiento_maestro.columns]
                print(cls._conocimiento_maestro[columns_to_show].head(10).to_string(index=False))
                print("==================================================================\n")

            else:
                print(f"❌ Archivo no encontrado: {path_maestro}")
                return False

            # 3. Cargar Glosario de Errores Dinámicos sin fallbacks integrados
            if os.path.exists(path_glosario):
                with open(path_glosario, 'r', encoding='utf-8') as f:
                    cls._glosario = pd.DataFrame(json.load(f))
            else:
                print(f"❌ Archivo no encontrado: {path_glosario}")
                return False

            print("✅ [RAM INITIALIZATION COMPLETE] Todos los catálogos mapeados en memoria.")
            return True

        except FileNotFoundError as fnf:
            print(f"❌ Error crítico: Ausencia de archivo de definiciones requerido: {fnf}")
            return False
        except Exception as e:
            print(f"❌ Error crítico en geo_manager.py al levantar componentes: {e}")
            return False
    @classmethod
    def normalizar_entidad_geografica(cls, texto_usuario: str, umbral: float = 0.70) -> str:
        """
        AUTENTICADOR DE LUGARES: Analiza un string de entrada, colapsa múltiples
        espacios en blanco internos y tabulaciones accidentales, y realiza una 
        búsqueda exacta (indexada) o elástica (difusa) sobre la base de sinónimos.
        """
        if cls._hierarchy_data is None or cls._hierarchy_data.empty:
            return texto_usuario.strip() if texto_usuario else ""

        if not texto_usuario:
            return ""

        texto_clean = re.sub(r'\s+', ' ', texto_usuario).strip().lower()

        # Paso 1: Match indexado rápido por Regex estructurado sobre la columna 'sinonimos'
        filtro_exacto = cls._hierarchy_data['sinonimos'].str.lower().str.contains(
            f"(?:^|,)\\s*{re.escape(texto_clean)}\\s*(?:,|$)", na=False, regex=True
        )
        if filtro_exacto.any():
            return cls._hierarchy_data[filtro_exacto].iloc[0]['zona'].strip()

        # Paso 2: Construcción del árbol inverso para Fuzzy Match
        todos_los_sinonimos = []
        mapeo_sinonimo_a_zona = {}
        
        for _, row in cls._hierarchy_data.dropna(subset=['sinonimos']).iterrows():
            zona_oficial = row['zona'].strip()
            lista_s = [re.sub(r'\s+', ' ', s).strip().lower() for s in row['sinonimos'].split(',') if s.strip()]
            
            for sinonimo in lista_s:
                todos_los_sinonimos.append(sinonimo)
                mapeo_sinonimo_a_zona[sinonimo] = zona_oficial

        # Paso 3: Motor matemático de distancia de Levenshtein
        coincidencias = difflib.get_close_matches(texto_clean, todos_los_sinonimos, n=1, cutoff=umbral)
        
        if coincidencias:
            return mapeo_sinonimo_a_zona[coincidencias[0]]

        return texto_clean