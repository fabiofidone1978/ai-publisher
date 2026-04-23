import os
import re
import csv
import json
import hashlib
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List

# =========================================================
# CONFIGURAZIONE PERCORSI
# =========================================================
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
PROMPTS_FILE = os.path.join(DATA_DIR, "aiprompts.json")

# =========================================================
# FONTI AD ALTO RENDIMENTO
# =========================================================
HIGH_YIELD_SOURCES = [
    "https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/main/prompts.csv",
    "https://raw.githubusercontent.com/Anil-Matcha/ChatGPT-Prompts/main/prompts.csv",
    "https://raw.githubusercontent.com/mattnigh/ChatGPT3-Free-Prompt-List/main/market-research.csv",
    "https://raw.githubusercontent.com/travistangvh/ChatGPT-Data-Science-Prompts/main/data_science_prompts.csv",
    "https://raw.githubusercontent.com/cloud-community/ChatGPT-Prompts/main/prompts.json"
]

# Nuove fonti artistiche (PromptHero Style)
EXTRA_ART_SOURCES = [
    "https://raw.githubusercontent.com/mooler0410/LLMs-Generate-Prompts/main/datasets/diffusion_prompts.csv",
    "https://raw.githubusercontent.com/willwulfken/MidJourney-Styles-and-Keywords-Reference/main/prompts/composition.csv",
    "https://raw.githubusercontent.com/S-S-S-S-S-S-S-S-S-S/Stable-Diffusion-Prompts/main/prompts.csv"
]

MAX_PROMPTS_TOTAL = 8000
USER_AGENT = "fabiofidone-archiver/6.0"

# =========================================================
# LOGICA DI FILTRAGGIO E DEDUP
# =========================================================

def is_pure_prompt(text: str) -> bool:
    """Filtro severo per scartare discussioni e rumore sociale."""
    if not text or len(text) < 120: return False
    
    text_low = text.lower()
    
    # Scarta se contiene troppi punti di domanda o termini da forum
    noise = ["?", "anyone", "help", "thoughts", "opinion", "advice", "guys", "work for me", "how to"]
    if text_low.count("?") > 1 or any(word in text_low for word in noise):
        return False
        
    # Scarta narrazioni in prima persona (discussioni)
    if text_low.startswith(("i've", "i have", "my experience", "so i built")):
        return False
        
    return True

def generate_fingerprint(text: str) -> str:
    """Genera un hash unico del testo per escludere i doppioni."""
    # Normalizza per ignorare spazi e maiuscole nel confronto
    clean_text = re.sub(r'\W+', '', text).lower()
    return hashlib.sha1(clean_text.encode("utf-8")).hexdigest()[:12]

# =========================================================
# ESTRAZIONE DATI
# =========================================================

def fetch_prompts(url_list: List[str], category: str) -> List[Dict[str, Any]]:
    """Scarica e processa i file remoti (CSV o JSON)."""
    out = []
    for url in url_list:
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            if r.status_code != 200: continue

            if url.endswith(".csv"):
                reader = csv.DictReader(r.text.splitlines())
                for row in reader:
                    # Mappatura flessibile delle colonne
                    title = row.get('act') or row.get('title') or row.get('name') or "AI System"
                    body = row.get('prompt') or row.get('text') or row.get('instruction')
                    if body and is_pure_prompt(body):
                        out.append(format_item(title, body, category, "github_repo"))
            
            elif url.endswith(".json"):
                data = r.json()
                items = data if isinstance(data, list) else data.get("items", [])
                for i in items:
                    title = i.get("title") or "AI Task"
                    body = i.get("prompt") or i.get("text")
                    if body and is_pure_prompt(body):
                        out.append(format_item(title, body, category, "github_repo"))
        except: continue
    return out

def format_item(title: str, text: str, category: str, source: str) -> Dict[str, Any]:
    """Formatta l'oggetto finale per il sito."""
    return {
        "id": generate_fingerprint(text), # L'ID è basato sul testo (DEDUP)
        "title": title.strip(),
        "category": category,
        "text": text.strip(),
        "source": source,
        "published_at": datetime.now(timezone.utc).isoformat()
    }

# =========================================================
# MAIN
# =========================================================

def main():
    print("Inizio scansione fonti massive...")
    
    # 1. Carica i dati attuali (se esistono) per evitare di ricaricare duplicati
    all_items = []
    seen_hashes = set()
    
    if os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f).get("items", [])
            for item in old_data:
                all_items.append(item)
                seen_hashes.add(item["id"])

    # 2. Scarica nuovi dati dividendo per categoria
    print("Acquisizione prompt generici...")
    generic_prompts = fetch_prompts(HIGH_YIELD_SOURCES, "prompt")
    
    print("Acquisizione prompt artistici...")
    art_prompts = fetch_prompts(EXTRA_ART_SOURCES, "creative")

    # 3. Merge con esclusione rigorosa dei doppioni
    new_added = 0
    for p in (generic_prompts + art_prompts):
        if p["id"] not in seen_hashes:
            all_items.append(p)
            seen_hashes.add(p["id"])
            new_added += 1

    # 4. Ordinamento e limite
    all_items = sorted(all_items, key=lambda x: x["published_at"], reverse=True)[:MAX_PROMPTS_TOTAL]

    # 5. Scrittura file
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_items),
        "items": all_items
    }

    with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"--- RISULTATO ---")
    print(f"Nuovi prompt (unici) aggiunti: {new_added}")
    print(f"Totale prompt pronti sul sito: {len(all_items)}")

if __name__ == "__main__":
    main()