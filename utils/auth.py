# core/auth_core.py
from jose import jwt, JWTError, ExpiredSignatureError
from core import security
from services.attendant_service import AttendantService
import logging

logger = logging.getLogger(__name__)

async def verify_token_payload(token: str, service: AttendantService) -> dict:
    """
    Decodifica o token e valida contra o cache (Redis).
    Retorna o payload se válido, ou lança exceções específicas.
    """
    try:
        # 1. Decodifica JWT
        payload = jwt.decode(
            token, 
            security.SECRET_KEY, 
            algorithms=[security.ALGORITHM]
        )
        
        attendant_id = payload.get("_id")
        if not attendant_id:
            raise ValueError("Token inválido: Payload sem ID")

        # 2. Valida no Cache (Redis)
        # Passamos o token limpo para o serviço validar
        is_valid = await service.verify_token(token, attendant_id)
        
        if not is_valid:
            raise ValueError("Sessão invalidada ou expirada (Cache miss)")

        return payload

    except ExpiredSignatureError:
        raise ValueError("Token expirado")
    except JWTError as e:
        raise ValueError(f"Erro de decodificação: {str(e)}")