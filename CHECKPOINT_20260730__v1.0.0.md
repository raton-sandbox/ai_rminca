# Punto de Restauración y Versión Estable (Checkpoint v1.0.0)

**Proyecto:** `raton-sandbox/ai_rminca`  
**Entorno de Despliegue:** Render + GitHub Pages  
**Fecha:** 30 de Julio de 2026  
**Estado:** 🟢 Operativo / Estable en Producción  

---

## 📌 1. Resumen Ejecutivo

En este punto del desarrollo se ha logrado la sincronización completa del pipeline de persistencia de logs en GitHub desde el servicio en la nube (Render) y la ejecución correcta del cliente de pruebas (*frontend*) publicado en GitHub Pages.

Este documento establece la línea base (*baseline*) técnica y los comandos necesarios para crear un **Tag/Release** de Git que funcione como punto de restauración seguro.

---

## 🏗️ 2. Arquitectura y Componentes Validados

| Componente | Entorno | Nombre / Ruta | Estado |
| :--- | :--- | :--- | :--- |
| **Frontend** | GitHub Pages | `https://raton-sandbox.github.io/ai_rminca/testw.html` | Operativo |
| **Backend API** | Render | `https://ai-rminca.onrender.com/chat` | Operativo |
| **Código Fuente** | GitHub (Branch) | `main` | Limpio / Sin Rastreo de Logs |
| **Persistencia Data** | GitHub (Branch) | `data-logs` | Aislado / Persistencia Activa |
| **Endpoint API GitHub** | REST API v3 | `https://api.github.com/repos/raton-sandbox/ai_rminca/contents/interacciones_aprendizaje.jsonl?ref=data-logs` | HTTP 200/201 OK |

---

## ⚙️ 3. Configuración del Repositorio (`main` vs `data-logs`)

1. **Rama `main` (Código Fuente Exclusivo):**
   - Contiene únicamente la lógica de la API, scripts del bot (`raton_2.py`, `logger_aprendizaje_2.py`) e interfaz web (`testw.html`).
   - El archivo `interacciones_aprendizaje.jsonl` está **ignorado explícitamente** en `.gitignore` para evitar conflictos de *merge*.

2. **Rama `data-logs` (Base de Datos remota `.jsonl`):**
   - Rama dedicada a almacenar las interacciones de aprendizaje mediante llamadas HTTP `PUT` enviadas desde la API en Render.

---

## 🚀 4. Guía Paso a Paso para Congelar el Punto Seguro en Git

Ejecuta los siguientes comandos desde tu terminal local para congelar este estado mediante un **Git Tag**:

```bash
# 1. Posicionarte en la rama principal y asegurar sincronización
git checkout main
git pull origin main

# 2. Crear un Tag anotado con la versión estable
git tag -a v1.0.0 -m "Release Estable: Integración Render + GitHub API + GitHub Pages"

# 3. Subir el Tag al repositorio remoto
git push origin v1.0.0
```

---

## 🔄 5. Protocolo de Restauración (En caso de fallos futuros)

Si en desarrollos posteriores se introduce una regresión o error crítico, puedes volver inmediatamente a este estado ejecutando:

```bash
# Volver al estado exacto del Tag v1.0.0 en una nueva rama de recuperación
git checkout -b fix-restauracion v1.0.0

# O restablecer la rama main al commit del Tag
git reset --hard v1.0.0
git push origin main --force
```

---

*Documento generado automáticamente para el repositorio `raton-sandbox/ai_rminca`.*
