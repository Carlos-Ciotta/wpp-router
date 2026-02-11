from pydantic_settings import BaseSettings


class EnvironmentSettings(BaseSettings):
    # MongoDB
    DATABASE_URI: str
    DATABASE_NAME: str

    # Credenciais (definir no .env)
    WHATSAPP_PHONE_ID: str
    WHATSAPP_BUSINESS_ACCOUNT_ID: str
    WHATSAPP_TOKEN: str
    WHATSAPP_INTERNAL_TOKEN:str

    REDIS_URL: str
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "allow",
    }


def get_environment() -> EnvironmentSettings:
    return EnvironmentSettings()