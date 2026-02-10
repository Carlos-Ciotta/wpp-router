"""Main application for the Documents service with async RabbitMQ integration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from core.dependencies import get_event_consumer
from core.indexes import ensure_indexes
from core.db import mongo_manager
from core.environment import get_environment
from infrastructure.messaging.rabbitmq import RabbitMQBroker

env = get_environment()

event_consumer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    global event_consumer
    
    # Startup
    await mongo_manager.connect()
    
    try:
        db = mongo_manager.get_db(db_name=env.DATABASE_NAME)
        await ensure_indexes(db)
    except Exception:
        pass
    
    # Start RabbitMQ consumer (documents)
    try:
        event_consumer = await get_event_consumer()
        await event_consumer.start()
    except Exception as err:
        print(f"[Documents Main] Failed to start event consumer: {err}")
    
    yield
    
    # Shutdown
    if event_consumer:
        try:
            await event_consumer.stop()
        except Exception:
            pass
    
    await mongo_manager.disconnect()


app = FastAPI(title="Documents Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    try:
        broker = RabbitMQBroker()
        await broker.connect()
        await broker.close()
        mq = "ok"
    except Exception:
        mq = "down"
    return {"status": "ok", "rabbitmq": mq}


if __name__ == "__main__":
    uvicorn.run(app, host=env.HOST, port=env.PORT)