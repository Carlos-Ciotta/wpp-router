"""Main application for the Documents service with async RabbitMQ integration."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routes.messages import get_message_ws

import json
from routes.chat_routes import admin_chat_ws, attendant_chat_ws
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
async def messages_websocket(websocket: WebSocket):
    await get_message_ws(websocket)

@app.websocket("/attendant/ws")
async def attendant_chat_websocket(websocket: WebSocket):
    await attendant_chat_ws(websocket)

@app.websocket("/admin/ws")
async def admin_chat_websocket(websocket: WebSocket):
    await admin_chat_ws(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host=env.HOST, port=env.PORT)