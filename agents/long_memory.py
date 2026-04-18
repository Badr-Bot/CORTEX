"""
CORTEX — Long-Term Memory System (Gemini Pro)
Mémoire longue durée en 3 niveaux :

  Niveau 1 — Compressions hebdomadaires
    Chaque dimanche, Gemini Pro compresse 7 jours d'analyses → ~200 mots par secteur.
    Stocké dans : weekly_summaries (Supabase)

  Niveau 2 — Patterns permanents
    Configurations/corrélations de marché récurrentes détectées via le bilan du dimanche.
    Classés par nb d'occurrences. Stocké dans : agent_patterns (Supabase)

  Niveau 3 — Recherche sémantique
    Chaque jour, les signaux analysés sont vectorisés (text-embedding-004, 768 dims).
    À l'analyse suivante, les 3 journées passées les plus similaires sont injectées.
    Stocké dans : signal_embeddings (Supabase + pgvector)

Tables Supabase requises : exécuter database/migration_long_memory.sql

Fonctions exposées :
  run_weekly_compression(week_of)           — Dimanche après bilan (tous secteurs)
  run_pattern_extraction(bilan_data, week)  — Dimanche après bilan
  embed_and_save(report_date, sector, data) — Quotidien après chaque analyse
  get_all_weekly_summaries(sector, limit)   — Lecture résumés hebdo
  get_all_patterns(sector)                  — Lecture patterns permanents
  semantic_search(query, sector, top_k)     — Recherche sémantique pgvector
  format_long_memory_context(...)           — Injection dans les prompts Claude
"""

import asyncio
import json
import os
import re
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("long_memory")

# Secteurs supportés par le système de mémoire longue
SECTORS = ["ai", "crypto", "market", "deeptech"]

# ── Clients ───────────────────────────────────────────────────────────────────

_gemini_model = None


def _get_gemini():
    """Retourne une instance GenerativeModel Gemini Pro, ou None si indisponible."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        logger.warning("GEMINI_API_KEY absent — long memory Gemini désactivé")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        _gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config={
                "temperature": 0,
                "max_output_tokens": 1024,
            },
        )
        logger.info("Gemini Pro (long_memory) initialisé")
        return _gemini_model
    except Exception as e:
        logger.warning(f"Gemini Pro init échoué: {e}")
        return None


def _get_supabase():
    """Retourne un client Supabase ou None."""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Supabase long_memory non disponible: {e}")
        return None


# ── Embeddings (text-embedding-004, 768 dims) ─────────────────────────────────

async def _embed(text: str) -> list[float] | None:
    """
    Génère un vecteur d'embedding (768 dims) via Gemini text-embedding-004.
    Gratuit, robuste, compatible pgvector.
    """
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)

        def _do_embed():
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text[:2000],
                task_type="RETRIEVAL_DOCUMENT",
            )
            return result["embedding"]

        embedding = await asyncio.to_thread(_do_embed)
        return embedding
    except Exception as e:
        logger.warning(f"Embedding text-embedding-004 échoué: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# NIVEAU 1 — COMPRESSIONS HEBDOMADAIRES
# ══════════════════════════════════════════════════════════════════════════════

_COMPRESS_PROMPT = """Tu es un système de mémoire compressée pour CORTEX, briefing d'investissement quotidien.

MISSION : Compresse 7 jours d'analyses du secteur {sector_upper} en un résumé ULTRA-DENSE de 180-220 mots.
Ce résumé sera injecté dans les prompts futurs pour donner une mémoire longue durée à CORTEX.

INCLURE OBLIGATOIREMENT :
1. Les 3-4 signaux les plus importants de la semaine (fait + impact)
2. La direction/tendance dominante observée
3. Les surprises par rapport aux attentes
4. Les acteurs/entreprises/tokens clés mentionnés
5. Ce qui ne s'est PAS réalisé (invalidations)

