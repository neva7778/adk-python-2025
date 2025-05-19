# api_server.py

import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel # Para definir modelos de solicitud/respuesta
import uvicorn # El servidor ASGI

# Importa tu agente ADK y los componentes necesarios
import agent as adk_agent # Renombramos para evitar conflicto si tuvieras una variable 'agent'
from google.adk.runners import InMemoryRunner
from google.adk.sessions import Session as ADKSession # Renombrar para evitar conflicto con pydantic.Session
from google.genai.types import Content, Part

# --- Modelos Pydantic para la validación de datos de la API ---
class ChatRequest(BaseModel):
    session_id: str | None = None # Opcional, podríamos crear una nueva si no se provee
    message: str

class ChatResponse(BaseModel):
    session_id: str
    agent_reply: str
    tool_calls: list[str] | None = None # Opcional, para depuración

class SessionResponse(BaseModel):
    session_id: str
    message: str

# --- Inicialización de FastAPI y ADK Runner ---
app = FastAPI(title="Mi Agente ADK con FastAPI", version="0.1.0")

# Configuración global del runner y session_service del ADK
# Esto se inicializa una vez cuando la aplicación FastAPI arranca
adk_runner_instance = InMemoryRunner(
    agent=adk_agent.root_agent, # Usamos el root_agent de tu agent.py
    app_name="mi_agente_fastapi"
)
adk_session_service = adk_runner_instance.session_service

# Diccionario en memoria para mantener un seguimiento simple de las sesiones activas
# En una aplicación real, esto podría ser una base de datos o un almacén más robusto.
active_sessions: dict[str, ADKSession] = {}

# --- Endpoints de la API ---

@app.post("/create_session", response_model=SessionResponse, tags=["Session Management"])
async def create_adk_session(user_id: str = "default_user"):
    """
    Crea una nueva sesión de conversación con el agente ADK.
    Devuelve el ID de la sesión creada.
    """
    try:
        print(f"API: Solicitud para crear sesión para el usuario: {user_id}")
        new_session = adk_session_service.create_session(
            app_name=adk_runner_instance.app_name, user_id=user_id
        )
        active_sessions[new_session.id] = new_session # Guardar la sesión (opcional si el service lo hace)
        print(f"API: Sesión creada con ID: {new_session.id}")
        return SessionResponse(session_id=new_session.id, message="Sesión creada exitosamente.")
    except Exception as e:
        print(f"API Error creando sesión: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al crear sesión: {str(e)}")

@app.post("/chat", response_model=ChatResponse, tags=["Agent Interaction"])
async def chat_with_agent(request: ChatRequest):
    """
    Envía un mensaje al agente ADK dentro de una sesión existente
    o crea una nueva sesión si no se proporciona session_id.
    Devuelve la respuesta del agente.
    """
    session_id = request.session_id
    adk_session_obj: ADKSession | None = None

    if session_id and session_id in active_sessions:
        adk_session_obj = active_sessions[session_id]
        print(f"API: Usando sesión existente: {session_id} para mensaje: '{request.message}'")
    elif session_id: # Se proveyó un ID pero no lo tenemos, podría ser un error o una sesión antigua
        print(f"API: ID de sesión '{session_id}' provisto pero no encontrado en sesiones activas. Creando una nueva.")
        # Opcionalmente, podríamos devolver un error aquí si queremos que el cliente maneje sesiones estrictamente.
        # Para este ejemplo, crearemos una nueva si el ID no es válido.
        try:
            adk_session_obj = adk_session_service.create_session(app_name=adk_runner_instance.app_name, user_id="default_user_chat")
            active_sessions[adk_session_obj.id] = adk_session_obj
            session_id = adk_session_obj.id # Actualizar al nuevo ID de sesión
            print(f"API: Nueva sesión creada para chat: {session_id}")
        except Exception as e:
            print(f"API Error creando sesión para chat: {e}")
            raise HTTPException(status_code=500, detail="Error creando sesión para chat.")
    else: # No se proveyó session_id, crear una nueva
        try:
            print(f"API: No se proveyó ID de sesión. Creando una nueva para mensaje: '{request.message}'")
            adk_session_obj = adk_session_service.create_session(app_name=adk_runner_instance.app_name, user_id="default_user_chat")
            active_sessions[adk_session_obj.id] = adk_session_obj
            session_id = adk_session_obj.id # Guardar el nuevo ID de sesión
            print(f"API: Nueva sesión creada para chat: {session_id}")
        except Exception as e:
            print(f"API Error creando sesión para chat: {e}")
            raise HTTPException(status_code=500, detail="Error creando sesión para chat.")

    if not adk_session_obj or not session_id: # Doble chequeo
        raise HTTPException(status_code=500, detail="No se pudo obtener o crear una sesión válida.")

    user_content = Content(role='user', parts=[Part.from_text(text=request.message)])
    
    agent_reply_text = ""
    tool_calls_details = []

    try:
        print(f"API: Enviando al runner para sesión {session_id}: '{request.message}'")
        async for event in adk_runner_instance.run_async(
            user_id=adk_session_obj.user_id, # Usar el user_id de la sesión
            session_id=session_id,
            new_message=user_content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        agent_reply_text += part.text
                    if part.function_call:
                        tool_calls_details.append(f"Llamada a herramienta: {part.function_call.name}({part.function_call.args})")
                        print(f"API DEBUG: Agente llamó a herramienta -> {part.function_call.name}({part.function_call.args})")
        
        print(f"API: Respuesta del agente para sesión {session_id}: '{agent_reply_text}'")
        return ChatResponse(
            session_id=session_id, 
            agent_reply=agent_reply_text.strip(),
            tool_calls=tool_calls_details if tool_calls_details else None
        )
    except Exception as e:
        print(f"API Error durante la ejecución del agente: {e}")
        # Podrías querer registrar el traceback completo aquí: import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor durante la ejecución del agente: {str(e)}")

@app.get("/", tags=["General"])
async def read_root():
    """Endpoint raíz para verificar que el servidor está funcionando."""
    return {"message": "Servidor del Agente ADK está funcionando!"}

# --- Para ejecutar el servidor (si este script se ejecuta directamente) ---
if __name__ == "__main__":
    # Cargar variables de entorno (asegúrate que .env está presente para GOOGLE_API_KEY)
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    print("Iniciando servidor FastAPI con Uvicorn...")
    uvicorn.run(
        "api_server:app", # 'nombre_archivo:nombre_instancia_FastAPI'
        host="127.0.0.1", # Solo accesible localmente
        port=8000,        # Puerto estándar para desarrollo
        reload=True       # El servidor se reinicia automáticamente si cambias el código (útil para desarrollo)
    )
