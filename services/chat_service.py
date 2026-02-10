from datetime import datetime, timedelta
from typing import Optional
from domain.session.chat_session import ChatSession, SessionStatus
from repositories.session import SessionRepository
from repositories.attendant import AttendantRepository
from client.whatsapp.V24 import WhatsAppClient

class ChatService:
    def __init__(
        self, 
        wa_client: WhatsAppClient, 
        session_repo: SessionRepository,
        attendant_repo: AttendantRepository
    ):
        self.wa_client = wa_client
        self.session_repo = session_repo
        self.attendant_repo = attendant_repo

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
        await self.session_repo.close_session(phone)
        self.wa_client.send_text(phone, "🕒 Chat encerrado por inatividade (30min).")

    async def process_incoming_message(self, message: dict):
        phone = message.get("from")
        if not phone:
            return

        # Ignore Status Updates
        if message.get("event_type") == "status":
            return

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
            
            buttons = [
                {"id": "btn_comercial", "title": "Comercial"},
                {"id": "btn_financeiro", "title": "Financeiro"},
                {"id": "btn_outros", "title": "Outros"}
            ]
            self.wa_client.send_buttons(
                to=phone,
                body_text="Olá! Escolha o setor desejado:",
                buttons=buttons,
                header_text="Bem-vindo"
            )
            return

        # Handle Existing Session
        if session.status == SessionStatus.WAITING_MENU:
            await self._handle_menu_selection(session, message)
        
        elif session.status == SessionStatus.ACTIVE:
            await self.session_repo.update_last_interaction(phone)
            # Here you could forward logic if needed, but for now we just track activity
            pass

    async def _handle_menu_selection(self, session: ChatSession, message: dict):
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

        if selected_option == "btn_comercial":
            await self._route_comercial(phone)
        elif selected_option == "btn_financeiro":
            await self.session_repo.assign_attendant(phone, "QUEUE_FIN", "financeiro")
            self.wa_client.send_text(phone, "📝 Encaminhado para o Financeiro. Aguarde um momento.")
        elif selected_option == "btn_outros":
             await self.session_repo.assign_attendant(phone, "QUEUE_GEN", "outros")
             self.wa_client.send_text(phone, "📝 Encaminhado para Outros. Aguarde um momento.")
        else:
            self.wa_client.send_text(phone, "❌ Opção inválida. Por favor, selecione um dos botões acima.")

    async def _route_comercial(self, phone: str):
        # 1. Find attendant for this client
        attendant = await self.attendant_repo.find_by_client_and_sector(phone, "Comercial")
        
        if not attendant:
            self.wa_client.send_text(phone, "🚫 Nenhum atendente comercial vinculado ao seu número.")
            return

        # 2. Check working hours
        wh = attendant.get("working_hours")
        if not self._is_working_hour(wh):
             self.wa_client.send_text(phone, "💤 O atendente responsável não está em horário de serviço no momento.")
             return

        # 3. Assign
        attendant_name = attendant.get("name", "Consultor")
        attendant_id = str(attendant.get("_id"))
        
        await self.session_repo.assign_attendant(phone, attendant_id, "comercial")
        self.wa_client.send_text(phone, f"✅ Você está sendo atendido por *{attendant_name}*.")
