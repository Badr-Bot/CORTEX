"""
CORTEX — Agent SCOUT-AI v2 (PULSE Intelligence)

Cycle complet :
  1. Collecte parallèle toutes sources (blogs, médias, newsletters,
     arXiv, GitHub, HuggingFace, Reddit, HN, Twitter)
  2. Déduplication stricte via fichier local + Supabase
  3. Claude Sonnet sélectionne et analyse les 5 meilleures news du jour
  4. Rapport Telegram en 1-2 messages (format approfondi)
  5. Question du matin dans un message séparé, 2 min après
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from utils.logger import get_logger
from agents.sources import titans, media, weak_signals, viral
from agents import summarizer

logger = get_logger("scout_ai")

# ── Traduction jours/mois en français ─────────────────────────────────────────
_DAYS_FR   = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# ── Déduplication locale ──────────────────────────────────────────────────────
_SEEN_URLS_FILE = Path(__file__).parent.parent / "data" / "seen_urls.json"


def _load_seen_urls() -> set:
    try:
        _SEEN_URLS_FILE.parent.mkdir(exist_ok=True)
        if _SEEN_URLS_FILE.exists():
            return set(json.loads(_SEEN_URLS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def _save_seen_urls(urls: set) -> None:
    try:
        url_list = list(urls)[-10_000:]
        _SEEN_URLS_FILE.write_text(json.dumps(url_list), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Impossible de sauvegarder seen_urls: {e}")


async def _is_duplicate_supabase(url: str) -> bool:
    try:
        from database.client import get_supabase_client
        client = get_supabase_client()
        result = client.table("signals").select("id").eq("source_url", url).limit(1).execute()
        return bool(result.data)
    except Exception:
        return False


async def _store_signal(signal: dict) -> bool:
    try:
        from database.client import insert_signal
        await insert_signal(
            sector=signal.get("sector", "ai"),
            title=signal.get("title", "")[:500],
            source_url=signal.get("source_url", ""),
            source_name=signal.get("source_name", ""),
            raw_content=signal.get("raw_content", "")[:2000],
            stars_count=signal.get("stars_count", 0),
            category=signal.get("category", "weak"),
            metadata={"scout_category": signal.get("category", "")},
        )
        return True
    except Exception as e:
        logger.debug(f"Supabase store échoué: {e}")
        return False


def _deduplicate_batch(signals: list[dict], seen_urls: set) -> list[dict]:
    """Déduplication en mémoire par URL et titre (80 chars)."""
    unique, seen_titles = [], set()
    for sig in signals:
        url   = sig.get("source_url", "")
        title = sig.get("title", "").lower()[:80]
        if url in seen_urls or title in seen_titles:
            continue
        unique.append(sig)
        seen_urls.add(url)
        seen_titles.add(title)
    return unique


# ── Formatage date en français ─────────────────────────────────────────────────

def _fr_date() -> str:
    now = datetime.now()
    return f"{_DAYS_FR[now.weekday()]} {now.day} {_MONTHS_FR[now.month - 1]} {now.year}"


# ── Builders de messages Telegram ─────────────────────────────────────────────

def _escape_md(text: str) -> str:
    """Nettoie le texte Claude pour éviter les erreurs de parsing Telegram Markdown."""
    return (
        text.replace("*", "")
            .replace("_", "")
            .replace("`", "")
            .replace("[", "")
            .replace("]", "")
            .strip()
    )


def _build_report_messages(analyzed: list[dict], total_count: int) -> list[str]:
    """
    Construit 1 ou 2 messages Telegram avec le rapport des top 5.
    Format approfondi : 3 sections par news + source cliquable.
    Auto-split entre stories si > 4000 chars.
    """
    THICK = "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    THIN  = "─────────────────────────────"
    NUMS  = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    header = f"{THICK}\n🧠 *INTELLIGENCE ARTIFICIELLE*\n📅 {_fr_date()}\n{THICK}"

    # Construire les blocs de chaque story (texte Claude échappé)
    story_blocks = []
    for i, sig in enumerate(analyzed[:5]):
        num        = NUMS[i]
        title      = _escape_md(sig.get("title", "")).upper()
        ce_qui     = _escape_md(sig.get("ce_qui_se_passe", ""))
        pourquoi   = _escape_md(sig.get("pourquoi_important", ""))
        surveiller = _escape_md(sig.get("ce_qu_il_faut_surveiller", ""))
        src_name   = _escape_md(sig.get("source_name", ""))
        src_url    = sig.get("source_url", "")

        source_line = f"[{src_name}]({src_url})" if src_url else src_name

        block = (
            f"{num} *{title}*\n\n"
            f"📌 *CE QUI SE PASSE*\n{ce_qui}\n\n"
            f"🧩 *POURQUOI C'EST IMPORTANT*\n{pourquoi}\n\n"
            f"⚡ *CE QU'IL FAUT SURVEILLER*\n{surveiller}\n\n"
            f"🔗 Source : {source_line}"
        )
        story_blocks.append(block)

    # Assembler en messages ≤ 4000 chars — découpe propre entre stories
    messages = []
    current  = header

    for block in story_blocks:
        sep = f"\n\n{THIN}\n\n"
        # Tester si l'ajout de ce block dépasse la limite
        if current == header:
            candidate = current + "\n\n" + block
        else:
            candidate = current + sep + block

        if len(candidate) > 4000 and current != header:
            # Fermer le message en cours
            messages.append(current + f"\n\n{THICK}")
            current = block
        else:
            current = candidate

    # Ajouter le dernier message
    if current:
        messages.append(current + f"\n\n{THICK}")

    return messages


def _build_question_message(question: str) -> str:
    """Message séparé pour la question du matin."""
    THICK = "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    return (
        f"{THICK}\n"
        f"☀️ *QUESTION DU MATIN*\n\n"
        f"{question}\n\n"
        f"→ _Réponds ici, ta réponse est stockée dans ton journal._\n"
        f"{THICK}"
    )


# ── Orchestrateur principal ───────────────────────────────────────────────────

async def run_scout_ai(hours: int = 48, send_telegram: bool = True) -> dict:
    """
    Lance le cycle complet SCOUT-AI v2.

    Args:
        hours:          Fenêtre de collecte en heures
        send_telegram:  Si True, envoie rapport + question sur Telegram

    Returns:
        dict avec analyzed, total, stored, report_messages, morning_question
    """
    logger.info("=" * 50)
    logger.info("SCOUT-AI v2 — Démarrage du cycle")
    logger.info("=" * 50)

    seen_urls = _load_seen_urls()

    # ── Étape 1 : Collecte parallèle toutes sources ──────────────────────────
    logger.info("Étape 1/3 — Collecte parallèle des sources...")
    results = await asyncio.gather(
        titans.collect(hours),
        media.collect(hours),
        weak_signals.collect(hours),
        viral.collect(hours),
        return_exceptions=True,
    )

    def _safe(result, name):
        if isinstance(result, Exception):
            logger.error(f"Collecte {name} échouée: {result}")
            return []
        return result

    titans_raw = _safe(results[0], "titans")
    media_raw  = _safe(results[1], "médias")
    weak_raw   = _safe(results[2], "signaux faibles")
    viral_raw  = _safe(results[3], "viral")

    all_raw = titans_raw + media_raw + weak_raw + viral_raw
    logger.info(
        f"Collecte brute: {len(titans_raw)} titans, {len(media_raw)} médias, "
        f"{len(weak_raw)} faibles, {len(viral_raw)} viraux → {len(all_raw)} total"
    )

    # ── Étape 2 : Déduplication + Stockage Supabase ──────────────────────────
    logger.info("Étape 2/3 — Déduplication et stockage...")
    all_deduped = _deduplicate_batch(all_raw, seen_urls.copy())
    total       = len(all_deduped)
    logger.info(f"Après dédup: {total} signaux uniques")

    stored = 0
    for sig in all_deduped:
        if await _store_signal(sig):
            stored += 1

    for sig in all_deduped:
        seen_urls.add(sig.get("source_url", ""))
    _save_seen_urls(seen_urls)
    logger.info(f"Stockés en Supabase: {stored}/{total}")

    # ── Étape 3 : Claude Sonnet — sélection et analyse top 5 ────────────────
    logger.info("Étape 3/3 — Claude Sonnet : sélection et analyse des top 5...")
    analyzed = await summarizer.select_and_analyze(all_deduped)
    logger.info(f"Top {len(analyzed)} analysés avec succès")

    # ── Construction des messages ─────────────────────────────────────────────
    report_messages  = _build_report_messages(analyzed, total)
    morning_question = summarizer.generate_morning_question(analyzed)
    question_message = _build_question_message(morning_question)

    # ── Envoi Telegram ────────────────────────────────────────────────────────
    if send_telegram:
        try:
            from tgbot.bot import send_message

            # Rapport principal (1 ou 2 messages)
            logger.info(f"Envoi rapport: {len(report_messages)} message(s)...")
            for i, msg in enumerate(report_messages, 1):
                await send_message(msg, parse_mode="Markdown")
                logger.info(f"  Rapport {i}/{len(report_messages)} envoyé ({len(msg)} chars)")
                if i < len(report_messages):
                    await asyncio.sleep(1)

            # Question du matin — message séparé, 2 minutes après
            logger.info("Attente 2 minutes avant la question du matin...")
            await asyncio.sleep(120)
            await send_message(question_message, parse_mode="Markdown")
            logger.info("Question du matin envoyée ✅")

            # Créer l'entrée journal (sans renvoyer de message)
            try:
                from tgbot.bot import ask_morning_question
                await ask_morning_question(morning_question, send=False)
                logger.info("Entrée journal créée")
            except Exception as e:
                logger.warning(f"Journal entry échouée: {e}")

        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")

    logger.info("=" * 50)
    logger.info("SCOUT-AI v2 — Cycle terminé")
    logger.info("=" * 50)

    return {
        "analyzed":         analyzed,
        "total":            total,
        "stored":           stored,
        "report_messages":  report_messages,
        "morning_question": morning_question,
    }
