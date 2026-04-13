"""
CORTEX — Orchestrateur Rapport du Matin v2
5 messages Telegram séquentiels :
  MSG 1 : 🧠 Intelligence Artificielle
  MSG 2 : 💰 Crypto & Web3
  MSG 3 : 📈 Marchés & Macro
  MSG 4 : ⚡ DeepTech & Ruptures
  MSG 5 : 🔗 Nexus + Scorecard + Question

Format strict selon CORTEX Design System (mobile-first, emojis comme palette).
"""

import asyncio
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger("morning_report")

# ── Constantes de design ───────────────────────────────────────────────────────
SEP_HEAVY  = "━━━━━━━━━━━━━━━━━━━━━━━━"
SEP_MED    = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
SEP_LIGHT  = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"

NUMS = ["❶", "❷", "❸"]

_DAYS_FR   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
_MONTHS_FR = [
    "Janvier","Février","Mars","Avril","Mai","Juin",
    "Juillet","Août","Septembre","Octobre","Novembre","Décembre",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fr_date() -> str:
    now = datetime.now()
    return f"{_DAYS_FR[now.weekday()]} {now.day} {_MONTHS_FR[now.month - 1]} {now.year}"


def _stars(n: int) -> str:
    n = max(1, min(5, int(n)))
    return "★" * n + "☆" * (5 - n)


def _sizing_emoji(sizing: str) -> str:
    m = {"Fort": "🟢", "Moyen": "🟡", "Faible": "🔴"}
    color = m.get(sizing, "🟡")
    return f"{color} {sizing}"


def _direction_color(direction: str) -> str:
    d = direction.upper()
    if "BEARISH" in d and "NEUTRE" not in d:  return "🔴"
    if "BULLISH" in d and "NEUTRE" not in d:  return "🟢"
    return "🟡"


def _indicator_emoji(status: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "🟡")


def _horizon_emoji(horizon: str) -> str:
    return {
        "1-2":  "🔴 1-2 ans",
        "3-5":  "🟡 3-5 ans",
        "5-10": "🟢 5-10 ans",
        "10+":  "⚪ 10+ ans",
    }.get(horizon, "🟡 ?")


def _arrow(change_pct: float) -> str:
    return "▴" if change_pct >= 0 else "▾"


def _fmt_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def _signal_block_ai(sig: dict, num: str) -> str:
    """Construit le bloc d'un signal IA (format exact)."""
    stars   = _stars(sig.get("conviction", 3))
    title   = sig.get("title", "SIGNAL").upper()
    fait    = sig.get("fait", "")
    impl2   = sig.get("implication_2", "")
    impl3   = sig.get("implication_3", "")
    these   = sig.get("these_opposee", "")
    action  = sig.get("action", "")
    sizing  = _sizing_emoji(sig.get("sizing", "Moyen"))
    inv     = sig.get("invalide_si", "")
    src_n   = sig.get("source_name", "Source")
    src_u   = sig.get("source_url", "")

    src_line = f"[{src_n}]({src_u})" if src_u else src_n

    lines = [
        f"{stars} {num} {title}",
        "",
        "📌 Ce qui se passe :",
        fait,
        "",
        "🧩 Implications :",
        f"→ Ordre 2 : {impl2}",
        f"→ Ordre 3 : {impl3}",
    ]

    if these and these != "N/A":
        lines += ["", "🔄 Thèse opposée :", these]

    lines += [
        "",
        "🎯 Action :",
        f"▸ Faire : {action}",
        f"▸ Sizing : {sizing}",
        f"▸ Invalide si : {inv}",
        "",
        f"🔗 {src_line}",
    ]

    return "\n".join(lines)


def _signal_block_generic(sig: dict, num: str, include_these: bool = True) -> str:
    """Bloc signal générique (Crypto / Market) — même structure que IA."""
    return _signal_block_ai(sig, num)


def _signal_block_deeptech(sig: dict, num: str) -> str:
    """Bloc signal DeepTech avec crédibilité + angle investissement."""
    stars   = _stars(sig.get("conviction", 3))
    title   = sig.get("title", "SIGNAL").upper()
    horizon = _horizon_emoji(sig.get("horizon", "3-5"))
    fait    = sig.get("fait", "")
    impl2   = sig.get("implication_2", "")
    impl3   = sig.get("implication_3", "")
    action  = sig.get("action", "")
    sizing  = _sizing_emoji(sig.get("sizing", "Faible"))
    inv     = sig.get("invalide_si", "")
    src_n   = sig.get("source_name", "Source")
    src_u   = sig.get("source_url", "")
    src_line = f"[{src_n}]({src_u})" if src_u else src_n

    # Crédibilité
    cred_score = sig.get("credibilite_score", 0)
    cred_lines = [
        f"▸ Peer-reviewed {'✓' if sig.get('peer_reviewed') else '✗'}"
        + (f" — {sig['peer_reviewed_detail']}" if sig.get('peer_reviewed_detail') else ""),
        f"▸ Financement {'✓' if sig.get('financement') else '✗'}"
        + (f" — {sig['financement_detail']}" if sig.get('financement_detail') else ""),
        f"▸ Prototype {'✓' if sig.get('prototype') else '✗'}"
        + (f" — {sig['prototype_detail']}" if sig.get('prototype_detail') else ""),
        f"▸ Adoption industrielle {'✓' if sig.get('adoption') else '✗'}"
        + (f" — {sig['adoption_detail']}" if sig.get('adoption_detail') else ""),
    ]

    # Angle investissement
    cotes  = sig.get("investissement_cotes", [])
    etfs   = sig.get("investissement_etf", [])
    early  = sig.get("investissement_early", [])
    inv_lines = []
    if cotes:  inv_lines.append(f"▸ Cotés : {', '.join(cotes)}")
    if etfs:   inv_lines.append(f"▸ ETF : {', '.join(etfs)}")
    if early:  inv_lines.append(f"▸ Early-stage : {', '.join(early)}")
    if not inv_lines:
        inv_lines.append("▸ Pas d'exposition directe identifiée")

    lines = [
        f"{stars} {num} {title}",
        f"🕐 Horizon : {horizon}",
        "",
        "📌 Ce qui se passe :",
        fait,
        "",
        "🧩 Implications :",
        f"→ Ordre 2 : {impl2}",
        f"→ Ordre 3 : {impl3}",
        "",
        f"✅ Crédibilité : {cred_score}/4",
    ] + cred_lines + [
        "",
        "💰 Angle investissement :",
    ] + inv_lines + [
        "",
        "🎯 Action :",
        f"▸ Faire : {action}",
        f"▸ Sizing : {sizing}",
        f"▸ Invalide si : {inv}",
        "",
        f"🔗 {src_line}",
    ]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 1 — INTELLIGENCE ARTIFICIELLE
# ══════════════════════════════════════════════════════════════════════════════

def build_msg1(ai_data: dict) -> str:
    signals   = ai_data.get("signals", [])[:3]
    watchlist = ai_data.get("watchlist", [])

    lines = [
        SEP_HEAVY,
        "🧠  C O R T E X  —  I A",
        f"📅 {_fr_date()}",
        SEP_HEAVY,
    ]

    if not signals:
        lines += ["", "_Aucun signal IA majeur aujourd'hui._"]
    else:
        for i, sig in enumerate(signals):
            if i > 0:
                lines += ["", SEP_MED, ""]
            lines += ["", _signal_block_ai(sig, NUMS[i])]

    # Watchlist
    if watchlist:
        lines += ["", SEP_LIGHT, "", "📡 WATCHLIST"]
        for item in watchlist[:3]:
            lines.append(f"◦ {item}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 2 — CRYPTO & WEB3
# ══════════════════════════════════════════════════════════════════════════════

def build_msg2(crypto_data: dict) -> str:
    dashboard = crypto_data.get("dashboard", {})
    phase     = crypto_data.get("phase", "N/A")
    vol_30d   = crypto_data.get("volume_vs_30d", "N/A")
    score     = crypto_data.get("score", {})
    direction = crypto_data.get("direction", "NEUTRE")
    magnitude = crypto_data.get("magnitude", "faible")
    bear_case = crypto_data.get("bear_case", "N/A")
    signals   = crypto_data.get("signals", [])[:3]

    # BTC price line
    btc_p  = dashboard.get("btc_price")
    btc_c  = dashboard.get("btc_change_24h", 0)
    btc_line = f"${btc_p:,.0f} {_arrow(btc_c)} {_fmt_pct(btc_c)}" if btc_p else "N/A"

    dir_color = _direction_color(direction)

    def _score_line(key: str, label: str, weight: str) -> str:
        s = score.get(key, {})
        val = s.get("value", 0)
        sign = "+" if val > 0 else ""
        return f"{label} ({weight}) ▸ {sign}{val}"

    lines = [
        SEP_HEAVY,
        "💰 C O R T E X  —  C R Y P T O",
        f"📅 {_fr_date()}",
        SEP_HEAVY,
        "",
        "📊 DASHBOARD",
        "",
        f"BTC      ▸ {btc_line}",
        f"Phase    ▸ {phase}",
        f"F&G      ▸ {dashboard.get('fear_greed_score', 'N/A')} — {dashboard.get('fear_greed_label', 'N/A')}",
        f"BTC dom. ▸ {dashboard.get('btc_dominance', 'N/A')}%",
        f"Funding  ▸ {dashboard.get('funding_description', 'N/A')}",
        f"Vol. 24h ▸ {vol_30d}",
        "",
        SEP_LIGHT,
        "",
        "📐 SCORE DE DIRECTION",
        "",
        _score_line("onchain",   "On-chain  ", "25%"),
        _score_line("cycle",     "Cycle     ", "25%"),
        _score_line("macro",     "Macro     ", "20%"),
        _score_line("sentiment", "Sentiment ", "15%"),
        _score_line("momentum",  "Momentum  ", "15%"),
        "",
        f"→ {dir_color} {direction} ({magnitude})",
        "",
        f"🔄 Invalide si : {bear_case}",
    ]

    if signals:
        for i, sig in enumerate(signals):
            lines += ["", SEP_MED, "", _signal_block_generic(sig, NUMS[i])]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 3 — MARCHÉS & MACRO
# ══════════════════════════════════════════════════════════════════════════════

def build_msg3(market_data: dict) -> str:
    dashboard = market_data.get("dashboard", {})
    rec_ind   = market_data.get("recession_indicators", {})
    rec_score = market_data.get("recession_score", 0)
    regime    = market_data.get("regime", "N/A")
    regime_j  = market_data.get("regime_justification", "")
    signals   = market_data.get("signals", [])[:3]

    def _dash_line(key: str, label: str) -> str:
        d = dashboard.get(key, {})
        price = d.get("price", "N/A")
        chg   = d.get("change_pct", 0)
        if key == "vix":
            interp = d.get("interpretation", "")
            return f"{label} ▸ {price} — {interp}"
        if key == "us_10y":
            bps = d.get("change_bps", "")
            return f"{label} ▸ {price} {bps}"
        arr  = _arrow(chg)
        pct  = _fmt_pct(chg)
        return f"{label} ▸ {price} {arr} {pct}"

    def _rec_line(key: str, label: str) -> str:
        ind = rec_ind.get(key, {})
        emoji = _indicator_emoji(ind.get("status", "yellow"))
        note  = ind.get("note", "")
        return f"{emoji} {label} — {note}"

    lines = [
        SEP_HEAVY,
        "📈 C O R T E X  —  M A R C H É S",
        f"📅 {_fr_date()}",
        SEP_HEAVY,
        "",
        "📊 DASHBOARD",
        "",
        _dash_line("sp500",  "S&P 500"),
        _dash_line("nasdaq", "Nasdaq "),
        _dash_line("gold",   "Or     "),
        _dash_line("oil",    "Pétrole"),
        _dash_line("dxy",    "DXY    "),
        _dash_line("vix",    "VIX    "),
        _dash_line("us_10y", "US 10Y "),
        "",
        SEP_LIGHT,
        "",
        f"⚠️ RISQUE RÉCESSION : {rec_score}/10",
        "",
        _rec_line("courbe_taux",   "Courbe des taux"),
        _rec_line("emploi",        "Emploi         "),
        _rec_line("ism_manuf",     "ISM Manuf.     "),
        _rec_line("ism_services",  "ISM Services   "),
        _rec_line("conso_conf",    "Conso. conf.   "),
        _rec_line("credit_spread", "Credit spreads "),
        _rec_line("earnings_rev",  "Earnings rev.  "),
        "",
        SEP_LIGHT,
        "",
        f"🏛️ RÉGIME : {regime}",
        "",
        regime_j,
    ]

    if signals:
        for i, sig in enumerate(signals):
            lines += ["", SEP_MED, "", _signal_block_generic(sig, NUMS[i])]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 4 — DEEPTECH & RUPTURES
# ══════════════════════════════════════════════════════════════════════════════

def build_msg4(deeptech_data: dict) -> str:
    signals = deeptech_data.get("signals", [])[:2]

    lines = [
        SEP_HEAVY,
        "⚡ C O R T E X  —  D E E P T E C H",
        f"📅 {_fr_date()}",
        SEP_HEAVY,
    ]

    if not signals:
        lines += ["", "_Aucun signal deeptech majeur aujourd'hui._"]
    else:
        for i, sig in enumerate(signals):
            if i > 0:
                lines += ["", SEP_MED]
            lines += ["", _signal_block_deeptech(sig, NUMS[i])]

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 5 — NEXUS + SCORECARD + QUESTION
# ══════════════════════════════════════════════════════════════════════════════

def build_msg5(nexus_data: dict, scorecard_data: dict | None = None) -> str:
    has_conn  = nexus_data.get("has_connexion", False)
    connexion = nexus_data.get("connexion", "")
    secteurs  = nexus_data.get("secteurs_lies", [])
    question  = nexus_data.get("question", "Quel est ton focus aujourd'hui ?")

    lines = [
        SEP_HEAVY,
        "🔗 C O R T E X  —  N E X U S",
        f"📅 {_fr_date()}",
        SEP_HEAVY,
        "",
        "🔗 CONNEXION DU JOUR",
        "",
    ]

    if has_conn and connexion:
        if secteurs:
            lines.append(f"_{' × '.join(secteurs)}_")
            lines.append("")
        lines.append(connexion)
    else:
        lines.append("_Pas de connexion significative aujourd'hui._")

    # Scorecard (lundi uniquement)
    if scorecard_data:
        lines += [
            "",
            SEP_LIGHT,
            "",
            "📊 SCORECARD",
            "",
        ]
        week  = scorecard_data.get("week_label", "")
        total = scorecard_data.get("total", 0)
        conf  = scorecard_data.get("confirmed", 0)
        inv   = scorecard_data.get("invalidated", 0)
        pend  = scorecard_data.get("pending", 0)
        hit   = scorecard_data.get("best_hit", "—")
        miss  = scorecard_data.get("worst_miss", "—")
        biais = scorecard_data.get("biais", "")

        conf_pct = round(conf / total * 100) if total else 0
        inv_pct  = round(inv  / total * 100) if total else 0
        pend_pct = round(pend / total * 100) if total else 0

        lines += [
            f"Semaine {week}" if week else "",
            "",
            f"Signaux remontés  ▸ {total}",
            f"Confirmés         ▸ {conf} ({conf_pct}%)",
            f"Invalidés         ▸ {inv} ({inv_pct}%)",
            f"En attente        ▸ {pend} ({pend_pct}%)",
            "",
            f"🏆 Meilleur hit : {hit}",
            f"❌ Plus gros miss : {miss}",
        ]
        if biais:
            lines += ["", f"🔍 Biais détecté : {biais}"]

    elif _is_monday():
        lines += [
            "",
            SEP_LIGHT,
            "",
            "📊 SCORECARD",
            "",
            "Système en démarrage — données disponibles",
            "après 7 jours de signaux trackés.",
        ]

    # Question du matin
    lines += [
        "",
        SEP_LIGHT,
        "",
        "☀️ QUESTION DU MATIN",
        "",
        question,
        "",
        SEP_HEAVY,
    ]

    return "\n".join(lines)


def _is_monday() -> bool:
    return datetime.now().weekday() == 0


def _split_at_boundary(text: str, max_chars: int = 3800) -> list[str]:
    """
    Découpe un message trop long en parties ≤ max_chars.
    Coupe toujours à un séparateur ▬▬▬ ou ┄┄┄ (jamais au milieu d'un signal).
    """
    if len(text) <= max_chars:
        return [text]

    parts = []
    current = ""

    # Découper sur les séparateurs de signaux (▬▬▬)
    sections = text.split(SEP_MED)

    for i, section in enumerate(sections):
        sep = f"\n\n{SEP_MED}\n\n" if i > 0 else ""
        candidate = current + sep + section if current else section

        if len(candidate) > max_chars and current:
            parts.append(current.rstrip())
            current = section
        else:
            current = candidate

    if current.strip():
        parts.append(current.strip())

    return parts if parts else [text[:max_chars]]


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATEUR PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

async def run_morning_report(hours: int = 24, send_telegram: bool = True) -> dict:
    """
    Lance le cycle complet CORTEX v2 :
      1. Collecte parallèle des 4 agents
      2. Analyse Claude Sonnet en parallèle
      3. Génération NEXUS
      4. Construction des 5 messages
      5. Envoi Telegram séquentiel

    Retourne : {messages, ai, crypto, market, deeptech, nexus}
    """
    logger.info("=" * 55)
    logger.info("CORTEX v2 — Démarrage rapport du matin")
    logger.info("=" * 55)

    # ── Étape 1 : Collecte parallèle ──────────────────────────────────────────
    logger.info("Étape 1/3 — Collecte parallèle (4 agents)...")

    from agents.sources import titans, media, weak_signals, viral
    from agents import scout_crypto, scout_market, scout_deeptech

    async def _collect_ai():
        results = await asyncio.gather(
            titans.collect(hours),
            media.collect(hours),
            weak_signals.collect(hours),
            viral.collect(hours),
            return_exceptions=True,
        )
        all_raw = []
        for r in results:
            if isinstance(r, list):
                all_raw.extend(r)
        # Déduplication rapide
        seen, unique = set(), []
        for s in all_raw:
            url = s.get("source_url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append(s)
        logger.info(f"  IA: {len(unique)} signaux collectés")
        return unique

    ai_raw, crypto_raw, market_raw, deeptech_raw = await asyncio.gather(
        _collect_ai(),
        scout_crypto.collect(hours),
        scout_market.collect(hours),
        scout_deeptech.collect(hours),
        return_exceptions=True,
    )

    # Fallbacks si exception
    if isinstance(ai_raw,       Exception): ai_raw       = []
    if isinstance(crypto_raw,   Exception): crypto_raw   = {"dashboard": {}, "signals": []}
    if isinstance(market_raw,   Exception): market_raw   = {"dashboard": {}, "signals": []}
    if isinstance(deeptech_raw, Exception): deeptech_raw = []

    # ── Étape 2 : Analyse Claude Sonnet en parallèle ──────────────────────────
    logger.info("Étape 2/3 — Analyse Claude Sonnet (4 agents en parallèle)...")

    from agents import summarizer

    ai_analyzed, crypto_analyzed, market_analyzed, deeptech_analyzed = await asyncio.gather(
        summarizer.analyze_ai(ai_raw if isinstance(ai_raw, list) else []),
        summarizer.analyze_crypto(crypto_raw),
        summarizer.analyze_market(market_raw),
        summarizer.analyze_deeptech(deeptech_raw if isinstance(deeptech_raw, list) else []),
        return_exceptions=True,
    )

    if isinstance(ai_analyzed,       Exception): ai_analyzed       = summarizer._fallback_ai([])
    if isinstance(crypto_analyzed,   Exception): crypto_analyzed   = summarizer._fallback_crypto({})
    if isinstance(market_analyzed,   Exception): market_analyzed   = summarizer._fallback_market({})
    if isinstance(deeptech_analyzed, Exception): deeptech_analyzed = {"signals": []}

    logger.info(
        f"  IA: {len(ai_analyzed.get('signals', []))} signaux | "
        f"Crypto: {len(crypto_analyzed.get('signals', []))} | "
        f"Marchés: {len(market_analyzed.get('signals', []))} | "
        f"DeepTech: {len(deeptech_analyzed.get('signals', []))}"
    )

    # ── Étape 3 : NEXUS ───────────────────────────────────────────────────────
    logger.info("Étape 3/3 — Génération NEXUS + Question du matin...")

    nexus_data = await summarizer.generate_nexus(
        ai_analyzed, crypto_analyzed, market_analyzed, deeptech_analyzed
    )

    # ── Construction des 5 messages ───────────────────────────────────────────
    msg1 = build_msg1(ai_analyzed)
    msg2 = build_msg2(crypto_analyzed)
    msg3 = build_msg3(market_analyzed)
    msg4 = build_msg4(deeptech_analyzed)
    msg5 = build_msg5(nexus_data)

    messages = [msg1, msg2, msg3, msg4, msg5]

    logger.info("Messages construits :")
    for i, m in enumerate(messages, 1):
        logger.info(f"  MSG {i}: {len(m)} chars")

    # ── Envoi Telegram ────────────────────────────────────────────────────────
    if send_telegram:
        try:
            from tgbot.bot import broadcast_message, ask_morning_question

            # Séparateurs visuels entre chaque catégorie (MSG 1→2, 2→3, 3→4, 4→5)
            CATEGORY_SEPARATORS = {
                1: f"{SEP_MED}\n💰 _Crypto & Web3_",
                2: f"{SEP_MED}\n📈 _Marchés & Macro_",
                3: f"{SEP_MED}\n⚡ _DeepTech & Ruptures_",
                4: f"{SEP_MED}\n🔗 _Nexus_",
            }

            total_sent = 0
            for i, msg in enumerate(messages, 1):
                parts = _split_at_boundary(msg, max_chars=3800)
                for j, part in enumerate(parts):
                    await broadcast_message(part, parse_mode="Markdown")
                    total_sent += 1
                    logger.info(
                        f"  MSG {i}/5"
                        + (f" partie {j+1}/{len(parts)}" if len(parts) > 1 else "")
                        + f" broadcasté ✅ ({len(part)} chars)"
                    )
                    if len(parts) > 1:
                        await asyncio.sleep(1)

                # Envoyer le séparateur entre catégories (pas après le dernier message)
                if i in CATEGORY_SEPARATORS:
                    await asyncio.sleep(1)
                    await broadcast_message(CATEGORY_SEPARATORS[i], parse_mode="Markdown")
                    await asyncio.sleep(1)

            logger.info(f"Total: {total_sent} broadcasts envoyés")

            # Entrée journal (admin uniquement — question personnelle pour Badr)
            question = nexus_data.get("question", "")
            if question:
                await ask_morning_question(question, send=False)

        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")

    logger.info("=" * 55)
    logger.info("CORTEX v2 — Rapport terminé")
    logger.info("=" * 55)

    return {
        "messages":  messages,
        "ai":        ai_analyzed,
        "crypto":    crypto_analyzed,
        "market":    market_analyzed,
        "deeptech":  deeptech_analyzed,
        "nexus":     nexus_data,
    }
