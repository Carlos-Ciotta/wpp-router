import boto3
from botocore.config import Config
from datetime import datetime
import io
import json

class R2Service:
    def __init__(self, account_id: str, access_key: str, secret_key: str, bucket_name: str):
        self.bucket_name = bucket_name
        self.endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )

    async def save_message(self, phone: str, message_data: dict):
        """Salva o JSON da mensagem."""
        file_path = f"chats/{phone}/{datetime.now().isostring()}_msg.json"
        body = json.dumps(message_data, indent=2).encode('utf-8')
        return self._upload(body, file_path, "application/json")

    async def save_contact(self, phone: str, contact_data: dict):
        """Salva dados de contato."""
        file_path = f"contacts/{phone}/profile.json"
        body = json.dumps(contact_data, indent=2).encode('utf-8')
        return self._upload(body, file_path, "application/json")

    async def save_media(self, phone: str, file_binary: bytes, file_name: str, content_type: str):
        """
        Salva mídias (Imagens, Áudios, Vídeos).
        Organiza em pastas por tipo baseado no content_type.
        """
        prefix = "others"
        if "image" in content_type: prefix = "images"
        elif "audio" in content_type: prefix = "audios"
        elif "video" in content_type: 
            prefix = "videos" # Arquivos aqui sofrerão o TTL de 90 dias via regra do bucket
        
        file_path = f"media/{phone}/{prefix}/{file_name}"
        return self._upload(file_binary, file_path, content_type)

    def _upload(self, body, key, content_type):
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type
            )
            return {"status": "success", "key": key, "url": f"{self.endpoint_url}/{self.bucket_name}/{key}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}