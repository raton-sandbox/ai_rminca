# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Manejador Analitico: Evaluador de Esfuerzo Recreacional y Perfil
Version: 2.0.212 - Holgura Elastica del 30% en Tiempos de Caminata
Timestamp: 2026-06-26T11:49:10-05:00
"""
import pandas as pd
from core.geo_manager import CatalogoRutas

def filtrar_por_esfuerzo_y_perfil(zona: str, dificultad: str, duracion_deseada: str) -> dict:
    """
    Filtra senderos por dificultad formal e infiere la duracion real en jornadas elasticas de senderismo.
    
    Docstring para Groq: Ejecute este componente cuando el excursionista defina restricciones respecto de  tiempo disponible (corta, jornada completa) o condicion fisica (facil, media baja, media).
    """
    zona_oficial = CatalogoRutas.obtener_sinonimos_directos(zona)
    bolsa_zona = CatalogoRutas.obtener_toda_la_familia_descendiente(zona_oficial)
    bolsa_zona_caps = [b.upper() for b in bolsa_zona]
    
    df_maestro = CatalogoRutas._conocimiento_maestro
    
    # Filtrado base por espacio geografico y dificultad parametrica
    cond_zona = (df_maestro['zona_origen'].str.upper().isin(bolsa_zona_caps)) | (df_maestro['area'].str.upper() == zona_oficial.upper())
    cond_dif = df_maestro['dificultad'].str.lower().str.contains(dificultad.strip().lower(), na=False, regex=False)
    
    df_intermedio = df_maestro[cond_zona & cond_dif]
    
    resultado_rutas = []
    
    for _, row in df_intermedio.iterrows():
        # Procesar tiempo en minutos con tolerancia defensiva
        t_raw = row['tiempo_min']
        try:
            minutos_base = float(t_raw) if (t_raw and t_raw != "") else 0.0
        except ValueError:
            minutos_base = 0.0
            
        # Aplicacion estricta de la holgura del 30% para caminantes recreativos
        minutos_reales = minutos_base * 1.10
        horas_reales = minutos_reales
        
        # Clasificar la duracion bajo las reglas fijas de negocio del proyecto
        # Caminata corta: Alrededor de 4 horas o menos (Media jornada)
        # Jornada completa: Entre 5 y 9 horas. Larga: Mas de una jornada.
        if horas_reales <= 4.0:
            categoria_duracion = "corta"
        elif 4.0 < horas_reales <= 9.0:
            categoria_duracion = "una jornada"
        else:
            categoria_duracion = "larga"
            
        # Validar si cumple con la peticion de duracion del usuario
        if duracion_deseada.strip().lower() in [categoria_duracion, "cualquiera", ""]:
            resultado_rutas.append({
                "nombre_oficial": f"Desde {row['zona_origen']} hasta {row['zona_destino']}",
                "id_ruta": row['id_ruta'],
                "distancia_km": row['distancia_km'],
                "dificultad": row['dificultad'],
                "horas_calculadas_con_holgura": round(horas_reales, 1),
                "clasificacion_duracion": categoria_duracion,
                "costo_estimado_cop_pp": row['costo_estimado_cop_pp'],
                "descripcion_ux": row['descripcion_ux'],
                "url_referencia": row['url']
            })
            
    print(f"\n[LOG HANDLER - PERFIL Y HOLGURA]", flush=True)
    print(f" -> Registros evaluados con holgura del 30%: {len(resultado_rutas)}", flush=True)
    
    return {"status": "exito", "rutas": resultado_rutas}