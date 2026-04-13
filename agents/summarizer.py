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
    max_tokens: int = 3000,
    system_prompt: str = None,
) -> str | None:
    """
    Appel Claude Sonnet avec prompt caching optionnel.

    Si system_prompt fourni, il est envoyé avec cache_control ephemeral
    → Anthropic le met en cache côté serveur (TTL 5 min).
    Économies typiques : 80% sur les tokens input pour les appels répétés.
    """
    client = _get_client()
    if not client:
        return None
    try:
        kwargs = dict(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
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

MISSION : À partir des signaux fournis, sélectionne les 3 plus importants selon :
1. Impact réel sur l'industrie IA (pas du clickbait)
2. Nouveauté absolue (pas déjà vu cette semaine, cf. historique)
3. Utilité directe pour un investisseur/entrepreneur IA
4. Diversité : évite 3 signaux sur le même sous-thème

Pour chaque signal sélectionné, fournis une analyse approfondie en 3 ordres.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "signals": [
    {
      "conviction": 5,
      "title": "TITRE EN MAJUSCULES — CONCIS, PERCUTANT, FACTUEL (max 70 chars)",
      "fait": "Explication factuelle complète. Qui, quoi, d'où ça vient, chiffres précis. 4-5 lignes. Texte brut uniquement.",
      "implication_2": "Si c'est vrai, alors... — conséquences directes. 1-2 phrases.",
      "implication_3": "Qui gagne : [X]. Qui perd : [Y]. Où est l'asymétrie. 1-2 phrases.",
      "these_opposee": "Le meilleur argument contre cette lecture. 1-2 lignes max.",
      "action": "Action concrète que Badr peut prendre maintenant. Spécifique, pas vague.",
      "sizing": "Fort",
      "invalide_si": "Seuil ou événement précis qui invaliderait cette analyse.",
      "source_name": "Nom exact de la source",
      "source_url": "URL exacte"
    }
  ],
  "watchlist": [
    "Signal early pas encore mûr — [source] — pourquoi surveiller",
    "Autre signal — [source] — signal à confirmer"
  ]
}

Règles absolues :
- conviction : entier de 1 (faible) à 5 (exceptionnel)
- sizing : exactement "Fort", "Moyen" ou "Faible"
- Tout le texte en FRANÇAIS
- Texte brut uniquement — zéro markdown dans les valeurs de texte
- watchlist : 2-3 items max, 1 ligne chacun
- LIMITES DE LONGUEUR STRICTES (en caractères) :
  fait          : max 350 chars
  implication_2 : max 140 chars
  implication_3 : max 140 chars
  these_opposee : max 120 chars
  action        : max 120 chars
  invalide_si   : max 80 chars
  watchlist item: max 90 chars"""


async def analyze_ai(signals: list[dict]) -> dict:
    """
    Sélectionne les 3 meilleurs signaux IA et génère l'analyse complète.
    Groq pré-filtre les signaux bruts → top 15 avant envoi à Claude Sonnet.
    """
    if not signals:
        return _fallback_ai([])

    # Pré-filtrage Groq : 120 signaux → 15
    signals = _prefilter_with_groq(signals, sector="AI/tech", max_count=15)

    from agents.memory import get_sector_history, format_ai_history, save_analysis
    history     = await get_sector_history("ai", days=7)
    history_ctx = format_ai_history(history)

    context = _prep_signals(signals, 15)

    # Partie dynamique (signaux + historique — non mise en cache)
    user_prompt = ""
    if history_ctx:
        user_prompt += f"{history_ctx}\n\n"
    user_prompt += f"Voici {len(signals)} signaux IA collectés :\n\n{context}"

    raw = _call_claude(user_prompt, max_tokens=3500, system_prompt=_SYSTEM_AI)
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_ai: fallback activé")
        return _fallback_ai(signals[:3])

    logger.info(f"analyze_ai: {len(result.get('signals', []))} signaux analysés")
    await save_analysis("ai", result)
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

_SYSTEM_CRYPTO = """Tu es CORTEX, analyste crypto senior pour Badr — investisseur tech.

