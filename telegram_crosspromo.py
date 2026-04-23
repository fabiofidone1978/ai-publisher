"""
Cross-promo: pubblica una promo di AI Prompt Lab ITA sul canale PromoFinder.
Viene eseguito da GitHub Actions ogni lunedì e giovedì alle 09:00.
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN            = os.getenv("TELEGRAM_BOT_TOKEN")
PROMOFINDER_CHAT = os.getenv("PROMOFINDER_CHAT_ID")
BANNER_FILE      = Path(__file__).parent / "data" / "telegram_banner.png"
BASE             = f"https://api.telegram.org/bot{TOKEN}"

CAPTION = (
    "🧠 <b>AI Prompt Lab ITA</b>\n\n"
    "#AI #ChatGPT #prompt #intelligenzaartificiale"
)

TEXT = (
    "💡 <b>Scopri AI Prompt Lab ITA!</b>\n\n"
    "Prompt selezionati ogni giorno per ChatGPT, Midjourney "
    "e tutti gli strumenti di intelligenza artificiale.\n\n"
    "Gratis. Ogni giorno. 3 volte al giorno.\n\n"
    "👉 Unisciti al canale e porta la tua AI al livello successivo!\n\n"
    "🔗 <a href=\"https://www.fabiofidone.it\">fabiofidone.it</a>"
)


def send_photo():
    with open(BANNER_FILE, "rb") as img:
        resp = requests.post(
            f"{BASE}/sendPhoto",
            data={"chat_id": PROMOFINDER_CHAT, "caption": CAPTION, "parse_mode": "HTML"},
            files={"photo": img},
            timeout=30,
        )
    if not resp.ok:
        print(f"[ERROR] sendPhoto: {resp.status_code} — {resp.text}")
        resp.raise_for_status()


def send_text():
    resp = requests.post(
        f"{BASE}/sendMessage",
        json={"chat_id": PROMOFINDER_CHAT, "text": TEXT, "parse_mode": "HTML"},
        timeout=15,
    )
    if not resp.ok:
        print(f"[ERROR] sendMessage: {resp.status_code} — {resp.text}")
        resp.raise_for_status()


def main():
    if not TOKEN or not PROMOFINDER_CHAT:
        print("[ERROR] TELEGRAM_BOT_TOKEN o PROMOFINDER_CHAT_ID mancanti nel .env")
        return

    print(f"Invio cross-promo AI Prompt Lab → canale PromoFinder ({PROMOFINDER_CHAT})")
    if BANNER_FILE.exists():
        send_photo()
        print("[OK] Banner inviato")
    send_text()
    print("[OK] Cross-promo inviata")


if __name__ == "__main__":
    main()
