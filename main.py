"""Main application for the Documents service with async RabbitMQ integration."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from contextlib import asynccontextmanager
from core.websocket import manager
from core.indexes import ensure_indexes
from core.db import mongo_manager
from core.environment import get_environment
from core.dependencies import (get_clients,
                                get_cache,
                                get_repositories,
                                get_security,
                                get_chat_service, 
                                get_config_service,
                                get_attendant_service,
                                get_contact_service,
                                get_db_collection,
                                get_message_service,
                                get_settings)

env = get_environment()
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    
    # Startup s
    await mongo_manager.connect()

    try:
        db = mongo_manager.get_db(db_name=env.DATABASE_NAME)
        await ensure_indexes(db)
    except Exception:
        pass
    
    # Initialize async dependency factories after DB is connected so they
    # don't try to access the DB before `mongo_manager.connect()` runs.
    try:
        await get_config_service()
        await get_message_service()
        await get_contact_service()
        await get_attendant_service()
        await get_chat_service()
        await get_cache()
        await get_repositories()
        await get_security()
        await get_clients()
        # `get_settings()` is synchronous; call it to ensure settings are loaded
        get_settings()
    except Exception:
        # Ignore initialization errors here; individual endpoints will surface problems.
        pass

    yield

    await mongo_manager.disconnect()

from routes.webhook import router as webhook_router
from routes.attendants import router as attendants_router
from routes.config import router as config_router
from routes.chat_routes import router as chats_router
from routes.messages import router as messages_router
from routes.contacts import router as contacts_router


app = FastAPI(title="Whatsapp Cloud API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(attendants_router)
app.include_router(config_router)
app.include_router(chats_router)
app.include_router(messages_router)
app.include_router(contacts_router)

@app.websocket("/messages/ws")
async def get_message_by_phone_ws(websocket: WebSocket):
    await websocket.accept()
    
    auth_header = websocket.headers.get("authorization")
    attendant_id = None
    stop_event = asyncio.Event() # Sinaliza para as tasks pararem ao desconectar

    try:
        # --- Autenticação e Setup ---
        security = get_security() # Injeção manual
        message_service = get_message_service() # Injeção manual
        token = auth_header.replace("Bearer ", "") if auth_header and "Bearer " in auth_header else auth_header
        
        decoded = await security.verify_permission(token, allowed_permissions=["admin", "user"])
        attendant_id = str(decoded.get("_id"))
        await manager.connect(attendant_id, websocket)

        # --- Handshake Inicial ---
        # O cliente deve enviar primeiro: {"action": "start", "phone": "..."}
        raw_init = await websocket.receive_text()
        init_data = json.loads(raw_init)
        target_phone = init_data.get("phone")

        if not target_phone:
            await websocket.close(code=1008)
            return

        # 1. Carga Inicial (Últimas 50)
        initial_msgs = await message_service.get_messages_by_phone(target_phone, limit=50)
        await websocket.send_json({"type": "initial", "data": initial_msgs})

        # --- Task de Watcher (Background) ---
        async def watch_task():
            """Task que fica 'pendurada' no banco esperando novas mensagens."""
            try:
                async for new_msg in message_service.stream_new_messages(target_phone):
                    if stop_event.is_set():
                        break
                    await manager.send_personal_message({
                        "type": "new_message", 
                        "data": new_msg
                    }, attendant_id)
            except Exception as e:
                print(f"Watcher error: {e}")

        # Inicia o monitoramento em paralelo
        bg_task = asyncio.create_task(watch_task())

        # --- Loop de Comandos (Ouve o Cliente) ---
        while True:
            # Aqui o código fica livre para receber pedidos de 'histórico'
            client_msg = await websocket.receive_text()
            data = json.loads(client_msg)
            
            if data.get("action") == "load_history":
                last_ts = data.get("last_timestamp")
                history = await message_service.get_history(target_phone, last_ts)
                
                await manager.send_personal_message({
                    "type": "history",
                    "data": history
                }, attendant_id)

    except WebSocketDisconnect:
        print(f"Conexão encerrada: {attendant_id}")
    except Exception as e:
        print(f"Erro no WebSocket: {e}")
    finally:
        stop_event.set() # Para a task do banco
        if attendant_id:
            manager.disconnect(attendant_id)

if __name__ == "__main__":
    uvicorn.run(app, host=env.HOST, port=env.PORT)