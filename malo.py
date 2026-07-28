# -*- coding: utf-8 -*-
import os
import sys

print("🔍 --- DETECTIVE DE IMPORTACIONES DE PYTHON ---")

# 1. Validar nombres exactos en el disco (Sensibilidad a mayúsculas)
print("\n1. Inspeccionando nombres exactos en la raíz:")
for item in os.listdir('.'):
    if item.lower() == 'handlers':
        print(f"   • Encontrado: '{item}' (Para evitar errores DEBE ser exactamente 'handlers' en minúsculas)")

# 2. Validar si es un archivo sombra o una carpeta
try:
    import handlers
    print(f"\n2. ¿Desde dónde está cargando Python el módulo 'handlers'?:")
    print(f"   📍 Ruta física real: {handlers.__file__}")
    if not os.path.isdir('handlers'):
        print("   ⚠️ ALERTA: 'handlers' está siendo leído como un archivo, no como una carpeta.")
except Exception as e:
    print(f"\n2. ❌ Error al cargar la carpeta base 'handlers': {e}")

# 3. Intentar romper la importación del script del Intent
print("\n3. Intentando compilar 'origen_destino.py' de forma aislada:")
try:
    from handlers import origen_destino
    print("   ✅ ÉXITO ABSOLUTO: Python ya puede leer el archivo y compilarlo.")
except Exception as e:
    print("   ❌ FALLO CRÍTICO:")
    import traceback
    traceback.print_exc()

print("\n------------------------------------------------")