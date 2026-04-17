"""
CORTEX — DebateBoard v1

Board multi-modeles : 3 IA gratuites debattent sur les signaux,
Claude Sonnet arbitre et selectionne les 3-4 meilleurs.

Pipeline :
  Round 1 — Plaidoirie  : Llama 3.3 + Gemma 2 (Groq) + Gemini 1.5 Pro (Google)
  Round 2 — Debat       : chaque modele soutient ou challenge les picks des autres
  Arbitrage             : Claude Sonnet lit tout le debat et selectionne 3-4 finaux

Modeles gratuits : Llama 3.3 70B + Gemma 2 9B (GROQ_API_KEY) + Gemini 1.5 Pro (GEMINI_API_KEY)
Arbitre payant   : Claude Sonnet (ANTHROPIC_API_KEY)
"""

import os
import json
import re
from utils.logger import get_logger

logger = get_logger("board")


# ── Clients ───────────────────────────────────────────────────────────────────

def _get_groq():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=key)
    except Exception as e:
        logger.warning(f"Groq init echec: {e}")
        return None


def _get_gemini():
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        return genai.GenerativeModel("gemini-1.5-pro")
    except Exception as e:
        logger.warning(f"Gemini init echec: {e}")
        return None


# ── JSON helper ───────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if m:
            text = m.group(1).strip()
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return None


# ── Prompts ───────────────────────────────────────────────────────────────────

def _prompt_round1(signals: list[dict], sector: str, model_name: str) -> str:
    lines = []
    for i, s in enumerate(signals):
        title   = s.get("title", "")[:120]
        src     = s.get("source_name", "?")
        content = s.get("raw_content", "")[:150]
        lines.append(f"[{i}] [{src}] {title}\n    {content}")

    sigs = "\n\n".join(lines)
    return (
        f"Tu es {model_name}, analyste Board CORTEX — secteur {sector}.\n\n"
        f"Voici {len(signals)} signaux collectes. Selectionne tes 3 meilleurs selon :\n"
        f"nouveaute reelle, impact marche, credibilite source, potentiel actionnable.\n\n"
        f"SIGNAUX :\n{sigs}\n\n"
        f"Reponds UNIQUEMENT avec ce JSON (sans markdown) :\n"
        '{{\n'
        '  "picks": [index1, index2, index3],\n'
        '  "arguments": {{\n'
        '    "index1": "Raison factuelle (max 100 chars)",\n'
        '    "index2": "Raison factuelle (max 100 chars)",\n'
        '    "index3": "Raison factuelle (max 100 chars)"\n'
        '  }}\n'
        '}}'
    ).format()


def _prompt_round2(model_name: str, my_picks: dict, others: dict, signals: list[dict]) -> str:
    my_list = []
    for idx in my_picks.get("picks", []):
        title = signals[idx].get("title", "?")[:80] if idx < len(signals) else "?"
        arg   = my_picks.get("arguments", {}).get(str(idx), "")
        my_list.append(f"  [{idx}] {title!r} - {arg}")

    other_list = []
    for other_model, data in others.items():
        if other_model == model_name:
            continue
        for idx in data.get("picks", []):
            title = signals[idx].get("title", "?")[:80] if idx < len(signals) else "?"
            arg   = data.get("arguments", {}).get(str(idx), "")
            other_list.append(f"  {other_model}: [{idx}] {title!r} - {arg}")

    return (
        f"Tu es {model_name}, Round 2 Board CORTEX.\n\n"
        f"TES PICKS :\n" + "\n".join(my_list) + "\n\n"
        f"PICKS DES AUTRES :\n" + "\n".join(other_list) + "\n\n"
        f"SUPPORTER (accord) ou CHALLENGER (desaccord factuel) les picks des autres.\n\n"
        'Reponds UNIQUEMENT avec ce JSON (sans markdown) :\n'
        '{\n'
        '  "support": [indices que tu soutiens],\n'
        '  "challenge": {"index": "raison (max 80 chars)"},\n'
        '  "defend": {"index": "defense de ton pick (max 80 chars)"}\n'
        '}'
    )


