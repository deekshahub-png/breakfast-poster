import os
import mimetypes
import json

PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
GRAPH_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")

def _require_credentials():
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN must be set as environment variables."
        )

def detect_mime_type(file_path: str) -> str:
    """Detects MIME type from file extension or magic bytes."""
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        return mime
    
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.png']:
        return 'image/png'
    elif ext in ['.jpg', '.jpeg']:
        return 'image/jpeg'
    elif ext in ['.webp']:
        return 'image/webp'
    return 'image/jpeg'

def upload_media(file_path: str) -> str:
    """
    Uploads media file to Meta WhatsApp Cloud API with correct MIME type detection.
    Returns media_id.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    _require_credentials()
    mime_type = detect_mime_type(file_path)
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/media"

    try:
        import requests
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, mime_type),
                "messaging_product": (None, "whatsapp"),
                "type": (None, mime_type)
            }
            response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json().get("id")
    except ImportError:
        import urllib.request
        import uuid

        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }

        body = []
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode("utf-8"))
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\n{mime_type}\r\n".encode("utf-8"))
        filename = os.path.basename(file_path)
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: {mime_type}\r\n\r\n".encode("utf-8"))
        with open(file_path, "rb") as f:
            body.append(f.read())
        body.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        payload_bytes = b"".join(body)
        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("id")

def send_image_message(to_number: str, media_id: str, caption: str = "") -> dict:
    """
    Sends an image message using Meta WhatsApp Cloud API.
    """
    _require_credentials()
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption
        }
    }

    try:
        import requests
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except ImportError:
        import urllib.request
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