MISSION :
1. Détermine la phase du cycle (Accumulation / Markup / Distribution / Markdown)
2. Score chaque facteur de direction de -2 à +2 avec justification courte
3. Sélectionne max 3 signaux news pertinents (si aucun signal solide, 1 seul suffit)
4. Rédige le bear case qui invaliderait ta lecture

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "phase": "Accumulation",
  "volume_vs_30d": "description humaine du volume vs moyenne (ex: -18% vs moy. 30j)",
  "score": {
    "onchain":   {"value": 1,  "note": "justification courte 1 ligne"},
    "cycle":     {"value": 1,  "note": "justification courte 1 ligne"},
    "macro":     {"value": 0,  "note": "justification courte 1 ligne"},
    "sentiment": {"value": -1, "note": "justification courte 1 ligne"},
    "momentum":  {"value": 0,  "note": "justification courte 1 ligne"}
  },
  "direction": "NEUTRE-BULLISH",
  "magnitude": "faible",
  "bear_case": "Ce qui invaliderait cette lecture — 2 lignes max.",
  "signals": [
    {
      "conviction": 4,
      "title": "TITRE SIGNAL EN MAJUSCULES (max 70 chars)",
      "fait": "Factuel. Complet. 3-4 lignes. Texte brut.",
      "implication_2": "Si vrai, alors... 1-2 phrases.",
      "implication_3": "Qui gagne / perd. 1 phrase.",
      "these_opposee": "Argument contre. 1-2 lignes.",
      "action": "Action concrète pour Badr.",
      "sizing": "Moyen",
      "invalide_si": "Condition d'invalidation précise.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ]
}

Règles absolues :
- score values : entiers de -2 à +2 uniquement
- direction : parmi BULLISH / NEUTRE-BULLISH / NEUTRE / NEUTRE-BEARISH / BEARISH
- magnitude : parmi "forte" / "modérée" / "faible"
- sizing : "Fort", "Moyen" ou "Faible"
- Texte brut uniquement dans toutes les valeurs string
- Si moins de 3 signaux solides, mettre moins (qualité > quantité)
- LIMITES strictes : fait≤350, implication_2≤140, implication_3≤140, these_opposee≤120, action≤120, invalide_si≤80"""


async def analyze_crypto(data: dict) -> dict:
    """
    Analyse le marché crypto : phase du cycle, score de direction, signaux.
    Groq pré-filtre les signaux bruts → top 12 avant envoi à Claude Sonnet.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    signals   = _prefilter_with_groq(signals, sector="crypto/blockchain", max_count=12)
    context   = _prep_signals(signals, 12)

    from agents.memory import get_sector_history, format_crypto_history, save_analysis as _save
    history     = await get_sector_history("crypto", days=7)
    history_ctx = format_crypto_history(history)

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

    user_prompt = "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    if history_ctx:
        user_prompt += f"\n\n{history_ctx}"
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw = _call_claude(user_prompt, max_tokens=3500, system_prompt=_SYSTEM_CRYPTO)
    result = _parse_json(raw)

    if not result or "score" not in result:
        logger.warning("analyze_crypto: fallback activé")
        return _fallback_crypto(dashboard)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_crypto: direction={result.get('direction')}, "
        f"{len(result.get('signals', []))} signaux"
    )
    await _save("crypto", result)
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
1. Évalue chaque indicateur de récession (green/yellow/red) avec justification courte
2. Calcule le score total (/10)
3. Détermine le régime de marché actuel
4. Sélectionne max 3 signaux news macro pertinents

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "recession_indicators": {
    "courbe_taux":    {"status": "yellow", "note": "Plate à 0.1%, non inversée"},
    "emploi":         {"status": "green",  "note": "Claims stables, NFP solide"},
    "ism_manuf":      {"status": "yellow", "note": "49.2, contraction légère"},
    "ism_services":   {"status": "green",  "note": "53.1, expansion"},
    "conso_conf":     {"status": "green",  "note": "En hausse ce mois"},
    "credit_spread":  {"status": "green",  "note": "IG serrés, pas de stress"},
    "earnings_rev":   {"status": "yellow", "note": "Mixtes — quelques downgrades"}
  },
  "recession_score": 3,
  "regime": "Risk-on prudent",
  "regime_justification": "2-3 lignes expliquant le régime. Factuel.",
  "signals": [
    {
      "conviction": 4,
      "title": "TITRE EN MAJUSCULES (max 70 chars)",
      "fait": "Factuel. Complet. 3-4 lignes. Texte brut.",
      "implication_2": "Si vrai, alors... 1-2 phrases.",
      "implication_3": "Qui gagne / perd. 1 phrase.",
      "these_opposee": "Argument contre. 1-2 lignes.",
      "action": "Action concrète pour Badr.",
      "sizing": "Moyen",
      "invalide_si": "Condition d'invalidation précise.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ]
}

Règles absolues :
- status : "green", "yellow" ou "red" uniquement
- recession_score : calculé ainsi : score = (nb red) + 0.5 × (nb yellow), arrondi
- regime : parmi "Risk-on", "Risk-off", "Inflation trade", "Stagflation", "Transition"
- sizing : "Fort", "Moyen" ou "Faible"
- Texte brut uniquement dans toutes les valeurs string
- Si moins de 3 signaux solides disponibles, mettre moins
- LIMITES strictes : fait≤350, implication_2≤140, implication_3≤140, these_opposee≤120, action≤120, invalide_si≤80, note récession≤60"""


async def analyze_market(data: dict) -> dict:
    """
    Analyse les marchés : score récession, régime, signaux macro.
    Groq pré-filtre les signaux bruts → top 12 avant envoi à Claude Sonnet.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    signals   = _prefilter_with_groq(signals, sector="macro/markets/finance", max_count=12)
    context   = _prep_signals(signals, 12)

    from agents.memory import get_sector_history, format_market_history, save_analysis as _save_mkt
    history     = await get_sector_history("market", days=7)
    history_ctx = format_market_history(history)

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

    user_prompt = "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    if history_ctx:
        user_prompt += f"\n\n{history_ctx}"
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw = _call_claude(user_prompt, max_tokens=3500, system_prompt=_SYSTEM_MARKET)
    result = _parse_json(raw)

    if not result or "recession_indicators" not in result:
        logger.warning("analyze_market: fallback activé")
        return _fallback_market(dashboard)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_market: régime={result.get('regime')}, "
        f"récession={result.get('recession_score')}/10"
    )
    await _save_mkt("market", result)
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

