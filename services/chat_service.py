from datetime import datetime, timedelta
from typing import Optional
from domain.session.chat_session import ChatSession, SessionStatus
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
from client.whatsapp.V24 import WhatsAppClient
from domain.config.chat_config import ChatConfig

from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from utils.cache import Cache
# Configuração de fuso horário fixo
TZ_BR = ZoneInfo("America/Sao_Paulo")

class ChatService:
    def __init__(self, wa_client, session_repo, attendant_repo, config_repo, cache):
        self.wa_client : WhatsAppClient = wa_client
        self.session_repo : SessionRepository= session_repo
        self._config_repo : ConfigRepository = config_repo
        self.attendant_repo :AttendantRepository= attendant_repo
        self._cache : Cache = cache

    async def get_cached_config(self) -> ChatConfig:
        """Evita idas excessivas ao banco de dados."""
        cached = await self._cache.get(key="chat_config")
        if cached:
            return ChatConfig(**cached[0])  # Cache armazena lista de dicts
        config = await self._config_repo.get_config()
        return ChatConfig(**config.dict()) if config else ChatConfig()

    async def get_active_sessions(self) -> list[ChatSession]:
        return await self._cache.get(key="active_sessions") or []
    
    async def get_active_session_by_phone(self, phone: str) -> Optional[ChatSession]:
        sessions = await self.get_active_sessions()
        exist = next((s for s in sessions if s.phone_number == phone), False)
        return bool(exist)
    
    async def set_active_sessions(self, phone:str) -> None:
        await self._cache.set(key="active_sessions", value=phone)
    
    def _is_working_hour(self, working_hours: dict) -> bool:
        if not working_hours:
            return False
            
        now_dt = datetime.now(TZ_BR)
        current_day = str(now_dt.weekday())
        current_time = now_dt.time()
        
        intervals = working_hours.get(current_day, [])
        
        for interval in intervals:
            try:
                # Se for dict, usa .get(), se for objeto, usa getattr
                start_str = interval.get("start") if isinstance(interval, dict) else interval.start
                end_str = interval.get("end") if isinstance(interval, dict) else interval.end
                
                # Otimização: Comparação direta de strings de horário costuma ser mais rápida 
                # que parsear datetime se o formato for estrito "HH:MM"
                if start_str <= current_time.strftime("%H:%M") <= end_str:
                    return True
            except Exception as e:
                logging.error(f"Erro ao validar horário: {e}")
                
        return False

    async def process_incoming_message(self, message: dict):
        phone = message.get("from")
        type = message.get("type")

        # Early returns rápidos para economizar processamento
        if not phone or type == "status_update" or phone == self.wa_client.phone_id:
            return

        config = await self.get_cached_config()
        session = await self.get_active_session_by_phone(phone=phone)

        if not session:
            return await self._start_new_session(phone, config)

        # Gerenciamento de Estado usando Match (Python 3.10+)
        match session.status:
            case SessionStatus.WAITING_MENU:
                await self._handle_menu_selection(session, message, config)
            case SessionStatus.ACTIVE:
                await self.session_repo.update_last_interaction(phone)

    async def _start_new_session(self, phone: str, config: ChatConfig):
        new_session = ChatSession(
                                phone_number=phone,
                                created_at=datetime.now(TZ_BR),
                                last_interaction_at=datetime.now(TZ_BR)
                                )
        await self.session_repo.create_session(new_session)
        await self.set_active_sessions(phone=phone)
        
        # Prepara botões - Garante fallback se config estiver vazia
        buttons = [{"id": b.id, "title": b.title} for b in config.greeting_buttons] or \
                  [{"id": "atendimento", "title": "Atendimento"}]

        self.wa_client.send_buttons(
            to=phone,
            body_text=config.greeting_message,
            buttons=buttons[:3], # O WhatsApp Cloud API suporta no máximo 3 botões nesta função
            header_text=config.greeting_header
        )

    async def _handle_menu_selection(self, session: ChatSession, message: dict, config: ChatConfig):
        # Extração limpa do payload de resposta
        msg_type = message.get("type")
        content = message.get("content", {})
        
        selected_option = (
            content.get("id") if msg_type == "interactive" 
            else content.get("payload") if msg_type == "button" 
            else None
        )

        selected_btn = next((b for b in config.greeting_buttons if b.id == selected_option), None)

        if not selected_btn:
            return self.wa_client.send_text(session.phone_number, "Por favor, selecione uma opção válida.")

        # Roteamento baseado em setor
        if selected_btn.sector in ["Comercial", "Financeiro"]:
            await self._route_sector(session.phone_number, config, selected_btn.sector)
        else:
            sector_name = selected_btn.sector or "Atendimento"
            queue_id = selected_btn.queue_id or "QUEUE_GEN"
            await self.session_repo.assign_attendant(session.phone_number, queue_id, sector_name)
            self.wa_client.send_text(session.phone_number, config.queue_redirect_message.format(sector=sector_name))

    def _normalize_phone(self, phone: str) -> str:
        """Normaliza telefone para formato padrão (BR com 9 dígitos)"""
        if phone and phone.startswith("55") and len(phone) == 12:
            return f"{phone[:4]}9{phone[4:]}"
        return phone

    async def _get_next_attendant(self, sector: str) -> Optional[dict]:
        # 1. Busca todos atendentes do setor
        all_attendants = await self.attendant_repo.list({"sector": sector})
        
        # 2. Filtra por horário de trabalho
        working_attendants = [
            a for a in all_attendants 
            if self._is_working_hour(a.get("working_hours"))
        ]
        
        if not working_attendants:
            return None
            
        # 3. Ordena para estabilidade (por _id)
        working_attendants.sort(key=lambda x: str(x["_id"]))
        
        # 4. Recupera último atendente atribuído genericamente nesta categoria
        last_id = await self.session_repo.get_last_assigned_attendant_id(sector.lower())
        
        if not last_id:
            return working_attendants[0]
            
        # 5. Rotativo (Round Robin)
        try:
            # Procura índice do último (comparando strings)
            last_index = next(
                i for i, a in enumerate(working_attendants) 
                if str(a["_id"]) == str(last_id)
            )
            # Pega o próximo
            next_index = (last_index + 1) % len(working_attendants)
            return working_attendants[next_index]
        except StopIteration:
            # Caso o último não esteja mais trabalhando/existindo, pega o primeiro
            return working_attendants[0]

    async def _route_sector(self, phone: str, config: ChatConfig, sector_name: str):
        # 1. Tenta encontrar atendente vinculado diretamente
        search_phone = self._normalize_phone(phone)
        attendant = await self.attendant_repo.find_by_client_and_sector(search_phone, sector_name)
        
        if attendant:
            # Verifica apenas se está no horário
            wh = attendant.get("working_hours")
            if not self._is_working_hour(wh):
                self._get_next_attendant(sector_name)
                return
        else:
            # 2. Se não tem vínculo, faz rodízio entre disponíveis
            attendant = await self._get_next_attendant(sector_name)
            
            if not attendant:
                self.wa_client.send_text(phone, config.absence_message)
                return

        # 3. Atribuição
        attendant_name = attendant.get("name", "Consultor")
        attendant_id = str(attendant.get("_id"))
        
        await self.session_repo.assign_attendant(phone, attendant_id, sector_name.lower())
        
        # Mensagem de boas vindas
        welcome_msg = attendant.get("welcome_message")
        if not welcome_msg:
            welcome_msg = config.attendant_assigned_message.format(attendant_name=attendant_name)
            
        self.wa_client.send_text(phone, welcome_msg)