def _prompt_arbitrage(signals: list[dict], sector: str, round1: dict, round2: dict) -> str:
    sig_lines = "\n".join(
        f"[{i}] [{s.get('source_name','?')}] {s.get('title','')[:100]}"
        for i, s in enumerate(signals)
    )

    r1 = []
    for model, data in round1.items():
        r1.append(f"\n{model}:")
        for idx in data.get("picks", []):
            title = signals[idx].get("title", "?")[:60] if idx < len(signals) else "?"
            arg   = data.get("arguments", {}).get(str(idx), "")
            r1.append(f"  [{idx}] {title}: {arg}")

    r2 = []
    for model, data in round2.items():
        supports   = data.get("support", [])
        challenges = data.get("challenge", {})
        r2.append(f"\n{model}:")
        if supports:
            r2.append(f"  Soutient: {supports}")
        for idx, reason in challenges.items():
            r2.append(f"  Challenge [{idx}]: {reason}")

    return (
        f"Tu es Claude Sonnet, arbitre Board CORTEX — secteur {sector}.\n\n"
        f"Selectionne les 3-4 signaux les plus robustes (consensus + arguments solides).\n\n"
        f"SIGNAUX :\n{sig_lines}\n\n"
        f"ROUND 1 :\n" + "\n".join(r1) + "\n\n"
        f"ROUND 2 :\n" + "\n".join(r2) + "\n\n"
        'Reponds UNIQUEMENT avec ce JSON (sans markdown) :\n'
        '{\n'
        '  "selected_indices": [3-4 indices retenus],\n'
        '  "consensus_scores": {"index": score_0_a_3},\n'
        '  "reasoning": "Synthese arbitrage en 1-2 lignes"\n'
        '}'
    )


# ── Appels ────────────────────────────────────────────────────────────────────

def _call_groq(prompt: str, model: str) -> dict | None:
    client = _get_groq()
    if not client:
        return None
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0,
        )
        return _extract_json(resp.choices[0].message.content)
    except Exception as e:
        logger.warning(f"Groq [{model}] echec: {e}")
        return None


def _call_gemini(prompt: str) -> dict | None:
    model = _get_gemini()
    if not model:
        return None
    try:
        resp = model.generate_content(prompt)
        return _extract_json(resp.text)
    except Exception as e:
        logger.warning(f"Gemini Pro echec: {e}")
        return None


def _call_claude_arbitre(prompt: str) -> dict | None:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_json(resp.content[0].text)
    except Exception as e:
        logger.warning(f"Claude arbitre echec: {e}")
        return None


# ── Board ─────────────────────────────────────────────────────────────────────

BOARD_MODELS = {
    "Llama 3.3":  lambda p: _call_groq(p, "llama-3.3-70b-versatile"),
    "Gemma 2":    lambda p: _call_groq(p, "gemma2-9b-it"),
    "Gemini Pro": lambda p: _call_gemini(p),
}


def _validate_picks(result: dict | None, n: int) -> list[int]:
    if not result:
        return []
    return [i for i in result.get("picks", []) if isinstance(i, int) and 0 <= i < n][:3]


def _vote_fallback(round1: dict, n: int, top_k: int = 4) -> list[int]:
    votes: dict[int, int] = {}
    for data in round1.values():
        for idx in data.get("picks", []):
            if isinstance(idx, int) and 0 <= idx < n:
                votes[idx] = votes.get(idx, 0) + 1
    return [i for i, _ in sorted(votes.items(), key=lambda x: x[1], reverse=True)][:top_k]


async def run_debate(signals: list[dict], sector: str) -> list[dict]:
    """
    Lance le debat multi-modeles sur les signaux pre-filtres.

    Args:
        signals : signaux apres Groq pre-filter (~12)
        sector  : nom du secteur pour les prompts

    Returns:
        Les 3-4 signaux selectionnes par consensus.
        Fallback sur signals[:4] si echec total.
    """
    n = len(signals)
    if n <= 4:
        logger.info(f"Board [{sector}]: {n} signaux <= 4, debat inutile")
        return signals

    logger.info(f"Board [{sector}]: debat sur {n} signaux")

    # Round 1
    round1: dict[str, dict] = {}
    for model_name, call_fn in BOARD_MODELS.items():
        result = call_fn(_prompt_round1(signals, sector, model_name))
        valid  = _validate_picks(result, n)
        if valid and result:
            result["picks"] = valid
            round1[model_name] = result
            logger.info(f"  {model_name} R1 picks: {valid}")
        else:
            logger.warning(f"  {model_name} R1: invalide")

    if not round1:
        logger.warning(f"Board [{sector}]: Round 1 vide — fallback")
        return signals[:4]

    # Round 2
    round2: dict[str, dict] = {}
    for model_name, call_fn in BOARD_MODELS.items():
        if model_name not in round1:
            continue
        result = call_fn(_prompt_round2(model_name, round1[model_name], round1, signals))
        if result:
            round2[model_name] = result

    # Arbitrage Claude Sonnet
    arbitrage = _call_claude_arbitre(_prompt_arbitrage(signals, sector, round1, round2))

    if arbitrage and "selected_indices" in arbitrage:
        selected_indices = [i for i in arbitrage["selected_indices"] if isinstance(i, int) and 0 <= i < n][:4]
        logger.info(f"Board [{sector}] arbitrage: {selected_indices} | {arbitrage.get('reasoning','')[:100]}")
    else:
        logger.warning(f"Board [{sector}]: arbitrage echec — vote simple")
        selected_indices = _vote_fallback(round1, n)

    selected = [signals[i] for i in selected_indices if 0 <= i < n]
    if not selected:
        return signals[:4]

    logger.info(f"Board [{sector}]: {n} -> {len(selected)} signaux retenus")
    return selected
