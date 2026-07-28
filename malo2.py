import json
import pandas as pd
from core.geo_manager import CatalogoRutas

# 1. Forzar carga
CatalogoRutas.cargar_componentes()

df_j = CatalogoRutas._hierarchy_data
df_m = CatalogoRutas._conocimiento_maestro

# 2. Ver qué hijos está encontrando el sistema para Minca y Bonda
hijos_m = df_j[df_j['padre'].astype(str).str.strip().str.lower() == 'minca']['zona'].tolist()
hijos_b = df_j[df_j['padre'].astype(str).str.strip().str.lower() == 'bonda']['zona'].tolist()

print("🔍 HIJOS ENCONTRADOS EN JERARQUÍA:")
print(f"Hijos de Minca en Jerarquía: {hijos_m}")
print(f"Hijos de Bonda en Jerarquía: {hijos_b}\n")

print("📊 MUESTRA DE ZONAS REALES EN EL MAESTRO (Primeras 10 filas):")
print(df_m[['zona_origen', 'zona_destino']].head(10))