import os
import sys
import json
import random
import re
import requests
from datetime import datetime
# Libreria per la traduzione gratuita (installa con: pip install deep-translator)
from deep_translator import GoogleTranslator

# =========================
# CONFIG
# =========================

DATA_FILE = r"D:\Documents and Settings\fabio-fidone\My Documents\data\aiprompts.json"
STATE_FILE = "linkedin_publisher_state.json"

# TOKEN DIRETTO
ACCESS_TOKEN = "AQU96cKvdpN1ZKeZPtErnLtHalIdiMpkwnWoCmtcJ8FYVx7ZqQUUXbuYpwEcVR3XOmAFJzE-DJEjc8VZd7iiFmAP7NjbpmKQ0rKPKQz5SnSa94PzSf48kFYVgvfLzrWbXa8X-TL21S09yD9-vNsDbszvKNNwvlwx4v0n710kTvFs86B5YtwLkHRya55aLGev2CQLLwB-Sk5HqFQUFXKRQUqB68jRAOAGEtBhCeOWCA1YpYOTtovB_dgGRC17ABiFclei90ce7WfVg7yaOZntVhCgO4uJl_Y8wE8SdJkMctEKEYuNg193c2vPR_1HdjiWWpFiLKFKfH_n6cL5Fhd0t0_ler4bfg"

LINKEDIN_API_POST = "https://api.linkedin.com/rest/posts"
LINKEDIN_API_USERINFO = "https://api.linkedin.com/v2/userinfo"

HEADERS_BASE = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Linkedin-Version": "202603",
    "X-Restli-Protocol-Version": "2.0.0"
}

HASHTAGS = "#AI #PromptEngineering #ChatGPT #Innovazione"

# =========================
# UTILS TRADUZIONE (Gratis)
# =========================

def translate_it(text: str) -> str:
    """Traduce il testo in italiano gestendo il limite di caratteri della libreria"""
    try:
        if not text or len(text.strip()) < 3:
            return text
        
        # Paracadute: Google Translate free ha limiti di caratteri per singola chiamata
        if len(text) > 4000:
            text = text[:4000]
            print(f"[WARN] Testo troncato a 4000 caratteri per la traduzione.")
        
        translated = GoogleTranslator(source='auto', target='it').translate(text)
        return translated
    except Exception as e:
        print(f"[WARN] Errore traduzione: {e}")
        return text

# =========================
# UTILS BASE
# =========================

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def load_prompts():
    if not os.path.exists(DATA_FILE):
        print(f"[ERROR] File non trovato: {DATA_FILE}")
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", [])
    return items if isinstance(items, list) else []

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"used_ids": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            return state if isinstance(state, dict) else {"used_ids": []}
    except:
        return {"used_ids": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# =========================
# LINKEDIN API
# =========================

def get_user_sub():
    try:
        r = requests.get(LINKEDIN_API_USERINFO, headers={"Authorization": f"Bearer {ACCESS_TOKEN}"}, timeout=30)
        if r.status_code == 200:
            return r.json().get("sub")
    except Exception as e:
        print(f"[ERROR] Errore Profilo: {e}")
    return None

def publish(author, text):
    payload = {
        "author": author,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "lifecycleState": "PUBLISHED"
    }
    try:
        r = requests.post(LINKEDIN_API_POST, headers=HEADERS_BASE, json=payload, timeout=30)
        return r.status_code, r.text
    except Exception as e:
        return 0, str(e)

# =========================
# CLEANING & LOGIC
# =========================

def split_prompt_items(text: str):
    text = (text or "").strip().strip('"').strip("'").replace("\n", " ")
    parts = [p.strip(" ,.;:-") for p in text.split(",")]
    return [p for p in parts if len(p) > 1]

def looks_like_keyword_stack(text: str) -> bool:
    if not text: return False
    return text.count(",") >= 6 or len(split_prompt_items(text)) >= 7

def fix_title(title: str, raw_text: str) -> str:
    title = normalize_spaces(title or "").strip('"\'')
    if not title:
        parts = split_prompt_items(raw_text)
        title = parts[0][:120].title() if parts else "Prompt AI"
    
    print(f"[INFO] Traduzione titolo...")
    return translate_it(title[:120]).title()

def clean_prompt_text(text: str) -> str:
    text = (text or "").strip()
    if not text: return ""

    if looks_like_keyword_stack(text):
        parts = split_prompt_items(text)
        cleaned = f" {parts[0]}. \n\n Stile e dettagli: {', '.join(parts[1:])}."
    else:
        # Pulizia base per testi narrativi
        text = text.replace("\r", " ").replace("\n", " ")
        cleaned = normalize_spaces(text)
    
    print(f"[INFO] Traduzione contenuto...")
    return translate_it(cleaned)

def build_post_text(prompt):
    today = datetime.now().strftime("%d/%m/%Y")
    title = prompt.get("_clean_title", "Prompt del giorno")
    content = prompt.get("_clean_text", "")
    
    # Tronca per LinkedIn se necessario (max 3000 caratteri per i post, restiamo sicuri a 2500)
    if len(content) > 2500:
        content = content[:2500] + "..."

    post = (
        f" Prompt AI del giorno — {today}\n\n"
        f" {title}\n\n"
        f" {content}\n\n"
        f"---------------------------------\n"
        f" Scopri altri prompt e news su:\n"
        f" www.fabiofidone.it\n\n"
        f"{HASHTAGS}"
    )
    return post

# =========================
# MAIN
# =========================

def main():
    if not ACCESS_TOKEN:
        print("[ERROR] Token mancante")
        sys.exit(1)

    prompts = load_prompts()
    state = load_state()
    used_ids = state.get("used_ids", [])

    sub = get_user_sub()
    if not sub:
        print("[ERROR] LinkedIn non autorizzato")
        sys.exit(1)

    author = f"urn:li:person:{sub}"

    # Tentativi per trovare un prompt non usato
    for _ in range(5):
        prompt_data = random.choice(prompts) if prompts else None
        if not prompt_data or prompt_data.get("id") in used_ids:
            continue

        # Elaborazione e Traduzione
        raw_text = str(prompt_data.get("text", ""))
        prompt_data["_clean_text"] = clean_prompt_text(raw_text)
        prompt_data["_clean_title"] = fix_title(prompt_data.get("title", ""), raw_text)

        post_body = build_post_text(prompt_data)
        
        print(f"[INFO] Pubblicazione prompt ID: {prompt_data['id']}")
        status, response = publish(author, post_body)

        if status in (200, 201):
            print("[OK] POST PUBBLICATO CON SUCCESSO")
            state["used_ids"].append(prompt_data["id"])
            save_state(state)
            sys.exit(0)
        elif "DUPLICATE_POST" in response:
            print("[WARN] Già pubblicato, ne provo un altro...")
            state["used_ids"].append(prompt_data["id"])
            save_state(state)
        else:
            print(f"[ERROR] Errore LinkedIn: {status} - {response}")
            sys.exit(1)

    print("[ERROR] Nessun post inviato dopo vari tentativi.")

if __name__ == "__main__":
    main()