# -*- coding: utf-8 -*-
"""
Script de Verificación de Conectividad con la API de Groq
Version: 2.0.212
"""
import os
from groq import Groq

def verificar_sistema():
    # El SDK busca por defecto la variable de entorno 'GROQ_API_KEY'
    api_key = os.environ.get("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Error: La variable de entorno GROQ_API_KEY no está configurada.")
        return

    try:
        # Inicializar el cliente oficial
        client = Groq(api_key=api_key)
        
        # Ejecutar una consulta semántica mínima de prueba usando Llama 3.1
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": "Confirma con la palabra 'OK' si recibes este mensaje."
                }
            ],
            temperature=0.1
        )
        
        print("✅ ¡Instalación Exitosa!")
        print(f"Respuesta del servidor: {completion.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Error al conectar con el servidor de Groq: {str(e)}")

if __name__ == "__main__":
    verificar_sistema()