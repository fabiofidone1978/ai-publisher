"""
Ricava il chat_id del canale. Esegui DOPO aver postato un messaggio nel canale.
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def main():
    # Verifica identità bot
    me = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=10).json()
    print(f"Bot: @{me['result']['username']} — {me['result']['first_name']}")

    # Recupera aggiornamenti recenti (tutti i tipi)
    updates = requests.get(
        f"https://api.telegram.org/bot{TOKEN}/getUpdates",
        params={"allowed_updates": ["message","channel_post","my_chat_member","chat_member"]},
        timeout=10
    ).json()
    results = updates.get("result", [])

    if not results:
        print("\nNessun aggiornamento trovato.")
        print("-> Posta un messaggio qualsiasi nel canale e rilancia questo script.")
        return

    chat_ids = {}
    for u in results:
        for key in ("message", "channel_post", "my_chat_member", "chat_member"):
            if key in u:
                chat = u[key].get("chat", {})
                chat_ids[chat.get("id")] = chat.get("title") or chat.get("username") or "?"

    print("\nChat trovate:")
    for cid, title in chat_ids.items():
        print(f"  {title}: {cid}")

    print("\n-> Copia l'ID del tuo canale e incollalo come TELEGRAM_CHAT_ID nel .env")

if __name__ == "__main__":
    main()
