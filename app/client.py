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
