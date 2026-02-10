from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Documents Service"
    ENV: str = "development"
    
    DATABASE_NAME: str = "documents"
    # Web server config
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security / operational
    REQUEST_TIMEOUT: int = 5  # seconds for outgoing requests

    # Pydantic v2 requires model_config instead of Config
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow",  # <— ESSENCIAL para não quebrar com variáveis extras do .env
    }


settings = Settings()