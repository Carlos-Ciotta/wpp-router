from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from services.attendant_service import AttendantService
from core.dependencies import get_attendant_service
from typing import List, Optional, Dict
from pydantic import BaseModel
from utils.auth import PermissionChecker

from core.dependencies import RequirePermission
admin_permission = RequirePermission(["admin"])
user_permission = RequirePermission(["user", "admin"])


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
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route("/", self.create_attendant, methods=["POST"], status_code=status.HTTP_201_CREATED)
        self.router.add_api_route("/login", self.login, methods=["POST"])
        self.router.add_api_route("/logout", self.logout, methods=["POST"])
        self.router.add_api_route("/verify-token", self.verify_token, methods=["POST"])
        self.router.add_api_route("/", self.list_attendants, methods=["GET"], response_model=List[dict])

    async def create_attendant(
        self,
        attendant: AttendantCreate,
        token: str = Depends(admin_permission),
        service: AttendantService = Depends(get_attendant_service),
    ):
        """
        Cria um novo atendente.
        """
        result = await service.create_attendant(attendant.model_dump())
        return {"id": str(result), "message": "Attendant created successfully"}

    async def login(self,
        self_form_data: OAuth2PasswordRequestForm = Depends(),
        service: AttendantService = Depends(get_attendant_service)
    ):
        """
        Realiza login e retorna token JWT.
        """
        attendant = await service.authenticate_attendant(self_form_data.username, self_form_data.password)
        if not attendant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await service.create_token_for_attendant(attendant)

    async def logout(self,
        attendant_id: str = Depends(OAuth2PasswordBearer(tokenUrl="attendants/login")),
        service: AttendantService = Depends(get_attendant_service)
    ):
        await service.logout(attendant_id)

    async def verify_token(self,
        token: str = Depends(OAuth2PasswordBearer(tokenUrl="attendants/login")),
        attendant_id: str = Depends(OAuth2PasswordBearer(tokenUrl="attendants/login")),
        service: AttendantService = Depends(get_attendant_service)
    ):
        token = await service.verify_token(token, attendant_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def list_attendants(self,
        service: AttendantService = Depends(get_attendant_service),
        token: str = Depends(admin_permission),
    ):
        """
        Lista todos os atendentes.
        """
        attendants = await service.list_attendants()
        for att in attendants:
            if "_id" in att:
                att["_id"] = str(att["_id"])
        return attendants


_routes = AttendantRoutes()
router = _routes.router
