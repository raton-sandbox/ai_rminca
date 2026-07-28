# Ubicación: D:\AI_RMinca\app.py
"""
==============================================================================
PROYECTO: Ratón de Minca - Guía de Senderos (Sierra Nevada de Santa Marta)
ARCHIVO: app.py (API Web FastAPI - Producción 24/7)
TIMESTAMP: 2026-07-26T14:49:44-05:00
DESCRIPCIÓN: Exposición HTTP/REST del orquestador raton.py para Google Sites.
==============================================================================
"""
# 2026/07/26 14:36
import io
import sys
import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel



# Carga e inicialización de tu orquestador existente
from raton import CatalogoRutas, inicializar_listas_analiticas_ram, orquestar_pipeline

#NOmbre de la app para uvicorn
app = FastAPI(title="API Ratón de Minca 24/7")

# Configuración CORS para permitir peticiones desde Google Sites
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción puedes restringir al dominio de tu Google Site
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estructura del cuerpo de la petición
class UserQuery(BaseModel):
    prompt : str

# Inicialización al arrancar el servidor web en la nube
@app.on_event("startup")

def startup_event():
    # Invocación directa y segura de la función subyacente del classmethod
    # se puede regresar a la forma normal ()
    if CatalogoRutas.cargar_componentes.__func__(CatalogoRutas):
        inicializar_listas_analiticas_ram()
        print("🚀 [CLOUD BACKEND]: Base de datos RAM e IA Groq inicializadas")

@app.get("/")
def health_check():
    return {"status": "online", "service": "Raton de Minca API 24/7"}

@app.post("/chat")
def process_chat(query: UserQuery):
    user_text = query.prompt.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    # Intercepción de salida estándar para capturar la respuesta generada por raton.py
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    try:
        orquestar_pipeline(user_text, metadata_red={"ip": "cloud_client"})
        output_text = buffer.getvalue()
    except Exception as e:
        output_text = f"❌ Error interno del servidor: {str(e)}"
    finally:
        sys.stdout = old_stdout

    return {"respuesta": output_text, "reply": output_text}