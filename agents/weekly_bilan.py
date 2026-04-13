"""
CORTEX — Bilan hebdomadaire (Dimanche 20:00)

Boucle d'apprentissage :
  1. Récupère les questions de la semaine + réponses de Badr
  2. Récupère les signaux/prédictions de la semaine
  3. Vérifie ce qui s'est réalisé (prix, events)
  4. Claude Sonnet évalue : avait-il raison ? Quels patterns ?
  5. Sauvegarde les learnings → alimentent les agents la semaine suivante
  6. Envoie le Bilan Dimanche sur Telegram (HTML)

Objectif : Badr devient de plus en plus intelligent semaine après semaine.
"""

import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from utils.logger import get_logger

logger = get_logger("weekly_bilan")

_DAYS_FR   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
_MONTHS_FR = [
    "Janvier","Février","Mars","Avril","Mai","Juin",
    "Juillet","Août","Septembre","Octobre","Novembre","Décembre",
]

SEP = "━━━━━━━━━━━━━━━━━━━━━━━━"
MED = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"


# ── Prompt Claude pour l'évaluation hebdomadaire ──────────────────────────────

_SYSTEM_BILAN = """Tu es CORTEX, coach intellectuel et conseiller d'investissement de Badr.

MISSION DIMANCHE : Analyse la semaine de Badr — ses réponses, ses biais, ce qu'il a bien vu et mal vu.
Ton rôle est de le rendre plus intelligent semaine après semaine.

DONNÉES FOURNIES :
- Questions posées chaque matin + réponses de Badr
- Signaux de la semaine avec leurs prédictions directionnelles
- Mouvements de prix réels observés

RÈGLES D'ÉVALUATION :
- Sois honnête et direct — pas de compliments vides
- Si Badr a eu raison mais pour les mauvaises raisons : "partiel"
- La "bonne réponse" doit expliquer le raisonnement complet, pas juste le résultat
- Les patterns doivent être spécifiques ("tu as tendance à...") pas vagues
- Les learnings doivent être actionnables la semaine prochaine

Réponds UNIQUEMENT avec ce JSON valide (sans markdown) :
{
  "score": {
    "correct": 0,
    "partiel": 0,
    "incorrect": 0,
    "total": 0,
    "taux_reussite": 0
  },
  "evaluations": [
    {
      "date": "Lundi 07 Avril",
      "question": "...",
      "reponse_badr": "...",
      "verdict": "correct",
      "reponse_correcte": "Ce qu'il fallait dire et pourquoi — 3-4 lignes",
      "pourquoi": "Le raisonnement clé derrière la bonne réponse — 2 lignes",
      "learning": "Ce que cette situation enseigne — 1 ligne actionnable"
    }
  ],
  "patterns": [
    "Pattern de pensée détecté #1 — spécifique et actionnable",
    "Pattern de pensée détecté #2"
  ],
  "signal_manque": "Signal important de la semaine que Badr n'a pas bien vu",
  "meilleur_coup": "Meilleure analyse ou prédiction de Badr cette semaine",
  "learnings_cles": [
    "Learning #1 à appliquer dès lundi prochain",
    "Learning #2 à appliquer dès lundi prochain",
    "Learning #3 à appliquer dès lundi prochain"
  ],
  "focus_semaine": "Une seule chose sur laquelle Badr doit se concentrer la semaine prochaine"
}

Règles absolues :
- verdict : exactement "correct", "partiel" ou "incorrect"
- taux_reussite : (correct + partiel*0.5) / total * 100, arrondi entier
- Tout en FRANÇAIS
- Texte brut dans toutes les valeurs string (pas de markdown)
- evaluations : uniquement les jours où Badr a répondu (ignorer les jours sans réponse)"""


# ── Récupération des données de la semaine ────────────────────────────────────

async def _get_week_data() -> dict:
    """Récupère journal + analyses + mouvements de prix de la semaine."""
    try:
        from database.client import get_week_journal, get_week_analyses
        journal, analyses = await asyncio.gather(
            get_week_journal(days_back=7),
            get_week_analyses(days_back=7),
        )
    except Exception as e:
        logger.warning(f"Erreur récupération données semaine: {e}")
        journal, analyses = [], []

    # Prix BTC semaine (CoinGecko gratuit)
    btc_weekly = await _fetch_btc_weekly()

    # Signaux clés de la semaine (top signal par secteur par jour)
    signals_summary = _summarize_analyses(analyses)

    return {
        "journal":         journal,
        "analyses":        analyses,
        "signals_summary": signals_summary,
        "btc_weekly":      btc_weekly,
    }


