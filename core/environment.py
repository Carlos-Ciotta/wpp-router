from pydantic_settings import BaseSettings


class EnvironmentSettings(BaseSettings):
    # MongoDB
    DATABASE_URI: str
    DATABASE_NAME: str
    # Redis
    REDIS_URL: str
    # WhatsApp Cloud API Configurações
    WHATSAPP_API_VERSION = "v24.0"
    WHATSAPP_API_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"

    # Credenciais (definir no .env)
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
    WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")

    # Webhook
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "meu_token_secreto_123")
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