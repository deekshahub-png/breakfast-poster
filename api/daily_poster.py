import os
import sys
import glob
from http.server import BaseHTTPRequestHandler
import json

# Add parent directory to path so we can import whatsapp_sender
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from whatsapp_sender import upload_media, send_image_message

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS_DIR = os.path.join(BASE_DIR, "full dish photos")

def find_poster_image(dish_name: str) -> str:
    """
    Finds the first poster image file in the matching subfolder under 'full dish photos/'.
    Sends the file directly, untouched.
    """
    if not os.path.exists(PHOTOS_DIR):
        raise FileNotFoundError(f"Directory not found: {PHOTOS_DIR}")

    dish_name_clean = dish_name.strip().lower()

    target_folder = None
    for folder in os.listdir(PHOTOS_DIR):
        folder_path = os.path.join(PHOTOS_DIR, folder)
        if os.path.isdir(folder_path):
            if folder.strip().lower() in dish_name_clean or dish_name_clean in folder.strip().lower():
                target_folder = folder_path
                break

    if not target_folder:
        # Fallback to direct directory match
        target_folder = os.path.join(PHOTOS_DIR, dish_name)

    if not os.path.exists(target_folder):
        raise FileNotFoundError(f"No poster folder found for dish '{dish_name}' in {PHOTOS_DIR}")

    # Find image files in target_folder sorted alphabetically
    valid_extensions = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    image_files = []
    for ext in valid_extensions:
        image_files.extend(glob.glob(os.path.join(target_folder, ext)))
        image_files.extend(glob.glob(os.path.join(target_folder, ext.upper())))

    image_files = sorted(list(set(image_files)))

    if not image_files:
        raise FileNotFoundError(f"No image files found in {target_folder}")

    # Return the first matching poster file
    return image_files[0]

def send_daily_poster(dish_name: str, recipient_number: str) -> dict:
    """
    Finds dish poster directly and sends via WhatsApp.
    """
    poster_path = find_poster_image(dish_name)
    media_id = upload_media(poster_path)
    caption = f"Good Evening! 🤗 Tomorrow's Healthy Breakfast: {dish_name}. Have a great evening!"

    response = send_image_message(recipient_number, media_id, caption)
    return {
        "status": "success",
        "dish": dish_name,
        "poster_path": poster_path,
        "media_id": media_id,
        "response": response
    }

class handler(BaseHTTPRequestHandler):
    """
    Vercel Serverless Function Handler
    """
    def do_GET(self):
        try:
            dish = os.environ.get("TODAY_DISH", "bread omlete")
            recipient = os.environ.get("RECIPIENT_PHONE_NUMBER", "")
            
            result = send_daily_poster(dish, recipient)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

if __name__ == "__main__":
    dish_arg = sys.argv[1] if len(sys.argv) > 1 else "bread omlete"
    recipient_arg = sys.argv[2] if len(sys.argv) > 2 else "1234567890"
    print(f"Finding poster for '{dish_arg}'...")
    try:
        path = find_poster_image(dish_arg)
        print(f"Found poster image: {path}")
    except Exception as err:
        print(f"Error: {err}")
