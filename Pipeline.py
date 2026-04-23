#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI NEWS NEWSLETTER PIPELINE
Legge news da ainews.json, seleziona le top 5, invia newsletter
"""

import os
import sys
import json
import smtplib
import requests
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv(Path(__file__).parent / "_.env")

EMAIL_FROM     = os.getenv("EMAIL_FROM", "noreply@fabiofidone.it")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER    = os.getenv("SMTP_SERVER", "smtps.aruba.it")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "465"))

EMAILS_PHP_URL   = os.getenv("EMAILS_PHP_URL", "https://www.fabiofidone.it/get_newsletter_emails.php")
EMAILS_PHP_TOKEN = os.getenv("EMAILS_PHP_TOKEN", "fabiofidone_secure_token_2026")

BASE_DIR  = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"
NEWS_FILE = DATA_DIR / "ainews.json"
LOG_DIR   = BASE_DIR / "logs"
JSON_DIR  = BASE_DIR / "json_news"

LOG_DIR.mkdir(exist_ok=True)
JSON_DIR.mkdir(exist_ok=True)


# ============================================================
# LOGGER
# ============================================================

class Logger:
    def __init__(self):
        self.log_file  = LOG_DIR / f"pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"
        self.start_time = datetime.now()

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")

    def section(self, title):
        self.log("=" * 80)
        self.log(f"  {title}")
        self.log("=" * 80)

logger = Logger()


# ============================================================
# STEP 1 — Leggi news da ainews.json
# ============================================================

def load_news_from_file():
    logger.section("STEP 1: LETTURA NEWS DA ainews.json")

    if not NEWS_FILE.exists():
        logger.log(f"[ERROR] File non trovato: {NEWS_FILE}", "ERROR")
        logger.log("Esegui prima publish_all.py per raccogliere le news.", "ERROR")
        return []

    try:
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data.get("items", []) if isinstance(data, dict) else data
        items = [i for i in items if isinstance(i, dict) and i.get("title") and i.get("url")]

        logger.log(f"[OK] Caricate {len(items)} news da {NEWS_FILE}")
        return items

    except Exception as e:
        logger.log(f"[ERROR] Lettura ainews.json: {e}", "ERROR")
        return []


# ============================================================
# STEP 2 — Selezione editoriale algoritmica (no AI)
# ============================================================

# Priorità per publisher: più alto = più importante
PUBLISHER_PRIORITY = {
    "Anthropic":        10,
    "OpenAI":           10,
    "Google DeepMind":   9,
    "Google Research":   8,
    "Hugging Face":      7,
    "TechCrunch":        4,
}

def score_item(item):
    pub_score  = PUBLISHER_PRIORITY.get(item.get("publisher", ""), 3)
    has_summary = 1 if item.get("summary") else 0

    # Punteggio data: più recente = più alto
    from datetime import timezone
    date_score = 0
    pub_date = item.get("published_at")
    if pub_date:
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date) if "," in pub_date else datetime.fromisoformat(pub_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - dt).days
            date_score = max(0, 30 - age_days)  # 0-30 punti
        except Exception:
            pass

    return pub_score * 3 + date_score + has_summary


def editorial_selection(news_items):
    logger.section("STEP 2: SELEZIONE EDITORIALE (algoritmica)")

    if not news_items:
        logger.log("[ERROR] Nessuna news disponibile", "ERROR")
        return None

    ranked = sorted(news_items, key=score_item, reverse=True)

    # Prendi le prime 5, una per publisher per evitare duplicati della stessa fonte
    selected = []
    seen_publishers = set()
    for item in ranked:
        pub = item.get("publisher", "unknown")
        if pub not in seen_publishers or len(selected) < 5:
            selected.append(item)
            seen_publishers.add(pub)
        if len(selected) == 5:
            break

    news = []
    for item in selected:
        summary = (item.get("summary") or "").strip()
        news.append({
            "title":     item.get("title", "N/D"),
            "editorial": summary if summary else "Nessun sommario disponibile.",
            "source":    item.get("publisher", item.get("source", "N/D")),
            "url":       item.get("url", "#"),
            "relevance": f"Pubblicato da {item.get('publisher', 'N/D')}",
        })

    logger.log(f"[OK] Selezionate {len(news)} notizie")
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "news": news,
    }


# ============================================================
# STEP 3 — Salva JSON
# ============================================================

def save_json(news_data):
    logger.section("STEP 3: SALVATAGGIO JSON")
    try:
        filename = f"news_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        filepath = JSON_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        logger.log(f"[OK] JSON salvato: {filepath}")
        return filepath
    except Exception as e:
        logger.log(f"[ERROR] Salvataggio JSON: {e}", "ERROR")
        return None


# ============================================================
# STEP 4 — Genera HTML newsletter
# ============================================================

def generate_html(news_data):
    html = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News Daily</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 620px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 24px 20px; border-radius: 8px; text-align: center; margin-bottom: 30px; }
        .header h1 { margin: 0 0 6px; font-size: 24px; }
        .header p  { margin: 0; font-size: 14px; opacity: 0.85; }
        .news-item { background: white; padding: 20px; margin-bottom: 16px; border-radius: 6px; border-left: 4px solid #667eea; box-shadow: 0 1px 3px rgba(0,0,0,.07); }
        .news-item h3 { margin: 0 0 8px; font-size: 16px; color: #222; }
        .meta  { font-size: 12px; color: #999; margin-bottom: 10px; }
        .editorial { font-size: 14px; color: #444; line-height: 1.6; margin-bottom: 10px; }
        .relevance { font-size: 13px; color: #555; margin-bottom: 12px; }
        .cta { display: inline-block; background: #667eea; color: white; padding: 8px 14px; text-decoration: none; border-radius: 4px; font-size: 13px; }
        .footer { text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI News Daily</h1>
        <p>Le notizie più importanti del mondo AI — selezionate per te</p>
    </div>
"""

    for news in news_data.get("news", []):
        title     = news.get("title", "N/D")
        editorial = news.get("editorial", news.get("abstract", "N/D"))
        source    = news.get("source", "N/D")
        url       = news.get("url", "#")
        relevance = news.get("relevance", "")
        date      = news_data.get("date", "N/D")

        html += f"""
    <div class="news-item">
        <h3>{title}</h3>
        <div class="meta">Fonte: {source} &nbsp;|&nbsp; {date}</div>
        <p class="editorial">{editorial}</p>
        {"<p class='relevance'><strong>Perché è rilevante:</strong> " + relevance + "</p>" if relevance else ""}
        <a href="{url}" class="cta">Leggi l'articolo</a>
    </div>
"""

    html += """
    <div class="footer">
        <p>Newsletter di Fabio Fidone — AI &amp; Data Engineering</p>
        <p>www.fabiofidone.it</p>
    </div>
</body>
</html>"""

    return html


