"""
Telegram Prompt Publisher — AI Prompt Lab ITA
Pubblica prompt in modo deterministico su 3 fasce orarie (Lun-Ven).
Sabato: recap settimanale. Domenica: pausa.
"""

import os
import json
import argparse
import requests
from pathlib import Path
from datetime import date, datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID")
PROMPTS_URL  = os.getenv("PROMPTS_URL", "https://www.fabiofidone.it/data/aiprompts.json")
PROMPTS_FILE = Path(__file__).parent / "data" / "aiprompts.json"
BANNER_FILE  = Path(__file__).parent / "data" / "telegram_banner.png"
BASE         = f"https://api.telegram.org/bot{TOKEN}"
REF_DATE     = date(2026, 1, 1)

SLOTS = [
    {"id": 0, "label": "Prompt del Mattino",  "emoji": "🌅", "utc_hour": 7},
    {"id": 1, "label": "Prompt della Pausa",  "emoji": "☀️", "utc_hour": 12},
    {"id": 2, "label": "Prompt della Sera",   "emoji": "🌆", "utc_hour": 17},
]

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


# ── Selezione deterministica ────────────────────────────────────────────────

def day_index(d=None):
    return ((d or date.today()) - REF_DATE).days


def current_slot():
    hour = datetime.now(timezone.utc).hour
    if hour < 10:
        return 0
    elif hour < 15:
        return 1
    return 2


def get_prompt(prompts, d=None, slot=None):
    di = day_index(d)
    si = slot if slot is not None else current_slot()
    idx = (di * 3 + si) % len(prompts)
    return prompts[idx], si


# ── Caricamento prompt ──────────────────────────────────────────────────────

def load_prompts():
    if PROMPTS_FILE.exists():
        with open(PROMPTS_FILE, encoding="utf-8") as f:
            return json.load(f).get("items", [])
    print(f"File locale assente, scarico da {PROMPTS_URL}...")
    resp = requests.get(PROMPTS_URL, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


# ── Formattazione messaggi ──────────────────────────────────────────────────

def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_caption(prompt, slot_id):
    slot  = SLOTS[slot_id]
    title = esc(prompt.get("title") or prompt.get("text", "")[:60])
    cat   = prompt.get("category", "prompt").lower()
    return (
        f"{slot['emoji']} <b>{slot['label']}</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"#{cat} #aiprompt #promptlab #AI"
    )


def build_text(prompt):
    text = esc(prompt.get("text", "").strip())
    return (
        f"📝 <b>Prompt:</b>\n\n"
        f"{text}\n\n"
        f"🔗 <a href=\"https://www.fabiofidone.it\">fabiofidone.it</a>"
    )


def build_weekly_recap(prompts):
    today = date.today()
    lines = ["📅 <b>Prompt della Settimana</b>\n\nI migliori prompt di questa settimana su AI Prompt Lab ITA:\n"]
    for days_back in range(5, 0, -1):
        d     = date.fromordinal(today.toordinal() - days_back)
        p, _  = get_prompt(prompts, d=d, slot=0)
        title = esc(p.get("title") or p.get("text", "")[:60])
        giorno = GIORNI_IT[d.weekday()]
        lines.append(f"<b>{giorno}</b> — {title}")
    lines.append("\n🔔 Seguici per non perdere nessun prompt!\n🔗 <a href=\"https://www.fabiofidone.it\">fabiofidone.it</a>")
    return "\n".join(lines)


# ── Invio Telegram ──────────────────────────────────────────────────────────

def send_photo(caption):
    with open(BANNER_FILE, "rb") as img:
        resp = requests.post(
            f"{BASE}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
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
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if not resp.ok:
        print(f"[ERROR] sendMessage: {resp.status_code} — {resp.text}")
        resp.raise_for_status()
    return resp.json()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN mancante nel .env")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int, choices=[0, 1, 2], default=None,
                        help="Forza slot: 0=mattino 1=pausa 2=sera")
    parser.add_argument("--recap", action="store_true", help="Forza recap settimanale")
    args = parser.parse_args()

    today     = date.today()
    weekday   = today.weekday()  # 0=Lun, 5=Sab, 6=Dom

    if weekday == 6 and not args.recap and args.slot is None:
        print("Domenica — nessuna pubblicazione.")
        return

    prompts = load_prompts()

    if weekday == 5 or args.recap:
        print("Sabato — invio recap settimanale")
        if BANNER_FILE.exists():
            send_photo("📅 <b>Prompt della Settimana</b>\n\n#aiprompt #promptlab #AI")
        send_text(build_weekly_recap(prompts))
        print("[OK] Recap settimanale inviato")
        return

    prompt, slot_id = get_prompt(prompts, slot=args.slot)
    title = prompt.get("title") or prompt.get("text", "")[:60]
    print(f"Slot {slot_id} — {SLOTS[slot_id]['label']}: {title}")

    if BANNER_FILE.exists():
        send_photo(build_caption(prompt, slot_id))
        print("[OK] Banner inviato")

    send_text(build_text(prompt))
    print(f"[OK] Prompt inviato a {CHAT_ID}")


if __name__ == "__main__":
    main()
