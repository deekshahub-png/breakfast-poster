import os
import json
import uuid
import mimetypes
import urllib.request
import urllib.error

GRAPH_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")


def _credentials():
    # Read at call time (not import time) so env changes / local .env loading are picked up.
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "").strip()
    access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "").strip()
    if not phone_number_id or not access_token:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN must be set as environment variables."
        )
    return phone_number_id, access_token


def detect_mime_type(file_path: str) -> str:
    """Detects MIME type from the file extension. WhatsApp accepts image/jpeg and image/png."""
    mime, _ = mimetypes.guess_type(file_path)
    if mime in ("image/jpeg", "image/png", "image/webp"):
        return mime
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def _post(url: str, body: bytes, content_type: str) -> dict:
    """POSTs to the Graph API and raises an error that includes Meta's error message."""
    _, access_token = _credentials()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(detail).get("error", {})
            extra = err.get("error_data", {}).get("details", "")
            detail = f"{err.get('message')} (code {err.get('code')}{', ' + extra if extra else ''})"
        except Exception:
            pass
        raise RuntimeError(f"WhatsApp API error {e.code}: {detail}") from None


def upload_media(file_path: str) -> str:
    """Uploads an image to the WhatsApp Cloud API and returns its media_id."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")

    phone_number_id, _ = _credentials()
    mime_type = detect_mime_type(file_path)
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/media"

    boundary = f"----PosterBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(file_path).encode("ascii", "ignore").decode() or "poster.png"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"messaging_product\"\r\n\r\nwhatsapp\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\n{mime_type}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime_type}\r\n\r\n".encode(),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    data = _post(url, body, f"multipart/form-data; boundary={boundary}")
    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"Media upload returned no id: {data}")
    return media_id


def _send(payload: dict) -> dict:
    phone_number_id, _ = _credentials()
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    return _post(url, json.dumps(payload).encode("utf-8"), "application/json")


def register_phone_number(pin: str) -> dict:
    """Registers the business phone number with the Cloud API (sets the two-step PIN if none exists)."""
    phone_number_id, access_token = _credentials()
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}"
    result = {}
    try:
        req = urllib.request.Request(
            base + "?fields=display_phone_number,verified_name,code_verification_status,status,platform_type",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["number"] = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        result["number_error"] = e.read().decode("utf-8", errors="replace")
    try:
        result["register"] = _post(
            base + "/register",
            json.dumps({"messaging_product": "whatsapp", "pin": pin}).encode("utf-8"),
            "application/json",
        )
    except Exception as e:
        result["register_error"] = str(e)
    return result


def send_image_message(to_number: str, media_id: str, caption: str = "") -> dict:
    """
    Sends a plain image message. NOTE: WhatsApp only delivers this if the recipient has
    messaged the business number within the last 24 hours. Use send_template_image_message
    for scheduled/broadcast sends.
    """
    return _send({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "image",
        "image": {"id": media_id, "caption": caption},
    })


def send_template_image_message(to_number: str, media_id: str, template_name: str,
                                language: str = "en") -> dict:
    """
    Sends an approved message template whose header is an IMAGE, using the poster as the header.
    Templates can be delivered at any time (no 24-hour window restriction).
    """
    return _send({
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]}
            ],
        },
    })
