"""
Telegram Prompt Publisher — AI Prompt Lab ITA
Pubblica prompt in modo deterministico su 4 fasce orarie (Lun-Ven, 2 nel weekend).
Sabato mattina: recap settimanale. Lo slot arriva sempre da --slot (workflow), non dall'ora di esecuzione:
un ritardo dei cron di GitHub non sposta piu il prompt.

Uso:  python telegram_prompt_publisher.py --slot N      pubblica lo slot N (0 mattino, 1 pausa, 2 sera, 3 notte)
      python telegram_prompt_publisher.py --recap       recap settimanale
      python telegram_prompt_publisher.py --dry ...     mostra cosa invierebbe, senza inviare
      python telegram_prompt_publisher.py --check       verifica token, canale e permessi del bot (sola lettura)
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from datetime import date, datetime, timezone
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN              = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID            = os.getenv("TELEGRAM_CHAT_ID")
PROMOFINDER_CHAT   = os.getenv("PROMOFINDER_CHAT_ID")
PROMOFINDER_URL    = os.getenv("PROMOFINDER_URL", "https://www.promofinder.it")
PROMPTS_URL        = os.getenv("PROMPTS_URL", "https://www.fabiofidone.it/data/aiprompts.json")
PROMPTS_FILE       = Path(__file__).parent / "data" / "aiprompts.json"
BANNER_FILE        = Path(__file__).parent / "data" / "telegram_banner.png"
BANNER_PROMO_FILE  = Path(__file__).parent / "data" / "banner_promo_promofinder.png"
BASE               = f"https://api.telegram.org/bot{TOKEN}"
REF_DATE           = date(2026, 1, 1)    # vecchia numerazione: 3 slot al giorno (fino al 22/06/2026)
CROSSPROMO_EVERY   = 10   # ogni N post → promo PromoFinder
# Nuova numerazione: 4 slot al giorno, continua dal punto in cui il vecchio schema si e fermato
# (ultimo indice usato 172*3+2 = 518), cosi i prompt gia pubblicati non tornano.
REF_NEW            = date(2026, 10, 12)
OLD_END_INDEX      = 518
SLOTS_PER_DAY      = 4
MAX_TEXT           = 4000   # limite Telegram 4096 per messaggio
MAX_CAPTION        = 1000   # limite Telegram 1024 per didascalia

SLOTS = [
    {"id": 0, "label": "Prompt del Mattino",  "emoji": "🌅", "utc_hour": 7},
    {"id": 1, "label": "Prompt della Pausa",  "emoji": "☀️", "utc_hour": 12},
    {"id": 2, "label": "Prompt della Sera",   "emoji": "🌆", "utc_hour": 17},
    {"id": 3, "label": "Prompt della Notte",  "emoji": "🌙", "utc_hour": 19},
]

GIORNI_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]


# ── Selezione deterministica ────────────────────────────────────────────────

def day_index(d=None):
    return ((d or date.today()) - REF_DATE).days


def current_slot():
    """Solo per uso manuale senza --slot: il workflow passa sempre lo slot esplicito."""
    hour = datetime.now(timezone.utc).hour
    if hour < 10:
        return 0
    elif hour < 15:
        return 1
    elif hour < 19:
        return 2
    return 3


def post_number(d, si):
    """Numero progressivo del post (indice assoluto, prima del modulo sul numero di prompt)."""
    d = d or date.today()
    if d < REF_NEW:
        return day_index(d) * 3 + si
    return OLD_END_INDEX + 1 + (d - REF_NEW).days * SLOTS_PER_DAY + si


def get_prompt(prompts, d=None, slot=None):
    si = slot if slot is not None else current_slot()
    return prompts[post_number(d, si) % len(prompts)], si


def is_crosspromo_turn(slot=None):
    si = slot if slot is not None else current_slot()
    return post_number(None, si) % CROSSPROMO_EVERY == 0


# ── Caricamento prompt ──────────────────────────────────────────────────────

def is_readable(prompt):
    text = prompt.get("text", "").strip()
    if not text or len(text) < 30:
        return False
    if text.startswith("{") or text.startswith("["):
        return False
    return True


def load_prompts():
    if PROMPTS_FILE.exists():
        with open(PROMPTS_FILE, encoding="utf-8") as f:
            raw = json.load(f).get("items", [])
    else:
        print(f"File locale assente, scarico da {PROMPTS_URL}...")
        resp = requests.get(PROMPTS_URL, timeout=15)
        resp.raise_for_status()
        raw = resp.json().get("items", [])
    prompts = [p for p in raw if is_readable(p)]
    print(f"Prompt validi: {len(prompts)} / {len(raw)}")
    return prompts


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


def build_crosspromo_promofinder():
    return (
        "💸 <b>Risparmia ogni giorno con PromoFinder!</b>\n\n"
        "Codici sconto, offerte esclusive e cashback selezionati per te.\n"
        "Migliaia di brand italiani e internazionali.\n\n"
        "👉 Unisciti al canale e non perdere nessuna promozione!\n\n"
        f"🔗 <a href=\"{PROMOFINDER_URL}\">promofinder.it</a>"
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

DRY = False


def _post(method, attempts=4, **kwargs):
    """POST all'API Telegram con ritentativi: rispetta il 429 (retry_after) e gli errori di rete."""
    last = None
    for attempt in range(attempts):
        try:
            resp = requests.post(f"{BASE}/{method}", **kwargs)
        except requests.RequestException as e:
            last = e
            print(f"[WARN] {method} tentativo {attempt + 1}/{attempts}: {type(e).__name__}")
            time.sleep(3 * (attempt + 1))
            continue
        if resp.ok:
            return resp.json()
        if resp.status_code == 429:
            wait = int(resp.json().get("parameters", {}).get("retry_after", 5))
            print(f"[WARN] {method} 429: attendo {wait}s")
            time.sleep(min(wait + 1, 60))
            continue
        if resp.status_code >= 500:
            last = RuntimeError(f"{method} {resp.status_code}")
            time.sleep(3 * (attempt + 1))
            continue
        print(f"[ERROR] {method}: {resp.status_code} — {resp.text[:300]}")
        resp.raise_for_status()
    raise RuntimeError(f"{method} fallito dopo {attempts} tentativi: {last}")


