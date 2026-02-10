"""
Repository Pattern para WhatsApp Messages
Encapsula operações de banco de dados
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.collection import Collection
from bson import ObjectId

from ..domain.webhook.message import Message, MessageStatusUpdate
from ..domain.webhook.value_objects import PhoneNumber


class MessageRepository:
    """Repositório para operações com mensagens"""
    
    def __init__(self, db_uri: str = "mongodb://localhost:27017/", db_name: str = "whatsapp_db"):
        self.client = MongoClient(db_uri)
        self.db = self.client[db_name]
        self.messages: Collection = self.db["messages"]

    # ========== OPERAÇÕES DE MENSAGEM ==========
    
    def save_message(self, message: Message) -> ObjectId:
        """
        Salva mensagem no banco
        
        Args:
            message: Instância de Message
        
        Returns:
            ObjectId do documento
        """
        return message.save_to_db()
    
    def get_messages_by_phone(
        self, 
        phone: str, 
        limit: int = 50,
        skip: int = 0
    ) -> List[Message]:
        """
        Busca mensagens de um número
        
        Args:
            phone: Número de telefone
            limit: Limite de resultados
            skip: Quantos pular (paginação)
        
        Returns:
            Lista de mensagens
        """
        try:
            phone_obj = PhoneNumber(phone)
            phone_str = str(phone_obj)
        except ValueError:
            phone_str = phone
        
        docs = self.messages.find(
            {"from_number": phone_str}
        ).sort("received_at", DESCENDING).skip(skip).limit(limit)
        
        return [Message.from_dict(doc) for doc in docs]
    
    def get_recent_messages(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Message]:
        """
        Busca mensagens recentes
        
        Args:
            hours: Últimas N horas
            limit: Limite de resultados
        
        Returns:
            Lista de mensagens
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        docs = self.messages.find(
            {"received_at": {"$gte": since}}
        ).sort("received_at", DESCENDING).limit(limit)
        
        return [Message.from_dict(doc) for doc in docs]
    def search_messages(
        self,
        query: str,
        limit: int = 50
    ) -> List[Message]:
        """
        Busca por texto nas mensagens
        
        Args:
            query: Texto a buscar
            limit: Limite de resultados
        
        Returns:
            Lista de mensagens
        """
        docs = self.messages.find(
            {"text": {"$regex": query, "$options": "i"}}
        ).sort("received_at", DESCENDING).limit(limit)
        
        return [Message.from_dict(doc) for doc in docs]
    
    def count_messages(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Conta mensagens
        
        Args:
            filter_dict: Filtros opcionais
        
        Returns:
            Quantidade de mensagens
        """
        if filter_dict:
            return self.messages.count_documents(filter_dict)
        return self.messages.count_documents({})
    
    def get_conversation_history(
        self,
        phone: str,
        limit: int = 100
    ) -> List[Message]:
        """
        Obtém histórico completo de conversa
        
        Args:
            phone: Número de telefone
            limit: Limite de mensagens
        
        Returns:
            Lista de mensagens em ordem cronológica
        """
        try:
            phone_obj = PhoneNumber(phone)
            phone_str = str(phone_obj)
        except ValueError:
            phone_str = phone
        
        docs = self.messages.find(
            {"from_number": phone_str}
        ).sort("received_at", ASCENDING).limit(limit)
        
        return [Message.from_dict(doc) for doc in docs]