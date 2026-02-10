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
            
        now_dt = datetime.now()
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
        if selected_btn.sector == "Comercial":
            await self._route_comercial(phone, config)
        elif selected_btn.queue_id:
            # Generic routing
             sector_name = selected_btn.sector or "Atendimento"
             await self.session_repo.assign_attendant(phone, selected_btn.queue_id, sector_name)
             self.wa_client.send_text(phone, config.queue_redirect_message.format(sector=sector_name))
        else:
             # Fallback
             await self.session_repo.assign_attendant(phone, "QUEUE_GEN", "Geral")
             self.wa_client.send_text(phone, config.queue_redirect_message.format(sector="Geral"))


    async def _route_comercial(self, phone: str, config: ChatConfig):
        # 1. Find attendant for this client
        attendant = await self.attendant_repo.find_by_client_and_sector(phone, "Comercial")
        
        if not attendant:
            self.wa_client.send_text(phone, config.not_found_message)
            return

        # 2. Check working hours
        wh = attendant.get("working_hours")
        if not self._is_working_hour(wh):
             self.wa_client.send_text(phone, config.absence_message)
             return

        # 3. Assign
        attendant_name = attendant.get("name", "Consultor")
        attendant_id = str(attendant.get("_id"))
        
        await self.session_repo.assign_attendant(phone, attendant_id, "comercial")
        
        # Determine welcome message: Attendant Custom > Global Config
        welcome_msg = attendant.get("welcome_message")
        if not welcome_msg:
            welcome_msg = config.attendant_assigned_message.format(attendant_name=attendant_name)
            
        self.wa_client.send_text(phone, welcome_msg)