async def _fetch_btc_weekly() -> dict:
    """Prix BTC sur 7 jours pour évaluer les prédictions crypto."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                params={"vs_currency": "usd", "days": "7", "interval": "daily"},
                timeout=10,
            )
            data   = r.json()
            prices = data.get("prices", [])
            if len(prices) >= 2:
                start = prices[0][1]
                end   = prices[-1][1]
                chg   = (end - start) / start * 100
                return {
                    "start_price": round(start),
                    "end_price":   round(end),
                    "change_pct":  round(chg, 1),
                    "direction":   "hausse" if chg > 2 else ("baisse" if chg < -2 else "stable"),
                }
    except Exception as e:
        logger.debug(f"BTC weekly: {e}")
    return {}


def _summarize_analyses(analyses: list) -> str:
    """Résume les signaux de la semaine pour le contexte Claude."""
    if not analyses:
        return "Aucune analyse disponible cette semaine."

    lines = []
    by_date = {}
    for a in analyses:
        date = a.get("report_date", "")
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(a)

    for date in sorted(by_date.keys()):
        day_analyses = by_date[date]
        day_lines = [f"\n--- {date} ---"]
        for a in day_analyses:
            sector = a.get("sector", "")
            data   = a.get("analysis_json", {})
            signals = data.get("signals", [])
            if signals:
                top = signals[0]
                direction = data.get("direction", "")
                regime    = data.get("regime", "")
                context   = direction or regime or ""
                day_lines.append(
                    f"[{sector.upper()}] {top.get('title','')[:80]}"
                    + (f" | {context}" if context else "")
                )
        lines.extend(day_lines)

    return "\n".join(lines)


# ── Appel Claude Sonnet pour l'évaluation ────────────────────────────────────

def _call_claude_bilan(journal: list, signals_summary: str, btc_weekly: dict) -> dict | None:
    """Appel Claude Sonnet pour évaluer la semaine."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Formater le journal
        journal_text = ""
        for entry in journal:
            date_raw = entry.get("created_at", "")[:10]
            question = entry.get("question_asked", "")
            response = entry.get("your_response", "")
            if question and response:
                journal_text += f"\nQuestion : {question}\nRéponse de Badr : {response}\n"

        if not journal_text.strip():
            journal_text = "Badr n'a pas répondu aux questions cette semaine."

        btc_str = ""
        if btc_weekly:
            btc_str = (
                f"\nBTC semaine : ${btc_weekly.get('start_price','?'):,} → "
                f"${btc_weekly.get('end_price','?'):,} "
                f"({btc_weekly.get('change_pct','?')}%) — {btc_weekly.get('direction','')}"
            )

        user_prompt = (
            f"JOURNAL DE LA SEMAINE :\n{journal_text}\n\n"
            f"SIGNAUX ET PRÉDICTIONS :\n{signals_summary}\n"
            f"{btc_str}"
        )

        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
            system=[{
                "type": "text",
                "text": _SYSTEM_BILAN,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = resp.content[0].text.strip()

        # Parse JSON
        if "```" in raw:
            match = re.search(r"```(?:json)?\s*([\s\S]+?)```", raw)
            if match:
                raw = match.group(1).strip()
        return json.loads(raw)

    except Exception as e:
        logger.error(f"Claude bilan error: {e}")
        return None


# ── Sauvegarde des learnings ──────────────────────────────────────────────────

async def _save_learnings(evaluation: dict) -> None:
    """Sauvegarde les learnings dans agent_learnings pour alimenter les agents."""
    from database.client import save_learning
    week_of = (datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d")

    # Learnings globaux
    for learning in evaluation.get("learnings_cles", []):
        if learning:
            await save_learning(
                week_of=week_of,
                sector="global",
                learning=learning,
            )

    # Pattern détecté
    patterns = evaluation.get("patterns", [])
    for pattern in patterns:
        if pattern:
            await save_learning(
                week_of=week_of,
                sector="global",
                learning=pattern,
                pattern=pattern,
            )

    # Learnings par évaluation
    for ev in evaluation.get("evaluations", []):
        learning = ev.get("learning", "")
        if learning:
            sector = "global"
            title  = ev.get("question", "")[:80]
            mat    = ev.get("verdict") == "correct"
            await save_learning(
                week_of=week_of,
                sector=sector,
                learning=learning,
                signal_title=title,
                materialized=mat,
            )

    logger.info(f"Learnings sauvegardés pour la semaine du {week_of}")


# ── Construction du message Telegram ─────────────────────────────────────────

def _build_bilan_message(evaluation: dict, btc_weekly: dict) -> str:
    """Construit le message HTML du bilan du dimanche."""
    now = datetime.now()
    week_start = now - timedelta(days=6)
    date_range = (
        f"{week_start.day} {_MONTHS_FR[week_start.month-1]} "
        f"→ {now.day} {_MONTHS_FR[now.month-1]} {now.year}"
    )

    def _h(t) -> str:
        return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    score  = evaluation.get("score", {})
    total  = score.get("total", 0)
    ok     = score.get("correct", 0)
    part   = score.get("partiel", 0)
    nok    = score.get("incorrect", 0)
    taux   = score.get("taux_reussite", 0)

    # Couleur du taux
    if taux >= 70:   score_icon = "🟢"
    elif taux >= 45: score_icon = "🟡"
    else:            score_icon = "🔴"

    lines = [
        SEP,
        "<b>🧠 CORTEX — BILAN DE SEMAINE</b>",
        f"<i>📅 {_h(date_range)}</i>",
        "<i>Tes prédictions, tes biais, ce que tu aurais dû voir.</i>",
        SEP,
        "",
        f"<b>📊 Score de la semaine</b>",
        "",
        f"  {score_icon} <b>Taux de réussite : {taux}%</b>",
        f"  ✅ Correct : {ok}  |  🟡 Partiel : {part}  |  ❌ Incorrect : {nok}",
        f"  Total : {total} question(s) analysée(s)",
    ]

    # BTC
    if btc_weekly:
        btc_dir = btc_weekly.get("direction", "")
        btc_chg = btc_weekly.get("change_pct", 0)
        btc_col = "🟢" if btc_chg > 0 else "🔴"
        lines += [
            "",
            f"  {btc_col} BTC cette semaine : {'+' if btc_chg > 0 else ''}{btc_chg}% "
            f"(${btc_weekly.get('start_price',0):,} → ${btc_weekly.get('end_price',0):,})",
        ]

    # Évaluations par jour
    evaluations = evaluation.get("evaluations", [])
    if evaluations:
        lines += ["", MED, "", "<b>📅 Analyse jour par jour</b>", ""]
        for ev in evaluations:
            date    = _h(ev.get("date", ""))
            verdict = ev.get("verdict", "")
            v_icon  = {"correct": "✅", "partiel": "🟡", "incorrect": "❌"}.get(verdict, "❓")

            lines += [
                f"{v_icon} <b>{date}</b>",
                f"<i>Question : {_h(ev.get('question',''))}</i>",
                f"Ta réponse : {_h(ev.get('reponse_badr',''))}",
                "",
                f"<b>La bonne réponse :</b>",
                _h(ev.get("reponse_correcte", "")),
                "",
                f"<b>Pourquoi :</b> <i>{_h(ev.get('pourquoi',''))}</i>",
                f"<b>→ Retenir :</b> {_h(ev.get('learning',''))}",
                "",
            ]

    # Patterns
    patterns = evaluation.get("patterns", [])
    if patterns:
        lines += [MED, "", "<b>🔍 Tes angles morts cette semaine</b>", ""]
        for p in patterns:
            lines.append(f"  ⚠️ {_h(p)}")
        lines.append("")

    # Meilleur coup / Signal manqué
    coup   = evaluation.get("meilleur_coup", "")
    manque = evaluation.get("signal_manque", "")
    if coup or manque:
        lines += [MED, ""]
        if coup:
            lines += [f"<b>🏆 Ta meilleure analyse :</b>", f"<i>{_h(coup)}</i>", ""]
        if manque:
            lines += [f"<b>📉 Ce que tu as manqué :</b>", f"<i>{_h(manque)}</i>", ""]

    # Learnings clés
    learnings = evaluation.get("learnings_cles", [])
    if learnings:
        lines += [MED, "", "<b>📚 À retenir pour la semaine prochaine</b>", ""]
        for i, l in enumerate(learnings, 1):
            lines.append(f"  <b>{i}.</b> {_h(l)}")
        lines.append("")

    # Focus semaine prochaine
    focus = evaluation.get("focus_semaine", "")
    if focus:
        lines += [
            MED,
            "",
            "<b>🎯 Ton focus de la semaine prochaine</b>",
            "",
            f"<b>{_h(focus)}</b>",
            "",
        ]

    lines += [SEP]
    return "\n".join(lines)


# ── Point d'entrée principal ──────────────────────────────────────────────────

async def run_weekly_bilan() -> None:
    """
    Lance le bilan hebdomadaire complet.
    Appelé le dimanche à 20:00 par le scheduler.
    """
    logger.info("=" * 55)
    logger.info("CORTEX — Bilan hebdomadaire démarré")
    logger.info("=" * 55)

    # 1. Récupérer les données
    data = await _get_week_data()
    journal         = data["journal"]
    signals_summary = data["signals_summary"]
    btc_weekly      = data["btc_weekly"]

    logger.info(f"  {len(journal)} entrées journal, BTC {btc_weekly.get('change_pct','?')}%")

    # 2. Évaluation Claude Sonnet
    evaluation = await asyncio.to_thread(
        _call_claude_bilan, journal, signals_summary, btc_weekly
    )

    if not evaluation:
        # Fallback minimal si Claude échoue
        evaluation = {
            "score":          {"correct": 0, "partiel": 0, "incorrect": 0, "total": 0, "taux_reussite": 0},
            "evaluations":    [],
            "patterns":       [],
            "learnings_cles": ["Données insuffisantes cette semaine pour une analyse complète."],
            "focus_semaine":  "Continue à répondre aux questions du matin pour activer l'apprentissage.",
        }

    # 3. Sauvegarder les learnings
    await _save_learnings(evaluation)
    logger.info("Learnings sauvegardés dans agent_learnings")

    # 4. Construire et envoyer le message
    msg = _build_bilan_message(evaluation, btc_weekly)

    try:
        from tgbot.bot import send_message
        await send_message(msg, parse_mode="HTML")
        logger.info(f"Bilan hebdo envoyé ({len(msg)} chars)")
    except Exception as e:
        logger.error(f"Erreur envoi bilan: {e}")

    logger.info("=" * 55)
    logger.info("CORTEX — Bilan hebdomadaire terminé")
    logger.info("=" * 55)
