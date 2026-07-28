from google import genai

# El cliente busca automáticamente la variable de entorno GEMINI_API_KEY
client = genai.Client()

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents='Dame una lista de 3 ideas para proyectos de Python.',
)

print(response.text)