from datetime import datetime, timedelta
from typing import Optional, Any, Union
from domain.chat.chats import Chat, ChatStatus
from repositories.chat_repo import ChatRepository
from services.attendant_service import AttendantService
from repositories.config import ConfigRepository
from repositories.template import TemplateRepository
from services.contact_service import ContactService
from client.whatsapp.V24 import WhatsAppClient
from domain.config.chat_config import ChatConfig

from typing import List, Dict
import json
from bson import ObjectId
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from utils.cache import Cache
# Configuração de fuso horário fixo
TZ_BR = ZoneInfo("America/Sao_Paulo")

class ChatService:
    def __init__(self, wa_client, 
                 chat_repo, 
                 attendant_service, 
                 config_repo, 
                 template_repo, 
                 contact_service, 
                 cache,):
        self.wa_client : WhatsAppClient = wa_client
        self.chat_repo : ChatRepository= chat_repo
        self._config_repo : ConfigRepository = config_repo
        self._attendant_service: AttendantService= attendant_service
        self._template_repo : TemplateRepository = template_repo
        self._contact_service : ContactService = contact_service
        self._cache : Cache = cache

    # ------
    # Config Cache
    # ------
    async def get_cached_config(self) -> ChatConfig:
        """Busca configuração no cache ou banco e retorna objeto ChatConfig."""
        cache_key = "config:global"
        cached = await self._cache.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            return ChatConfig(**data)

        # Busca no repositório (ajustado para usar self._config_repo)
        config_data = await self._config_repo.get_active_config()
        if config_data:
            # Cache de longa duração (ex: 1 hora) para configs que mudam pouco
            await self._cache.set(cache_key, json.dumps(config_data), expire=3600)
            return ChatConfig(**config_data)
        
        raise ValueError("Configuração do sistema não encontrada no banco.")
   # ----------------------------------------------------------------
    # CONTACT CACHE (Utilizando HASH para acesso rápido a campos)
    # ----------------------------------------------------------------
    
    async def get_cached_contact(self, phone: str) -> Optional[Dict]:
        key = f"contact:{phone}"
        contact = await self._cache.hgetall(key)
        if contact:
            return contact
        
        # Se não houver no cache, busca no service (banco)
        contact = await self._contact_service.find_by_phone(phone)
        if contact:
            # Salva como Hash
            await self._cache.hset(key, contact)
        return contact

    # ----------------------------------------------------------------
    # CHAT CACHE (Listagens e Status)
    # ----------------------------------------------------------------

    async def get_chats_by_attendant(self, attendant_id: str) -> List[Dict]:
        try:
            await self._validate_objectid(attendant_id)
            cache_key = f"chats:attendant:{attendant_id}"
            
            # 1. Tenta Cache
            cached = await self._cache.get(cache_key)
            if cached:
                return json.loads(cached) if isinstance(cached, str) else cached

            # 2. Busca Banco
            chats = await self.chat_repo.get_chats_by_attendant(attendant_id)
            
            # 3. Salva no Cache (serializando para string JSON)
            if chats:
                await self._cache.set(cache_key, json.dumps(chats))
            
            return chats
        except Exception as e:
            logging.error(f"Erro ao buscar chats por atendente: {e}")
            return []

    async def get_last_chat_status(self, phone: str) -> Optional[Dict]:
        """Retorna o objeto do último chat, priorizando o cache."""
        cache_key = f"chat:last:{phone}"
        
        cached = await self._cache.get(cache_key)
        if cached:
            return json.loads(cached) if isinstance(cached, str) else cached

        chat = await self.chat_repo.get_last_chat(phone)
        if chat:
            await self._cache.set(cache_key, json.dumps(chat))
        return chat

    # ----------------------------------------------------------------
    # INVALIDAÇÃO (Gatilhos de mudança de estado)
    # ----------------------------------------------------------------

    async def _invalidate_chat_data(self, phone: str, attendant_id: Optional[str] = None):
        """Limpa o cache relacionado quando um chat muda de estado ou atendente."""
        # Limpa o último chat do cliente
        await self._cache.delete(f"chat:last:{phone}")
        
        # Se soubermos o atendente, limpamos a lista dele
        if attendant_id:
            await self._cache.delete(f"chats:attendant:{attendant_id}")
        
        # Alternativa: Se houver muitos atendentes, pode usar o prefixo
        # await self._cache.invalidate_prefix("chats:attendant:")

    # ------------------------
    # Template Operations
    # ------------------------

    async def sync_templates_from_whatsapp(self):
        """Busca templates do WhatsApp e salva no repositório local."""
        try:
            # get_templates currently is sync and returns data, it doesn't do async storage itself
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
        
    async def list_chats(self):
        """Lista todas as sessões de chat."""
        try:
            return [c async for c in self.chat_repo.get_chats_by_attendant()]
        except Exception as e:
            logging.error(f"Erro ao listar sessões: {e}")
            return []

    # ------------------------
    # Sending Messages
    # ------------------------

    async def send_text_message(self, phone: str, text: str):
        """Envia mensagem de texto validando janela de 24h e atualizando interação."""
        try:
            if not await self.can_send_free_message(phone):
                raise ValueError("Janela de 24h fechada. Envie um Template Message.")
            
            response = await self.wa_client.send_text(phone, text)
            await self.update_sent_message(phone, {"type": "text", 
                                                   "text": {"body": text}, 
                                                   "timestamp": int(datetime.now(TZ_BR).timestamp())})
            return response
        except ValueError as ve:
            logging.warning(f"Validação ao enviar mensagem para {phone}: {ve}")
            raise ve
    async def send_image_message(self, phone: str, image_url: str, caption: str = None):
        """Envia imagem validando janela de 24h e atualizando interação."""
        try:
            if not await self.can_send_free_message(phone):
                raise ValueError("Janela de 24h fechada. Envie um Template Message.")
                
            response = await self.wa_client.send_image(phone, image_url, caption=caption)
            await self.update_sent_message(phone, {"type": "image",
                                                    "text": {"body": caption} if caption else {},
                                                    "timestamp": int(datetime.now(TZ_BR).timestamp())})
            return response
        
        except ValueError as ve:
            logging.warning(f"Validação ao enviar imagem para {phone}: {ve}")
            raise ve

    async def send_video_message(self, phone: str, video_url: str, caption: str = None):
        """Envia vídeo validando janela de 24h e atualizando interação."""
        try:
            if not await self.can_send_free_message(phone):
                raise ValueError("Janela de 24h fechada. Envie um Template Message.")
                
            response = await self.wa_client.send_video(phone, video_url, caption=caption)
            await self.update_sent_message(phone, {"type": "video",
                                                    "text": {"body": caption} if caption else {},
                                                    "timestamp": int(datetime.now(TZ_BR).timestamp())})
            return response
        
        except ValueError as ve:
            logging.warning(f"Validação ao enviar vídeo para {phone}: {ve}")
            raise ve

    async def send_document_message(self, phone: str, document_url: str, caption: str = None, filename: str = None):
        """Envia documento validando janela de 24h e atualizando interação."""
        try:
            if not await self.can_send_free_message(phone):
                raise ValueError("Janela de 24h fechada. Envie um Template Message.")
                
            response = await self.wa_client.send_document(phone, document_url, caption=caption, filename=filename)
            await self.update_sent_message(phone, {"type": "document",
                                                    "text": {"body": caption} if caption else {},
                                                    "timestamp": int(datetime.now(TZ_BR).timestamp())})
            return response
        
        except ValueError as ve:
            logging.warning(f"Validação ao enviar documento para {phone}: {ve}")
            raise ve

    async def send_template_message(self, phone: str, template_name: str, language_code: str = "pt_BR", components: list = None):
        """Envia mensagem de template (HSM)."""
        try:
            response = await self.wa_client.send_template(phone, template_name, language_code, components)
            # Templates podem ser enviados fora da janela de 24h, então atualizamos a interação
            await self.update_sent_message(phone, {"type": "template",
                                                    "text": {"body": f"Template: {template_name}"},
                                                    "timestamp": int(datetime.now(TZ_BR).timestamp())})
            return response
        
        except Exception as e:
            logging.error(f"Erro ao enviar template para {phone}: {e}")
            raise ValueError("Não foi possível enviar a mensagem de template. Tente novamente mais tarde.")

    # ------------------------
    # CRUD Operations
    # ------------------------
    async def _update_chat_state(self, phone: str, update_data: dict):
        """
        Garante que Banco e Cache estejam SEMPRE iguais.
        Resolve o problema de 'Stale Data'.
        """
        # 1. Atualiza o banco (o repositório deve retornar o objeto atualizado)
        updated_chat = await self.chat_repo.update(data=update_data, phone_number=phone)
        
        if updated_chat:
            # 2. Atualiza o cache imediatamente
            cache_key = f"chat:last:{phone}"
            await self._cache.set(cache_key, json.dumps(updated_chat))
        
        return updated_chat
    
    async def update_received_message(self, phone: str, message: dict):
        """Atualiza banco e cache após receber mensagem."""
        last_message = {
            "type": message.get("type"),
            "text": message.get("text", {}).get("body") if message.get("type") == "text" else "",
            "timestamp": message.get("timestamp"),
            "direction": "incoming"
        }
        data = {
            "last_client_interaction_at": int(datetime.now(TZ_BR).timestamp()),
            "last_message": last_message
        }
        return await self._update_chat_state(phone, data)

    async def update_sent_message(self, phone: str, message: dict):
        """Atualiza banco e cache após enviar mensagem."""
        last_message = {
            "type": message.get("type"),
            "text": message.get("text", {}).get("body", "Nova mensagem"),
            "timestamp": message.get("timestamp"),
            "direction": "outgoing"
        }
        data = {
            "last_interaction_at": int(datetime.now(TZ_BR).timestamp()),
            "last_message": last_message
        }
        return await self._update_chat_state(phone, data)
    # ------------------------
    # Chat Managment
    # ------------------------

    async def start_chat(self, phone: str, attendant_id: str, category: str):
        """Inicia uma nova sessão de chat para um cliente."""
        # 1. Verifica se já tem sessão ativa
        try:
            chat = await self.get_last_chat_status(phone)
            if chat and (chat.get("status") == ChatStatus.ACTIVE.value or chat.get("status") == ChatStatus.WAITING_MENU.value):
                raise ValueError("Cliente já possui uma sessão ativa ou está no menu de espera")

            # 2. Cria nova sessão
            new_chat = Chat(
                phone_number=phone,
                attendant_id=attendant_id,
                category=category,
                status=ChatStatus.ACTIVE.value,
                created_at=int(datetime.now(TZ_BR).timestamp()),
                last_interaction_at=int(datetime.now(TZ_BR).timestamp()),
                last_client_interaction_at=int(datetime.now(TZ_BR).timestamp()),
            ).to_dict()
            await self.chat_repo.create_chat(new_chat)

            await self.set_active_chats(phone=phone)
            await self._invalidate_attendant_cache(attendant_id)

            await self._invalidate_chat_data(phone, attendant_id)
            return new_chat
        except Exception as e:
            logging.error(f"Erro ao iniciar chat: {e}")
            raise ValueError("Não foi possível iniciar o chat. Tente novamente mais tarde.")
        
    async def transfer_chat(self, phone: str, new_attendant_id: str):
        """Transfere o atendimento para outro atendente."""
        # 1. Verifica se o novo atendente existe
        new_attendant = await self._attendant_service.find_by_id(new_attendant_id)
        if not new_attendant:
            raise ValueError("Novo atendente não encontrado.")

        # 2. Verifica se tem sessão ativa
        chat = await self.get_last_chat_status(phone = phone)

        if not chat or not (chat.get("status") == ChatStatus.ACTIVE.value or chat.get("status") == ChatStatus.WAITING_MENU.value):
            raise ValueError("Cliente não possui sessão ativa para transferir.")
            
        old_attendant_id = chat.get("attendant_id")
        category = new_attendant.get("category")
        
        assing = await self.chat_repo.assign_attendant(phone, new_attendant_id, category)
        
        await self._invalidate_attendant_cache(new_attendant_id)
        if old_attendant_id:
            await self._invalidate_attendant_cache(old_attendant_id)
        
        return assing

    async def finish_chat(self, phone: str):
        """Finaliza a sessão ativa do cliente."""
        try:
            chat = await self.get_last_chat_status(phone)
            if not chat:
                raise ValueError("Sessão não encontrada.")

            await self.chat_repo.close_chat(phone)
            
            # GATILHO CACHE: Remove do cache pois o status mudou
            await self._invalidate_chat_data(phone, chat.get("attendant_id"))
            return {"message": "Finalizado"}
        except Exception as e:
            logging.error(f"Erro ao finalizar chat para {phone}: {e}")
            raise ValueError("Não foi possível finalizar a sessão. Tente novamente mais tarde.")

    async def can_send_free_message(self, phone: str) -> bool:
        """
        Verifica regra de 24h:
        - Se cliente não tem sessão anterior: Janela fechada (False)
        - Se interagir pela última vez > 24h: Janela fechada (False)
        - Se dentro de 24h: Janela aberta (True)
        """
        # 1. Busca sessão ativa ou última sessão
        chat = await self.get_last_chat_status(phone)

        if not chat:
            return False # Nunca houve contato

        last_interaction = chat.get("last_client_interaction_at")
        if not last_interaction:
            return False

        if int(last_interaction) < int(datetime.now(TZ_BR).timestamp() - 24*3600):
            return False
        
        return True
    
    async def process_incoming_message(self, message: Any):
        try:
            # Determine message type from parsed domain model
            msg_dict = message if isinstance(message, dict) else getattr(message, "__dict__", {})
            msg_type = msg_dict.get("type")

            if msg_type == "status":
                return None  # Status são tratados em outro lugar

            if msg_type != "message":
                return None

            phone = message.get("from") if isinstance(message, dict) else getattr(message, "from", None)
            profile_name = msg_dict.get("profile", {}).get("name")
            await self._ensure_contact_synced(phone, profile_name)

            # Always fetch config early because it is used in multiple branches
            config = await self.get_cached_config()

            chat = await self.get_last_chat_status(phone)
            if not chat or chat.get("status") not in [ChatStatus.ACTIVE.value, ChatStatus.WAITING_MENU.value]:
                return await self._automated_start_new_chat(phone, config=config)

            # Gerenciamento de Estado usando Match (Python 3.10+)
            status = chat.get("status")
            if status == ChatStatus.WAITING_MENU.value or status == "waiting_menu":
                await self._handle_menu_selection(chat, msg_dict, config)
                await self.update_received_message(phone, msg_dict)
            elif status == ChatStatus.ACTIVE.value or status == "active":
                await self.update_received_message(phone, msg_dict)
        except Exception as e:
            logging.error(f"Erro ao processar mensagem: {e}")
            return None
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
    
    async def _automated_start_new_chat(self, phone: str, config: ChatConfig):
        new_chat = Chat(
                phone_number=phone,
                status=ChatStatus.ACTIVE.value,
                created_at=int(datetime.now(TZ_BR).timestamp()),
                last_interaction_at=int(datetime.now(TZ_BR).timestamp()),
                last_client_interaction_at=int(datetime.now(TZ_BR).timestamp()),
            )
        await self.chat_repo.create_chat(new_chat.to_dict())
        # Removed set_active_chats which was undefined
        
        # Prepara botões - Garante fallback se config estiver vazia
        buttons = [{"id": b.id, "title": b.title} for b in config.greeting_buttons] or \
                  [{"id": "atendimento", "title": "Atendimento"}]

        await self.wa_client.send_buttons(
            to=phone,
            body_text=config.greeting_message,
            buttons=buttons[:3], # O WhatsApp Cloud API suporta no máximo 3 botões nesta função
            header_text=config.greeting_header
        )

    async def _handle_menu_selection(self, chat: dict, message: dict, config: ChatConfig):
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
        phone = chat.get("phone_number")

        if not selected_btn:
            if selected_option: # If they selected something but it didn't match
                return await self.wa_client.send_text(phone, "Opção inválida ou expirada.")
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
        all_attendants = await self._attendant_service.list_attendants({"sector": sector})
        
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
        last_id = await self.chat_repo.get_last_assigned_attendant_id(sector.lower())
        
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
                await self.wa_client.send_text(phone, config.absence_message)
                return None

        # 3. Atribuição
        attendant_name = attendant.get("name", "Atendente")
        attendant_id = str(attendant.get("_id"))
        
        await self.chat_repo.assign_attendant(phone, attendant_id, sector_name.lower())
        await self._invalidate_chat_data(phone, attendant_id)
        
        # Mensagem de boas vindas
        welcome_msg = attendant.get("welcome_message")
        if not welcome_msg:
            welcome_msg = config.attendant_assigned_message.format(attendant_name=attendant_name)
            
        await self.wa_client.send_text(phone, welcome_msg)

    async def _ensure_contact_synced(self, phone: str, profile_name: str):
        """
        Evita o gargalo de I/O: Só faz upsert se o contato não existir 
        ou se o nome de perfil mudou.
        """
        contact_key = f"contact:{phone}"
        # hgetall retorna {} se não existir
        cached_contact = await self._cache.hgetall(contact_key)

        # Se o nome é o mesmo, não faz nada (Economia de DB)
        if cached_contact and cached_contact.get("name") == profile_name:
            return cached_contact

        # Caso contrário, atualiza banco e cache
        contact = await self._contact_service.upsert_contact(
            phone=phone,
            name=profile_name,
            timestamp=int(datetime.now(TZ_BR).timestamp())
        )
        await self._cache.hset(contact_key, contact)
        return contact