FORMAT : texte brut ultra-dense, pas de markdown, pas de titres, pas de listes à puces.
Commence par "Semaine {week_of} [{sector_upper}] :"

Analyses de la semaine à compresser :
{analyses_text}"""


async def compress_week(week_of: str, sector: str, analyses: list[dict]) -> str | None:
    """
    Compresse 7 jours d'analyses en ~200 mots via Gemini Pro.

    Args:
        week_of  : date ISO "2026-04-14" (lundi de la semaine)
        sector   : "ai" | "crypto" | "market" | "deeptech"
        analyses : liste de {'report_date': str, 'data': dict}
    Returns:
        Texte compressé (~200 mots) ou None si échec
    """
    if not analyses:
        return None

    client = _get_gemini()
    if not client:
        return None

    # Formater les signaux des 7 jours
    lines = []
    for entry in sorted(analyses, key=lambda x: x.get("report_date", "")):
        date = entry.get("report_date", "?")
        data = entry.get("data", {})
        signals = data.get("signals", [])
        for s in signals[:2]:
            title = s.get("title", "")[:80]
            fait  = s.get("fait", "")[:200]
            if title:
                lines.append(f"[{date}] {title}. {fait}")
        # Direction/régime si disponible
        direction = data.get("direction") or data.get("regime", "")
        if direction:
            lines.append(f"[{date}] Tendance: {direction}")

    if not lines:
        return None

    prompt = _COMPRESS_PROMPT.format(
        sector_upper=sector.upper(),
        week_of=week_of,
        analyses_text="\n".join(lines),
    )

    try:
        def _do_call():
            resp = client.generate_content(prompt)
            return resp.text.strip()

        summary = await asyncio.to_thread(_do_call)
        logger.info(f"compress_week [{sector}] {week_of}: {len(summary)} chars")
        return summary
    except Exception as e:
        logger.warning(f"compress_week [{sector}] échoué: {e}")
        return None


async def save_weekly_summary(week_of: str, sector: str, summary: str) -> bool:
    """Upsert une compression hebdomadaire dans weekly_summaries."""
    client = _get_supabase()
    if not client:
        return False

    def _do_save():
        try:
            client.table("weekly_summaries").delete() \
                .eq("week_of", week_of).eq("sector", sector).execute()
        except Exception:
            pass
        client.table("weekly_summaries").insert({
            "week_of": week_of,
            "sector":  sector,
            "summary": summary,
        }).execute()

    try:
        await asyncio.to_thread(_do_save)
        logger.info(f"weekly_summaries: [{sector}] {week_of} ✅")
        return True
    except Exception as e:
        logger.warning(f"save_weekly_summary [{sector}] échoué: {e}")
        return False


async def get_all_weekly_summaries(sector: str, limit: int = 12) -> list[dict]:
    """
    Récupère les N dernières compressions hebdomadaires pour un secteur.
    Returns: liste de {'week_of': str, 'summary': str}, du plus récent au plus ancien
    """
    client = _get_supabase()
    if not client:
        return []

    def _do_fetch():
        return (
            client.table("weekly_summaries")
            .select("week_of, summary")
            .eq("sector", sector)
            .order("week_of", desc=True)
            .limit(limit)
            .execute()
        )

    try:
        result = await asyncio.to_thread(_do_fetch)
        return result.data or []
    except Exception as e:
        logger.warning(f"get_all_weekly_summaries [{sector}] échoué: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# NIVEAU 2 — PATTERNS PERMANENTS
# ══════════════════════════════════════════════════════════════════════════════

_PATTERN_PROMPT = """Tu es un système d'extraction de patterns de MARCHÉ pour CORTEX.

MISSION : À partir du bilan de semaine ci-dessous, extrait les patterns de marché
ACTIONNABLES qui méritent d'être mémorisés à long terme.