def send_photo(caption, banner=None):
    caption = cut(caption, MAX_CAPTION)
    if DRY:
        print(f"[dry] foto ({(banner or BANNER_FILE).name}) + didascalia:\n{caption}\n")
        return {}
    with open(banner or BANNER_FILE, "rb") as img:
        return _post("sendPhoto", data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                     files={"photo": img}, timeout=30)


def send_text(text):
    text = cut(text, MAX_TEXT)
    if DRY:
        print(f"[dry] messaggio:\n{text}\n")
        return {}
    return _post("sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)


def cut(text, limit):
    """Tronca senza spezzare un tag HTML a meta."""
    if len(text) <= limit:
        return text
    head = text[: limit - 1]
    if head.rfind("<") > head.rfind(">"):
        head = head[: head.rfind("<")]
    return head.rstrip() + "…"


def check():
    """Sola lettura: token valido, canale raggiungibile, il bot e amministratore con diritto di pubblicare."""
    me = requests.get(f"{BASE}/getMe", timeout=15).json()
    if not me.get("ok"):
        print(f"[KO] token non valido: {me.get('description')}")
        return 1
    bot_id = me["result"]["id"]
    print(f"[OK] bot @{me['result']['username']}")
    chat = requests.get(f"{BASE}/getChat", params={"chat_id": CHAT_ID}, timeout=15).json()
    if not chat.get("ok"):
        print(f"[KO] canale non raggiungibile: {chat.get('description')}")
        return 1
    print(f"[OK] canale {chat['result'].get('title')} ({chat['result'].get('username') and '@' + chat['result']['username']})")
    mem = requests.get(f"{BASE}/getChatMember", params={"chat_id": CHAT_ID, "user_id": bot_id}, timeout=15).json()
    st = mem.get("result", {})
    can_post = st.get("status") == "creator" or st.get("can_post_messages")
    print(f"[{'OK' if can_post else 'KO'}] ruolo del bot: {st.get('status')}, puo pubblicare: {bool(can_post)}")
    return 0 if can_post else 1


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN or not CHAT_ID:
        print("[ERROR] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID mancanti")
        raise SystemExit(1)          # esito KO: il workflow risulta fallito e si vede

    global DRY
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # emoji ok anche su console Windows
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int, choices=[0, 1, 2, 3], default=None,
                        help="Slot: 0=mattino 1=pausa 2=sera 3=notte")
    parser.add_argument("--recap", action="store_true", help="Forza recap settimanale")
    parser.add_argument("--dry", action="store_true", help="Non invia nulla: stampa i messaggi")
    parser.add_argument("--check", action="store_true", help="Verifica token, canale e permessi (sola lettura)")
    args = parser.parse_args()
    DRY = args.dry

    if args.check:
        raise SystemExit(check())

    today     = date.today()
    weekday   = today.weekday()  # 0=Lun, 5=Sab, 6=Dom

    prompts = load_prompts()

    # Il sabato senza --slot (cron del mattino) e il recap; con --slot si pubblica il prompt normale.
    if args.recap or (weekday == 5 and args.slot is None):
        print("Sabato — invio recap settimanale")
        if BANNER_FILE.exists():
            send_photo("📅 <b>Prompt della Settimana</b>\n\n#aiprompt #promptlab #AI")
        send_text(build_weekly_recap(prompts))
        print("[OK] Recap settimanale inviato")
        return

    prompt, slot_id = get_prompt(prompts, slot=args.slot)
    title = prompt.get("title") or prompt.get("text", "")[:60]

    if is_crosspromo_turn(args.slot):
        print(f"Slot {slot_id} — CROSS-PROMO PromoFinder")
        if BANNER_PROMO_FILE.exists():
            send_photo(
                "💸 <b>Risparmia ogni giorno!</b>\n\n#offerte #codici #risparmio #promofinder",
                banner=BANNER_PROMO_FILE
            )
        send_text(build_crosspromo_promofinder())
        print(f"[OK] Cross-promo PromoFinder inviata a {CHAT_ID}")
        return

    print(f"Slot {slot_id} — {SLOTS[slot_id]['label']}: {title}")
    if BANNER_FILE.exists():
        send_photo(build_caption(prompt, slot_id))
        print("[OK] Banner inviato")
    send_text(build_text(prompt))
    print(f"[OK] Prompt inviato a {CHAT_ID}")


if __name__ == "__main__":
    main()
