from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from app.db import sessions, sellers, leads, messages
from app.client import send_message, send_interactive_buttons
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

MENU_TIMEOUT = timedelta(minutes=40)
LEAD_ACTIVE_TIME = timedelta(minutes=40)

# ========== FUNÇÕES DE UTILIDADE ==========

def normalize_phone(phone: str) -> str:
    """Remove + e adiciona 9 se número brasileiro tiver 12 dígitos"""
    phone = phone.lstrip("+")
    
    # Normaliza número brasileiro: se tiver 12 dígitos, adiciona o 9
    if phone.startswith("55") and len(phone) == 12:
        phone = phone[:4] + "9" + phone[4:]
        print(f"📱 Phone normalized: {phone}")
    
    return phone

def extract_message_data(msg: dict) -> tuple:
    """Extrai texto e tipo de mensagem (text ou interactive button)"""
    interactive = msg.get("interactive")
    if interactive:
        text = interactive.get("button_reply", {}).get("id", "")
        print(f"Interactive button clicked: {text}")
        return text, "button"
    else:
        text = msg.get("text", {}).get("body", "")
        return text, "text"

# ========== HANDLERS DO FLUXO ==========

def handle_lead_forwarding(phone: str, text: str, now: datetime) -> bool:
    """
    Verifica se existe lead ativo e espelha mensagem para vendedor.
    Retorna True se lead existe, False caso contrário.
    """
    lead = leads.find_one({"client": phone, "status": "pending"})
    print(f"🔍 Lead check: {lead}")
    
    if not lead:
        return False
    
    print(f"📨 Lead exists! Forwarding to seller: {lead['seller']}")
    
    # Salva mensagem no histórico
    messages.insert_one({
        "client": phone,
        "text": text,
        "timestamp": now
    })
    
    # Encaminha para vendedor
    send_message(
        lead["seller"],
        f"[Cliente {phone}]\n{text}"
    )
    
    # Verifica timeout de 40 minutos
    if now - lead["created_at"] > LEAD_ACTIVE_TIME:
        print("⏰ Lead expired (40 min), closing")
        leads.update_one(
            {"_id": lead["_id"]},
            {"$set": {"status": "closed"}}
        )
    
    return True

def handle_new_client(phone: str, now: datetime) -> None:
    """Cria nova sessão e envia botões interativos"""
    print("🆕 New client, creating session and showing menu")
    
    sessions.insert_one({
        "phone": phone,
        "step": "menu",
        "last_menu": now
    })
    
    send_interactive_buttons(
        phone,
        "Olá! Qual setor você deseja falar?",
        [
            {"id": "comercial", "title": "Comercial"},
            {"id": "financeiro", "title": "Financeiro"},
            {"id": "outros", "title": "Outros"}
        ]
    )

def handle_menu_selection(phone: str, text: str, session: dict, now: datetime) -> bool:
    """
    Processa seleção de menu (botão ou texto).
    Retorna True se processou, False se deve continuar.
    """
    if session["step"] != "menu":
        return False
    
    print(f"📋 Menu step, text: '{text}'")
    
    # Mapeia opções válidas
    sector_map = {
        "comercial": "comercial",
        "1": "comercial",
        "financeiro": "financeiro",
        "2": "financeiro",
        "outros": "outros",
        "3": "outros"
    }
    
    sector = sector_map.get(text)
    
    if sector:
        print(f"✅ Selected: {sector}")
        sessions.update_one(
            {"phone": phone},
            {"$set": {"step": "message", "choice": sector}}
        )
        send_message(phone, "Logo um responsável do setor escolhido irá te atender. " \
        "Por enquanto, por favor, envie sua mensagem:")
    else:
        # Verifica timeout apenas para opção inválida (evitar spam de menu)
        if now - session["last_menu"] < MENU_TIMEOUT:
            print("🔒 Menu timeout active for invalid option, ignoring")
            return True
        
        print("❌ Invalid option")
        send_interactive_buttons(
            phone,
            "Opção inválida. Por favor, escolha uma das opções:",
            [
                {"id": "comercial", "title": "Comercial"},
                {"id": "financeiro", "title": "Financeiro"},
                {"id": "outros", "title": "Outros"}
            ]
        )
        # Atualiza last_menu ao reenviar
        sessions.update_one(
            {"phone": phone},
            {"$set": {"last_menu": now}}
        )
    
    return True

def handle_message_and_create_lead(phone: str, text: str, session: dict, now: datetime) -> bool:
    """
    Recebe mensagem do cliente e cria lead com vendedor disponível.
    Retorna True se processou.
    """
    if session["step"] != "message":
        return False
    
    print(f"💬 Message step, sector: {session['choice']}")
    
    # Busca vendedor online do setor
    seller = sellers.find_one_and_update(
        {"online": True, "sector": session["choice"]},
        {"$set": {"lastAssigned": now}},
        sort=[("lastAssigned", 1)]
    )
    
    if not seller:
        print("❌ ERROR: No online seller found!")
        send_message(phone, "Desculpe, nenhum vendedor disponível no momento.")
        return True
    
    print(f"👨‍💼 Seller assigned: {seller['phone']}")
    
    # Cria lead
    leads.insert_one({
        "client": phone,
        "seller": seller["phone"],
        "sector": session["choice"],
        "status": "pending",
        "created_at": now
    })
    print("✅ Lead created")
    
    # Notifica vendedor
    send_message(
        seller["phone"],
        f"Novo lead:\nCliente: {phone}\n"
        f"Mensagem: {text}\n"
        f"Link direto: https://wa.me/{phone}"
    )
    
    # Confirma para cliente
    send_message(phone, "Um vendedor já recebeu sua mensagem e vai te responder em breve.")
    
    # Reset sessão para menu (com timeout ativo)
    sessions.update_one(
        {"phone": phone},
        {"$set": {"step": "menu", "last_menu": now}}
    )
    
    return True

# ========== ENDPOINTS ==========

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Webhook verification handshake."""
    mode = request.query_params.get("hub.mode")
    challenge = request.query_params.get("hub.challenge")
    token = request.query_params.get("hub.verify_token")

    if mode == "subscribe" and token == os.getenv("VERIFY_TOKEN") and challenge:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def webhook(req: Request):
    """Processa mensagens recebidas do WhatsApp"""
    data = await req.json()
    print("\n=== WEBHOOK POST ===")

    # Extrai mensagem
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        print(f"✅ Received message: {msg}")
    except:
        print("⚠️ No message in payload, ignoring")
        return {"ok": True}

    # Normaliza dados
    phone = normalize_phone(msg["from"])
    text, msg_type = extract_message_data(msg)
    now = datetime.utcnow()
    print(f"📱 Phone: {phone} | Text: '{text}' | Type: {msg_type}")

    # 1. Verifica se é lead ativo (espelhamento)
    if handle_lead_forwarding(phone, text, now):
        return {"ok": True}

    # 2. Verifica sessão
    session = sessions.find_one({"phone": phone})
    print(f"👤 Session: {session}")

    # 3. Novo cliente → envia botões
    if not session:
        handle_new_client(phone, now)
        return {"ok": True}

    # 4. Cliente escolhendo no menu
    if handle_menu_selection(phone, text, session, now):
        return {"ok": True}

    # 5. Cliente enviando mensagem → cria lead
    if handle_message_and_create_lead(phone, text, session, now):
        return {"ok": True}

    # Fallback
    print("⚠️ Unhandled flow state")
    return {"ok": True}
