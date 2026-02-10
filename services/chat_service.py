from datetime import datetime, timedelta
from typing import Optional
from domain.session.chat_session import ChatSession, SessionStatus
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from repositories.config import ConfigRepository
from client.whatsapp.V24 import WhatsAppClient
from domain.config.chat_config import ChatConfig

class ChatService:
    def __init__(
        self, 
        wa_client: WhatsAppClient, 
        session_repo: SessionRepository,
        attendant_repo: AttendantRepository,
        config_repo: ConfigRepository
    ):
        self.wa_client = wa_client
        self.session_repo = session_repo
        self.attendant_repo = attendant_repo
        self.config_repo = config_repo

    def _is_working_hour(self, working_hours: dict) -> bool:
        if not working_hours:
            return False
            
        # Ajuste para Horário de Brasília (Server Time - 3 horas)
        now_dt = datetime.now() - timedelta(hours=3)
        
        current_day = str(now_dt.weekday())  # 0=Monday, 6=Sunday
        current_time = now_dt.time()
        
        # working_hours is expected to be Dict[str, List[WorkInterval]] (or list of dicts)
        today_intervals = working_hours.get(current_day)
        
        if not today_intervals:
            return False
            
        for interval in today_intervals:
            try:
                # Access attributes whether it's an object or dict
                if isinstance(interval, dict):
                    start_str = interval.get("start")
                    end_str = interval.get("end")
                else:
                    start_str = interval.start
                    end_str = interval.end
                
                start = datetime.strptime(start_str, "%H:%M").time()
                end = datetime.strptime(end_str, "%H:%M").time()
                
                if start <= current_time <= end:
                    return True
            except Exception as e:
                print(f"Error parsing time interval: {e}")
                continue
                
        return False

    async def _close_session(self, phone: str):
        config: ChatConfig = await self.config_repo.get_config()
        await self.session_repo.close_session(phone)
        self.wa_client.send_text(phone, config.inactivity_closed_message)

    async def process_incoming_message(self, message: dict):
        phone = message.get("from")
        if not phone:
            return

        # Ignore Status Updates
        if message.get("event_type") == "status":
            return
            
        # Ignore messages sent by us (status message might come as different type sometimes)
        if message.get("from") == self.wa_client.phone_id:
             return

        config: ChatConfig = await self.config_repo.get_config()
        session = await self.session_repo.get_active_session(phone)
        
        # Check Timeout (30 min)
        if session:
            last_activity = session.last_interaction_at
            if (datetime.now() - last_activity) > timedelta(minutes=30):
                await self._close_session(phone)
                session = None

        # Start New Session
        if not session:
            new_session = ChatSession(phone_number=phone)
            await self.session_repo.create_session(new_session)
            
            # Convert buttons from config to list of dicts required by WA client
            buttons_payload = []
            for btn in config.greeting_buttons:
                buttons_payload.append({"id": btn.id, "title": btn.title})
            
            # If no buttons configured, add a fallback? 
            # Ideally config should always have buttons.
            if not buttons_payload:
                 buttons_payload = [{"id": "fallback", "title": "Atendimento"}]
                 
            self.wa_client.send_buttons(
                to=phone,
                body_text=config.greeting_message,
                buttons=buttons_payload,
                header_text=config.greeting_header
            )
            return

        # Handle Existing Session
        if session.status == SessionStatus.WAITING_MENU:
            await self._handle_menu_selection(session, message, config)
        
        elif session.status == SessionStatus.ACTIVE:
            await self.session_repo.update_last_interaction(phone)
            pass

    async def _handle_menu_selection(self, session: ChatSession, message: dict, config: ChatConfig):
        msg_type = message.get("type")
        content = message.get("content", {})
        
        selected_option = ""
        
        if msg_type == "interactive":
           if "id" in content: 
                selected_option = content["id"]
        elif msg_type == "button":
            if "payload" in content:
                selected_option = content["payload"]
        
        phone = session.phone_number
        
        # Find the button config that matches selection
        selected_btn = next((btn for btn in config.greeting_buttons if btn.id == selected_option), None)

        if not selected_btn:
            self.wa_client.send_text(phone, "❌ Opção inválida. Por favor, selecione um dos botões acima.")
            return

        # Route logic
        # Setores que devem ter atendimento humano direto (Rotativo ou Vinculado)
        if selected_btn.sector in ["Comercial", "Financeiro"]:
            await self._route_sector(phone, config, selected_btn.sector)
            
        elif selected_btn.queue_id:
            # Rotea para fila genérica (ex: Suporte) se não for um dos setores acima
             sector_name = selected_btn.sector or "Atendimento"
             await self.session_repo.assign_attendant(phone, selected_btn.queue_id, sector_name)
             self.wa_client.send_text(phone, config.queue_redirect_message.format(sector=sector_name))
        else:
             # Fallback
             await self.session_repo.assign_attendant(phone, "QUEUE_GEN", "Geral")
             self.wa_client.send_text(phone, config.queue_redirect_message.format(sector="Geral"))

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
                 self.wa_client.send_text(phone, config.absence_message)
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