MISSION : Sélectionne les 2 signaux deeptech les plus importants selon :
1. Crédibilité (publication peer-reviewed, financement, prototype, adoption)
2. Potentiel de rupture réel (pas juste intéressant — transformateur)
3. Utilité pour un investisseur (angle investissement concret)
4. Diversité des domaines si possible (biotech, quantique, robotique, énergie, matériaux, espace)

Pour chaque signal, fournis l'analyse complète.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "signals": [
    {
      "conviction": 4,
      "horizon": "3-5",
      "title": "TITRE EN MAJUSCULES — DOMAINE (max 70 chars)",
      "fait": "Factuel. Qui, quoi, où, chiffres précis. 4-5 lignes. Texte brut.",
      "implication_2": "Si vrai, alors... — impact sur l'industrie. 1-2 phrases.",
      "implication_3": "Qui gagne : [X]. Qui perd : [Y]. 1-2 phrases.",
      "credibilite_score": 3,
      "peer_reviewed": true,
      "peer_reviewed_detail": "Nature, vol. 612, 2024",
      "financement": true,
      "financement_detail": "$120M Series C (a16z)",
      "prototype": true,
      "prototype_detail": "Démonstration publique au MIT, vidéo disponible",
      "adoption": false,
      "adoption_detail": "",
      "investissement_cotes": ["NVDA", "IONQ", "ARKG"],
      "investissement_etf": ["ARKG", "BOTZ"],
      "investissement_early": ["Startup X (non coté)", "Surveiller la IPO de Y"],
      "action": "Action concrète pour Badr — spécifique.",
      "sizing": "Faible",
      "invalide_si": "Seuil précis d'invalidation.",
      "source_name": "Nature / arXiv / MIT Tech Review",
      "source_url": "URL exacte"
    }
  ]
}

