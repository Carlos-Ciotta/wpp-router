from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from dataclasses import dataclass

class ButtonOption(BaseModel):
    id: str
    title: str
    queue_id: Optional[str] = None # To map "btn_financeiro" -> "QUEUE_FIN"
    sector: Optional[str] = None # To map "btn_comercial" -> "Comercial"

@dataclass
class WorkInterval:
    start: str  # Format "HH:MM"
    end: str    # Format "HH:MM"

class ChatConfig(BaseModel):

    greeting_message: str = "Olá! Escolha o setor desejado:"
    greeting_header: str = "Bem-vindo"
    greeting_buttons: List[ButtonOption] = Field(default_factory=lambda: [
        ButtonOption(id="btn_comercial", title="Comercial", sector="Comercial"),
        ButtonOption(id="btn_financeiro", title="Financeiro", queue_id="QUEUE_FIN", sector="financeiro"),
        ButtonOption(id="btn_outros", title="Outros", queue_id="QUEUE_GEN", sector="outros")
    ])
    
    # Message templates
    attendant_assigned_message: str = "✅ Você está sendo atendido por *{attendant_name}*."
    queue_redirect_message: str = "📝 Encaminhado para {sector}. Aguarde um momento."
    
    working_hours_message: str = "Estamos fora do nosso horário de atendimento. Envie sua mensagem, assim que retornarmos, entraremos em contato!"

    absence_message: str = "💤 O atendente responsável não está em horário de serviço no momento."
    not_found_message: str = "🚫 Nenhum atendente vinculado ao seu número."
    working_hours: Optional[Dict[str, List[WorkInterval]]] = None
    inactivity_closed_message: str = "🕒 Chat encerrado por inatividade (30min)."
    
    _id: Optional[str] = None
