from repositories.config import ConfigRepository

class ConfigService():
    def __init__(self, repo: ConfigRepository):
        self._repo = repo

    async def get_config(self):
        return await self._repo.get_config()

    async def save_config(self, config):
        return await self._repo.save_config(config)