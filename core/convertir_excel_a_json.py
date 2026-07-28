# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Utilidad Core: Conversor Directo de Excel (XLSX) a JSON Estándar UTF-8
jerarquia y definiciones
Versión: 2.0.0
"""
import os
import json
import pandas as pd

def migrar_hojas_excel_a_json():
    # Ruta estricta al libro de Excel maestro
    path_excel = 'D:/AI_RMinca/core/catalogo_rutas.xlsx'
    
    # Rutas de destino para los archivos JSON limpios
    path_jerarquia_out = 'D:/AI_RMinca/core/jerarquia_geografica.json'
    path_definiciones_out = 'D:/AI_RMinca/core/definiciones.json'

    print(f"[PROCESO] Abriendo el libro de Excel en: {path_excel}", flush=True)

    if not os.path.exists(path_excel):
        print(f"❌ [ERROR] El archivo Excel no existe en la ruta especificada.")
        return

    # 1. Procesamiento directo de la hoja 'Jerarquia_geografica'
    try:
        print(" -> Leyendo pestaña 'Jerarquia_Geografica'...", end="", flush=True)
        # Se lee la hoja del libro directamente de forma binaria en RAM
        df_j = pd.read_excel(path_excel, sheet_name='Jerarquia_Geografica')
        
        # Estandarización defensiva de nombres de columnas a minúsculas
        df_j.columns = df_j.columns.str.strip().str.lower()
        # Remoción de espacios fantasmas y parseo de nulos a cadenas vacías
        df_j = df_j.map(lambda x: str(x).strip() if pd.notnull(x) else "")
        
        # Conversión a registros nativos de Python
        lista_jerarquia = df_j.to_dict(orient='records')
        
        # Volcado a JSON forzando UTF-8 puro sin caracteres de escape Unicode
        with open(path_jerarquia_out, 'w', encoding='utf-8') as f:
            json.dump(lista_jerarquia, f, indent=4, ensure_ascii=False)
        print(f" ¡ÉXITO! -> {os.path.basename(path_jerarquia_out)} ({len(lista_jerarquia)} registros).")
        
    except ValueError:
        print(" ❌ [FALLO]: No se encontró una pestaña llamada 'Jerarquia_geografica' en el archivo.")
    except Exception as e:
        print(f" ❌ [FALLO INESPERADO]: {str(e)}")

    # 2. Procesamiento directo de la hoja 'Definiciones'
    try:
        print(" -> Leyendo pestaña 'Definiciones'...", end="", flush=True)
        df_d = pd.read_excel(path_excel, sheet_name='Definiciones')
        
        df_d.columns = df_d.columns.str.strip().str.lower()
        df_d = df_d.map(lambda x: str(x).strip() if pd.notnull(x) else "")
        
        lista_definiciones = df_d.to_dict(orient='records')
        
        with open(path_definiciones_out, 'w', encoding='utf-8') as f:
            json.dump(lista_definiciones, f, indent=4, ensure_ascii=False)
        print(f" ¡ÉXITO! -> {os.path.basename(path_definiciones_out)} ({len(lista_definiciones)} registros).")
        
    except ValueError:
        print(" ❌ [FALLO]: No se encontró una pestaña llamada 'Definiciones' en el archivo.")
    except Exception as e:
        print(f" ❌ [FALLO INESPERADO]: {str(e)}")

if __name__ == "__main__":
    print("=== PIPELINE DE EXTRACCIÓN DIRECTA XLSX -> JSON ===")
    migrar_hojas_excel_a_json()