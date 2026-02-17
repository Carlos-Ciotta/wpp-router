from motor.motor_asyncio import AsyncIOMotorDatabase

from core.environment import get_environment

env = get_environment()

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    messages = db.get_collection("messages")
    chats = db.get_collection("chats")

    await chats.create_index("phone_number", unique=True)
    await chats.create_index("attendant_id")
    # Garante índice único pelo ID da mensagem (WAMID)
    await messages.create_index("message_id", unique=True)
    
    # Índice para buscas por remetente (não único!)
    try:
        await messages.drop_index("from_number_1")
    except:
        pass
        
    await messages.create_index("from")