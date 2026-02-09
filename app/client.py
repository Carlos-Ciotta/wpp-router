import requests, os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_NUMBER_ID")

def send_message(to: str, text: str):
    url = f"https://graph.facebook.com/v24.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    
    print(f"=== WhatsApp API Call ===")
    print(f"URL: {url}")
    print(f"To: {to}")
    print(f"Payload: {payload}")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    print(f"========================")
    
    if resp.status_code != 200:
        print(f"❌ ERROR: Failed to send message to {to}")
    
    return resp

def send_interactive_buttons(to: str, body_text: str, buttons: list):
    """
    Envia mensagem interativa com botões (máximo 3 botões)
    
    buttons = [
        {"id": "comercial", "title": "Comercial"},
        {"id": "financeiro", "title": "Financeiro"},
        {"id": "outros", "title": "Outros"}
    ]
    """
    #teste
    url = f"https://graph.facebook.com/v24.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Formata os botões
    formatted_buttons = [
        {
            "type": "reply",
            "reply": {
                "id": btn["id"],
                "title": btn["title"]
            }
        }
        for btn in buttons[:3]  # Máximo 3 botões
    ]
    
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": formatted_buttons
            }
        }
    }
    
    resp = requests.post(url, json=payload, headers=headers)
    
    print(f"=== WhatsApp Interactive Message ===")
    print(f"To: {to}")
    print(f"Body: {body_text}")
    print(f"Buttons: {buttons}")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    print(f"===================================")
    
    if resp.status_code != 200:
        print(f"❌ ERROR: Failed to send interactive message to {to}")
    
    return resp
