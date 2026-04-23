#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPLOAD FILE SU ARUBA VIA PHP
Carica file tramite POST HTTP:
- ainews.json + aiprompts.json da data/
- news_*.json da json_news/
"""

import os
import sys
import io
import requests
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_BASE = Path(__file__).parent
load_dotenv(_BASE / "_.env")

# Configurazione
ARUBA_UPLOAD_URL    = "https://www.fabiofidone.it/upload_files.php"
ARUBA_UPLOAD_TOKEN  = os.getenv("ARUBA_UPLOAD_TOKEN", "fabiofidone_secure_token_2026")
ARUBA_FILES         = [f.strip() for f in os.getenv("ARUBA_FILES", "ainews.json,aiprompts.json").split(",") if f.strip()]
ARUBA_LOCAL_FOLDER  = os.getenv("ARUBA_LOCAL_FOLDER", str(_BASE / "data"))
ARUBA_JSON_NEWS_FOLDER = os.getenv("ARUBA_JSON_NEWS_FOLDER", str(_BASE / "json_news"))

print("=" * 80)
print("UPLOAD FILE SU ARUBA (VIA PHP)")
print("=" * 80)
print()

print(f"URL: {ARUBA_UPLOAD_URL}")
print(f"Cartella data: {ARUBA_LOCAL_FOLDER}")
print(f"Cartella json_news: {ARUBA_JSON_NEWS_FOLDER}")
print()

# ============================================================================
# VERIFICA FILE DATA
# ============================================================================

print("[1/3] Verifica file locali...")
files_found = {}

for filename in ARUBA_FILES:
    filepath = Path(ARUBA_LOCAL_FOLDER) / filename
    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  ✓ {filename} ({size_mb:.2f} MB)")
        files_found[filename] = filepath
    else:
        print(f"  ✗ {filename} NON TROVATO")

# ============================================================================
# VERIFICA NEWS JSON
# ============================================================================

print()
print("  Notizie JSON:")

json_news_folder = Path(ARUBA_JSON_NEWS_FOLDER)

if json_news_folder.exists():
    # Trova il file JSON più recente
    news_files = sorted(json_news_folder.glob("news_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if news_files:
        latest_news = news_files[0]
        size_mb = latest_news.stat().st_size / (1024 * 1024)
        print(f"  ✓ {latest_news.name} ({size_mb:.2f} MB) - PIU RECENTE")
        files_found[latest_news.name] = latest_news
    else:
        print(f"  ✗ Nessun file news trovato in {ARUBA_JSON_NEWS_FOLDER}")
else:
    print(f"  ✗ Cartella {ARUBA_JSON_NEWS_FOLDER} non trovata")

if not files_found:
    print()
    print("[ERROR] Nessun file trovato!")
    exit(1)

print()

# ============================================================================
# UPLOAD VIA PHP
# ============================================================================

print("[2/3] Upload in corso...")
try:
    files_to_upload = []
    for filename, filepath in files_found.items():
        with open(filepath, 'rb') as f:
            files_to_upload.append((filename, (filename, f.read())))
    
    # POST a PHP
    response = requests.post(
        f"{ARUBA_UPLOAD_URL}?token={ARUBA_UPLOAD_TOKEN}",
        files=[(f[0], f[1]) for f in files_to_upload],
        timeout=30
    )
    
    response.raise_for_status()
    data = response.json()
    
    print()
    print("[3/3] Elaborazione risposta...")
    print()
    
    # Mostra risultati
    if data.get('files_uploaded'):
        print("File caricati:")
        for file_info in data['files_uploaded']:
            print(f"  ✓ {file_info['filename']} ({file_info.get('folder', 'data')})")
    
    if data.get('errors'):
        print()
        print("Errori:")
        for error in data['errors']:
            print(f"  ✗ {error}")
    
    print()
    print("=" * 80)
    
    if data.get('status') == 'success':
        print("SUCCESSO!")
        print()
        print("File disponibili su:")
        for file_info in data['files_uploaded']:
            print(f"  {file_info['url']}")
        print()
        print("=" * 80)
        exit(0)
    else:
        print("COMPLETATO CON ERRORI")
        print()
        print("=" * 80)
        exit(1)

except requests.exceptions.RequestException as e:
    print(f"[ERROR] Errore HTTP: {e}")
    print()
    print("Assicurati che:")
    print("  1. upload_files.php è online su https://www.fabiofidone.it/upload_files.php")
    print("  2. ARUBA_UPLOAD_TOKEN è corretto nel .env")
    print("  3. Sei connesso a Internet")
    exit(1)

except Exception as e:
    print(f"[ERROR] Errore: {e}")
    exit(1)