Règles absolues :
- horizon : exactement "1-2", "3-5", "5-10" ou "10+"
- credibilite_score : 0-4 (nombre de critères remplis parmi les 4)
- sizing : "Fort", "Moyen" ou "Faible"
- Si un critère n'est pas rempli, mettre false et detail vide
- investissement_cotes/etf/early : listes vides [] si rien de pertinent
- Texte brut uniquement
- Maximum 2 signaux même si plus de bons candidats
- LIMITES strictes : fait≤350, implication_2≤140, implication_3≤140, action≤120, invalide_si≤80, detail crédibilité≤60"""


async def analyze_deeptech(signals: list[dict]) -> dict:
    """
    Sélectionne les 2 meilleurs signaux deeptech et génère l'analyse complète.
    Groq pré-filtre les signaux bruts → top 10 avant envoi à Claude Sonnet.
    """
    if not signals:
        return {"signals": []}

    # Pré-filtrage Groq : 50 signaux → 10
    signals = _prefilter_with_groq(signals, sector="deeptech/science/research", max_count=10)

    from agents.memory import get_sector_history, format_deeptech_history, save_analysis as _save_dt
    history     = await get_sector_history("deeptech", days=7)
    history_ctx = format_deeptech_history(history)

    context = _prep_signals(signals, 10)

    user_prompt = ""
    if history_ctx:
        user_prompt += f"{history_ctx}\n\n"
    user_prompt += f"Voici {len(signals)} signaux deeptech collectés :\n\n{context}"

    raw = _call_claude(user_prompt, max_tokens=3000, system_prompt=_SYSTEM_DEEPTECH)
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_deeptech: fallback activé")
        return _fallback_deeptech(signals[:2])

    logger.info(f"analyze_deeptech: {len(result.get('signals', []))} signaux analysés")
    await _save_dt("deeptech", result)
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

_SYSTEM_NEXUS = """Tu es CORTEX, analyste stratégique senior pour Badr — investisseur tech.

MISSION 1 — CONNEXION DU JOUR :
Trouve le lien le plus puissant et authentique entre 2+ secteurs parmi les signaux fournis.
Si aucune connexion réelle n'existe → retourne has_connexion: false.
NE JAMAIS forcer une connexion artificielle.
Si connexion : 1 paragraphe max, dense, avec les faits précis qui la justifient.

MISSION 2 — QUESTION DU MATIN :
Une seule question qui force Badr à DÉCIDER (pas observer).
Format binaire : "Si [fait précis du jour], tu [action A] ou tu [action B] ?"
Basée sur le signal le plus fort, tous secteurs confondus.
Ton direct, frontal. 1 phrase. En français.

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "has_connexion": true,
  "connexion": "1 paragraphe ou null si pas de connexion.",
  "secteurs_lies": ["IA", "Marchés"],
  "question": "Si [fait], tu [action A] ou tu [action B] ?"
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

    user_prompt = (
        f"SIGNAUX DU JOUR :\n{summary}\n\n"
        f"Crypto : {crypto_dir} | Marché : {market_regime}\n\n"
        f"Signal le plus fort : {top_title}\n"
        f"Détail : {top_fait[:300]}"
    )

    raw = _call_claude(user_prompt, max_tokens=800, system_prompt=_SYSTEM_NEXUS)
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
