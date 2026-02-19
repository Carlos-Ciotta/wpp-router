import hmac
import hashlib

def verify_whatsapp_signature(payload: bytes, signature: str, app_secret: str):
    # O WhatsApp envia "sha256=XXXX"
    expected_sig = hmac.new(
        app_secret.encode(), 
        payload, 
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected_sig}", signature)