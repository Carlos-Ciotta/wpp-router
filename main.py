from fastapi import FastAPI, Request
from app.db import sessions, sellers, leads, messages
from app.client import send_message
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

MENU_TIMEOUT = timedelta(minutes=40)
LEAD_ACTIVE_TIME = timedelta(minutes=40)

@app.get("/webhook")
def verify(hub_challenge: str = None, hub_verify_token: str = None):
    if hub_verify_token == os.getenv("VERIFY_TOKEN"):
        return int(hub_challenge)
    return "Erro"

@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
    except:
        return {"ok": True}

    phone = msg["from"]
    text = msg.get("text", {}).get("body", "")
    now = datetime.utcnow()

    lead = leads.find_one({"client": phone, "status": "pending"})

    # Se existe lead → espelha sempre
    if lead:
        messages.insert_one({
            "client": phone,
            "text": text,
            "timestamp": now
        })

        send_message(
            lead["seller"],
            f"[Cliente {phone}]\n{text}"
        )

        # se passou 40 min, libera
        if now - lead["created_at"] > LEAD_ACTIVE_TIME:
            leads.update_one(
                {"_id": lead["_id"]},
                {"$set": {"status": "closed"}}
            )

        return {"ok": True}

    session = sessions.find_one({"phone": phone})

    # Novo cliente
    if not session:
        sessions.insert_one({"phone": phone, "step": "menu", "last_menu": now})
        send_message(phone, "Qual setor deseja?\n1 - Vendas\n2 - Financeiro")
        return {"ok": True}

    # Menu bloqueado
    if now - session["last_menu"] < MENU_TIMEOUT:
        return {"ok": True}

    # Menu
    if session["step"] == "menu":
        if text == "1":
            sessions.update_one(
                {"phone": phone},
                {"$set": {"step": "message", "choice": "vendas"}}
            )
            send_message(phone, "Escreva sua mensagem:")
        elif text == "2":
            sessions.update_one(
                {"phone": phone},
                {"$set": {"step": "message", "choice": "financeiro"}}
            )
            send_message(phone, "Escreva sua mensagem:")
        else:
            send_message(phone, "Opção inválida.\n1 - Vendas\n2 - Financeiro")
        return {"ok": True}

    # Criação do lead
    if session["step"] == "message":
        seller = sellers.find_one_and_update(
            {"online": True, "sector": session["choice"]},
            {"$set": {"lastAssigned": now}},
            sort=[("lastAssigned", 1)]
        )

        leads.insert_one({
            "client": phone,
            "seller": seller["phone"],
            "sector": session["choice"],
            "status": "pending",
            "created_at": now
        })

        send_message(
            seller["phone"],
            f"Novo lead:\nCliente: {phone}\n"
            f"Link direto:\nhttps://wa.me/{phone}"
        )

        send_message(phone, "Um vendedor já recebeu sua mensagem.")

        sessions.update_one(
            {"phone": phone},
            {"$set": {"step": "menu", "last_menu": now}}
        )

        return {"ok": True}