Types de patterns recherchés :
- Corrélations confirmées ou infirmées cette semaine
- Signaux qui se sont réalisés ou pas (avec contexte)
- Configurations de marché récurrentes à surveiller
- Erreurs d'analyse systémiques à ne pas répéter
- Secteurs/actifs qui sur/sous-performent dans ce contexte macro

NE PAS inclure : comportements de Badr, patterns humains, coaching

Réponds UNIQUEMENT avec un JSON valide (sans markdown) :
{
  "patterns": [
    {"sector": "crypto",  "pattern": "description courte et actionnable — max 120 chars"},
    {"sector": "ai",      "pattern": "..."},
    {"sector": "market",  "pattern": "..."}
  ]
}

Secteurs valides : "ai", "crypto", "market", "deeptech", "global"
Maximum 6 patterns au total. En français. Texte brut.

Bilan de la semaine :
{bilan_text}"""


async def extract_patterns_from_bilan(bilan_data: dict, week_of: str) -> list[dict]:
    """
    Extrait les patterns de marché depuis le bilan hebdomadaire du dimanche.

    Args:
        bilan_data : dict retourné par _call_claude_bilan() de weekly_bilan.py
        week_of    : date ISO "2026-04-14"
    Returns:
        Liste de {'sector': str, 'pattern': str}
    """
    client = _get_gemini()
    if not client:
        return []

    # Assembler le texte du bilan pour Gemini
    lines = []
    for ev in bilan_data.get("evaluations", []):
        learning = ev.get("learning", "").strip()
        verdict  = ev.get("verdict", "")
        question = ev.get("question", "")[:80]
        if learning:
            lines.append(f"[{verdict}] {question} → {learning}")
    for p in bilan_data.get("patterns", []):
        if p:
            lines.append(f"Pattern détecté: {p}")
    for l in bilan_data.get("learnings_cles", []):
        if l:
            lines.append(f"Learning clé: {l}")
    manque = bilan_data.get("signal_manque", "")
    if manque:
        lines.append(f"Signal manqué: {manque}")

    if not lines:
        return []

    prompt = _PATTERN_PROMPT.format(bilan_text="\n".join(lines))

    try:
        def _do_call():
            resp = client.generate_content(prompt)
            return resp.text.strip()

        raw = await asyncio.to_thread(_do_call)

        # Nettoyer markdown si présent
        if "```" in raw:
            m = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
            if m:
                raw = m.group(1).strip()

        data = json.loads(raw)
        patterns = data.get("patterns", [])
        logger.info(f"extract_patterns: {len(patterns)} patterns pour semaine {week_of}")
        return patterns
    except Exception as e:
        logger.warning(f"extract_patterns_from_bilan échoué: {e}")
        return []


async def save_pattern(sector: str, pattern: str, week_of: str) -> bool:
    """
    Sauvegarde ou incrémente un pattern dans agent_patterns.
    Si le pattern (texte exact) existe déjà → incrémente occurrences + met à jour last_confirmed.
    Sinon → crée une nouvelle ligne.
    """
    client = _get_supabase()
    if not client:
        return False

    def _do_save():
        existing = (
            client.table("agent_patterns")
            .select("id, occurrences")
            .eq("sector", sector)
            .eq("pattern", pattern)
            .limit(1)
            .execute()
        )
        rows = existing.data or []
        if rows:
            row_id = rows[0]["id"]
            occ    = rows[0]["occurrences"] + 1
            client.table("agent_patterns").update({
                "occurrences":    occ,
                "last_confirmed": week_of,
            }).eq("id", row_id).execute()
        else:
            client.table("agent_patterns").insert({
                "sector":         sector,
                "pattern":        pattern,
                "occurrences":    1,
                "first_seen":     week_of,
                "last_confirmed": week_of,
            }).execute()

    try:
        await asyncio.to_thread(_do_save)
        return True
    except Exception as e:
        logger.warning(f"save_pattern [{sector}] échoué: {e}")
        return False


async def get_all_patterns(sector: str, min_occurrences: int = 1) -> list[dict]:
    """
    Récupère tous les patterns confirmés pour un secteur, triés par occurrences (desc).
    Returns: liste de {'pattern': str, 'occurrences': int, 'last_confirmed': str}
    """
    client = _get_supabase()
    if not client:
        return []

    def _do_fetch():
        return (
            client.table("agent_patterns")
            .select("pattern, occurrences, last_confirmed")
            .eq("sector", sector)
            .gte("occurrences", min_occurrences)
            .order("occurrences", desc=True)
            .limit(20)
            .execute()
        )

    try:
        result = await asyncio.to_thread(_do_fetch)
        return result.data or []
    except Exception as e:
        logger.warning(f"get_all_patterns [{sector}] échoué: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# NIVEAU 3 — EMBEDDINGS + RECHERCHE SÉMANTIQUE
# ══════════════════════════════════════════════════════════════════════════════

async def embed_and_save(report_date: str, sector: str, data: dict) -> bool:
    """
    Vectorise les signaux du jour et les sauvegarde dans signal_embeddings.
    Permet la recherche sémantique des journées passées similaires.

    Args:
        report_date : "2026-04-18"
        sector      : "ai" | "crypto" | "market" | "deeptech"
        data        : dict retourné par analyze_*()
    Returns:
        True si succès, False sinon
    """
    client_sb = _get_supabase()
    if not client_sb:
        return False

    signals = data.get("signals", [])
    if not signals:
        return False

    # Construire le texte à vectoriser (titres + faits tronqués)
    parts = []
    for s in signals[:3]:
        title = s.get("title", "")
        fait  = s.get("fait", "")[:250]
        if title:
            parts.append(f"{title}. {fait}")
    # Ajouter le contexte macro si disponible
    for key in ("direction", "regime", "phase"):
        val = data.get(key, "")
        if val:
            parts.append(f"Tendance: {val}")
            break

    content = " | ".join(parts)[:2000]
    if not content.strip():
        return False

    # Générer l'embedding
    embedding = await _embed(content)
    if not embedding:
        return False

    metadata = {
        "signals_count":   len(signals),
        "direction":       data.get("direction", ""),
        "regime":          data.get("regime", ""),
        "recession_score": data.get("recession_score"),
    }

    def _do_save():
        try:
            client_sb.table("signal_embeddings").delete() \
                .eq("report_date", report_date).eq("sector", sector).execute()
        except Exception:
            pass
        client_sb.table("signal_embeddings").insert({
            "report_date": report_date,
            "sector":      sector,
            "content":     content,
            "embedding":   embedding,
            "metadata":    metadata,
        }).execute()

    try:
        await asyncio.to_thread(_do_save)
        logger.info(f"signal_embeddings: [{sector}] {report_date} vectorisé ✅")
        return True
    except Exception as e:
        logger.warning(f"embed_and_save [{sector}] échoué: {e}")
        return False


async def semantic_search(query_text: str, sector: str, top_k: int = 3) -> list[dict]:
    """
    Recherche sémantique dans signal_embeddings via pgvector RPC.
    Trouve les journées passées les plus similaires au contexte courant.

    Args:
        query_text : texte décrivant le contexte actuel (~500 chars)
        sector     : "ai" | "crypto" | "market" | "deeptech"
        top_k      : nombre de résultats
    Returns:
        Liste de {'report_date': str, 'content': str, 'similarity': float}
    """
    client = _get_supabase()
    if not client:
        return []

    query_embedding = await _embed(query_text[:1000])
    if not query_embedding:
        return []

    def _do_search():
        return client.rpc("search_similar_signals", {
            "query_embedding": query_embedding,
            "match_sector":    sector,
            "match_count":     top_k,
        }).execute()

    try:
        result = await asyncio.to_thread(_do_search)
        rows = result.data or []
        return [
            {
                "report_date": r.get("report_date", ""),
                "content":     r.get("content", ""),
                "similarity":  round(float(r.get("similarity", 0)), 3),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"semantic_search [{sector}] échoué: {e}")
        return []


# ── Formatage du contexte long mémoire ───────────────────────────────────────

def format_long_memory_context(
    summaries: list[dict],
    patterns:  list[dict],
    similar:   list[dict],
) -> str:
    """
    Formate les 3 niveaux de mémoire en bloc injectable dans les prompts Claude.
    Compact mais dense — ~500-600 chars max pour ne pas polluer le contexte.

    Returns:
        Texte multi-lignes à préfixer au user_prompt, ou '' si tout est vide
    """
    blocks = []

    # Niveau 1 : Compressions hebdomadaires (max 4 semaines)
    if summaries:
        lines = ["── Mémoire long terme (compressions hebdo) ──"]
        for s in summaries[:4]:
            week = s.get("week_of", "?")
            text = s.get("summary", "").strip()
            if text:
                short = text[:220] + ("..." if len(text) > 220 else "")
                lines.append(f"  {short}")
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    # Niveau 2 : Patterns permanents (max 6, triés par occurrences)
    if patterns:
        lines = ["── Patterns de marché détectés ──"]
        for p in patterns[:6]:
            pattern = p.get("pattern", "").strip()
            occ     = p.get("occurrences", 1)
            if pattern:
                badge = f"×{occ}" if occ > 1 else "×1"
                lines.append(f"  [{badge}] {pattern}")
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    # Niveau 3 : Contextes similaires passés (max 2 pour rester compact)
    if similar:
        lines = ["── Journées similaires passées (recherche sémantique) ──"]
        for s in similar[:2]:
            date    = s.get("report_date", "?")
            content = s.get("content", "")[:160].strip()
            sim     = s.get("similarity", 0)
            if content:
                lines.append(f"  [{date} | {sim:.2f}] {content}...")
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION — Dimanche après bilan
# ══════════════════════════════════════════════════════════════════════════════

async def run_weekly_compression(week_of: str) -> None:
    """
    Compresse tous les secteurs pour la semaine écoulée.
    Appelé le dimanche après run_weekly_bilan().

    Args:
        week_of : date ISO du lundi de la semaine "2026-04-14"
    """
    from agents.memory import get_sector_history

    logger.info(f"run_weekly_compression — semaine {week_of}")
    saved = 0

    for sector in SECTORS:
        try:
            analyses = await get_sector_history(sector, days=7)
            if not analyses:
                logger.debug(f"  [{sector}] aucune analyse — skip")
                continue

            summary = await compress_week(week_of, sector, analyses)
            if not summary:
                logger.warning(f"  [{sector}] compression échouée")
                continue

            ok = await save_weekly_summary(week_of, sector, summary)
            if ok:
                saved += 1

            # Rate limit Gemini Pro (gratuit = 2 RPM)
            await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"  [{sector}] erreur: {e}")

    logger.info(f"run_weekly_compression terminé — {saved}/{len(SECTORS)} secteurs")


async def run_pattern_extraction(bilan_data: dict, week_of: str) -> None:
    """
    Extrait et sauvegarde les patterns de marché depuis le bilan du dimanche.

    Args:
        bilan_data : dict retourné par _call_claude_bilan()
        week_of    : date ISO "2026-04-14"
    """
    logger.info(f"run_pattern_extraction — semaine {week_of}")

    patterns = await extract_patterns_from_bilan(bilan_data, week_of)
    if not patterns:
        logger.info("  Aucun pattern extrait")
        return

    saved = 0
    for item in patterns:
        sector  = item.get("sector", "global")
        pattern = item.get("pattern", "").strip()
        if pattern and sector in (SECTORS + ["global"]):
            ok = await save_pattern(sector, pattern, week_of)
            if ok:
                saved += 1

    logger.info(f"  {saved}/{len(patterns)} patterns sauvegardés ✅")
