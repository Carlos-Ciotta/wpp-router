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
router = APIRouter(prefix="/attendants", tags=["Attendants"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="attendants/login")
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

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_attendant(
    attendant: AttendantCreate, 
    token: str = Depends(admin_permission), # Only admins can create attendants
    service: AttendantService = Depends(get_attendant_service)
):
    """
    Cria um novo atendente.
    """
    # Verify if login already exists? The service assumes repo save is enough, but unique index would be better.
    # For now, we trust the repo/service flow.
    result = await service.create_attendant(attendant.model_dump())
    return {"id": str(result), "message": "Attendant created successfully"}

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: AttendantService = Depends(get_attendant_service)
):
    """
    Realiza login e retorna token JWT.
    """
    attendant = await service.authenticate_attendant(form_data.username, form_data.password)
    if not attendant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return await service.create_token_for_attendant(attendant)

@router.post("/logout")
async def logout(
    attendant_id: str = Depends(oauth2_scheme),
    service: AttendantService = Depends(get_attendant_service)
):
    await service.logout(attendant_id)

@router.post("/verify-token")
async def verify_token(
    token: str = Depends(oauth2_scheme),
    attendant_id: str = Depends(oauth2_scheme),
    service: AttendantService = Depends(get_attendant_service)
):
    token = await service.verify_token(token,attendant_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
@router.get("/", response_model=List[dict])
async def list_attendants(
    service: AttendantService = Depends(get_attendant_service),
    token: str = Depends(admin_permission),
    # Could add token dependency here to secure listing
):
    """
    Lista todos os atendentes.
    """
    attendants = await service.list_attendants()
    # Convert ObjectId to str for response
    for att in attendants:
        if "_id" in att:
            att["_id"] = str(att["_id"])
    return attendants
