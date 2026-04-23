import os
import re
import csv
import json
import html
import time
import hashlib
import requests
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urljoin
from email.utils import parsedate_to_datetime

# ============================================================
# CONFIG
# ============================================================

REQUEST_TIMEOUT = 20
MAX_PROMPTS = 8000
MAX_NEWS = 1200
NEWS_MAX_AGE_DAYS = 45

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(REPO_ROOT, "data")

PROMPTS_FILE = os.path.join(DATA_DIR, "aiprompts.json")
NEWS_FILE    = os.path.join(DATA_DIR, "ainews.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Publisher/2.0"
}

csv.field_size_limit(10_000_000)

# ============================================================
# CLASSIFICATION SCHEMA
# ============================================================
#
# Ogni sorgente può portare questi campi opzionali di classificazione.
# Vengono copiati così come sono in ogni item prodotto da quella sorgente,
# così il JSON finale è filtrabile/raggruppabile senza cambiare la logica.
#
#   platform        : str  — piattaforma AI di destinazione dei prompt
#                            valori: "chatgpt" | "gpt4" | "claude" | "gemini" |
#                                    "midjourney" | "stable_diffusion" | "dall-e" |
#                                    "llama" | "multi" | "unknown"
#
#   content_type    : str  — natura del contenuto del prompt
#                            valori: "instruction" | "system_prompt" | "roleplay" |
#                                    "chain_of_thought" | "image_gen" | "conversation" |
#                                    "template" | "few_shot" | "unknown"
#
#   use_case        : str  — applicazione reale principale
#                            valori: "general" | "coding" | "writing" | "marketing" |
#                                    "education" | "data_science" | "legal" | "medical" |
#                                    "finance" | "hr" | "seo" | "customer_support" |
#                                    "design" | "research" | "productivity" |
#                                    "image_generation" | "agent" | "unknown"
#
#   language        : str  — lingua principale dei prompt (ISO 639-1)
#                            valori: "en" | "it" | "multi" | "unknown"
#
#   quality_tier    : str  — segnale di qualità editoriale
#                            valori: "curated"    (selezionati manualmente)
#                                  | "community"  (crowd-sourced / votati)
#                                  | "automated"  (scraping / generati da modello)
#                                  | "research"   (dataset accademico / fine-tuning)
#
#   volume_estimate : str  — stima del numero di prompt nella sorgente
#                            valori: "small"  (<500)
#                                  | "medium" (500-5k)
#                                  | "large"  (5k-100k)
#                                  | "xlarge" (>100k)
#
#   license         : str  — licenza dati nota (best-effort, non consulenza legale)
#                            valori: "mit" | "apache2" | "cc0" | "cc-by" |
#                                    "cc-by-sa" | "open" | "unknown"
#
# ============================================================

# ============================================================
# PROMPT SOURCES
# ============================================================

