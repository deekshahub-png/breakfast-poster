import importlib.util
import os
import sys

# Dynamic import of daily_poster module to support hyphenated Vercel filename
spec = importlib.util.spec_from_file_location("daily_poster", os.path.join(os.path.dirname(__file__), "daily_poster.py"))
daily_poster = importlib.util.module_from_spec(spec)
sys.modules["daily_poster"] = daily_poster
spec.loader.exec_module(daily_poster)

handler = daily_poster.handler
find_poster_image = daily_poster.find_poster_image
send_daily_poster = daily_poster.send_daily_poster

if __name__ == "__main__":
    dish_arg = sys.argv[1] if len(sys.argv) > 1 else "bread omlete"
    print(f"Finding poster image for '{dish_arg}'...")
    try:
        path = find_poster_image(dish_arg)
        print(f"Found poster image: {path}")
    except Exception as err:
        print(f"Error: {err}")