# ============================================================
# STEP 4b — Leggi destinatari dal DB MySQL
# ============================================================

def fetch_emails_from_db():
    logger.section("STEP 4: LETTURA DESTINATARI DA PHP/MySQL")

    try:
        url = f"{EMAILS_PHP_URL}?token={EMAILS_PHP_TOKEN}"
        logger.log(f"Chiamata a {EMAILS_PHP_URL}...")
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "ok":
            logger.log(f"[ERROR] PHP ha risposto: {data.get('error', 'errore sconosciuto')}", "ERROR")
            return []

        emails = [e.strip() for e in data.get("emails", []) if e and e.strip()]
        logger.log(f"[OK] {len(emails)} destinatari letti dal DB via PHP")
        return emails

    except Exception as e:
        logger.log(f"[ERROR] Lettura email via PHP: {e}", "ERROR")
        return []


# ============================================================
# STEP 5 — Invia email
# ============================================================

def send_emails(emails, news_data):
    logger.section("STEP 5: INVIO EMAIL")

    if not all([EMAIL_FROM, EMAIL_PASSWORD]):
        logger.log("[ERROR] Credenziali email incomplete nel .env", "ERROR")
        return False

    if not emails:
        logger.log("[ERROR] Nessun destinatario in EMAIL_LIST", "ERROR")
        return False

    try:
        html_content = generate_html(news_data)
        logger.log(f"Connessione a {SMTP_SERVER}:{SMTP_PORT}...")

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            logger.log("[OK] Connessione stabilita")
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            logger.log("[OK] Autenticato")

            failed = []
            for email in emails:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = f"AI News Daily — {news_data.get('date', 'N/D')}"
                    msg["From"]    = EMAIL_FROM
                    msg["To"]      = email
                    msg.attach(MIMEText(html_content, "html", "utf-8"))
                    server.send_message(msg)
                    logger.log(f"    [OK] Inviata a {email}")
                except Exception as e:
                    logger.log(f"    [ERROR] {email}: {e}", "ERROR")
                    failed.append(email)

            logger.log(f"[OK] {len(emails) - len(failed)}/{len(emails)} email inviate")
            return len(failed) == 0

    except Exception as e:
        logger.log(f"[ERROR] SMTP: {e}", "ERROR")
        return False



# ============================================================
# MAIN
# ============================================================

def main():
    logger.section("[START] AI NEWS NEWSLETTER PIPELINE")

    results = {}

    # 1 — Leggi news dal file
    news_items = load_news_from_file()
    if not news_items:
        logger.log("[ERROR] Nessuna news disponibile. ABORT", "ERROR")
        return 1
    results["news_loaded"] = len(news_items)

    # 2 — Gemini: selezione editoriale
    news_data = editorial_selection(news_items)
    if not news_data:
        logger.log("[ERROR] Selezione editoriale fallita. ABORT", "ERROR")
        return 1
    results["editorial"] = True

    # 3 — Salva JSON
    json_file = save_json(news_data)
    results["json_saved"] = json_file is not None

    # 4 — Destinatari dal DB
    emails = fetch_emails_from_db()
    results["recipients"] = len(emails)

    # 5 — Invia email
    email_success = send_emails(emails, news_data) if emails else False
    results["emails_sent"] = email_success

    # Riepilogo
    logger.section("[RIEPILOGO]")
    for step, status in results.items():
        if status is True:
            status_str = "[OK]"
        elif status is False:
            status_str = "[ERROR]"
        else:
            status_str = f"[INFO] {status}"
        logger.log(f"  {step:20} {status_str}")

    duration = (datetime.now() - logger.start_time).total_seconds()
    logger.log(f"[TIME] Durata: {duration:.1f}s")
    logger.log("[END] PIPELINE COMPLETATA")

    return 0


if __name__ == "__main__":
    sys.exit(main())
