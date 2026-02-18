from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from core.dependencies import get_attendant_service, get_security
from typing import List, Optional, Dict
from pydantic import BaseModel


fastapi_security = HTTPBearer()

# --- Schemas ---
class WorkIntervalSchema(BaseModel):
    start: str
    end: str


class AttendantCreate(BaseModel):
    name: str
    login: str
    password: str
    permission: str
    sector: List[str]
    clients: List[str] = []
    welcome_message: Optional[str] = None
    working_hours: Optional[Dict[str, List[WorkIntervalSchema]]] = None


class AttendantRoutes():
    def __init__(self):
        self.router = APIRouter(prefix="/attendants", tags=["Attendants"])
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="attendants/login")
        # avoid calling dependency factories at import time
        self._attendant_service = None
        self._security = None
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.create_attendant, methods=["POST"], status_code=status.HTTP_201_CREATED)
        self.router.add_api_route("/login", self.login, methods=["POST"], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/logout", self.logout, methods=["POST"], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/verify-token", self.verify_token, methods=["POST"], status_code=status.HTTP_200_OK)
        self.router.add_api_route("/", self.list_attendants, methods=["GET"], response_model=List[dict], status_code=status.HTTP_200_OK)

    async def create_attendant(
        self,
        attendant: AttendantCreate = Body(...),
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Cria um novo atendente.
        """
        security = get_security()
        attendant_service = get_attendant_service()
        await security.verify_permission(token.credentials, ["admin"])
        result = await attendant_service.create_attendant(attendant.model_dump())
        return {"id": str(result), "message": "Attendant created successfully"}

    async def login(self,
        self_form_data: OAuth2PasswordRequestForm = Depends()
    ):
        """
        Realiza login e retorna token JWT.
        """
        attendant_service = get_attendant_service()
        attendant = await attendant_service.authenticate_attendant(self_form_data.username, self_form_data.password)
        if not attendant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await attendant_service.create_token_for_attendant(attendant)

    async def logout(self,
        attendant_id: str = Query(..., description="ID do atendente a ser deslogado"),
    ):
        attendant_service = get_attendant_service()
        await attendant_service.logout(attendant_id)

    async def verify_token(self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="attendants/login")),
        attendant_id: str = Depends(OAuth2PasswordBearer(tokenUrl="attendants/login")),
    ):
        attendant_service = get_attendant_service()
        token = await attendant_service.verify_token(token, attendant_id)

    async def list_attendants(self,
        token: HTTPAuthorizationCredentials = Depends(fastapi_security),
    ):
        """
        Lista todos os atendentes.
        """
        security = get_security()
        attendant_service = get_attendant_service()
        await security.verify_permission(token.credentials, ["admin"])
        attendants = await attendant_service.list_attendants()
        for att in attendants:
            if "_id" in att:
                att["_id"] = str(att["_id"])
        return attendants


_routes = AttendantRoutes()
router = _routes.router
