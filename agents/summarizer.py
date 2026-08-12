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
import time
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


def _call_anthropic(
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
        logger.warning(f"Anthropic indisponible: {str(e)[:160]}")
        return None


# ── Fournisseurs gratuits (Groq / Gemini) ─────────────────────────────────────

# Modèles gratuits utilisés pour l'analyse profonde.
# gpt-oss-120b : 120B params, excellent en JSON structuré — c'est le cheval de trait.
GROQ_DEEP_MODEL   = os.getenv("GROQ_DEEP_MODEL", "openai/gpt-oss-120b")
GROQ_BACKUP_MODEL = os.getenv("GROQ_BACKUP_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Attente avant nouvel essai quand un fournisseur gratuit dit "quota atteint".
RATE_LIMIT_WAIT = int(os.getenv("LLM_RATE_LIMIT_WAIT", "20"))

# Ordre des fournisseurs. Par défaut les GRATUITS d'abord : l'API Anthropic
# payante n'est sollicitée qu'en dernier recours (et seulement si elle a du crédit).
# Surchargeable via LLM_PROVIDER_ORDER="anthropic,groq,gemini".
DEFAULT_PROVIDER_ORDER = ["groq", "gemini", "anthropic"]


def _parse_provider_order() -> list[str]:
    """Lit LLM_PROVIDER_ORDER, en retombant sur l'ordre par défaut si elle est
    absente, vide ou ne contient aucun fournisseur connu (une variable définie
    à la chaîne vide viderait sinon la liste et couperait toute analyse)."""
    raw = os.getenv("LLM_PROVIDER_ORDER", "")
    parsed = [p.strip().lower() for p in raw.split(",") if p.strip()]
    known = [p for p in parsed if p in DEFAULT_PROVIDER_ORDER]
    return known or DEFAULT_PROVIDER_ORDER


PROVIDER_ORDER = _parse_provider_order()


def _call_groq_deep(
    prompt: str,
    max_tokens: int = 4000,
    system_prompt: str = None,
    model: str = None,
) -> str | None:
    """Analyse profonde via Groq (gratuit). Essaie le gros modèle puis le backup."""
    client = _get_groq_client()
    if not client:
        return None

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Deux contraintes opposées sur le palier gratuit :
    #  - trop peu de tokens → réponse coupée en plein JSON (le bug du 12/08 :
    #    4000 ne suffisait pas, il faut ~3500 tokens de JSON)
    #  - trop de tokens d'un coup → Groq répond 413 "request too large", car le
    #    quota par minute restant est inférieur à ce qu'on demande
    # Donc : on demande large, on patiente si le quota est momentanément à sec,
    # et seulement ensuite on descend d'un palier. Mieux vaut attendre 20 s
    # qu'obtenir une analyse tronquée.
    budgets = sorted({min(max_tokens, 8000), 6000, 4500}, reverse=True)

    for groq_model in [m for m in (model, GROQ_DEEP_MODEL, GROQ_BACKUP_MODEL) if m]:
        model_broken = False

        for budget in budgets:
            if model_broken:
                break
            for attempt in (1, 2):
                try:
                    response = client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        max_tokens=budget,
                        temperature=0.2,
                        response_format={"type": "json_object"},
                    )
                    choice = response.choices[0]
                    text = (choice.message.content or "").strip()

                    if choice.finish_reason == "length":
                        logger.warning(
                            f"Groq [{groq_model}] réponse tronquée à {budget} tokens — réparation JSON"
                        )
                    if text:
                        logger.info(f"Analyse via Groq [{groq_model}] ✅ (gratuit, {budget} tokens)")
                        return text
                    break  # réponse vide : palier suivant

                except Exception as e:
                    msg = str(e)[:200]
                    is_quota = _is_quota_error(msg)
                    if is_quota and attempt == 1:
                        logger.info(
                            f"Groq [{groq_model}] quota momentané — nouvel essai dans {RATE_LIMIT_WAIT}s"
                        )
                        time.sleep(RATE_LIMIT_WAIT)
                        continue
                    if is_quota:
                        logger.info(f"Groq [{groq_model}] {budget} tokens hors quota — palier inférieur")
                        break  # palier plus petit
                    logger.warning(f"Groq [{groq_model}] échoué: {msg}")
                    model_broken = True  # modèle indisponible → modèle suivant
                    break
    return None


def _is_quota_error(message: str) -> bool:
    """413 (requête trop grosse pour le quota restant) ou 429 (limite atteinte)."""
    m = message.lower()
    return any(x in m for x in ("too large", "rate limit", "413", "429", "quota", "resource_exhausted"))


def _call_gemini_deep(
    prompt: str,
    max_tokens: int = 4000,
    system_prompt: str = None,
) -> str | None:
    """Analyse profonde via Gemini Flash (gratuit)."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None

    for attempt in (1, 2):
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=key)
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=max(max_tokens, 8000),
                response_mime_type="application/json",
            )
            if system_prompt:
                config.system_instruction = system_prompt

            response = client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt, config=config
            )
            text = (response.text or "").strip()
            if text:
                logger.info(f"Analyse via Gemini [{GEMINI_MODEL}] ✅ (gratuit)")
                return text
            return None
        except Exception as e:
            msg = str(e)[:200]
            if _is_quota_error(msg) and attempt == 1:
                logger.info(f"Gemini quota momentané — nouvel essai dans {RATE_LIMIT_WAIT}s")
                time.sleep(RATE_LIMIT_WAIT)
                continue
            logger.warning(f"Gemini échoué: {msg}")
            return None
    return None


def _call_llm(
    prompt: str,
    max_tokens: int = 4000,
    system_prompt: str = None,
    model: str = "claude-sonnet-4-6",
) -> str | None:
    """
    Appel LLM en cascade sur plusieurs fournisseurs.

    Par défaut : Groq (gratuit) → Gemini (gratuit) → Anthropic (payant, dernier recours).

    Objectif : le rapport CORTEX doit rester complet même sans crédit Anthropic.
    C'est la panne du 2026-08 (crédit épuisé → sections Crypto et Marchés vides).
    `model` reste le modèle Anthropic souhaité si on retombe sur ce fournisseur.
    """
    for provider in PROVIDER_ORDER:
        if provider == "groq":
            out = _call_groq_deep(prompt, max_tokens, system_prompt)
        elif provider == "gemini":
            out = _call_gemini_deep(prompt, max_tokens, system_prompt)
        elif provider == "anthropic":
            out = _call_anthropic(prompt, max_tokens, system_prompt, model)
        else:
            continue
        if out:
            return out

    logger.error("Tous les fournisseurs LLM ont échoué — fallback dégradé")
    return None


# Alias de compatibilité (ancien nom utilisé dans le code historique).
_call_claude = _call_llm


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

    # Tentative 3 : réparer un JSON tronqué (réponse coupée par la limite de tokens).
    # Mieux vaut récupérer les 2 premiers signaux complets que perdre toute la section.
    repaired = _repair_truncated_json(text)
    if repaired is not None:
        logger.warning("JSON tronqué réparé — analyse partielle conservée")
        return repaired

    logger.error(f"JSON parse impossible: {text[:200]}")
    return None


def _repair_truncated_json(text: str):
    """
    Referme un JSON coupé en cours de route : on tronque à la dernière virgule de
    haut niveau puis on referme les accolades/crochets encore ouverts.
    Retourne None si la réparation ne donne rien d'exploitable.
    """
    start = next((i for i, c in enumerate(text) if c in "{["), None)
    if start is None:
        return None
    text = text[start:]

    stack, in_str, escape = [], False, False
    last_safe = None  # position juste après le dernier élément complet

    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]":
            if stack:
                stack.pop()
            if not stack:
                last_safe = i + 1
        elif c == "," and len(stack) <= 2:
            last_safe = i

    if last_safe is None:
        return None

    candidate = text[:last_safe].rstrip().rstrip(",")

    # Refermer ce qui reste ouvert, dans l'ordre inverse
    stack, in_str, escape = [], False, False
    for c in candidate:
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]" and stack:
            stack.pop()

    closing = "".join("}" if b == "{" else "]" for b in reversed(stack))
    try:
        return json.loads(candidate + closing)
    except json.JSONDecodeError:
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

RÈGLE DE STYLE (PRIORITAIRE) : Badr n'est PAS expert en finance ni en IA technique. Écris simplement, comme si tu expliquais à un ami intelligent mais non spécialiste. Chaque terme technique (ex : LLM, inférence, fine-tuning, valorisation, dilution...) est expliqué en quelques mots entre parenthèses la PREMIÈRE fois qu'il apparaît. Phrases courtes. Zéro jargon non expliqué. Quitte à être plus long, sois limpide — la clarté prime sur la concision.

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
      "en_clair": "Résumé en 1 phrase ULTRA-simple, zéro jargon — ce qu'il faut retenir si on ne lit rien d'autre. Max 150 chars.",
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
  "decision": {
    "ticker": "NVDA",
    "direction": "LONG",
    "horizon": "1-4 semaines",
    "conviction_pct": 70,
    "reasoning": "Explication concise de la décision — max 200 chars"
  },
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
- decision : OBLIGATOIRE — 1 décision concrète basée sur les signaux du jour. ticker = action/ETF/crypto exact. direction = "LONG" ou "WATCH" (pas de short sans levier). conviction_pct = 50-90.
- questions : EXACTEMENT 2 questions en français, directes, basées sur les signaux du jour
- LIMITES DE LONGUEUR (en caractères) :
  en_clair      : 80-150 chars (1 phrase simple, obligatoire)
  fait          : 500-800 chars (minimum 500 — analyse complète)
  implication_2 : 200-300 chars
  implication_3 : 200-300 chars
  these_opposee : 150-250 chars
  action        : 150-200 chars
  invalide_si   : 100-150 chars
  watchlist item: max 120 chars"""


async def analyze_ai(signals: list[dict]) -> dict:
    """
    Pipeline : Groq (→12) → Board débat (→4) → Claude Sonnet deep analysis.
    """
    if not signals:
        return _fallback_ai([])

    signals = _prefilter_with_groq(signals, sector="AI/tech", max_count=12)
    from agents.board import run_debate
    signals = await run_debate(signals, sector="Intelligence Artificielle")

    from agents.context import load_context
    context    = _prep_signals(signals, 15)
    ctx_str    = load_context(sector="ai", days=14)

    user_prompt = ""
    if ctx_str:
        user_prompt += f"{ctx_str}\n\n"
    user_prompt += f"Voici {len(signals)} signaux IA collectés :\n\n{context}"

    raw    = _call_llm(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_AI, model="claude-sonnet-4-6")
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_ai: fallback activé")
        return _fallback_ai(signals[:3])

    logger.info(f"analyze_ai: {len(result.get('signals', []))} signaux analysés")
    return result


def _degraded_signals(signals: list[dict], limit: int = 3, label: str = "SIGNAL") -> list[dict]:
    """
    Transforme des news brutes en blocs signaux affichables, sans LLM.

    Filet de sécurité : si TOUS les fournisseurs LLM tombent, on préfère afficher
    la news brute (titre + source + lien) plutôt qu'une section vide.
    C'est exactement ce qui manquait à Crypto et Marchés (sections à 0 signal).
    """
    out = []
    for s in signals[:limit]:
        title   = (s.get("title") or label).strip()
        content = (s.get("raw_content") or "").strip()
        out.append({
            "conviction":    2,
            "theme":         s.get("theme"),
            "title":         title[:80].upper(),
            "en_clair":      title[:150],
            "fait":          (content or title)[:500],
            "implication_2": "Analyse automatique indisponible ce matin — news affichée brute.",
            "implication_3": "À lire à la source pour te faire ton avis.",
            "these_opposee": "",
            "action":        "Ouvrir la source et juger par toi-même.",
            "sizing":        "Faible",
            "invalide_si":   "Pas d'analyse automatique disponible pour ce signal.",
            "source_name":   s.get("source_name", ""),
            "source_url":    s.get("source_url", ""),
            "degraded":      True,
        })
    return out


def _fallback_ai(signals: list[dict]) -> dict:
    return {"signals": _degraded_signals(signals, 3, "SIGNAL IA"), "watchlist": []}


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_CRYPTO — Dashboard + Score + Signaux
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_CRYPTO = """Tu es CORTEX, analyste crypto senior pour Badr — investisseur tech avec objectif de longueur d'avance sur le marché.

RÈGLE DE STYLE (PRIORITAIRE) : Badr n'est PAS expert en finance/crypto. Écris simplement, comme à un ami intelligent mais non spécialiste. Chaque terme technique (ex : funding rate, on-chain, TVL, DePIN, perps, dominance...) est expliqué en quelques mots entre parenthèses la PREMIÈRE fois. Phrases courtes. Zéro jargon non expliqué. Quitte à être plus long, sois limpide — la clarté prime sur la concision.

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
      "en_clair": "Résumé en 1 phrase ULTRA-simple, zéro jargon — ce qu'il faut retenir. Max 150 chars.",
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
  "decision": {
    "ticker": "BTC",
    "direction": "LONG",
    "horizon": "2-4 semaines",
    "conviction_pct": 65,
    "reasoning": "Explication concise — max 200 chars"
  },
  "questions": [
    "Question directe sur le signal crypto le plus fort — force un choix. Ex: 'BTC est à $75k avec Fear&Greed à 23, tu achètes maintenant ou tu attends $65k ?' 1 phrase.",
    "Question sur un altcoin ou projet web3 trending — évalue si Badr a compris la thèse. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS exactement 3 signaux dans signals — sélectionne les 3 meilleurs news disponibles
- TOUJOURS exactement 3 trending_alts — si peu de data, choisis les plus pertinents selon le contexte macro
- decision : OBLIGATOIRE — ticker précis (BTC/ETH/SOL/MSTR etc.), direction "LONG" ou "WATCH", conviction 50-90%.
- recommandation.verdict : parmi ACHETER / ACCUMULER / TENIR / ALLÉGER / VENDRE
- recommandation.alts : parmi ACHETER / ACCUMULER / TENIR / ALLÉGER / VENDRE / ATTENDRE
- score values : entiers de -2 à +2 uniquement — JAMAIS de N/A dans les notes
- direction : parmi BULLISH / NEUTRE-BULLISH / NEUTRE / NEUTRE-BEARISH / BEARISH
- magnitude : parmi "forte" / "modérée" / "faible"
- sizing : "Fort", "Moyen" ou "Faible"
- trending_alts.verdict : parmi ACHETER / ACCUMULER / SURVEILLER / EVITER
- Tout en FRANÇAIS — texte brut, zéro markdown
- LIMITES : en_clair=80-150 (obligatoire), fait=500-800 chars, implication_2=200-300, implication_3=200-300, these_opposee=150-250, action=150-200, invalide_si=100-150, recommandation.raisonnement=200-250 chars"""


async def analyze_crypto(data: dict) -> dict:
    """
    Pipeline : Groq (→12) → Board débat (→4) → Claude Sonnet deep analysis.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    signals   = _prefilter_with_groq(signals, sector="crypto/blockchain", max_count=12)
    from agents.board import run_debate
    signals   = await run_debate(signals, sector="Crypto & Web3")
    context   = _prep_signals(signals, 12)

    from agents.context import load_context
    ctx_str = load_context(sector="crypto", days=14)

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
    if ctx_str:
        user_prompt += f"{ctx_str}\n\n"
    user_prompt += "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw    = _call_llm(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_CRYPTO, model="claude-haiku-4-5-20251001")
    result = _parse_json(raw)

    if not result or "score" not in result:
        logger.warning("analyze_crypto: fallback activé")
        return _fallback_crypto(dashboard, signals)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_crypto: direction={result.get('direction')}, "
        f"{len(result.get('signals', []))} signaux"
    )
    return result


def _fallback_crypto(dashboard: dict, signals: list[dict] | None = None) -> dict:
    return {
        "dashboard":     dashboard,
        "phase":         dashboard.get("cycle", {}).get("phase", "N/A"),
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
        "signals":    _degraded_signals(signals or [], 3, "SIGNAL CRYPTO"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_MARKET — Dashboard + Score récession + Régime + Signaux
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_MARKET = """Tu es CORTEX, analyste macro senior pour Badr — investisseur tech.

RÈGLE DE STYLE (PRIORITAIRE) : Badr n'est PAS expert en finance/macro. Écris simplement, comme à un ami intelligent mais non spécialiste. Chaque terme technique (ex : courbe des taux, VIX, DXY, ISM, spread de crédit, régime de marché...) est expliqué en quelques mots entre parenthèses la PREMIÈRE fois. Phrases courtes. Zéro jargon non expliqué. Quitte à être plus long, sois limpide — la clarté prime sur la concision.

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
      "en_clair": "Résumé en 1 phrase ULTRA-simple, zéro jargon — ce qu'il faut retenir. Max 150 chars.",
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
  "decision": {
    "ticker": "SPY",
    "direction": "WATCH",
    "horizon": "1-3 semaines",
    "conviction_pct": 55,
    "reasoning": "Explication concise — max 200 chars"
  },
  "questions": [
    "Question directe sur le macro/marché le plus impactant du jour. 1 phrase, force un choix.",
    "Question sur le risque de récession ou sur un marché spécifique. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS exactement 3 signaux dans signals
- status : "green", "yellow" ou "red" uniquement
- recession_indicators : EXACTEMENT 10 indicateurs
- decision : OBLIGATOIRE — ticker précis (SPY/QQQ/GLD/TLT/MSFT etc.), direction "LONG" ou "WATCH", conviction 50-90%. (courbe_taux, emploi, ism_manuf, ism_services, conso_conf, credit_spread, earnings_rev, pmi_composite, retail_sales, housing)
- recession_score : score = (nb red) + 0.5 × (nb yellow), arrondi sur 10
- regime : parmi "Risk-on", "Risk-off", "Inflation trade", "Stagflation", "Transition"
- sizing : "Fort", "Moyen" ou "Faible"
- Tout en FRANÇAIS — texte brut, zéro markdown
- questions : EXACTEMENT 2 questions en français, directes, basées sur les données macro du jour
- LIMITES : en_clair=80-150 (obligatoire), fait=500-800 chars, implication_2=200-300, implication_3=200-300, these_opposee=150-250, action=150-200, invalide_si=100-150, note récession=60-100"""


async def analyze_market(data: dict) -> dict:
    """
    Pipeline : Groq (→12) → Board débat (→4) → Claude Sonnet deep analysis.
    data = {dashboard: dict, signals: list}
    """
    dashboard = data.get("dashboard", {})
    signals   = data.get("signals", [])
    signals   = _prefilter_with_groq(signals, sector="macro/markets/finance", max_count=12)
    from agents.board import run_debate
    signals   = await run_debate(signals, sector="Marchés & Macro")
    context   = _prep_signals(signals, 12)

    from agents.context import load_context
    ctx_str = load_context(sector="market", days=14)

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

    fred = dashboard.get("fred", {})
    fred_lines = []
    if fred.get("yield_curve_10y2y"):
        d = fred["yield_curve_10y2y"]
        fred_lines.append(f"Courbe taux 10Y-2Y : {d['value']:+.2f}pts (prev {d['prev']:+.2f})")
    if fred.get("jobless_claims"):
        d = fred["jobless_claims"]
        fred_lines.append(f"Jobless claims : {d['value']:,.0f}k ({'+' if d['change']>=0 else ''}{d['change']:.0f}k)")
    if fred.get("housing_starts"):
        d = fred["housing_starts"]
        fred_lines.append(f"Housing starts : {d['value']:,.0f}k annualisé ({'+' if d['change']>=0 else ''}{d['change']:.0f}k)")
    if fred.get("consumer_confidence"):
        d = fred["consumer_confidence"]
        fred_lines.append(f"Consumer confidence : {d['value']:.1f} ({'+' if d['change']>=0 else ''}{d['change']:.1f})")
    if fred.get("retail_sales"):
        d = fred["retail_sales"]
        fred_lines.append(f"Retail sales : ${d['value']:,.0f}M ({'+' if d['change']>=0 else ''}{d['change']:.0f}M)")
    if fred.get("hy_spread"):
        d = fred["hy_spread"]
        fred_lines.append(f"HY credit spread : {d['value']:.2f}% ({'+' if d['change']>=0 else ''}{d['change']:.3f}%)")
    fed_watch = dashboard.get("fed_watch", {})
    if fed_watch.get("fed_hold_prob") is not None:
        fred_lines.append(f"CME FedWatch : {fed_watch['fed_hold_prob']}% maintien / {fed_watch['fed_cut_prob']}% baisse")
    fred_str = "\n".join(fred_lines) if fred_lines else "FRED data indisponible"

    user_prompt = ""
    if ctx_str:
        user_prompt += f"{ctx_str}\n\n"
    user_prompt += "DONNÉES MARCHÉ TEMPS RÉEL :\n" + dash_str
    user_prompt += f"\n\nINDICATEURS MACRO FRED (données officielles US) :\n{fred_str}"
    user_prompt += f"\n\nSIGNAUX NEWS ({len(signals)} collectés) :\n{context}"

    raw    = _call_llm(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_MARKET, model="claude-sonnet-4-6")
    result = _parse_json(raw)

    if not result or "recession_indicators" not in result:
        logger.warning("analyze_market: fallback activé")
        return _fallback_market(dashboard, signals)

    result["dashboard"] = dashboard
    logger.info(
        f"analyze_market: régime={result.get('regime')}, "
        f"récession={result.get('recession_score')}/10"
    )
    return result


def _fallback_market(dashboard: dict, signals: list[dict] | None = None) -> dict:
    neutral = {"status": "yellow", "note": "données indisponibles"}
    return {
        "dashboard": dashboard,
        # Les 10 indicateurs du schéma — le fallback n'en produisait que 7,
        # ce qui cassait le rendu du tableau récession côté dashboard.
        "recession_indicators": {k: neutral for k in [
            "courbe_taux", "emploi", "ism_manuf", "ism_services",
            "conso_conf", "credit_spread", "earnings_rev",
            "pmi_composite", "retail_sales", "housing",
        ]},
        "recession_score": 3,
        "regime":               "Transition",
        "regime_justification": "Analyse automatique indisponible ce matin.",
        "signals":              _degraded_signals(signals or [], 3, "SIGNAL MARCHÉ"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ANALYZE_DEEPTECH — 2 signaux avec crédibilité + investissement
# ══════════════════════════════════════════════════════════════════════════════

_SYSTEM_DEEPTECH = """Tu es CORTEX, analyste deeptech senior pour Badr — investisseur tech.

RÈGLE DE STYLE (PRIORITAIRE) : Badr n'est PAS expert scientifique. Écris simplement, comme à un ami intelligent mais non spécialiste. Chaque terme technique (ex : peer-reviewed, qubit, Series C, early-stage, prototype...) est expliqué en quelques mots entre parenthèses la PREMIÈRE fois. Phrases courtes. Zéro jargon non expliqué. Quitte à être plus long, sois limpide — la clarté prime sur la concision.

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
      "en_clair": "Résumé en 1 phrase ULTRA-simple, zéro jargon — ce qu'il faut retenir. Max 150 chars.",
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
- LIMITES : en_clair=80-150 (obligatoire), fait=500-800 chars, implication_2=200-300, implication_3=200-300, action=150-200, invalide_si=100-150, detail crédibilité=60-120"""


async def analyze_deeptech(signals: list[dict]) -> dict:
    """
    Pipeline : Groq (→10) → Board débat (→4) → Claude Sonnet deep analysis.
    """
    if not signals:
        return {"signals": []}

    signals = _prefilter_with_groq(signals, sector="deeptech/science/research", max_count=10)
    from agents.board import run_debate
    signals = await run_debate(signals, sector="DeepTech & Science")

    from agents.context import load_context
    context = _prep_signals(signals, 10)
    ctx_str = load_context(sector="deeptech", days=14)

    user_prompt = ""
    if ctx_str:
        user_prompt += f"{ctx_str}\n\n"
    user_prompt += f"Voici {len(signals)} signaux deeptech collectés :\n\n{context}"

    raw    = _call_llm(user_prompt, max_tokens=3500, system_prompt=_SYSTEM_DEEPTECH, model="claude-haiku-4-5-20251001")
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_deeptech: fallback activé")
        return _fallback_deeptech(signals[:2])

    logger.info(f"analyze_deeptech: {len(result.get('signals', []))} signaux analysés")
    return result


_SYSTEM_ECOMMERCE = """Tu es CORTEX, analyste e-commerce senior pour Badr — entrepreneur qui vend en ligne et investit dans la tech.

RÈGLE DE STYLE (PRIORITAIRE) : Badr n'est PAS expert en marketing technique. Écris simplement, comme à un ami intelligent mais non spécialiste. Chaque terme technique (ex : ROAS, CPM, délivrabilité, flow, agentic commerce, retail media, LTV...) est expliqué en quelques mots entre parenthèses la PREMIÈRE fois. Phrases courtes. Zéro jargon non expliqué. Quitte à être plus long, sois limpide.

MISSION : à partir des nouveautés e-commerce fournies, produis un briefing ACTIONNABLE pour quelqu'un qui gère une boutique en ligne.
1. Sélectionne EXACTEMENT 3 signaux à fort impact, en couvrant des thèmes DIFFÉRENTS
2. Pour chaque grand thème (automatisation, emailing, créas/publicité, plateformes), donne la nouveauté du jour à retenir
3. Termine par 2 actions concrètes à tester cette semaine

Les 5 thèmes suivis :
  marketplace — Shopify, Amazon, TikTok Shop, Temu, marketplaces, D2C
  automation  — automatisation, agents IA, agentic commerce, no-code, outils
  emailing    — email/SMS marketing, Klaviyo, rétention, délivrabilité, CRM
  creatives   — publicités, créas, UGC, Meta/TikTok Ads, ce qui convertit
  operations  — logistique, paiement, supply chain, fraude, retours

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "tendance_globale": "Ce qui bouge vraiment en e-commerce en ce moment, en 3-4 phrases simples et factuelles. Ce que ça veut dire pour une boutique en ligne aujourd'hui. 250-350 chars.",
  "nouveautes": [
    {
      "theme": "automation",
      "titre": "Titre court de la nouveauté (max 70 chars)",
      "quoi": "Ce que c'est, en une phrase simple et concrète. 100-180 chars.",
      "pourquoi": "Pourquoi ça compte pour une boutique en ligne. 100-180 chars.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ],
  "signals": [
    {
      "conviction": 4,
      "theme": "creatives",
      "title": "TITRE EN MAJUSCULES (max 80 chars)",
      "en_clair": "Résumé en 1 phrase ULTRA-simple, zéro jargon. Max 150 chars.",
      "fait": "Factuel, complet et APPROFONDI : qui, quoi, chiffres, contexte, ce qui change concrètement pour les vendeurs en ligne. Minimum 6 lignes. Texte brut.",
      "implication_2": "Impact direct sur une boutique en ligne : coûts, trafic, conversion, marges. 3-4 phrases.",
      "implication_3": "Qui gagne / qui perd dans l'écosystème (plateformes, marques, agences, outils). 3-4 phrases.",
      "these_opposee": "Meilleur argument contre cette lecture. 2-3 lignes.",
      "action": "Action concrète et spécifique pour Badr — quel outil, quel test, quel délai.",
      "sizing": "Moyen",
      "invalide_si": "Condition précise et mesurable qui invaliderait l'analyse.",
      "source_name": "Source",
      "source_url": "URL"
    }
  ],
  "actions_semaine": [
    "Action concrète et testable cette semaine, avec le résultat attendu. Max 160 chars.",
    "Deuxième action, sur un autre thème. Max 160 chars."
  ],
  "questions": [
    "Question directe qui force Badr à décider sur le sujet e-commerce le plus fort du jour. 1 phrase."
  ]
}

Règles absolues :
- TOUJOURS exactement 3 signaux dans signals, sur 3 thèmes DIFFÉRENTS
- nouveautes : 3 à 5 items, thèmes variés — priorité à automation, emailing et creatives
- theme : uniquement "marketplace", "automation", "emailing", "creatives" ou "operations"
- source_url : reprends l'URL EXACTE fournie dans les signaux, n'invente jamais de lien
- conviction : entier de 1 à 5 | sizing : "Fort", "Moyen" ou "Faible"
- actions_semaine : EXACTEMENT 2 actions
- Tout en FRANÇAIS — texte brut, zéro markdown
- LIMITES : en_clair=80-150, fait=500-800 chars, implication_2=200-300, implication_3=200-300, these_opposee=150-250, action=150-200, invalide_si=100-150"""


async def analyze_ecommerce(data: dict) -> dict:
    """
    Pipeline : Groq (→12) → Board débat (→4) → analyse profonde.
    data = {dashboard: dict, signals: list, themes: dict}
    """
    dashboard = data.get("dashboard", {})
    raw_signals = data.get("signals", [])
    themes = data.get("themes", {})

    if not raw_signals:
        return _fallback_ecommerce(dashboard, [])

    signals = _prefilter_with_groq(raw_signals, sector="ecommerce/retail/marketing", max_count=12)
    from agents.board import run_debate
    signals = await run_debate(signals, sector="E-commerce")
    context = _prep_signals(signals, 12)

    from agents.context import load_context
    ctx_str = load_context(sector="ecommerce", days=14)

    stocks = dashboard.get("stocks", [])
    secteur = dashboard.get("secteur", {})
    dash_lines = [
        f"{s['nom']} ({s['ticker']}) : {s['price']} ({'+' if s['change_pct'] >= 0 else ''}{s['change_pct']}%)"
        for s in stocks[:10]
    ]
    if secteur:
        dash_lines.append(
            f"Secteur : {secteur.get('pct_hausse')}% des actions en hausse — {secteur.get('sentiment')}"
        )
    dash_str = "\n".join(dash_lines) if dash_lines else "Données actions indisponibles"

    themes_str = ", ".join(f"{k}: {v}" for k, v in themes.items()) or "n/a"

    user_prompt = ""
    if ctx_str:
        user_prompt += f"{ctx_str}\n\n"
    user_prompt += "ACTIONS E-COMMERCE COTÉES (aujourd'hui) :\n" + dash_str
    user_prompt += f"\n\nRÉPARTITION DES NOUVEAUTÉS PAR THÈME : {themes_str}"
    user_prompt += f"\n\nNOUVEAUTÉS E-COMMERCE ({len(signals)} retenues) :\n{context}"

    raw = _call_llm(user_prompt, max_tokens=4000, system_prompt=_SYSTEM_ECOMMERCE, model="claude-haiku-4-5-20251001")
    result = _parse_json(raw)

    if not result or "signals" not in result:
        logger.warning("analyze_ecommerce: fallback activé")
        return _fallback_ecommerce(dashboard, signals)

    result["dashboard"] = dashboard
    result["themes"] = themes
    logger.info(
        f"analyze_ecommerce: {len(result.get('signals', []))} signaux, "
        f"{len(result.get('nouveautes', []))} nouveautés"
    )
    return result


def _fallback_ecommerce(dashboard: dict, signals: list[dict] | None = None) -> dict:
    signals = signals or []
    nouveautes = [
        {
            "theme":       s.get("theme", "marketplace"),
            "titre":       s.get("title", "")[:70],
            "quoi":        (s.get("raw_content") or s.get("title", ""))[:180],
            "pourquoi":    "Analyse automatique indisponible — à lire à la source.",
            "source_name": s.get("source_name", ""),
            "source_url":  s.get("source_url", ""),
        }
        for s in signals[:4]
    ]
    return {
        "dashboard":         dashboard,
        "tendance_globale":  "Analyse automatique indisponible ce matin — nouveautés affichées brutes.",
        "nouveautes":        nouveautes,
        "signals":           _degraded_signals(signals, 3, "SIGNAL E-COMMERCE"),
        "actions_semaine":   [],
        "themes":            {},
    }


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


