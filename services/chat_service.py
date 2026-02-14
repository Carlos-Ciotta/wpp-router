from datetime import datetime, timedelta
from typing import Optional, Any, Union
from domain.session.chat_session import ChatSession, SessionStatus
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
from repositories.template import TemplateRepository
from repositories.contact import ContactRepository
from client.whatsapp.V24 import WhatsAppClient
from domain.config.chat_config import ChatConfig
from domain.template.template import Template

from bson import ObjectId
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from utils.cache import Cache
# Configuração de fuso horário fixo
TZ_BR = ZoneInfo("America/Sao_Paulo")

class ChatService:
    def __init__(self, wa_client, session_repo, attendant_repo, config_repo, template_repo, contact_repo, cache, session_cache_key="session_cache"):
        self.wa_client : WhatsAppClient = wa_client
        self.session_repo : SessionRepository= session_repo
        self._config_repo : ConfigRepository = config_repo
        self.attendant_repo :AttendantRepository= attendant_repo
        self._template_repo : TemplateRepository = template_repo
        self._contact_repo : ContactRepository = contact_repo
        self._cache : Cache = cache
        self._cache_key = session_cache_key

    # ------------------------
    # Cache Functions
    # ------------------------

    async def get_cached_config(self) -> ChatConfig:
        """Evita idas excessivas ao banco de dados."""
        cached = await self._cache.get(key="chat_config")
        if cached:
            return ChatConfig(**cached[0])  # Cache armazena lista de dicts
        config = await self._config_repo.get_config()
        # O repositório retorna um dict, não um objeto Pydantic
        return ChatConfig(**config) if config else ChatConfig()

    async def _invalidate_attendant_cache(self, attendant_id: str):
        if attendant_id:
            try:
                await self._cache.delete(f"sessions:{attendant_id}")
            except Exception as e:
                logging.error(f"Erro ao invalidar cache do atendente {attendant_id}: {e}")

    # ------------------------
    # Template Operations
    # ------------------------

    async def sync_templates_from_whatsapp(self):
        """Busca templates do WhatsApp e salva no repositório local."""
        try:
            raw_templates = self.wa_client.get_templates(status="APPROVED")
            templates = [{
                "id": t.get("id"),
                "name": t.get("name"),
                "status": t.get("status"),
                "category": t.get("category"),
                "language": t.get("language"),
                "components": t.get("components", [])
            } for t in raw_templates]
            await self._template_repo.save_templates(templates)
            return templates
        except Exception as e:
            logging.error(f"Erro ao sincronizar templates: {e}")
            return []

    async def list_templates(self):
        """Retorna templates salvos localmente."""
        return await self._template_repo.list_templates()

    # ------------------------
    # Query operations
    # ------------------------
    async def get_sessions_by_attendant(self, attendant_id: str):
        try:
            await self._validate_objectid(attendant_id)
            
            if self._cache.ensure:
                cached = await self._cache.get(f"sessions:{attendant_id}")
                if cached:
                    return cached
            sessions = [s async for s in self.session_repo.get_sessions_by_attendant(attendant_id)]
            
            await self._cache.set(f"sessions:{attendant_id}", sessions)
            return sessions
        
        except ValueError as ve:
            logging.error(f"Erro de validação: {ve}")
            return None
    
    async def list_sessions(self):
        """Lista todas as sessões de chat."""
        try:
            return [s async for s in self.session_repo.get_all_sessions()]
        except Exception as e:
            logging.error(f"Erro ao listar sessões: {e}")

    # ------------------------
    # Sending Messages
    # ------------------------

    async def send_text_message(self, phone: str, text: str):
        """Envia mensagem de texto validando janela de 24h e atualizando interação."""
        if not await self.can_send_free_message(phone):
            raise ValueError("Janela de 24h fechada. Envie um Template Message.")
        
        response = self.wa_client.send_text(phone, text)
        await self.session_repo.update({"last_interaction_at": datetime.now(TZ_BR).timestamp()}, phone)
        return response

    async def send_image_message(self, phone: str, image_url: str, caption: str = None):
        """Envia imagem validando janela de 24h e atualizando interação."""
        if not await self.can_send_free_message(phone):
            raise ValueError("Janela de 24h fechada. Envie um Template Message.")
            
        response = self.wa_client.send_image(phone, image_url, caption=caption)
        await self.session_repo.update({"last_interaction_at": datetime.now(TZ_BR).timestamp()}, phone)
        return response

    async def send_video_message(self, phone: str, video_url: str, caption: str = None):
        """Envia vídeo validando janela de 24h e atualizando interação."""
        if not await self.can_send_free_message(phone):
            raise ValueError("Janela de 24h fechada. Envie um Template Message.")
            
        response = self.wa_client.send_video(phone, video_url, caption=caption)
        await self.session_repo.update({"last_interaction_at": datetime.now(TZ_BR).timestamp()}, phone)
        return response

    async def send_document_message(self, phone: str, document_url: str, caption: str = None, filename: str = None):
        """Envia documento validando janela de 24h e atualizando interação."""
        if not await self.can_send_free_message(phone):
            raise ValueError("Janela de 24h fechada. Envie um Template Message.")
            
        response = self.wa_client.send_document(phone, document_url, caption=caption, filename=filename)
        await self.session_repo.update({"last_interaction_at": datetime.now(TZ_BR).timestamp()}, phone)
        return response

    # ------------------------
    # Chat Managment
    # ------------------------

    async def start_chat(self, phone: str, attendant_id: str, category: str):
        """Inicia uma nova sessão de chat para um cliente."""
        # 1. Verifica se já tem sessão ativa
        try:
            session = await self.session_repo.get_last_session(phone)
            if session and (session.get("status") == SessionStatus.ACTIVE.value or session.get("status") == SessionStatus.WAITING_MENU.value):
                raise ValueError("Cliente já possui uma sessão ativa ou está no menu de espera")
            

            # 2. Cria nova sessão
            new_session = ChatSession(
                phone_number=phone,
                attendant_id=attendant_id,
                category=category,
                status=SessionStatus.ACTIVE.value,
                created_at=datetime.now(TZ_BR).timestamp(),
                last_interaction_at=datetime.now(TZ_BR).timestamp()
            )
            await self.session_repo.create_session(new_session.to_dict())
            await self.set_active_sessions(phone=phone)
            await self._invalidate_attendant_cache(attendant_id)

            return new_session
        except Exception as e:
            logging.error(f"Erro ao iniciar chat: {e}")
            raise ValueError("Não foi possível iniciar o chat. Tente novamente mais tarde.")
        
    async def transfer_chat(self, phone: str, new_attendant_id: str):
        """Transfere o atendimento para outro atendente."""
        # 1. Verifica se o novo atendente existe
        new_attendant = await self.attendant_repo.get_by_id(new_attendant_id)
        if not new_attendant:
            raise ValueError("Novo atendente não encontrado.")

        # 2. Verifica se tem sessão ativa
        session = await self.session_repo.get_last_session(phone = phone)

        if not session or not session.get("status") == SessionStatus.ACTIVE.value:
            raise ValueError("Cliente não possui sessão ativa para transferir.")
            
        old_attendant_id = session.get("attendant_id")
        sector = new_attendant.get("sector")
        
        assing = await self.session_repo.assign_attendant(phone, new_attendant_id, sector)
        
        await self._invalidate_attendant_cache(new_attendant_id)
        if old_attendant_id:
            await self._invalidate_attendant_cache(old_attendant_id)
        
        return assing

    async def finish_session(self, phone: str):
        """Finaliza a sessão ativa do cliente."""
        session = await self.session_repo.get_last_session(phone)
        attendant_id = session.get("attendant_id") if session else None

        await self.session_repo.close_session(phone)
        
        if attendant_id:
            await self._invalidate_attendant_cache(attendant_id)

        return {"message": "Sessão finalizada com sucesso."}

    async def can_send_free_message(self, phone: str) -> bool:
        """
        Verifica regra de 24h:
        - Se cliente não tem sessão anterior: Janela fechada (False)
        - Se interagir pela última vez > 24h: Janela fechada (False)
        - Se dentro de 24h: Janela aberta (True)
        """
        # 1. Busca sessão ativa ou última sessão
        session = await self.session_repo.get_last_session(phone)

        if not session:
            return False # Nunca houve contato

        last_interaction = session.get("last_client_interaction_at")
        if not last_interaction:
            return False

        if int(last_interaction) < datetime.now(TZ_BR).timestamp() - 24*3600:
            return False
        
        return True
    
    async def process_incoming_message(self, message: Any):
        # Extração de dados compatível com dict ou Objeto Message
        if hasattr(message, "from_number"): 
            phone = message.from_number
            msg_type = message.type
            profile_name = message.profile_name
            # Captura o texto para o objeto se ele existir
            text_body = message.text if hasattr(message, "text") else ""
            timestamp = float(message.timestamp) if message.timestamp else datetime.now(TZ_BR).timestamp()
            msg_dict = message.to_dict() if hasattr(message, "to_dict") else message.__dict__
        else: 
            phone = message.get("from_number") or message.get("from")
            msg_type = message.get("type")
            profile_name = message.get("profile_name") or message.get("profile", {}).get("name")
            # No seu log, o texto está na chave 'text' diretamente ou dentro de 'raw_data'
            text_body = message.get("text") or message.get("raw_data", {}).get("text", {}).get("body", "")
            timestamp = float(message.get("timestamp") or datetime.now(TZ_BR).timestamp())
            msg_dict = {**message, "text_body": text_body} # Injeta o texto limpo aqui

        if not phone or msg_type == "status_update":
            return False

        # 1. Atualizar ou Criar Contato
        try:
             await self._contact_repo.update_contact(
                 phone=phone,
                 name=profile_name,
                 timestamp=timestamp
             )
        except Exception as e:
             logging.error(f"Erro ao salvar contato {phone}: {e}")

        config = await self.get_cached_config()
        session = await self.session_repo.get_last_session(phone=phone)
        
        # Se não existe sessao ou está fechada -> Inicia nova
        if not session or session.get("status") not in [SessionStatus.ACTIVE.value, SessionStatus.WAITING_MENU.value]:
            return await self._automated_start_new_session(phone, config)

        # Gerenciamento de Estado usando Match (Python 3.10+)
        status = session.get("status")
        match status:
            case SessionStatus.WAITING_MENU.value: # Add .value
                await self._handle_menu_selection(session, msg_dict, config)
            case SessionStatus.ACTIVE.value: # Add .value
                await self.session_repo.update(data={"last_client_interaction_at": datetime.now(TZ_BR).timestamp()}, phone_number=phone)
            case _: # Handle string fallback if enum lookup fails
                if status == "waiting_menu":
                    await self._handle_menu_selection(session, msg_dict, config)
                elif status == "active":
                    await self.session_repo.update(data={"last_client_interaction_at": datetime.now(TZ_BR).timestamp()}, phone_number=phone)
    
    # -----------------------
    # Helpers
    # -----------------------

    async def _validate_objectid(self, id_str: str):
        try:
            ObjectId(id_str)
        except Exception:
            raise ValueError("ID inválido. Deve ser um ObjectId válido.")
    
    def _is_working_hour(self, working_hours: dict) -> bool:
        if not working_hours:
            return False
            
        now_dt = datetime.now(TZ_BR)
        current_day = str(now_dt.weekday())
        current_time = now_dt.time()
        
        intervals = working_hours.get(current_day, [])
        
        now = current_time.strftime("%H:%M")

        for i in intervals:
            start = i["start"] if isinstance(i, dict) else i.start
            end   = i["end"]   if isinstance(i, dict) else i.end

            if start <= now <= end:
                return True
                
        return False
    
    async def _automated_start_new_session(self, phone: str, config: ChatConfig):
        new_session = ChatSession(
                                phone_number=phone,
                                status=SessionStatus.WAITING_MENU.value,
                                created_at=datetime.now(TZ_BR).timestamp(),
                                last_client_interaction_at=datetime.now(TZ_BR).timestamp(),
                                last_interaction_at=datetime.now(TZ_BR).timestamp(),
                                )
        await self.session_repo.create_session(new_session.to_dict())
        # Removed set_active_sessions which was undefined
        
        # Prepara botões - Garante fallback se config estiver vazia
        buttons = [{"id": b.id, "title": b.title} for b in config.greeting_buttons] or \
                  [{"id": "atendimento", "title": "Atendimento"}]

        self.wa_client.send_buttons(
            to=phone,
            body_text=config.greeting_message,
            buttons=buttons[:3], # O WhatsApp Cloud API suporta no máximo 3 botões nesta função
            header_text=config.greeting_header
        )

    async def _handle_menu_selection(self, session: dict, message: dict, config: ChatConfig):
        # Extração limpa do payload de resposta
        msg_type = message.get("type")
        raw_data = message.get("raw_data", {})
        
        selected_option = None
        
        if msg_type == "interactive":
           interactive = raw_data.get("interactive", {})
           if interactive.get("type") == "button_reply":
               selected_option = interactive.get("button_reply", {}).get("id")
           elif interactive.get("type") == "list_reply":
               selected_option = interactive.get("list_reply", {}).get("id")
        elif msg_type == "button":
            selected_option = raw_data.get("button", {}).get("payload")

        selected_btn = next((b for b in config.greeting_buttons if b.id == selected_option), None)
        phone = session.get("phone_number")

        if not selected_btn:
            if selected_option: # If they selected something but it didn't match
                return self.wa_client.send_text(phone, "Opção inválida ou expirada.")
            return # If no option selected (e.g. text message), do nothing or generic handler

        # Roteamento baseado em setor
        if selected_btn.sector in ["Comercial", "Financeiro", "Outros"]:
            await self._route_sector(phone, config, selected_btn.sector)

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
                return None
        else:
            # 2. Se não tem vínculo, faz rodízio entre disponíveis
            attendant = await self._get_next_attendant(sector_name)
            
            if not attendant:
                self.wa_client.send_text(phone, config.absence_message)
                return None

        # 3. Atribuição
        attendant_name = attendant.get("name", "Atendente")
        attendant_id = str(attendant.get("_id"))
        
        await self.session_repo.assign_attendant(phone, attendant_id, sector_name.lower())
        await self._invalidate_attendant_cache(attendant_id)
        
        # Mensagem de boas vindas
        welcome_msg = attendant.get("welcome_message")
        if not welcome_msg:
            welcome_msg = config.attendant_assigned_message.format(attendant_name=attendant_name)
            
        self.wa_client.send_text(phone, welcome_msg)