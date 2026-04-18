"""
CORTEX — Summarizer v3 (Groq pre-filter + Claude Sonnet deep analysis)

Architecture 80/20 :
  1. Groq (Llama 3.3 70B, gratuit) pré-filtre les signaux bruts → top 15 par secteur
  2. Claude Sonnet analyse uniquement ces 15 signaux → JSON structuré complet

Économies : ~70% de tokens Sonnet en moins sur les inputs.
Prompt caching toujours actif sur les system prompts.

Fonctions :
  analyze_ai(signals)          → 3 signaux IA + watchlist
  analyze_crypto(data)         → dashboard + score + 3 signaux crypto
  analyze_market(data)         → dashboard + score récession + 3 signaux
  analyze_deeptech(signals)    → 2 signaux deeptech avec crédibilité
  generate_nexus(all_data)     → connexion cross-secteurs + question
"""

import asyncio
import os
import json
import re
from utils.logger import get_logger

logger = get_logger("scout_ai.summarizer")

# ── Groq pre-filter ───────────────────────────────────────────────────────────

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
        return _groq_client
    except Exception as e:
        logger.warning(f"Groq client init échoué: {e}")
        return None


def _prefilter_with_groq(signals: list[dict], sector: str, max_count: int = 15) -> list[dict]:
    """
    Pré-filtre les signaux bruts avec Groq (Llama 3.3 70B, gratuit).
    Réduit 50-120 signaux → top 15 avant envoi à Claude Sonnet.
    Fallback : retourne les max_count premiers si Groq indisponible.
    """
    if len(signals) <= max_count:
        return signals

    client = _get_groq_client()
    if not client:
        logger.debug("Groq indisponible — fallback sur les premiers signaux")
        return signals[:max_count]

    # Format compact : juste l'index, la source et le titre
    lines = [
        f"{i}: [{s.get('source_name', '?')}] {s.get('title', '')[:100]}"
        for i, s in enumerate(signals[:150])
    ]

    prompt = (
        f"You are a signal relevance filter for a {sector} intelligence briefing.\n\n"
        f"From the {len(lines)} signals below, select the {max_count} most important "
        f"based on: novelty, real impact, credibility, topic diversity.\n\n"
        f"Signals:\n" + "\n".join(lines) +
        f"\n\nReturn ONLY a JSON array of {max_count} selected indices. "
        f"Example: [0, 3, 7, 12, 25]. No explanation, no markdown."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        # Extraire le tableau JSON
        match = re.search(r"\[[\d,\s]+\]", raw)
        if not match:
            raise ValueError(f"Pas de tableau JSON dans la réponse: {raw[:100]}")

        indices = json.loads(match.group())
        selected = [signals[i] for i in indices if isinstance(i, int) and i < len(signals)]

        if len(selected) < 3:
            raise ValueError(f"Trop peu de signaux sélectionnés: {len(selected)}")

        logger.info(f"Groq pré-filtre [{sector}]: {len(signals)} → {len(selected)} signaux")
        return selected

    except Exception as e:
        logger.warning(f"Groq pré-filtre échoué [{sector}]: {e} — fallback")
        return signals[:max_count]

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not api_key.startswith("sk-ant"):
        logger.warning("ANTHROPIC_API_KEY absente ou invalide")
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
        return _client
    except Exception as e:
        logger.warning(f"Anthropic client init échoué: {e}")
        return None


def _call_claude(
    prompt: str,
    max_tokens: int = 4000,
    system_prompt: str = None,
    model: str = "claude-sonnet-4-6",
) -> str | None:
    """
    Appel Claude avec prompt caching optionnel.
    model : "claude-sonnet-4-6" (défaut) ou "claude-haiku-4-5-20251001" (4x moins cher)

    Si system_prompt fourni, il est envoyé avec cache_control ephemeral
    → Anthropic le met en cache côté serveur (TTL 5 min).
    Économies typiques : 80% sur les tokens input pour les appels répétés.
    """
    client = _get_client()
    if not client:
        return None
    try:
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )

        if system_prompt:
            # Cache_control sur le system prompt (parties stables : schémas + règles)
            kwargs["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]

        try:
            response = client.messages.create(**kwargs)
        except Exception as sdk_err:
            # Fallback si SDK trop ancien pour cache_control
            if system_prompt and ("cache_control" in str(sdk_err) or "unknown" in str(sdk_err).lower()):
                logger.warning("cache_control non supporté par ce SDK — fallback sans cache")
                kwargs["system"] = system_prompt
                response = client.messages.create(**kwargs)
            else:
                raise

        # Log usage si disponible (pour suivre les économies de cache)
        usage = getattr(response, "usage", None)
        if usage:
            cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
            cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
            if cache_read or cache_write:
                logger.debug(
                    f"Cache tokens — read: {cache_read}, write: {cache_write}, "
                    f"input: {usage.input_tokens}"
                )

        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Claude API call échoué: {e}")
        return None


def _parse_json(raw: str) -> dict | list | None:
    """Parse JSON depuis la réponse Claude — nettoyage robuste."""
    if not raw:
        return None
    text = raw.strip()

    # Nettoyer les balises ```json ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if match:
            text = match.group(1).strip()

    # Tentative 1 : parsing direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentative 2 : extraire le premier objet/array JSON valide
    try:
        start = next((i for i, c in enumerate(text) if c in "{["), None)
        if start is None:
            return None
        bracket = text[start]
        close   = "}" if bracket == "{" else "]"
        depth, in_str, escape = 0, False, False
        for i, c in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if c == "\\" and in_str:
                escape = True
                continue
            if c == '"' and not escape:
                in_str = not in_str
                continue
            if not in_str:
                if c == bracket or c == ("{" if bracket == "{" else "["):
                    depth += 1
                elif c == close:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            break
    except Exception:
        pass

    logger.error(f"JSON parse impossible: {text[:200]}")
    return None


def _prep_signals(signals: list[dict], max_count: int = 80) -> str:
    """Formate les signaux bruts pour le contexte Claude (compact)."""
    lines = []
    for i, s in enumerate(signals[:max_count], 1):
        title   = s.get("title", "")[:120]
        src     = s.get("source_name", "")
        url     = s.get("source_url", "")
        content = s.get("raw_content", "")[:200]
        lines.append(f"{i}. [{src}] {title}\n   {url}\n   {content}")
    return "\n\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_AI — Signal IA
# ══════════════════════════════════════════════════════════════════════════════

# Partie stable mise en cache (schéma JSON + règles = ~600 tokens)
_SYSTEM_AI = """Tu es CORTEX, système de veille IA pour Badr — investisseur et entrepreneur tech.

MISSION : À partir des signaux fournis, sélectionne EXACTEMENT 3 signaux IA importants selon :
1. Impact réel sur l'industrie IA (pas du clickbait)
2. Nouveauté absolue (pas déjà vu cette semaine, cf. historique)
3. Utilité directe pour un investisseur/entrepreneur IA
4. Diversité : évite 3 signaux sur le même sous-thème

Pour chaque signal sélectionné, fournis une analyse APPROFONDIE et DÉTAILLÉE — c'est pour un dashboard web, pas Telegram. Développe chaque champ au maximum de sa limite.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "signals": [
    {
      "conviction": 5,
      "title": "TITRE EN MAJUSCULES — CONCIS, PERCUTANT, FACTUEL (max 80 chars)",
      "fait": "Explication factuelle COMPLÈTE et APPROFONDIE. Qui, quoi, pourquoi maintenant, d'où ça vient, chiffres précis, contexte historique si pertinent, implications techniques. Minimum 6-8 lignes denses. Texte brut uniquement.",
      "implication_2": "Si c'est vrai, alors... — conséquences directes sur l'industrie, les marchés, les entreprises. Développe. 3-4 phrases.",
      "implication_3": "Qui gagne concrètement : [entreprise/secteur X avec raison]. Qui perd : [Y avec raison]. Où est l'asymétrie exacte. 3-4 phrases.",
      "these_opposee": "Le meilleur argument contre cette lecture, avec des faits. Pourquoi l'analyse pourrait être fausse. 2-3 lignes.",
      "action": "Action concrète et SPÉCIFIQUE que Badr peut prendre maintenant. Pas vague — quel ticker, quelle étape, quel timing.",
      "sizing": "Fort",
      "invalide_si": "Seuil ou événement précis et mesurable qui invaliderait cette analyse.",
      "source_name": "Nom exact de la source",
      "source_url": "URL exacte"
    }
  ],
  "watchlist": [
    "Signal early pas encore mûr — [source] — pourquoi surveiller et quand agir",
    "Autre signal — [source] — signal à confirmer d'ici [délai]"
  ],
  "questions": [
    "Question DIRECTE qui force Badr à prendre position sur le signal IA le plus fort du jour. Format : 'Si [fait], tu [action A] ou [action B] ?' ou 'Est-ce que [évènement] change ta thèse sur [sujet] ?'. 1 phrase max.",
    "Deuxième question sur un autre angle IA — technique, business ou investissement. 1 phrase max."
  ]
}

Règles absolues :
- TOUJOURS 3 signaux dans le tableau signals — ni plus, ni moins
- conviction : entier de 1 (faible) à 5 (exceptionnel)
- sizing : exactement "Fort", "Moyen" ou "Faible"
- Tout le texte en FRANÇAIS
- Texte brut uniquement — zéro markdown dans les valeurs de texte
- watchlist : 2-3 items max
- questions : EXACTEMENT 2 questions en français, directes, basées sur les signaux du jour
- LIMITES DE LONGUEUR (en caractères) :
  fait          : 500-800 chars (minimum 500 — analyse complète)
  implication_2 : 200-300 chars
  implication_3 : 200-300 chars
  these_opposee : 150-250 chars
  action        : 150-200 chars
  invalide_si   : 100-150 chars
  watchlist item: max 120 chars"""


async def analyze_ai(signals: list[dict]) -> dict:
    """
    Sélectionne les 3 meilleurs signaux IA et génère l'analyse complète.
    Pipeline : Groq (→12) → Board débat (→4) → Claude Sonnet deep analysis.
    """
    if not signals:
        return _fallback_ai([])

    # Étape 1 : Groq pré-filtre → 12
    signals = _prefilter_with_groq(signals, sector="AI/tech", max_count=12)
    # Étape 2 : Board débat → 4 signaux par consensus
    from agents.board import run_debate
    signals = await run_debate(signals, sector="Intelligence Artificielle")

    from agents.memory import get_sector_history, format_ai_history, save_analysis
    from agents.long_memory import (
        get_all_weekly_summaries, get_all_patterns, semantic_search,
        format_long_memory_context, embed_and_save,
    )
    from agents.memory import get_agent_learnings, format_learnings_context

    context = _prep_signals(signals, 15)

    # Charger toute la mémoire en parallèle
    history, summaries, patterns, learnings = await asyncio.gather(
        get_sector_history("ai", days=7),
        get_all_weekly_summaries("ai", limit=8),
        get_all_patterns("ai"),
        get_agent_learnings("ai", limit=5),
    )
    similar = await semantic_search(context[:600], "ai", top_k=3)

    history_ctx  = format_ai_history(history)
    long_ctx     = format_long_memory_context(summaries, patterns, similar)
    learnings_ctx = format_learnings_context(learnings, "IA")

    # Partie dynamique (signaux + mémoire — non mise en cache)
    user_prompt = ""
    if long_ctx:
        user_prompt += f"{long_ctx}\n\n"
    if learnings_ctx:
        user_prompt += f"{learnings_ctx}\n\n"
    if history_ctx:
        user_prompt += f"{history_ctx}\n\n"
    user_prompt += f"Voici {len(signals)} signaux IA collectés :\n\n{context}"

    raw = _call_claude(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_AI)
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_ai: fallback activé")
        return _fallback_ai(signals[:3])

    logger.info(f"analyze_ai: {len(result.get('signals', []))} signaux analysés")
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    await asyncio.gather(
        save_analysis("ai", result),
        embed_and_save(today, "ai", result),
    )
    return result


def _fallback_ai(signals: list[dict]) -> dict:
    fallback_signals = []
    for s in signals[:3]:
        fallback_signals.append({
            "conviction":    3,
            "title":         s.get("title", "SIGNAL IA")[:70].upper(),
            "fait":          s.get("raw_content", s.get("title", ""))[:300],
            "implication_2": "Analyse indisponible — Claude non connecté.",
            "implication_3": "Vérification manuelle recommandée.",
            "these_opposee": "N/A",
            "action":        "Lire la source directement.",
            "sizing":        "Faible",
            "invalide_si":   "N/A",
            "source_name":   s.get("source_name", ""),
            "source_url":    s.get("source_url", ""),
        })
    return {"signals": fallback_signals, "watchlist": []}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_CRYPTO — Dashboard + Score + Signaux
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_CRYPTO = """Tu es CORTEX, analyste crypto senior pour Badr — investisseur tech avec objectif de longueur d'avance sur le marché.

MISSION :
1. Analyse le cycle (Accumulation / Markup / Distribution / Markdown) avec données on-chain
2. Donne une RECOMMANDATION CLAIRE : acheter, tenir, ou vendre BTC + alts — avec timing précis
3. Identifie 3 altcoins/projets web3 TRENDING ou ÉMERGENTS à surveiller maintenant
4. Sélectionne EXACTEMENT 3 signaux news crypto/web3 à fort impact
5. Score chaque facteur de direction
6. Pose 2 questions pour forcer une décision

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "phase": "Accumulation",
  "recommandation": {
    "verdict": "ACCUMULER",
    "alts": "ATTENDRE",
    "horizon": "2-4 semaines",
    "raisonnement": "Explication factuelle avec les données concrètes qui justifient cette lecture. Fear&Greed, on-chain, niveaux clés. 200-250 chars."
  },
  "trending_alts": [
    {
      "ticker": "SOL",
      "nom": "Solana",
      "theme": "Memecoins + DePIN écosystème",
      "signal": "Volume DEX +67% en 7j, TVL $8.2B en hausse",
      "verdict": "SURVEILLER",
      "timing": "Entrée si BTC confirme au-dessus de $85k"
    },
    {
      "ticker": "SUI",
      "nom": "Sui Network",
      "theme": "L1 gaming + NFT",
      "signal": "Partenariat Sony Music annoncé",
      "verdict": "ACHETER",
      "timing": "Zone $3.2-3.4 — SL sous $2.8"
    },
    {
      "ticker": "HYPE",
      "nom": "Hyperliquid",
      "theme": "DEX perps decentralisé",
      "signal": "Volume record $18B/24h, dépasse Binance Futures",
      "verdict": "SURVEILLER",
      "timing": "Attendre retrace sur zone $20-22"
    }
  ],
  "volume_vs_30d": "description humaine complète du volume vs moyenne 30j avec contexte",
  "score": {
    "onchain":   {"value": 1,  "note": "justification précise avec données concrètes — pas de N/A"},
    "cycle":     {"value": 1,  "note": "justification précise avec données concrètes — pas de N/A"},
    "macro":     {"value": 0,  "note": "justification précise avec données concrètes — pas de N/A"},
    "sentiment": {"value": -1, "note": "justification précise avec données concrètes — pas de N/A"},
    "momentum":  {"value": 0,  "note": "justification précise avec données concrètes — pas de N/A"}
  },
  "direction": "NEUTRE-BULLISH",
  "magnitude": "faible",
  "bear_case": "Ce qui invaliderait cette lecture — développé, avec seuils précis et probabilité estimée. 3-4 lignes.",
  "signals": [
    {
      "conviction": 4,
      "title": "TITRE SIGNAL EN MAJUSCULES (max 80 chars)",
      "fait": "Factuel, complet et APPROFONDI. Minimum 6 lignes. Texte brut.",
      "implication_2": "Impact direct sur BTC/alts/DeFi. 3-4 phrases.",
      "implication_3": "Qui gagne / qui perd. Impact sur l'écosystème. 3-4 phrases.",
      "these_opposee": "Meilleur argument contre cette lecture. 2-3 lignes.",
      "action": "Action concrète et spécifique pour Badr — ticker, timing, condition d'entrée.",
      "sizing": "Moyen",
      "invalide_si": "Condition d'invalidation précise et mesurable.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ],
  "questions": [
    "Question directe sur le signal crypto le plus fort — force un choix. Ex: 'BTC est à $75k avec Fear&Greed à 23, tu achètes maintenant ou tu attends $65k ?' 1 phrase.",
    "Question sur un altcoin ou projet web3 trending — évalue si Badr a compris la thèse. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS exactement 3 signaux dans signals — sélectionne les 3 meilleurs news disponibles
- TOUJOURS exactement 3 trending_alts — si peu de data, choisis les plus pertinents selon le contexte macro
- recommandation.verdict : parmi ACHETER / ACCUMULER / TENIR / ALLÉGER / VENDRE
- recommandation.alts : parmi ACHETER / ACCUMULER / TENIR / ALLÉGER / VENDRE / ATTENDRE
- score values : entiers de -2 à +2 uniquement — JAMAIS de N/A dans les notes
- direction : parmi BULLISH / NEUTRE-BULLISH / NEUTRE / NEUTRE-BEARISH / BEARISH
- magnitude : parmi "forte" / "modérée" / "faible"
- sizing : "Fort", "Moyen" ou "Faible"
- trending_alts.verdict : parmi ACHETER / ACCUMULER / SURVEILLER / EVITER
- Tout en FRANÇAIS — texte brut, zéro markdown
- LIMITES : fait=500-800 chars, implication_2=200-300, implication_3=200-300, these_opposee=150-250, action=150-200, invalide_si=100-150, recommandation.raisonnement=200-250 chars"""


async def analyze_crypto(data: dict) -> dict:
    """
    Analyse le marché crypto : phase du cycle, score de direction, signaux.
    Groq pré-filtre les signaux bruts → top 12 avant envoi à Claude Sonnet.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    # Étape 1 : Groq pré-filtre → 12
    signals   = _prefilter_with_groq(signals, sector="crypto/blockchain", max_count=12)
    # Étape 2 : Board débat → 4
    from agents.board import run_debate
    signals   = await run_debate(signals, sector="Crypto & Web3")
    context   = _prep_signals(signals, 12)

    from agents.memory import get_sector_history, format_crypto_history, save_analysis as _save
    from agents.long_memory import (
        get_all_weekly_summaries, get_all_patterns, semantic_search,
        format_long_memory_context, embed_and_save,
    )
    from agents.memory import get_agent_learnings, format_learnings_context

    # Charger toute la mémoire en parallèle
    history, summaries, patterns, learnings = await asyncio.gather(
        get_sector_history("crypto", days=7),
        get_all_weekly_summaries("crypto", limit=8),
        get_all_patterns("crypto"),
        get_agent_learnings("crypto", limit=5),
    )
    similar = await semantic_search(context[:600], "crypto", top_k=3)

    history_ctx   = format_crypto_history(history)
    long_ctx      = format_long_memory_context(summaries, patterns, similar)
    learnings_ctx = format_learnings_context(learnings, "Crypto")

    dash_str = (
        f"BTC Prix     : ${dashboard.get('btc_price', 'N/A'):,} "
        f"({dashboard.get('btc_change_24h', '?')}% 24h)\n"
        f"BTC Dom.     : {dashboard.get('btc_dominance', 'N/A')}%\n"
        f"Fear & Greed : {dashboard.get('fear_greed_score', 'N/A')} — "
        f"{dashboard.get('fear_greed_label', 'N/A')}\n"
        f"Funding BTC  : {dashboard.get('funding_description', 'N/A')}\n"
        f"MktCap chg   : {dashboard.get('market_cap_change', 'N/A')}% 24h\n"
        f"Vol. 24h     : ${dashboard.get('total_volume_24h', 0):,.0f}"
    )

    user_prompt = ""
    if long_ctx:
        user_prompt += f"{long_ctx}\n\n"
    if learnings_ctx:
        user_prompt += f"{learnings_ctx}\n\n"
    user_prompt += "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    if history_ctx:
        user_prompt += f"\n\n{history_ctx}"
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw = _call_claude(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_CRYPTO)
    result = _parse_json(raw)

    if not result or "score" not in result:
        logger.warning("analyze_crypto: fallback activé")
        return _fallback_crypto(dashboard)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_crypto: direction={result.get('direction')}, "
        f"{len(result.get('signals', []))} signaux"
    )
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    await asyncio.gather(
        _save("crypto", result),
        embed_and_save(today, "crypto", result),
    )
    return result


def _fallback_crypto(dashboard: dict) -> dict:
    return {
        "dashboard":     dashboard,
        "phase":         "N/A",
        "volume_vs_30d": "données indisponibles",
        "score": {
            "onchain":   {"value": 0, "note": "N/A"},
            "cycle":     {"value": 0, "note": "N/A"},
            "macro":     {"value": 0, "note": "N/A"},
            "sentiment": {"value": 0, "note": "N/A"},
            "momentum":  {"value": 0, "note": "N/A"},
        },
        "direction":  "NEUTRE",
        "magnitude":  "faible",
        "bear_case":  "Analyse indisponible.",
        "signals":    [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_MARKET — Dashboard + Score récession + Régime + Signaux
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_MARKET = """Tu es CORTEX, analyste macro senior pour Badr — investisseur tech.

MISSION :
1. Évalue chaque indicateur de récession (green/yellow/red) avec justification précise et chiffrée
2. Calcule le score total (/10)
3. Détermine le régime de marché actuel avec justification développée
4. Sélectionne EXACTEMENT 3 signaux news macro importants et approfondis

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "recession_indicators": {
    "courbe_taux":    {"status": "yellow", "note": "2Y-10Y à +0.15% — pente redevenue positive après 2 ans d'inversion"},
    "emploi":         {"status": "green",  "note": "Claims 220K, NFP +175K — marché du travail résistant"},
    "ism_manuf":      {"status": "yellow", "note": "49.2, 6e mois sous 50 — contraction industrielle modérée"},
    "ism_services":   {"status": "green",  "note": "53.1, expansion solide — services tiennent"},
    "conso_conf":     {"status": "green",  "note": "Conference Board 104.2, en hausse de 3 pts"},
    "credit_spread":  {"status": "green",  "note": "IG à 85bps, HY à 340bps — pas de stress crédit"},
    "earnings_rev":   {"status": "yellow", "note": "Révisions S&P500 Q2 : -2.3% — mixtes mais pas catastrophiques"},
    "pmi_composite":  {"status": "green",  "note": "PMI composite 52.3 — expansion modérée, services dominent"},
    "retail_sales":   {"status": "green",  "note": "Ventes détail +0.4% MoM — consommateur encore actif"},
    "housing":        {"status": "yellow", "note": "Mises en chantier -8% — immobilier sous pression des taux"}
  },
  "recession_score": 3,
  "regime": "Risk-on prudent",
  "regime_justification": "Développement complet du régime en 4-5 lignes — données macro, Fed, flux de capitaux, positionnement des institutionnels. Factuel et chiffré.",
  "signals": [
    {
      "conviction": 4,
      "title": "TITRE EN MAJUSCULES (max 80 chars)",
      "fait": "Factuel, complet, APPROFONDI. Contexte macro, données chiffrées, implications sur les marchés. Minimum 6 lignes. Texte brut.",
      "implication_2": "Si vrai, alors... impact sur les actions, obligations, devises, commodités. 3-4 phrases.",
      "implication_3": "Qui gagne : [secteurs/pays/actifs]. Qui perd : [idem]. Asymétrie et timing. 3-4 phrases.",
      "these_opposee": "Meilleur argument contre cette lecture macro, avec données. 2-3 lignes.",
      "action": "Action concrète et spécifique pour Badr — ETF, ticker, allocation, timing.",
      "sizing": "Moyen",
      "invalide_si": "Condition précise et mesurable d'invalidation — seuil de prix, donnée économique, événement.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ],
  "questions": [
    "Question directe sur le macro/marché le plus impactant du jour. 1 phrase, force un choix.",
    "Question sur le risque de récession ou sur un marché spécifique. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS exactement 3 signaux dans signals
- status : "green", "yellow" ou "red" uniquement
- recession_indicators : EXACTEMENT 10 indicateurs (courbe_taux, emploi, ism_manuf, ism_services, conso_conf, credit_spread, earnings_rev, pmi_composite, retail_sales, housing)
- recession_score : score = (nb red) + 0.5 × (nb yellow), arrondi sur 10
- regime : parmi "Risk-on", "Risk-off", "Inflation trade", "Stagflation", "Transition"
- sizing : "Fort", "Moyen" ou "Faible"
- Tout en FRANÇAIS — texte brut, zéro markdown
- questions : EXACTEMENT 2 questions en français, directes, basées sur les données macro du jour
- LIMITES : fait=500-800 chars, implication_2=200-300, implication_3=200-300, these_opposee=150-250, action=150-200, invalide_si=100-150, note récession=60-100"""


async def analyze_market(data: dict) -> dict:
    """
    Analyse les marchés : score récession, régime, signaux macro.
    Groq pré-filtre les signaux bruts → top 12 avant envoi à Claude Sonnet.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    # Étape 1 : Groq pré-filtre → 12
    signals   = _prefilter_with_groq(signals, sector="macro/markets/finance", max_count=12)
    # Étape 2 : Board débat → 4
    from agents.board import run_debate
    signals   = await run_debate(signals, sector="Marchés & Macro")
    context   = _prep_signals(signals, 12)

    from agents.memory import get_sector_history, format_market_history, save_analysis as _save_mkt
    from agents.long_memory import (
        get_all_weekly_summaries, get_all_patterns, semantic_search,
        format_long_memory_context, embed_and_save,
    )
    from agents.memory import get_agent_learnings, format_learnings_context

    history, summaries, patterns, learnings = await asyncio.gather(
        get_sector_history("market", days=7),
        get_all_weekly_summaries("market", limit=8),
        get_all_patterns("market"),
        get_agent_learnings("market", limit=5),
    )
    similar = await semantic_search(context[:600], "market", top_k=3)

    history_ctx   = format_market_history(history)
    long_ctx      = format_long_memory_context(summaries, patterns, similar)
    learnings_ctx = format_learnings_context(learnings, "Marchés")

    def _fmt(key: str) -> str:
        d = dashboard.get(key, {})
        if not d:
            return "N/A"
        price = d.get("price", "N/A")
        chg   = d.get("change_pct", 0)
        arrow = "▴" if chg >= 0 else "▾"
        pct   = f"{'+' if chg >= 0 else ''}{chg:.1f}%"
        return f"{price} {arrow} {pct}"

    dash_str = (
        f"S&P 500  : {_fmt('sp500')}\n"
        f"Nasdaq   : {_fmt('nasdaq')}\n"
        f"Or       : {_fmt('gold')}\n"
        f"Pétrole  : {_fmt('oil')}\n"
        f"DXY      : {_fmt('dxy')}\n"
        f"VIX      : {dashboard.get('vix', {}).get('price', 'N/A')} — "
        f"{dashboard.get('vix', {}).get('interpretation', 'N/A')}\n"
        f"US 10Y   : {dashboard.get('us_10y', {}).get('price', 'N/A')} "
        f"({dashboard.get('us_10y', {}).get('change_bps', 'N/A')})"
    )

    user_prompt = ""
    if long_ctx:
        user_prompt += f"{long_ctx}\n\n"
    if learnings_ctx:
        user_prompt += f"{learnings_ctx}\n\n"
    user_prompt += "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    if history_ctx:
        user_prompt += f"\n\n{history_ctx}"
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw = _call_claude(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_MARKET)
    result = _parse_json(raw)

    if not result or "recession_indicators" not in result:
        logger.warning("analyze_market: fallback activé")
        return _fallback_market(dashboard)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_market: régime={result.get('regime')}, "
        f"récession={result.get('recession_score')}/10"
    )
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    await asyncio.gather(
        _save_mkt("market", result),
        embed_and_save(today, "market", result),
    )
    return result


def _fallback_market(dashboard: dict) -> dict:
    neutral = {"status": "yellow", "note": "données indisponibles"}
    return {
        "dashboard": dashboard,
        "recession_indicators": {k: neutral for k in [
            "courbe_taux", "emploi", "ism_manuf", "ism_services",
            "conso_conf", "credit_spread", "earnings_rev",
        ]},
        "recession_score": 3,
        "regime":               "Transition",
        "regime_justification": "Analyse indisponible — Claude non connecté.",
        "signals":              [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_DEEPTECH — 2 signaux avec crédibilité + investissement
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_DEEPTECH = """Tu es CORTEX, analyste deeptech senior pour Badr — investisseur tech.

MISSION : Sélectionne les 3 meilleurs signaux deeptech selon :
1. Crédibilité (publication peer-reviewed, financement confirmé, prototype, adoption)
2. Potentiel de rupture réel (pas juste intéressant — transformateur sur 3-10 ans)
3. Utilité pour un investisseur (angle investissement concret et actionnable)
4. Diversité des domaines si possible (biotech, quantique, robotique, énergie, matériaux, espace)

Pour chaque signal, fournis une analyse COMPLÈTE et APPROFONDIE.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "signals": [
    {
      "conviction": 4,
      "horizon": "3-5",
      "title": "TITRE EN MAJUSCULES — DOMAINE (max 80 chars)",
      "fait": "Factuel, complet et APPROFONDI. Qui, quoi, où, chiffres précis, contexte scientifique, état de l'art avant cette découverte, ce qui change. Minimum 6-8 lignes denses. Texte brut.",
      "implication_2": "Si vrai, alors... — impact sur l'industrie concernée, disruption des acteurs en place, nouveaux marchés créés. 3-4 phrases.",
      "implication_3": "Qui gagne concrètement : [entreprises/secteurs précis avec explication]. Qui perd : [idem]. Asymétrie temporelle. 3-4 phrases.",
      "credibilite_score": 3,
      "peer_reviewed": true,
      "peer_reviewed_detail": "Nature, vol. 612, décembre 2024 — peer-reviewed par 5 experts indépendants",
      "financement": true,
      "financement_detail": "$120M Series C (a16z, Sequoia) — valorisation $800M pré-money",
      "prototype": true,
      "prototype_detail": "Démonstration publique au MIT janvier 2025, vidéo disponible, résultats reproductibles",
      "adoption": false,
      "adoption_detail": "",
      "investissement_cotes": ["NVDA", "IONQ", "ARKG"],
      "investissement_etf": ["ARKG", "BOTZ"],
      "investissement_early": ["Startup X — surveiller tour Series A", "IPO de Y prévue Q3 2025"],
      "action": "Action concrète et spécifique pour Badr — ticker précis, timing d'entrée, conditions.",
      "sizing": "Faible",
      "invalide_si": "Seuil précis et mesurable d'invalidation — résultats négatifs, retrait financement, etc.",
      "source_name": "Nature / arXiv / MIT Tech Review",
      "source_url": "URL exacte"
    }
  ],
  "questions": [
    "Question sur la technologie ou l'investissement deeptech le plus pertinent du jour. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS 3 signaux dans le tableau signals
- horizon : UNIQUEMENT "5-10" ou "10+" — les technologies deeptech n'ont JAMAIS d'impact en moins de 5 ans
- credibilite_score : 0-4 (nombre de critères remplis)
- sizing : "Fort", "Moyen" ou "Faible"
- Si un critère n'est pas rempli, mettre false et detail vide ""
- investissement_cotes/etf/early : listes vides [] si rien de pertinent
- Tout en FRANÇAIS — texte brut, zéro markdown
- questions : 1 question en français, basée sur le signal deeptech le plus crédible
- LIMITES : fait=500-800 chars, implication_2=200-300, implication_3=200-300, action=150-200, invalide_si=100-150, detail crédibilité=60-120"""


async def analyze_deeptech(signals: list[dict]) -> dict:
    """
    Sélectionne les 2 meilleurs signaux deeptech et génère l'analyse complète.
    Groq pré-filtre les signaux bruts → top 10 avant envoi à Claude Sonnet.
    """
    if not signals:
        return {"signals": []}

    # Étape 1 : Groq pré-filtre → 10
    signals = _prefilter_with_groq(signals, sector="deeptech/science/research", max_count=10)
    # Étape 2 : Board débat → 4
    from agents.board import run_debate
    signals = await run_debate(signals, sector="DeepTech & Science")

    from agents.memory import get_sector_history, format_deeptech_history, save_analysis as _save_dt
    from agents.long_memory import (
        get_all_weekly_summaries, get_all_patterns, semantic_search,
        format_long_memory_context, embed_and_save,
    )
    from agents.memory import get_agent_learnings, format_learnings_context

    context = _prep_signals(signals, 10)

    history, summaries, patterns, learnings = await asyncio.gather(
        get_sector_history("deeptech", days=7),
        get_all_weekly_summaries("deeptech", limit=8),
        get_all_patterns("deeptech"),
        get_agent_learnings("deeptech", limit=5),
    )
    similar = await semantic_search(context[:600], "deeptech", top_k=3)

    history_ctx   = format_deeptech_history(history)
    long_ctx      = format_long_memory_context(summaries, patterns, similar)
    learnings_ctx = format_learnings_context(learnings, "DeepTech")

    user_prompt = ""
    if long_ctx:
        user_prompt += f"{long_ctx}\n\n"
    if learnings_ctx:
        user_prompt += f"{learnings_ctx}\n\n"
    if history_ctx:
        user_prompt += f"{history_ctx}\n\n"
    user_prompt += f"Voici {len(signals)} signaux deeptech collectés :\n\n{context}"

    raw = _call_claude(user_prompt, max_tokens=5000, system_prompt=_SYSTEM_DEEPTECH)
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_deeptech: fallback activé")
        return _fallback_deeptech(signals[:2])

    logger.info(f"analyze_deeptech: {len(result.get('signals', []))} signaux analysés")
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    await asyncio.gather(
        _save_dt("deeptech", result),
        embed_and_save(today, "deeptech", result),
    )
    return result


def _fallback_deeptech(signals: list[dict]) -> dict:
    return {
        "signals": [{
            "conviction":           3,
            "horizon":              "5-10",
            "title":                s.get("title", "SIGNAL DEEPTECH")[:70].upper(),
            "fait":                 s.get("raw_content", "")[:300],
            "implication_2":        "Analyse indisponible.",
            "implication_3":        "Vérification manuelle recommandée.",
            "credibilite_score":    1,
            "peer_reviewed":        True,
            "peer_reviewed_detail": "arXiv pré-print",
            "financement":          False,
            "financement_detail":   "",
            "prototype":            False,
            "prototype_detail":     "",
            "adoption":             False,
            "adoption_detail":      "",
            "investissement_cotes": [],
            "investissement_etf":   [],
            "investissement_early": [],
            "action":               "Lire la source directement.",
            "sizing":               "Faible",
            "invalide_si":          "N/A",
            "source_name":          s.get("source_name", ""),
            "source_url":           s.get("source_url", ""),
        } for s in signals]
    }


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE_NEXUS — Connexion cross-secteurs + Question du matin
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_NEXUS = """Tu es CORTEX, analyste stratégique senior pour Badr — investisseur individuel qui veut devenir plus intelligent chaque jour sur les marchés, la tech et l'économie mondiale.

MISSION 1 — CHAÎNE CAUSALE DU JOUR :
Identifie la chaîne causale la plus puissante entre les 4 secteurs (IA, Crypto, Marchés, DeepTech).
Format impératif : chaque maillon = "Fait précis [SECTEUR]" → conséquence.
Exemple : "Fed hawkish [MARCHÉS] → dollar fort [MARCHÉS] → BTC sous pression [CRYPTO] → rotation vers GPU cloud [IA]"
Si aucune chaîne réelle n'existe → retourne has_connexion: false.
NE JAMAIS forcer une connexion artificielle.
Maximum 3 maillons. Dense, factuel.

MISSION 2 — 3 QUESTIONS POUR GRANDIR INTELLECTUELLEMENT :
But unique : rendre Badr plus intelligent. Chaque question doit forcer une DÉCISION ou révéler une INSIGHT non-évident.
- Question 1 (binaire) : format strict "Si [fait précis du jour], tu [action A] ou tu [action B] ?" — peut porter sur N'IMPORTE QUEL secteur ou combinaison de secteurs.
- Question 2 (connexion inter-secteurs) : comment 2 signaux de secteurs DIFFÉRENTS se combinent pour créer une opportunité ou un risque non-évident. Peut être Marchés+DeepTech, Crypto+IA, etc.
- Question 3 (recul stratégique) : qu'est-ce que les signaux du jour révèlent sur une tendance de fond à 3-6 mois ? Forcer une prise de position.
Ton direct, frontal. 1 phrase max par question. En français.
ANTI-RÉPÉTITION ABSOLUE : Si des questions passées sont fournies en contexte, chaque question générée DOIT être sur un angle/ticker/secteur différent. Zéro tolérance pour la répétition de thème.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "has_connexion": true,
  "connexion": "Fait A [SECTEUR] → conséquence B [SECTEUR] → impact C [SECTEUR]",
  "secteurs_lies": ["Crypto", "Marchés"],
  "question": "La question binaire principale — format 'Si [fait], tu [action A] ou [action B] ?'",
  "questions": [
    "Question binaire : Si [fait précis de n'importe quel secteur], tu [action A] ou [action B] ?",
    "Question connexion : [Signal secteur X] combiné à [signal secteur Y] — qu'est-ce que ça implique concrètement pour Badr ?",
    "Question recul : Qu'est-ce que [tendance observée aujourd'hui] dit sur [marché/secteur] dans 3-6 mois ?"
  ]
}"""


async def generate_nexus(
    ai_data:       dict,
    crypto_data:   dict,
    market_data:   dict,
    deeptech_data: dict,
) -> dict:
    """
    Trouve la connexion la plus puissante entre les 4 secteurs.
    Génère la question du matin binaire et actionnée.
    """

    def _summarize(data: dict, sector: str) -> str:
        signals = data.get("signals", [])
        titles = [f"  - {s.get('title', '')}" for s in signals[:3]]
        return f"[{sector}]\n" + ("\n".join(titles) if titles else "  (aucun signal)")

    summary = "\n".join([
        _summarize(ai_data,       "IA"),
        _summarize(crypto_data,   "CRYPTO"),
        _summarize(market_data,   "MARCHÉS"),
        _summarize(deeptech_data, "DEEPTECH"),
    ])

    all_signals = (
        ai_data.get("signals", []) +
        crypto_data.get("signals", []) +
        market_data.get("signals", []) +
        deeptech_data.get("signals", [])
    )
    top_signal = max(all_signals, key=lambda x: x.get("conviction", 0)) if all_signals else {}
    top_title  = top_signal.get("title", "signal du jour")
    top_fait   = top_signal.get("fait", "")

    crypto_dir    = crypto_data.get("direction", "")
    market_regime = market_data.get("regime", "")

    # Charger mémoire longue durée Nexus (patterns globaux + contextes similaires)
    from agents.long_memory import get_all_patterns, semantic_search, format_long_memory_context
    nexus_query = f"{summary[:400]} | {crypto_dir} | {market_regime}"
    patterns_global, similar_nexus = await asyncio.gather(
        get_all_patterns("global"),
        semantic_search(nexus_query, "ai", top_k=2),
    )
    long_ctx = format_long_memory_context([], patterns_global, similar_nexus)

    # Anti-répétition Nexus : 7 jours de questions + connexions déjà vues
    from agents.memory import get_sector_history
    nexus_history = await get_sector_history("nexus", days=7)
    past_nexus = ""
    if nexus_history:
        conn_lines = ["── CONNEXIONS déjà générées (ne pas répéter le même angle) ──"]
        q_lines    = ["── QUESTIONS déjà posées (INTERDITES — trouver angles différents) ──"]
        for entry in nexus_history[:7]:
            report_date = entry["report_date"]
            data = entry["data"]
            conn = data.get("connexion", "")
            if conn:
                conn_lines.append(f"  {report_date}: {conn[:120]}")
            # Extraire toutes les questions posées ce jour
            qs = data.get("questions", [])
            q_main = data.get("question", "")
            if q_main:
                qs = [q_main] + [q for q in qs if q != q_main]
            for q in qs[:3]:
                if q and len(q) > 10:
                    q_lines.append(f"  [{report_date}] {q[:150]}")
        has_conn = len(conn_lines) > 1
        has_q    = len(q_lines) > 1
        parts = []
        if has_conn:
            parts.append("\n".join(conn_lines))
        if has_q:
            parts.append("\n".join(q_lines))
        past_nexus = "\n\n".join(parts)

    user_prompt = ""
    if long_ctx:
        user_prompt += f"{long_ctx}\n\n"
    if past_nexus:
        user_prompt += f"{past_nexus}\n\n"
    user_prompt += (
        f"SIGNAUX DU JOUR :\n{summary}\n\n"
        f"Crypto : {crypto_dir} | Marché : {market_regime}\n\n"
        f"Signal le plus fort : {top_title}\n"
        f"Détail : {top_fait[:300]}"
    )

    raw = _call_claude(user_prompt, max_tokens=1200, system_prompt=_SYSTEM_NEXUS, model="claude-haiku-4-5-20251001")
    result = _parse_json(raw)

    if not result or "question" not in result:
        logger.warning("generate_nexus: fallback activé")
        return {
            "has_connexion": False,
            "connexion":     None,
            "secteurs_lies": [],
            "question":      f"{top_title} — tu surveilles ou tu positions maintenant ?",
        }

    logger.info(
        f"generate_nexus: connexion={'oui' if result.get('has_connexion') else 'non'}, "
        f"question générée"
    )

    from agents.memory import save_analysis as _save_nexus
    await _save_nexus("nexus", result)

    return result
