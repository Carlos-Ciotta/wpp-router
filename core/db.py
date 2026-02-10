from motor.motor_asyncio import AsyncIOMotorClient
from core.environment import get_environment

# Load env
env = get_environment()

class MongoManager:
    def __init__(self):
        self._client: AsyncIOMotorClient | None = None
        self._uri = env.DATABASE_URI

    async def connect(self):
        """Establish MongoDB connection."""
        if not self._client:
            self._client = AsyncIOMotorClient(self._uri)
            print("MongoDB connected.")

    async def disconnect(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            print("MongoDB disconnected.")

    def get_client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client instance."""
        if not self._client:
            raise RuntimeError("MongoDB client not initialized. Call connect() first.")
        return self._client

    def get_db(self, db_name: str = None):
        """Get database instance."""
        client = self.get_client()
        database_name = db_name or env.DATABASE_NAME
        return client[database_name]

    def get_collection(self, collection_name: str, db_name: str = None):
        """Get collection instance."""
        db = self.get_db(db_name)
        return db[collection_name]


# Singleton instance
mongo_manager = MongoManager()