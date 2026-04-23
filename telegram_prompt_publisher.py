"""
Pubblica un prompt su Telegram con banner.
Uso: python telegram_prompt_publisher.py [--id <prompt_id>]
"""

import os
import json
import random
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID")
PROMPTS_URL = os.getenv("PROMPTS_URL", "https://www.fabiofidone.it/data/aiprompts.json")
PROMPTS_FILE = Path(__file__).parent / "data" / "aiprompts.json"
BANNER_FILE  = Path(__file__).parent / "data" / "telegram_banner.png"

BASE = f"https://api.telegram.org/bot{TOKEN}"


def load_prompts():
    if PROMPTS_FILE.exists():
        with open(PROMPTS_FILE, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    print(f"File locale non trovato, scarico da {PROMPTS_URL}...")
    resp = requests.get(PROMPTS_URL, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def pick_prompt(prompts, prompt_id=None):
    if prompt_id:
        for p in prompts:
            if p["id"] == prompt_id:
                return p
        raise ValueError(f"ID '{prompt_id}' non trovato.")
    return random.choice(prompts)


def build_caption(prompt):
    title    = prompt.get("title") or prompt.get("text", "")[:60]
    category = prompt.get("category", "prompt").upper()
    return f"🧠 *{title}*\n\n📂 #{category} #aiprompt #promptlab"


def build_text(prompt):
    text = prompt.get("text", "").strip()
    # Escape caratteri Markdown problematici
    for ch in ["_", "*", "[", "]", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return f"📝 *Prompt:*\n\n{text}\n\n🔗 [fabiofidone\\.it](https://www.fabiofidone.it)"


def send_photo(caption):
    with open(BANNER_FILE, "rb") as img:
        resp = requests.post(
            f"{BASE}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "MarkdownV2"},
            files={"photo": img},
            timeout=30,
        )
    if not resp.ok:
        print(f"[ERROR] sendPhoto: {resp.status_code} — {resp.text}")
        resp.raise_for_status()
    return resp.json()


def send_text(text):
    resp = requests.post(
        f"{BASE}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "MarkdownV2"},
        timeout=15,
    )
    if not resp.ok:
        print(f"[ERROR] sendMessage: {resp.status_code} — {resp.text}")
        resp.raise_for_status()
    return resp.json()


def main():
    if not TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN mancante nel .env")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--id", dest="prompt_id", default=None)
    args = parser.parse_args()

    prompts = load_prompts()
    prompt  = pick_prompt(prompts, args.prompt_id)
    title   = prompt.get("title") or prompt.get("text", "")[:60]

    print(f"Prompt selezionato: {title}")

    if BANNER_FILE.exists():
        send_photo(build_caption(prompt))
        print("[OK] Banner inviato")

    send_text(build_text(prompt))
    print(f"[OK] Testo inviato a {CHAT_ID}")


if __name__ == "__main__":
    main()
