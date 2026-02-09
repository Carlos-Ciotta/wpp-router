from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["whatsapp_bot"]
#teste
sessions = db.sessions
sellers = db.sellers
leads = db.leads
messages = db.messages
pending_responses = db.pending_responses  # Nova collection para mensagens aguardando resposta
