import os
import sys

# Import daily poster logic
from api.daily_poster import find_poster_image, send_daily_poster

def main():
    print("=== Breakfast Poster Runner (Local) ===")
    dish_name = input("Enter dish name (e.g. 'bread omlete'): ").strip()
    if not dish_name:
        dish_name = "bread omlete"

    try:
        poster_path = find_poster_image(dish_name)
        print(f"[SUCCESS] Located poster image for '{dish_name}': {poster_path}")
        
        send_now = input("Do you want to send this via WhatsApp? (y/N): ").strip().lower()
        if send_now == 'y':
            recipient = input("Enter recipient phone number with country code: ").strip()
            res = send_daily_poster(dish_name, recipient)
            print(f"[SENT] Result: {res}")
        else:
            print("[INFO] Poster lookup successful. Skipping WhatsApp send.")

    except Exception as e:
        print(f"[ERROR] Failed to find or send poster: {e}")

if __name__ == "__main__":
    main()
