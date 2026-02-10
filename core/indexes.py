from motor.motor_asyncio import AsyncIOMotorDatabase

from core.environment import get_environment

env = get_environment()

async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    documents = db.get_collection("documents")

    # Document indexes
    await documents.create_index("_id", unique=True)
    await documents.create_index("company_id", unique=True)
    await documents.create_index("responsible_id", unique=True)
    await documents.create_index("status", unique=True)
    await documents.create_index("_type", unique=True)
    await documents.create_index("external_code")
    await documents.create_index([("created_at", -1)])