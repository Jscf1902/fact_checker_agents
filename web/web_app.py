# web/web_app.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys

# --------------------------------------------------------------
# IMPORTS Y PATHS
# --------------------------------------------------------------

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from supervisor.coordinator import run_query

# --------------------------------------------------------------
# CONFIGURACIÓN FASTAPI
# --------------------------------------------------------------

app = FastAPI(title="Fact Checker Agents – Web UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar carpeta estática (CSS, JS)
STATIC_DIR = os.path.join(ROOT_DIR, "web", "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Path del archivo HTML
CHAT_HTML = os.path.join(ROOT_DIR, "web", "templates", "chat.html")

# --------------------------------------------------------------
# MODELO PARA EL INPUT DEL CHAT
# --------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str

# --------------------------------------------------------------
# RUTAS: SERVIR HTML
# --------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/chat", response_class=HTMLResponse)
def serve_chat():
    if not os.path.exists(CHAT_HTML):
        return HTMLResponse("<h2>Error: chat.html no encontrado</h2>", status_code=500)

    return FileResponse(CHAT_HTML)

# --------------------------------------------------------------
# API DEL CHAT
# --------------------------------------------------------------

@app.post("/api/chat")
async def chat_api(request: Request):
    try:
        data = await request.json()

        # Aceptar message o query
        user_query = data.get("message") or data.get("query")

        if not user_query:
            return JSONResponse({"error": "Mensaje vacío"}, status_code=400)

        print(f"🧠 Recibido del usuario: {user_query}")

        response = await run_query(user_query)

        return JSONResponse({"response": response})

    except Exception as e:
        print(f"❌ Error interno en /api/chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


