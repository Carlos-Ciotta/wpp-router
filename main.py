"""Main application for the Documents service with async RabbitMQ integration."""

from fastapi import FastAPI, WebSocket
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
        """Websocket endpoint to get the last chat of each client in the system. Permission: admin."""
        # Injetamos o serviço manualmente pois Depends não funciona dentro do while True
        await websocket.accept()

        auth_header = websocket.headers.get("authorization")
        print(f"DEBUG: Header recebido: {auth_header}")
        if not auth_header:
            await websocket.close(code=1008) # Policy Violation
            return None
        try:
            # Resolve dependencies at runtime (websockets can't use Depends inside loop)
            security = get_security()
            message_service = get_message_service()

            # 3. Limpar o prefixo 'Bearer ' se existir
            # Diferente do Depends, aqui recebemos a string bruta: "Bearer <token>"
            token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else auth_header

            # 4. Validar o token (usando a string limpa)
            decoded = await security.verify_permission(token, required_roles=["admin", "user"])
            attendant_id = decoded.get("_id")
            
        except Exception as e:
            # Se o token for inválido ou não tiver permissão
            await websocket.send_json({"type": "error", "message": "Unauthorized"})
            await websocket.close(code=1008)
            return None
        
        if not token:
            await websocket.close(code=1008)
            return None

        await manager.connect(attendant_id, websocket)
        try: 
            while True:
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)
                
                action = data.get("action") # ex: "get_chats", "update_chat"

                try:
                    result = await message_service.get_messages_by_phone(raw_data.get("phone"))

                    response = {
                        "type": "success",
                        "action": action,
                        "data": result
                    }

                    await manager.send_personal_message(response, attendant_id)

                except Exception as e:
                    await manager.send_personal_message({
                        "type": "error",
                        "action": action,
                        "message": str(e)
                    }, attendant_id)

                    manager.disconnect(attendant_id)
                    break
        except Exception as e:
            manager.disconnect(attendant_id)
            return None

if __name__ == "__main__":
    uvicorn.run(app, host=env.HOST, port=env.PORT)