from motor.motor_asyncio import AsyncIOMotorDatabase

from core.environment import get_environment

env = get_environment()

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    messages = db.get_collection("messages")

    # Document indexes
    await messages.create_index("from_number", unique=True)