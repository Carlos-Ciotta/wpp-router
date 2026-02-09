from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.db import sessions, sellers, leads, messages, pending_responses
from app.client import send_message, send_interactive_buttons
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

MENU_TIMEOUT = timedelta(minutes=40)
LEAD_ACTIVE_TIME = timedelta(minutes=5)  # Lead expira após 5 minutos
CLEANUP_TIME = timedelta(days=1)

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
    Verifica se existe lead ativo e salva mensagem no DB temporário.
    NÃO envia mensagens para o responsável automaticamente.
    Retorna True se lead existe, False caso contrário.
    """
    lead = leads.find_one({"client": phone, "status": "pending"})
    print(f"🔍 Lead check: {lead}")
    
    if not lead:
        return False
    
    # Verifica se lead expirou (5 minutos)
    if now - lead["created_at"] > LEAD_ACTIVE_TIME:
        print("⏰ Lead expired (5 min), closing")
        leads.update_one(
            {"_id": lead["_id"]},
            {"$set": {"status": "closed"}}
        )
        return False  # Lead expirado, trata como novo cliente
    
    print(f"📨 Lead exists! Saving message to pending DB (no notification sent)")
    
    # Salva mensagem no histórico
    messages.insert_one({
        "client": phone,
        "text": text,
        "timestamp": now
    })
    
    # Busca pending_response existente
    pending = pending_responses.find_one({
        "client": phone,
        "seller": lead["seller"],
        "respondida": False
    })
    
    if pending:
        # Adiciona mensagem ao array existente (sem notificar)
        pending_responses.update_one(
            {"_id": pending["_id"]},
            {
                "$push": {"messages": {"text": text, "timestamp": now}},
                "$set": {"last_update": now}
            }
        )
        print(f"📝 Message added to existing pending response (silent)")
        
        # Envia confirmação para o cliente
        send_message(phone, "✅ Mensagem recebida! Aguarde o contato do responsável.")
    
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
        "Seja bem vindo ao atendimento da Comercial Ciotta Materiais de Construção"\
            "Por favor, escolha uma das opções abaixo para direcionarmos seu atendimento:",
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
    lead_id = leads.insert_one({
        "client": phone,
        "seller": seller["phone"],
        "sector": session["choice"],
        "status": "pending",
        "created_at": now
    }).inserted_id
    print("✅ Lead created")
    
    # Cria pending_response com primeira mensagem
    pending_id = pending_responses.insert_one({
        "client": phone,
        "seller": seller["phone"],
        "sector": session["choice"],
        "messages": [{"text": text, "timestamp": now}],
        "respondida": False,
        "created_at": now,
        "last_update": now
    }).inserted_id
    print("📝 Pending response created")
    
    # Gera link para o vendedor
    base_url = os.getenv("SERVER_URL", "http://localhost:8000")
    response_link = f"{base_url}/response/{str(pending_id)}"
    
    # Notifica vendedor com link (ÚNICA notificação - mensagens seguintes não são enviadas)
    send_message(
        seller["phone"],
        f"🔔 Novo lead aguardando resposta!\n\n"
        f"📱 Cliente: {phone}\n"
        f"📂 Setor: {session['choice']}\n"
        f"💬 Primeira mensagem: {text}\n\n"
        f"👉 Clique para responder:\n{response_link}\n\n"
        f"⏱️ Lead expira em 5 minutos"
    )
    
    # Confirma para cliente
    send_message(phone, "✅ Mensagem recebida! Um responsável irá te contatar em breve.")
    
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

    # Fallback a
    print("⚠️ Unhandled flow state")
    return {"ok": True}

@app.get("/response/{request_id}", response_class=HTMLResponse)
async def show_response_page(request: Request, request_id: str):
    """Exibe interface para o responsável confirmar resposta"""
    try:
        # Busca pending_response
        pending = pending_responses.find_one({"_id": ObjectId(request_id)})
        
        if not pending:
            return HTMLResponse(
                content="<h1>Link inválido ou expirado</h1>",
                status_code=404
            )
        
        if pending["respondida"]:
            return HTMLResponse(
                content="<h1>✅ Esta conversa já foi iniciada</h1>",
                status_code=200
            )
        
        # Formata mensagens para exibição
        formatted_messages = []
        for msg in pending["messages"]:
            formatted_messages.append({
                "text": msg["text"],
                "timestamp": msg["timestamp"].strftime("%d/%m/%Y %H:%M:%S")
            })
        
        return templates.TemplateResponse("response.html", {
            "request": request,
            "request_id": request_id,
            "client": pending["client"],
            "sector": pending["sector"].capitalize(),
            "messages": formatted_messages
        })
        
    except Exception as e:
        print(f"❌ Error loading response page: {e}")
        return HTMLResponse(
            content=f"<h1>Erro ao carregar página: {str(e)}</h1>",
            status_code=500
        )

@app.post("/confirm-response/{request_id}")
async def confirm_response(request_id: str):
    """Confirma que o responsável vai responder e envia notificação via WhatsApp"""
    try:
        # Busca pending_response
        pending = pending_responses.find_one({"_id": ObjectId(request_id)})
        
        if not pending:
            raise HTTPException(status_code=404, detail="Request not found")
        
        if pending["respondida"]:
            return {"ok": True, "message": "Já confirmado anteriormente"}
        
        # Marca como respondida
        pending_responses.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {"respondida": True, "responded_at": datetime.utcnow()}}
        )
        
        # Envia mensagem para o responsável
        send_message(
            pending["seller"],
            f"✅ CONVERSA INICIADA\n\n"
            f"Cliente: {pending['client']}\n"
            f"Link direto: https://wa.me/{pending['client']}\n\n"
            f"Você pode responder diretamente via WhatsApp."
        )
        
        print(f"✅ Response confirmed for {pending['client']}")
        
        return {"ok": True, "message": "Confirmado com sucesso"}
        
    except Exception as e:
        print(f"❌ Error confirming response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cleanup-old-responses")
async def cleanup_old_responses():
    """Remove pending_responses com mais de 1 dia (respondidas ou não)"""
    try:
        cutoff_time = datetime.utcnow() - CLEANUP_TIME
        
        result = pending_responses.delete_many({
            "created_at": {"$lt": cutoff_time}
        })
        
        print(f"🗑️ Cleaned up {result.deleted_count} old responses")
        
        return {
            "ok": True,
            "deleted": result.deleted_count,
            "cutoff_time": cutoff_time.isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))
