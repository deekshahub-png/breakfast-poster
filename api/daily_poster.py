import os
import re
import sys
import glob
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add parent directory to path so we can import whatsapp_sender
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp_sender import upload_media, send_image_message, send_template_image_message

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS_DIR = os.path.join(BASE_DIR, "posters")          # finished posters from render_posters.py
PHOTOS_DIR = os.path.join(BASE_DIR, "full dish photos")  # fallback: plain dish photos

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# Common spellings -> folder name, so "bread omelette" finds "bread omlete" etc.
ALIASES = {
    "bread omelette": "bread omlete",
    "omelette": "bread omlete",
    "millet porridge": "milet porridge + pickles",
    "idiyappam": "idiyapam",
    "neeragaram": "fermented rice (ice biriyani)",
    "fermented rice": "fermented rice (ice biriyani)",
    "wheat dosa": "wheat dosa + coconut chutney",
    "poha": "poha +nuts",
    "sprouts": "steamed sprouts",
    "soup": "soups + veggies",
}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _match_name(dish_name: str, names) -> str:
    """Returns the entry of `names` that best matches dish_name, or None."""
    wanted = _norm(ALIASES.get(_norm(dish_name), dish_name))
    by_norm = {_norm(n): n for n in names}
    if wanted in by_norm:
        return by_norm[wanted]
    for n_norm, n in by_norm.items():
        if wanted and (wanted in n_norm or n_norm in wanted):
            return n
    return None


def find_poster_image(dish_name: str) -> str:
    """
    Returns the image to send for a dish:
      1. posters/<dish>.png  (designed "Good Evening / Tomorrow's" poster)
      2. otherwise the first image in 'full dish photos/<dish>/'
    """
    if os.path.isdir(POSTERS_DIR):
        posters = {
            os.path.splitext(f)[0]: f
            for f in os.listdir(POSTERS_DIR)
            if f.lower().endswith(IMAGE_EXTENSIONS)
        }
        match = _match_name(dish_name, posters.keys())
        if match:
            return os.path.join(POSTERS_DIR, posters[match])

    if not os.path.isdir(PHOTOS_DIR):
        raise FileNotFoundError(f"Directory not found: {PHOTOS_DIR}")

    folders = [f for f in os.listdir(PHOTOS_DIR) if os.path.isdir(os.path.join(PHOTOS_DIR, f))]
    folder = _match_name(dish_name, folders)
    if not folder:
        raise FileNotFoundError(
            f"No poster found for dish '{dish_name}'. Known dishes: {', '.join(sorted(folders))}"
        )

    target_folder = os.path.join(PHOTOS_DIR, folder)
    image_files = sorted(
        f for f in glob.glob(os.path.join(target_folder, "*"))
        if f.lower().endswith(IMAGE_EXTENSIONS)
    )
    if not image_files:
        raise FileNotFoundError(f"No image files found in {target_folder}")
    return image_files[0]


def get_recipients(raw: str) -> list:
    """Parses one or more comma-separated numbers into WhatsApp format (digits only, with country code)."""
    numbers = [re.sub(r"\D", "", n) for n in (raw or "").split(",")]
    numbers = [n for n in numbers if n]
    if not numbers:
        raise ValueError(
            "RECIPIENT_PHONE_NUMBER is not set. Set it to the number(s) with country code, "
            "comma-separated, e.g. 919876543210,919812345678"
        )
    return numbers


def send_daily_poster(dish_name: str, recipient_numbers) -> dict:
    """
    Finds the dish poster and sends it via WhatsApp to every recipient.

    If WHATSAPP_TEMPLATE_NAME is set, sends an approved template message with the poster as the
    image header. This is required by WhatsApp for business-initiated messages: a plain image
    message is only delivered if the recipient messaged the business number in the last 24 hours.
    """
    if isinstance(recipient_numbers, str):
        recipient_numbers = get_recipients(recipient_numbers)

    poster_path = find_poster_image(dish_name)
    media_id = upload_media(poster_path)

    dish_label = dish_name.strip().title()
    caption = f"Good Evening! 🤗 Tomorrow's Healthy Breakfast: {dish_label}. Have a great evening!"
    template_name = os.environ.get("WHATSAPP_TEMPLATE_NAME", "").strip()
    template_lang = os.environ.get("WHATSAPP_TEMPLATE_LANG", "en").strip()

    results, failures = [], []
    for number in recipient_numbers:
        try:
            if template_name:
                resp = send_template_image_message(number, media_id, template_name, template_lang)
            else:
                resp = send_image_message(number, media_id, caption)
            results.append({"to": number, "response": resp})
        except Exception as e:
            failures.append({"to": number, "error": str(e)})

    return {
        "status": "success" if not failures else ("partial" if results else "error"),
        "dish": dish_label,
        "poster_path": os.path.relpath(poster_path, BASE_DIR),
        "media_id": media_id,
        "mode": f"template:{template_name}" if template_name else "image",
        "sent": results,
        "failed": failures,
    }


def resolve_dish(query: dict) -> str:
    """Dish to announce: ?dish=... > TOMORROW_DISH > TODAY_DISH (legacy name) > bread omlete."""
    return (
        (query.get("dish") or [""])[0]
        or os.environ.get("TOMORROW_DISH")
        or os.environ.get("TODAY_DISH")
        or "bread omlete"
    )


class handler(BaseHTTPRequestHandler):
    """
    Vercel Serverless Function Handler (triggered by the cron in vercel.json).
    """
    def _reply(self, code: int, body: dict):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        try:
            cron_secret = os.environ.get("CRON_SECRET")
            if cron_secret and self.headers.get("Authorization") != f"Bearer {cron_secret}":
                return self._reply(401, {"status": "error", "message": "Unauthorized"})

            query = parse_qs(urlparse(self.path).query)

            # One-time setup: ?action=register&pin=<WHATSAPP_PIN> registers the number with the Cloud API
            if (query.get("action") or [""])[0] == "register":
                pin = os.environ.get("WHATSAPP_PIN", "")
                if not pin or (query.get("pin") or [""])[0] != pin:
                    return self._reply(403, {"status": "error", "message": "Wrong or missing pin"})
                from whatsapp_sender import register_phone_number
                return self._reply(200, register_phone_number(pin))

            dish = resolve_dish(query)
            recipients = get_recipients(os.environ.get("RECIPIENT_PHONE_NUMBER", ""))

            result = send_daily_poster(dish, recipients)
            self._reply(200 if result["status"] == "success" else 502, result)
        except Exception as e:
            self._reply(500, {"status": "error", "message": str(e)})


if __name__ == "__main__":
    dish_arg = sys.argv[1] if len(sys.argv) > 1 else "bread omlete"
    print(f"Finding poster for '{dish_arg}'...")
    try:
        path = find_poster_image(dish_arg)
        print(f"Found poster image: {path}")
    except Exception as err:
        print(f"Error: {err}")
