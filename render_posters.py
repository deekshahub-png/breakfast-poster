"""
Renders breakfast_poster_template.html into one PNG per dish using headless Chrome/Edge.

Output: posters/<dish folder name>.png  (the folder names match 'full dish photos/').
These finished posters ("Good Evening! / Tomorrow's Special Breakfast") are what
api/daily_poster.py sends over WhatsApp. Re-run this after editing the template,
then commit and push the posters/ folder.

Usage:  python render_posters.py
"""
import os
import pathlib
import shutil
import subprocess
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATE = BASE_DIR / "breakfast_poster_template.html"
OUT_DIR = BASE_DIR / "posters"

# Template dish key -> folder name under 'full dish photos/'
DISHES = {
    "Ragi_Dosa": "ragi dosa",
    "Wheat_Dosa_with_Coconut_Chutney": "wheat dosa + coconut chutney",
    "Poha_with_Nuts": "poha +nuts",
    "Idiyapam": "idiyapam",
    "Drumstick_Stew": "drumstick stew",
    "Fermented_Rice": "fermented rice (ice biriyani)",
    "Bread_Omelette": "bread omlete",
    "Millet_Porridge": "milet porridge + pickles",
    "Moong_Dal_Chilla": "Moong Dal Chilla",
    "Paneer_Bhurji": "Paneer Bhurji",
    "Ragi_Upma": "ragi upma",
    "Salad": "Salad",
    "Soups_with_Veggies": "soups + veggies",
    "Steamed_Sprouts": "steamed sprouts",
}

POSTER_W, POSTER_H = 595, 940
SCALE = 2  # 1190x1880 output, sharp on phones


def find_browser() -> str:
    candidates = [
        os.environ.get("CHROME_PATH", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome") or "",
        shutil.which("chromium") or "",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    sys.exit("Chrome or Edge not found. Set CHROME_PATH to the browser executable.")


def main():
    browser = find_browser()
    OUT_DIR.mkdir(exist_ok=True)
    for key, folder in DISHES.items():
        out = OUT_DIR / f"{folder}.png"
        url = TEMPLATE.as_uri() + f"?dish={key}&render=1"
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                f"--force-device-scale-factor={SCALE}",
                f"--window-size={POSTER_W},{POSTER_H}",
                "--virtual-time-budget=8000",  # let web fonts and images load
                f"--screenshot={out}",
                url,
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        print(f"[OK] {key:35s} -> {out.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