PROMPT_SOURCES = [

    # ----------------------------------------------------------
    # ORIGINALI — ChatGPT / GPT-4 · curated · English
    # ----------------------------------------------------------
    {
        "name": "f_prompts_chat_raw",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/f/awesome-chatgpt-prompts/refs/heads/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "medium",
        "license":         "cc0",
    },
    {
        "name": "fka_hf_mirror",
        "type": "csv",
        "category": "prompt",
        "url": "https://huggingface.co/datasets/fka/awesome-chatgpt-prompts/raw/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "medium",
        "license":         "cc0",
    },
    {
        # Può saltare se il file cambia o sparisce, ma il runtime lo gestisce
        "name": "krea_open_prompts_sample",
        "type": "csv",
        "category": "creative",
        "url": "https://raw.githubusercontent.com/krea-ai/open-prompts/main/data/1k.csv",
        "title_fields": ["title", "name", "category"],
        "text_fields":  ["prompt", "text", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "small",
        "license":         "open",
    },
    {
        "name": "gogptai_chatgpt_prompt",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/GoGPTAI/ChatGPT-Prompt/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "medium",
        "license":         "mit",
    },

    # ----------------------------------------------------------
    # GITHUB — repo ChatGPT/LLM molto citati · English
    # ----------------------------------------------------------
    {
        # Raccolta generalista con centinaia di ruoli / usi
        "name": "acheong08_chatgpt_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/acheong08/ChatGPT-Prompts/main/chatgpt_prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Fork curato da pacholoamit, aggiunge varianti e categorie
        "name": "pacholoamit_chatgpt_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/pacholoamit/ChatGPT-Prompts/main/chatgpt_prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Prompt focalizzati su data science e analisi dati
        "name": "travistang_ds_prompts",
        "type": "csv",
        "category": "data_science",
        "url": "https://raw.githubusercontent.com/travistangvh/ChatGPT-Data-Science-Prompts/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "data_science",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt SEO / marketing / copywriting
        "name": "yokoffing_chatgpt_prompts",
        "type": "csv",
        "category": "marketing",
        "url": "https://raw.githubusercontent.com/yokoffing/ChatGPT-Prompts/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "marketing",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Best-of dell'anno 2023-24, selezione editoriale manuale
        "name": "successfulstudy_prompt_of_year",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/successfulstudy/promptoftheyear/main/prompt.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per sviluppatori / coding / debugging
        "name": "dmatrix_genai_coding_prompts",
        "type": "csv",
        "category": "coding",
        "url": "https://raw.githubusercontent.com/dmatrix/genai-bootcamp/main/llm-apps/data/chatgpt_prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "coding",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "apache2",
    },
    {
        # Repo curato da promptslab con esempi avanzati di prompt engineering
        "name": "promptslab_awesome_pe",
        "type": "csv",
        "category": "prompt_engineering",
        "url": "https://raw.githubusercontent.com/promptslab/Awesome-Prompt-Engineering/main/resources/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "chain_of_thought",
        "use_case":        "research",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "apache2",
    },
    {
        # Prompt per roleplay / creative writing, repo molto attivo
        "name": "snackprompt_creative",
        "type": "csv",
        "category": "creative",
        "url": "https://raw.githubusercontent.com/snackprompt/snackprompt/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "roleplay",
        "use_case":        "writing",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Prompt per email, business writing e comunicazione professionale
        "name": "mattnigh_chatgpt_biz",
        "type": "csv",
        "category": "business",
        "url": "https://raw.githubusercontent.com/mattnigh/ChatGPT3-Free-Prompt-List/main/ChatGPT_Free_Prompt_List.csv",
        "title_fields": ["Category", "title", "act", "name"],
        "text_fields":  ["Prompt", "prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "productivity",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "medium",
        "license":         "mit",
    },
    {
        # Large CSV con oltre 1700 prompt, copertura molto ampia
        "name": "adeshola06_mega_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/adeshola06/chatgpt-prompts/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Prompt per educazione, insegnamento e tutoraggio
        "name": "educationalai_prompts",
        "type": "csv",
        "category": "education",
        "url": "https://raw.githubusercontent.com/microsoft/Education-Prompts/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "education",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt in italiano — raro, molto rilevante per siti italiani
        "name": "prompt_italiano_collection",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/Norby99/chatgpt-prompts-ita/main/prompts.csv",
        "title_fields": ["ruolo", "act", "title", "name"],
        "text_fields":  ["prompt", "testo", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "it",
        "quality_tier":    "community",
        "volume_estimate": "small",
        "license":         "unknown",
    },

    # ----------------------------------------------------------
    # SYSTEM PROMPTS — GPT / CustomGPTs leakati
    # ----------------------------------------------------------
    {
        # GPT-4 system prompts leakati e raccolti pubblicamente
        "name": "linexjlin_gpts_system_prompts",
        "type": "csv",
        "category": "system_prompt",
        "url": "https://raw.githubusercontent.com/linexjlin/GPTs/main/prompts.csv",
        "title_fields": ["name", "title", "act"],
        "text_fields":  ["prompt", "system_prompt", "text", "instruction", "content"],
        # classification
        "platform":        "gpt4",
        "content_type":    "system_prompt",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Collezione di system prompt da CustomGPTs pubblici
        "name": "LouisShark_chatgpt_system_prompts",
        "type": "csv",
        "category": "system_prompt",
        "url": "https://raw.githubusercontent.com/LouisShark/chatgpt_system_prompt/main/prompts.csv",
        "title_fields": ["name", "title", "act"],
        "text_fields":  ["prompt", "system_prompt", "text", "instruction", "content"],
        # classification
        "platform":        "gpt4",
        "content_type":    "system_prompt",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },

    # ----------------------------------------------------------
    # HUGGING FACE — istruzioni e conversazioni
    # ----------------------------------------------------------
    {
        # Dataset HF con ~170k prompt ChatGPT categorizzati
        "name": "hf_mohamedRashad_chatgpt_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://huggingface.co/datasets/MohamedRashad/ChatGPT-prompts/raw/main/data.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "cc0",
    },
    {
        # ShareGPT52K — conversazioni reali estratte da ShareGPT
        "name": "hf_anon8231489123_sharegpt",
        "type": "csv",
        "category": "prompt",
        "url": "https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/raw/main/ShareGPT_V3_unfiltered_cleaned_split.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["prompt", "instruction", "text", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "conversation",
        "use_case":        "general",
        "language":        "multi",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "unknown",
    },
    {
        # Alpaca cleaned — 52k istruzioni formato instruction/output
        "name": "hf_yahma_alpaca_cleaned",
        "type": "csv",
        "category": "instruction",
        "url": "https://huggingface.co/datasets/yahma/alpaca-cleaned/raw/main/alpaca_data_cleaned.csv",
        "title_fields": ["instruction", "title", "name"],
        "text_fields":  ["input", "instruction", "output", "text"],
        # classification
        "platform":        "llama",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "cc-by",
    },
    {
        # WizardLM Evol-Instruct 70k
        "name": "hf_WizardLM_evol_instruct",
        "type": "csv",
        "category": "instruction",
        "url": "https://huggingface.co/datasets/WizardLM/WizardLM_evol_instruct_70k/raw/main/alpaca_evol_instruct_70k.csv",
        "title_fields": ["instruction", "title", "act"],
        "text_fields":  ["instruction", "output", "text", "prompt"],
        # classification
        "platform":        "multi",
        "content_type":    "chain_of_thought",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "apache2",
    },
    {
        # OpenAssistant OASST1
        "name": "hf_oasst1_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://huggingface.co/datasets/OpenAssistant/oasst1/raw/main/data/train.csv",
        "title_fields": ["parent_id", "title", "name"],
        "text_fields":  ["text", "prompt", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "conversation",
        "use_case":        "general",
        "language":        "multi",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "apache2",
    },
    {
        # Dolly 15k — prompt aziendali da Databricks
        "name": "hf_databricks_dolly15k",
        "type": "csv",
        "category": "instruction",
        "url": "https://huggingface.co/datasets/databricks/databricks-dolly-15k/raw/main/databricks-dolly-15k.csv",
        "title_fields": ["instruction", "category", "title"],
        "text_fields":  ["instruction", "context", "response", "text"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "medium",
        "license":         "cc-by-sa",
    },
    {
        # FLAN-T5 2022 sample
        "name": "hf_flan_instructions_sample",
        "type": "csv",
        "category": "instruction",
        "url": "https://huggingface.co/datasets/conceptofmind/FLAN_2022/raw/main/flan2022_sample.csv",
        "title_fields": ["task_name", "title", "name"],
        "text_fields":  ["inputs", "instruction", "prompt", "text"],
        # classification
        "platform":        "multi",
        "content_type":    "few_shot",
        "use_case":        "research",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "apache2",
    },
    {
        # Camel AI — conversazioni role-play AI↔AI
        "name": "camel_ai_prompts",
        "type": "csv",
        "category": "agent",
        "url": "https://huggingface.co/datasets/camel-ai/ai_society/raw/main/ai_society_chat.csv",
        "title_fields": ["role_1", "title", "name"],
        "text_fields":  ["message_1", "prompt", "text", "instruction"],
        # classification
        "platform":        "multi",
        "content_type":    "roleplay",
        "use_case":        "agent",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "cc-by",
    },
    {
        # GPT4All curated prompts — dataset per fine-tuning open source
        "name": "nomic_gpt4all_prompts",
        "type": "csv",
        "category": "prompt",
        "url": "https://huggingface.co/datasets/nomic-ai/gpt4all-j-prompt-generations/raw/main/prompts.csv",
        "title_fields": ["title", "source", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "llama",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "large",
        "license":         "apache2",
    },

    # ----------------------------------------------------------
    # HUGGING FACE — Image Generation · Stable Diffusion / Midjourney
    # ----------------------------------------------------------
    {
        # ~2M prompt SD da Gustavosta
        "name": "hf_gustavosta_sd_prompts",
        "type": "csv",
        "category": "image_generation",
        "url": "https://huggingface.co/datasets/Gustavosta/Stable-Diffusion-Prompts/raw/main/data/train.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["Prompt", "prompt", "text", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "xlarge",
        "license":         "cc0",
    },
    {
        # Prompt Midjourney da succinctly
        "name": "hf_succinctly_midjourney",
        "type": "csv",
        "category": "image_generation",
        "url": "https://huggingface.co/datasets/succinctly/midjourney-prompts/raw/main/train.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["text", "Prompt", "prompt", "instruction"],
        # classification
        "platform":        "midjourney",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "unknown",
    },
    {
        # nateraw SD prompts — alta qualità artistica
        "name": "hf_nateraw_sd_prompts",
        "type": "csv",
        "category": "image_generation",
        "url": "https://huggingface.co/datasets/nateraw/stable-diffusion-prompts/raw/main/data/train.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["text", "prompt", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "cc0",
    },
    {
        "name": "hf_vivek7208_sd_prompts",
        "type": "csv",
        "category": "image_generation",
        "url": "https://huggingface.co/datasets/vivek7208/stable-diffusion-prompts/raw/main/prompts.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["prompt", "text", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "automated",
        "volume_estimate": "large",
        "license":         "unknown",
    },
    {
        # PromptHero / openjourney dataset
        "name": "prompthero_image_gen",
        "type": "csv",
        "category": "image_generation",
        "url": "https://raw.githubusercontent.com/prompthero/openjourney-dataset/main/mdjrny-v4-captions.csv",
        "title_fields": ["title", "name"],
        "text_fields":  ["text", "caption", "prompt", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "cc-by",
    },
    {
        # Civitai model prompts
        "name": "civitai_style_prompts",
        "type": "csv",
        "category": "image_generation",
        "url": "https://huggingface.co/datasets/Fazzie/Civitai/raw/main/prompts.csv",
        "title_fields": ["title", "name", "model"],
        "text_fields":  ["prompt", "text", "positive_prompt", "instruction"],
        # classification
        "platform":        "stable_diffusion",
        "content_type":    "image_gen",
        "use_case":        "image_generation",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "unknown",
    },

    # ----------------------------------------------------------
    # VERTICALI PER INDUSTRIA
    # ----------------------------------------------------------
    {
        # Prompt per HR, recruiting, gestione del personale
        "name": "hr_recruiting_prompts",
        "type": "csv",
        "category": "hr",
        "url": "https://raw.githubusercontent.com/filippodev/ChatGPT-Prompts-HR/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "hr",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per legal writing, contratti, analisi giuridica
        "name": "legal_prompts_collection",
        "type": "csv",
        "category": "legal",
        "url": "https://raw.githubusercontent.com/Awais-cb/chatgpt-legal-prompts/main/legal_prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "legal",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt medical / clinical — uso informativo
        "name": "medical_prompts_collection",
        "type": "csv",
        "category": "medical",
        "url": "https://raw.githubusercontent.com/abilzerian/LLM-Prompt-Library/main/prompts/medical/medical.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "medical",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt per finance, investimenti, analisi bilanci
        "name": "finance_prompts_abilzerian",
        "type": "csv",
        "category": "finance",
        "url": "https://raw.githubusercontent.com/abilzerian/LLM-Prompt-Library/main/prompts/finance/finance.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "finance",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Intera libreria abilzerian (all-in-one CSV)
        "name": "abilzerian_llm_library_all",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/abilzerian/LLM-Prompt-Library/main/prompts/all_prompts.csv",
        "title_fields": ["title", "name", "act", "category"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "medium",
        "license":         "mit",
    },
    {
        # Prompt per SEO: keyword research, meta descriptions, content briefs
        "name": "seo_prompts_collection",
        "type": "csv",
        "category": "seo",
        "url": "https://raw.githubusercontent.com/mikecreighton/ai-charter/main/data/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "seo",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per customer support e chatbot aziendale
        "name": "customer_support_prompts",
        "type": "csv",
        "category": "customer_support",
        "url": "https://raw.githubusercontent.com/hwchase17/langchain/master/docs/prompts/customer_service.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["template", "prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "template",
        "use_case":        "customer_support",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt per UX/design: user research, copy UI, wireframe descriptions
        "name": "ux_design_prompts",
        "type": "csv",
        "category": "design",
        "url": "https://raw.githubusercontent.com/aichaos/rivescript-js/master/data/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "design",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per STEM, matematica, scienze
        "name": "stem_education_prompts",
        "type": "csv",
        "category": "education",
        "url": "https://raw.githubusercontent.com/microsoft/promptbase/main/src/promptbase/data/prompts.csv",
        "title_fields": ["title", "name", "act", "category"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "gpt4",
        "content_type":    "chain_of_thought",
        "use_case":        "education",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt per marketing e social media
        "name": "socials_marketing_prompts",
        "type": "csv",
        "category": "marketing",
        "url": "https://raw.githubusercontent.com/ai-boost/awesome-prompts/main/prompts.csv",
        "title_fields": ["act", "title", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "marketing",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "medium",
        "license":         "unknown",
    },
    {
        # Prompt per creazione di contenuti: blog, newsletter, social
        "name": "content_creation_prompts",
        "type": "csv",
        "category": "content",
        "url": "https://raw.githubusercontent.com/Dromediansk/chatgpt-prompts-for-content-creation/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "template",
        "use_case":        "writing",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per coding: debug, refactor, review, architecture
        "name": "coding_prompts_collection",
        "type": "csv",
        "category": "coding",
        "url": "https://raw.githubusercontent.com/PromptExpert/coding-prompts/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "coding",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "unknown",
    },
    {
        # Prompt per scrittura creativa, fiction, worldbuilding
        "name": "creative_writing_prompts_large",
        "type": "csv",
        "category": "creative",
        "url": "https://raw.githubusercontent.com/JushBJJ/Mr.-Ranedeer-AI-Tutor/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "gpt4",
        "content_type":    "roleplay",
        "use_case":        "education",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Prompt per agenti AI autonomi (AutoGPT / BabyAGI style)
        "name": "agent_prompts_collection",
        "type": "csv",
        "category": "agent",
        "url": "https://raw.githubusercontent.com/Significant-Gravitas/AutoGPT/master/autogpts/autogpt/data/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "gpt4",
        "content_type":    "system_prompt",
        "use_case":        "agent",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "mit",
    },
    {
        # Mega-repo con prompt divisi per industria/verticale
        "name": "awesome_ai_prompts_by_industry",
        "type": "csv",
        "category": "business",
        "url": "https://raw.githubusercontent.com/ai-prompts-library/ai-prompts/main/all_prompts.csv",
        "title_fields": ["title", "category", "act", "name"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "template",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "unknown",
    },

    # ----------------------------------------------------------
    # LEARN PROMPTING / PROMPT REPORT — tecniche accademiche
    # ----------------------------------------------------------
    {
        # Learn Prompting — prompts dal corso open-source
        "name": "learnprompting_course_prompts",
        "type": "csv",
        "category": "prompt_engineering",
        "url": "https://raw.githubusercontent.com/trigaten/The-Prompt-Report/main/data/prompts.csv",
        "title_fields": ["title", "name", "technique"],
        "text_fields":  ["prompt", "text", "example", "instruction"],
        # classification
        "platform":        "multi",
        "content_type":    "few_shot",
        "use_case":        "research",
        "language":        "en",
        "quality_tier":    "research",
        "volume_estimate": "small",
        "license":         "cc-by",
    },
    {
        # PromptBase open samples
        "name": "promptbase_open_samples",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/trigaten/Learn_Prompting/main/data/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "multi",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "en",
        "quality_tier":    "curated",
        "volume_estimate": "small",
        "license":         "cc-by",
    },

    # ----------------------------------------------------------
    # COMMUNITY PLATFORMS
    # ----------------------------------------------------------
    {
        # FlowGPT export pubblico — comunità molto attiva con prompt votati
        "name": "flowgpt_public_export",
        "type": "csv",
        "category": "prompt",
        "url": "https://raw.githubusercontent.com/flowgpt-data/prompts/main/prompts.csv",
        "title_fields": ["title", "name", "act"],
        "text_fields":  ["prompt", "text", "instruction", "content"],
        # classification
        "platform":        "chatgpt",
        "content_type":    "instruction",
        "use_case":        "general",
        "language":        "multi",
        "quality_tier":    "community",
        "volume_estimate": "large",
        "license":         "unknown",
    },
]

# ============================================================
# NEWS SOURCES
# ============================================================

NEWS_SOURCES = [
    {
        "name": "openai_rss",
        "type": "rss",
        "publisher": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
    },
    {
        "name": "huggingface_blog_rss",
        "type": "rss",
        "publisher": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml",
    },
    {
        "name": "anthropic_news_html",
        "type": "html_list",
        "publisher": "Anthropic",
        "url": "https://www.anthropic.com/news",
        "item_pattern": r'<a[^>]+href="(?P<href>/news/[^"#?]+)"[^>]*>(?P<title>.*?)</a>',
    },
    {
        "name": "deepmind_blog_html",
        "type": "html_list",
        "publisher": "Google DeepMind",
        "url": "https://deepmind.google/blog/",
        "item_pattern": r'<a[^>]+href="(?P<href>/blog/[^"#?]+)"[^>]*>(?P<title>.*?)</a>',
    },
    {
        "name": "google_research_html",
        "type": "html_list",
        "publisher": "Google Research",
        "url": "https://research.google/blog/",
        "item_pattern": r'<a[^>]+href="(?P<href>/blog/[^"#?]+)"[^>]*>(?P<title>.*?)</a>',
    },
    {
        # Fallback pragmatico: se vuoi più volume editoriale AI
        "name": "techcrunch_ai_rss",
        "type": "rss",
        "publisher": "TechCrunch",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
    },
]

AI_NEWS_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "llm", "gpt", "openai",
    "anthropic", "claude", "gemini", "deepmind", "mistral", "hugging face",
    "model", "models", "agent", "agents", "reasoning", "inference", "training",
    "diffusion", "robotics", "multimodal", "computer use"
]

PROMPT_BAD_TERMS = [
    "anyone", "thoughts", "opinion", "built it", "reddit", "upvote", "comment",
    "discussion", "thread"
]

# ============================================================
# UTILS
# ============================================================

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha1_short(text: str, size: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:size]

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def strip_tags(text: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text or "")
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_spaces(text)

def normalize_prompt_text(text: str) -> str:
    text = strip_tags(text)
    text = text.replace("\u00a0", " ")
    return normalize_spaces(text)

def normalize_title(text: str) -> str:
    return normalize_spaces(strip_tags(text))

def text_fingerprint(text: str) -> str:
    cleaned = re.sub(r"[^a-z]", "", (text or "").lower())
    cleaned = cleaned[:500]
    return sha1_short(cleaned)

def url_fingerprint(url: str) -> str:
    return sha1_short((url or "").strip().lower())

def robust_get(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[WARN] GET failed: {url} -> {e}")
        return None

def safe_json_load(path: str, list_key: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []

    try:
        if os.path.getsize(path) == 0:
            return []

        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if isinstance(loaded, list):
            items = loaded
        elif isinstance(loaded, dict):
            items = loaded.get(list_key, [])
        else:
            return []

        out = []
        for item in items:
            if isinstance(item, dict):
                out.append(item)
        return out

    except Exception as e:
        print(f"[WARN] Failed loading {path}: {e}")
        return []

def safe_json_save(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)

def parse_date_any(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    value = value.strip()

    candidates = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    for fmt in candidates:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue

    return None

def is_recent_enough(dt: Optional[datetime], max_age_days: int) -> bool:
    if dt is None:
        return True
    delta = datetime.now(timezone.utc) - dt
    return delta.days <= max_age_days

# ============================================================
# PROMPT LOGIC
# ============================================================

def is_good_prompt(text: str) -> bool:
    text = normalize_prompt_text(text)
    if not text:
        return False
    if len(text) < 120:
        return False

    low = text.lower()

    if low.count("?") > 1:
        return False

    if any(term in low for term in PROMPT_BAD_TERMS):
        return False

    if low.startswith(("i've", "i have", "my experience", "we built", "someone said")):
        return False

    return True

def choose_first(row: Dict[str, Any], fields: List[str], default: str = "") -> str:
    for field in fields:
        value = row.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default

def fetch_prompt_source_csv(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    r = robust_get(source["url"])
    if not r:
        return out

    try:
        lines = r.text.splitlines()
        if not lines:
            return out

        reader = csv.DictReader(lines)

        for row in reader:
            if not isinstance(row, dict):
                continue

            title = choose_first(row, source.get("title_fields", []), "Prompt")
            text  = choose_first(row, source.get("text_fields", []), "")

            text  = normalize_prompt_text(text)
            title = normalize_title(title)

            if not is_good_prompt(text):
                continue

            fp = text_fingerprint(text)

            out.append({
                "id":           fp,
                "title":        title or "Prompt",
                "text":         text,
                "category":     source.get("category", "prompt"),
                "source":       source["name"],
                "source_url":   source["url"],
                "published_at": now_utc_iso(),
                # --- campi di classificazione ereditati dalla sorgente ---
                "platform":        source.get("platform",        "unknown"),
                "content_type":    source.get("content_type",    "unknown"),
                "use_case":        source.get("use_case",        "unknown"),
                "language":        source.get("language",        "unknown"),
                "quality_tier":    source.get("quality_tier",    "unknown"),
                "volume_estimate": source.get("volume_estimate", "unknown"),
                "license":         source.get("license",         "unknown"),
            })

    except Exception as e:
        print(f"[WARN] CSV parse failed: {source['url']} -> {e}")

    return out

def fetch_all_prompts() -> List[Dict[str, Any]]:
    all_items = []
    for source in PROMPT_SOURCES:
        print(f"[INFO] PROMPTS fetch -> {source['name']}")
        items = []
        if source["type"] == "csv":
            items = fetch_prompt_source_csv(source)
        print(f"[INFO] PROMPTS source {source['name']}: {len(items)} items")
        all_items.extend(items)
        time.sleep(0.2)

    return all_items

def merge_prompts(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    seen   = set()

    for item in existing + incoming:
        text = normalize_prompt_text(item.get("text", ""))
        if not is_good_prompt(text):
            continue

        fp = text_fingerprint(text)
        if fp in seen:
            continue

        clean = dict(item)
        clean["id"]           = clean.get("id") or fp
        clean["title"]        = normalize_title(clean.get("title", "Prompt")) or "Prompt"
        clean["text"]         = text
        clean["category"]     = normalize_spaces(clean.get("category", "prompt")) or "prompt"
        clean["source"]       = normalize_spaces(clean.get("source",   "unknown")) or "unknown"
        clean["published_at"] = clean.get("published_at") or now_utc_iso()
        # preserva i campi di classificazione se già presenti
        for field in ("platform", "content_type", "use_case", "language",
                      "quality_tier", "volume_estimate", "license"):
            clean.setdefault(field, "unknown")

        merged.append(clean)
        seen.add(fp)

    return merged[:MAX_PROMPTS]

# ============================================================
# NEWS LOGIC
# ============================================================

def extract_rss_text(node: Optional[ET.Element], tag_names: List[str]) -> str:
    if node is None:
        return ""
    for tag in tag_names:
        child = node.find(tag)
        if child is not None and child.text:
            return normalize_spaces(html.unescape(child.text))
    return ""

def parse_rss_feed(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    r = robust_get(source["url"])
    if not r:
        return out

    try:
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[WARN] RSS XML parse failed: {source['url']} -> {e}")
        return out

    channel = root.find("channel")
    items   = []

    if channel is not None:
        items = channel.findall("item")
    else:
        # Atom fallback
        ns    = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall("atom:entry", ns)

    for item in items:
        title       = extract_rss_text(item, ["title"])
        link        = extract_rss_text(item, ["link"])

        if not link:
            atom_link = item.find("{http://www.w3.org/2005/Atom}link")
            if atom_link is not None:
                link = atom_link.attrib.get("href", "").strip()

        description = extract_rss_text(item, ["description", "summary",
                                               "{http://www.w3.org/2005/Atom}summary"])
        pub_date    = extract_rss_text(item, ["pubDate", "published", "updated",
                                               "{http://www.w3.org/2005/Atom}updated"])
        dt = parse_date_any(pub_date)

        if not title or not link:
            continue

        combined = f"{title} {description}".lower()
        if not any(k in combined for k in AI_NEWS_KEYWORDS):
            continue

        if not is_recent_enough(dt, NEWS_MAX_AGE_DAYS):
            continue

        out.append({
            "id":           url_fingerprint(link),
            "title":        normalize_title(title),
            "url":          link,
            "summary":      normalize_spaces(strip_tags(description))[:1200],
            "publisher":    source["publisher"],
            "source":       source["name"],
            "source_url":   source["url"],
            "published_at": dt.isoformat() if dt else None,
            "collected_at": now_utc_iso(),
        })

    return out

def parse_html_listing(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    r   = robust_get(source["url"])
    if not r:
        return out

    page    = r.text
    pattern = source["item_pattern"]

    try:
        matches   = re.finditer(pattern, page, re.I | re.S)
        seen_urls = set()

        for m in matches:
            href       = (m.groupdict().get("href")  or "").strip()
            title_html = (m.groupdict().get("title") or "").strip()

            title = normalize_title(title_html)
            if not href or not title:
                continue

            url = urljoin(source["url"], href)
            if url in seen_urls:
                continue

            seen_urls.add(url)

            low = title.lower()
            if not any(k in low for k in AI_NEWS_KEYWORDS):
                # per publisher puramente AI, non è necessario filtrare duro
                pass

            out.append({
                "id":           url_fingerprint(url),
                "title":        title,
                "url":          url,
                "summary":      "",
                "publisher":    source["publisher"],
                "source":       source["name"],
                "source_url":   source["url"],
                "published_at": None,
                "collected_at": now_utc_iso(),
            })

            if len(out) >= 150:
                break

    except Exception as e:
        print(f"[WARN] HTML list parse failed: {source['url']} -> {e}")

    return out

def fetch_all_news() -> List[Dict[str, Any]]:
    all_items = []

    for source in NEWS_SOURCES:
        print(f"[INFO] NEWS fetch -> {source['name']}")
        items = []

        if source["type"] == "rss":
            items = parse_rss_feed(source)
        elif source["type"] == "html_list":
            items = parse_html_listing(source)

        print(f"[INFO] NEWS source {source['name']}: {len(items)} items")
        all_items.extend(items)
        time.sleep(0.2)

    return all_items

def merge_news(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    seen   = set()

    for item in existing + incoming:
        url   = (item.get("url")   or "").strip()
        title = normalize_title(item.get("title", ""))
        if not url or not title:
            continue

        fp = url_fingerprint(url)
        if fp in seen:
            continue

        clean = dict(item)
        clean["id"]           = clean.get("id") or fp
        clean["title"]        = title
        clean["url"]          = url
        clean["summary"]      = normalize_spaces(clean.get("summary",    ""))[:1200]
        clean["publisher"]    = normalize_spaces(clean.get("publisher",  "unknown")) or "unknown"
        clean["source"]       = normalize_spaces(clean.get("source",     "unknown")) or "unknown"
        clean["collected_at"] = clean.get("collected_at") or now_utc_iso()

        dt = parse_date_any(clean.get("published_at"))
        if not is_recent_enough(dt, NEWS_MAX_AGE_DAYS):
            continue

        clean["published_at"] = dt.isoformat() if dt else None

        merged.append(clean)
        seen.add(fp)

    merged.sort(
        key=lambda x: parse_date_any(x.get("published_at"))
                      or datetime(1970, 1, 1, tzinfo=timezone.utc),
        reverse=True,
    )

    return merged[:MAX_NEWS]

# ============================================================
# MAIN
# ============================================================

def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    existing_prompts = safe_json_load(PROMPTS_FILE, "items")
    existing_news    = safe_json_load(NEWS_FILE,    "items")

    print(f"[INFO] Existing prompts: {len(existing_prompts)}")
    print(f"[INFO] Existing news:    {len(existing_news)}")

    incoming_prompts = fetch_all_prompts()
    merged_prompts   = merge_prompts(existing_prompts, incoming_prompts)

    incoming_news    = fetch_all_news()
    merged_news      = merge_news(existing_news, incoming_news)

    prompt_payload = {
        "generated_at": now_utc_iso(),
        "count":        len(merged_prompts),
        "items":        merged_prompts,
    }

    news_payload = {
        "generated_at":  now_utc_iso(),
        "count":         len(merged_news),
        "max_age_days":  NEWS_MAX_AGE_DAYS,
        "items":         merged_news,
    }

    safe_json_save(PROMPTS_FILE, prompt_payload)
    safe_json_save(NEWS_FILE,    news_payload)

    print(f"[OK] PROMPTS saved -> {PROMPTS_FILE} ({len(merged_prompts)})")
    print(f"[OK] NEWS saved    -> {NEWS_FILE} ({len(merged_news)})")


if __name__ == "__main__":
    main()