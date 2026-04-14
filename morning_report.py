"""
CORTEX — Orchestrateur Rapport du Matin v3
5 messages Telegram séquentiels en HTML :
  MSG 1 : 🧠 Intelligence Artificielle
  MSG 2 : 💰 Crypto & Web3
  MSG 3 : 📈 Marchés & Macro + Actions chaudes
  MSG 4 : ⚡ DeepTech & Ruptures
  MSG 5 : 🔗 Nexus + Scorecard + Question

Format : HTML (Telegram), gras sur headers, emoji comme palette couleur.
Glossaire technique à la fin de chaque message.
"""

import asyncio
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger("morning_report")

# ── Constantes de design ───────────────────────────────────────────────────────
SEP_HEAVY = "━━━━━━━━━━━━━━━━━━━━━━━━"
SEP_MED   = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
SEP_LIGHT = "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄"

NUMS = ["❶", "❷", "❸"]

_DAYS_FR   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
_MONTHS_FR = [
    "Janvier","Février","Mars","Avril","Mai","Juin",
    "Juillet","Août","Septembre","Octobre","Novembre","Décembre",
]

# ── Glossaire global ───────────────────────────────────────────────────────────
GLOSSARY = {
    "conviction":      "Niveau de confiance dans l'analyse : ★☆☆☆☆ faible → ★★★★★ exceptionnel",
    "sizing":          "Taille de position conseillée : Fort = jusqu'à 5% du portefeuille, Moyen = 1-2%, Faible = observation",
    "invalide_si":     "Seuil précis qui annule l'analyse — surveille ce point avant d'agir",
    "thèse opposée":   "Le meilleur argument contre la lecture proposée — protège contre le biais de confirmation",
    "watchlist":       "Signaux émergents à surveiller mais pas encore assez solides pour agir",
    "fear & greed":    "Indice 0-100 : 0-25 = peur extrême (souvent bon pour acheter), 75-100 = euphorie (attention au retournement)",
    "funding rate":    "Taux payé entre traders long/short sur les marchés à terme — positif = le marché est majoritairement long",
    "open interest":   "Volume total de contrats à terme ouverts — hausse = conviction, baisse = dégagement de positions",
    "long/short ratio":"Proportion de traders pariant à la hausse vs à la baisse sur les marchés dérivés",
    "on-chain":        "Données directement lisibles sur la blockchain, sans intermédiaire (mouvements de baleines, adresses actives...)",
    "dominance btc":   "Part du Bitcoin dans la capitalisation totale des cryptos — hausse = fuite vers la sécurité, baisse = altseason",
    "phase du cycle":  "Accumulation → Markup (hausse) → Distribution → Markdown (baisse) — indique où on est dans le cycle",
    "vix":             "Indice de volatilité du S&P500 — <15 calme, >25 nerveux, >40 crise",
    "dxy":             "Indice du dollar américain contre un panier de devises — hausse = dollar fort = pression sur actifs risqués",
    "courbe des taux": "Différence entre taux courts et longs — inversée = signal historique de récession dans 12-18 mois",
    "ism manuf.":      "Indicateur de santé du secteur manufacturier — >50 = expansion, <50 = contraction",
    "peer-reviewed":   "Article validé par des experts indépendants avant publication — niveau de preuve scientifique élevé",
    "early-stage":     "Entreprise ou technologie en phase très précoce (avant produit de masse) — risque élevé, potentiel maximal",
    "bear case":       "Scénario pessimiste — raisons pour lesquelles l'analyse pourrait être fausse",
    "momentum":        "Force et direction d'une tendance de prix sur une période récente",
    "récession":       "Contraction économique sur 2 trimestres consécutifs — impact fort sur actions et crypto",
}


# ── Helpers HTML ───────────────────────────────────────────────────────────────

def _h(text) -> str:
    """Échappe les caractères HTML spéciaux dans le contenu."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _link(name: str, url: str) -> str:
    if url and url.startswith("http"):
        return f'<a href="{url}">{_h(name)}</a>'
    return _h(name)


def _b(text) -> str:
    return f"<b>{_h(text)}</b>"


def _i(text) -> str:
    return f"<i>{_h(text)}</i>"


def _fr_date() -> str:
    now = datetime.now()
    return f"{_DAYS_FR[now.weekday()]} {now.day} {_MONTHS_FR[now.month - 1]} {now.year}"


def _stars(n: int) -> str:
    n = max(1, min(5, int(n)))
    return "★" * n + "☆" * (5 - n)


def _sizing_tag(sizing: str) -> str:
    icons = {"Fort": "🟢", "Moyen": "🟡", "Faible": "🔴"}
    hints = {
        "Fort":   "jusqu'à 5% du portefeuille",
        "Moyen":  "1-2% du portefeuille",
        "Faible": "observation seulement, pas d'achat",
    }
    icon = icons.get(sizing, "🟡")
    hint = hints.get(sizing, "")
    return f"{icon} <b>{_h(sizing)}</b> <i>({_h(hint)})</i>"


def _direction_tag(direction: str) -> str:
    d = direction.upper()
    if "BEARISH" in d and "NEUTRE" not in d:  icon = "🔴"
    elif "BULLISH" in d and "NEUTRE" not in d: icon = "🟢"
    else: icon = "🟡"
    return f"{icon} <b>{_h(direction)}</b>"


def _indicator_tag(status: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "🟡")


def _horizon_tag(horizon: str) -> str:
    return {
        "1-2":  "🔴 Court terme (1-2 ans)",
        "3-5":  "🟡 Moyen terme (3-5 ans)",
        "5-10": "🟢 Long terme (5-10 ans)",
        "10+":  "⚪ Très long terme (10+ ans)",
    }.get(horizon, "🟡 ?")


def _arrow(change_pct: float) -> str:
    return "▴" if change_pct >= 0 else "▾"


def _fmt_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def _build_glossary(terms: list[str]) -> str:
    """Construit la section glossaire avec les termes demandés."""
    lines = ["", SEP_LIGHT, "", "<b>📖 Lexique du jour</b>", ""]
    items = [t for t in terms if GLOSSARY.get(t)]
    # Déduplique en gardant l'ordre
    seen, deduped = set(), []
    for t in items:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    for i, term in enumerate(deduped):
        definition = GLOSSARY[term]
        lines.append(f"<b>{_h(term.capitalize())}</b>")
        lines.append(f"<i>{_h(definition)}</i>")
        if i < len(deduped) - 1:
            lines.append("")
    return "\n".join(lines)


# ── Blocs signal ───────────────────────────────────────────────────────────────

def _signal_block(sig: dict, num: str, show_these: bool = True) -> str:
    """Bloc signal universel (IA / Crypto / Marchés) en HTML."""
    conv    = sig.get("conviction", 3)
    stars   = _stars(conv)
    title   = _h(sig.get("title", "SIGNAL").upper())
    fait    = _h(sig.get("fait", ""))
    impl2   = _h(sig.get("implication_2", ""))
    impl3   = _h(sig.get("implication_3", ""))
    these   = _h(sig.get("these_opposee", ""))
    action  = _h(sig.get("action", ""))
    sizing  = _sizing_tag(sig.get("sizing", "Moyen"))
    inv     = _h(sig.get("invalide_si", ""))
    src_n   = sig.get("source_name", "Source")
    src_u   = sig.get("source_url", "")

    # Label de conviction lisible
    conv_labels = {1: "très faible", 2: "faible", 3: "modérée", 4: "forte", 5: "exceptionnelle"}
    conv_label  = conv_labels.get(conv, "modérée")

    lines = [
        f"<b>{stars} {num} {title}</b>",
        f"<i>Conviction {stars} = {_h(conv_label)}</i>",
        "",
        "<b>📌 Ce qui se passe</b>",
        fait,
        "",
        "<b>🧩 Ce que ça change pour toi</b>",
        f"→ <b>Impact direct :</b> {impl2}",
        f"→ <b>Impact indirect :</b> {impl3}",
    ]

    if show_these and these and these not in ("N/A", ""):
        lines += [
            "",
            "<b>🔄 Contre-argument</b>",
            f"<i>{these}</i>",
        ]

    inv_display = inv if inv and inv not in ("N/A", "") else "Non défini"
    lines += [
        "",
        "<b>🎯 Que faire ?</b>",
        f"▸ Action : {action}",
        f"▸ Taille de position : {sizing}",
        f"▸ Abandonner l'analyse si : {inv_display}",
        "",
        f"🔗 Source : {_link(src_n, src_u)}",
    ]

    return "\n".join(lines)


def _signal_block_deeptech(sig: dict, num: str) -> str:
    """Bloc signal DeepTech enrichi : crédibilité + angle investissement."""
    conv    = sig.get("conviction", 3)
    stars   = _stars(conv)
    title   = _h(sig.get("title", "SIGNAL").upper())
    horizon = _horizon_tag(sig.get("horizon", "3-5"))
    fait    = _h(sig.get("fait", ""))
    impl2   = _h(sig.get("implication_2", ""))
    impl3   = _h(sig.get("implication_3", ""))
    action  = _h(sig.get("action", ""))
    sizing  = _sizing_tag(sig.get("sizing", "Faible"))
    inv     = _h(sig.get("invalide_si", ""))
    src_n   = sig.get("source_name", "Source")
    src_u   = sig.get("source_url", "")
    conv_labels = {1: "très faible", 2: "faible", 3: "modérée", 4: "forte", 5: "exceptionnelle"}
    conv_label  = conv_labels.get(conv, "modérée")
    cred    = sig.get("credibilite_score", 0)

    def _crit(key: str, label: str) -> str:
        ok     = sig.get(key, False)
        detail = _h(sig.get(f"{key}_detail", "") or "")
        icon   = "✅" if ok else "❌"
        line   = f"  {icon} {label}"
        if ok and detail:
            line += f" — <i>{detail}</i>"
        return line

    cots  = sig.get("investissement_cotes", [])
    etfs  = sig.get("investissement_etf", [])
    early = sig.get("investissement_early", [])
    inv_lines = []
    if cots:  inv_lines.append(f"  ▸ <b>Actions cotées :</b> {_h(', '.join(cots))}")
    if etfs:  inv_lines.append(f"  ▸ <b>ETF :</b> {_h(', '.join(etfs))}")
    if early: inv_lines.append(f"  ▸ <b>Early-stage :</b> {_h(', '.join(early))}")
    if not inv_lines:
        inv_lines.append("  ▸ Aucune exposition directe identifiée")

    inv_display = inv if inv and inv not in ("N/A", "") else "Non défini"

    lines = [
        f"<b>{stars} {num} {title}</b>",
        f"<i>Conviction {stars} = {_h(conv_label)} | Horizon : {horizon}</i>",
        "",
        "<b>📌 Ce qui se passe</b>",
        fait,
        "",
        "<b>🧩 Ce que ça change pour toi</b>",
        f"→ <b>Impact direct :</b> {impl2}",
        f"→ <b>Impact indirect :</b> {impl3}",
        "",
        f"<b>✅ Crédibilité scientifique : {cred}/4</b>",
        _crit("peer_reviewed",  "Publication validée par des experts (peer-reviewed)"),
        _crit("financement",    "Financement confirmé"),
        _crit("prototype",      "Prototype / démonstration existante"),
        _crit("adoption",       "Adoption industrielle en cours"),
        "",
        "<b>💰 Comment en profiter</b>",
    ] + inv_lines + [
        "",
        "<b>🎯 Que faire ?</b>",
        f"▸ Action : {action}",
        f"▸ Taille de position : {sizing}",
        f"▸ Abandonner l'analyse si : {inv_display}",
        "",
        f"🔗 Source : {_link(src_n, src_u)}",
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
        "<b>🧠 CORTEX — INTELLIGENCE ARTIFICIELLE</b>",
        f"<i>📅 {_fr_date()}</i>",
        SEP_HEAVY,
    ]

    if not signals:
        lines += ["", "<i>Aucun signal IA majeur aujourd'hui.</i>"]
    else:
        for i, sig in enumerate(signals):
            if i > 0:
                lines += ["", SEP_MED, ""]
            lines += ["", _signal_block(sig, NUMS[i])]

    if watchlist:
        lines += ["", SEP_LIGHT, "", "<b>📡 Signaux à surveiller</b>", ""]
        for item in watchlist[:3]:
            lines.append(f"◦ {_h(item)}")

    # Glossaire IA
    lines.append(_build_glossary([
        "conviction", "thèse opposée", "sizing", "invalide_si", "watchlist"
    ]))
    lines.append(SEP_HEAVY)

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

    # BTC
    btc_p = dashboard.get("btc_price")
    btc_c = dashboard.get("btc_change_24h", 0)
    btc_line = f"${btc_p:,.0f} {_arrow(btc_c)} {_fmt_pct(btc_c)}" if btc_p else "N/A"

    def _score_line(key: str, label: str, weight: str) -> str:
        s   = score.get(key, {})
        val = s.get("value", 0)
        note = _h(s.get("note", ""))
        sign = "+" if val > 0 else ""
        bar  = "🟢" if val > 0 else ("🔴" if val < 0 else "🟡")
        return f"  {bar} <b>{label}</b> ({weight}) → {sign}{val}  <i>{note}</i>"

    lines = [
        SEP_HEAVY,
        "<b>💰 CORTEX — CRYPTO &amp; WEB3</b>",
        f"<i>📅 {_fr_date()}</i>",
        SEP_HEAVY,
        "",
        "<b>📊 Tableau de bord Bitcoin</b>",
        "",
        f"  <b>Prix :</b> {_h(btc_line)}",
        f"  <b>Phase du cycle :</b> {_h(phase)}",
        f"  <b>Fear &amp; Greed :</b> {_h(dashboard.get('fear_greed_score', 'N/A'))} — {_h(dashboard.get('fear_greed_label', 'N/A'))}",
        f"  <b>Dominance BTC :</b> {_h(dashboard.get('btc_dominance', 'N/A'))}%",
        f"  <b>Funding rate :</b> {_h(dashboard.get('funding_description', 'N/A'))}",
        f"  <b>Volume vs moy. 30j :</b> {_h(vol_30d)}",
    ]

    # On-chain data (si disponible)
    oi      = dashboard.get("open_interest_btc")
    oi_chg  = dashboard.get("open_interest_change_pct")
    ls      = dashboard.get("long_short_ratio")
    mempool = dashboard.get("mempool_fee")
    if oi or ls or mempool:
        lines += ["", "<b>🔗 Données on-chain &amp; dérivés</b>", ""]
        if oi:
            oi_str = f"${oi/1e9:.1f}B" if oi > 1e9 else f"${oi/1e6:.0f}M"
            chg_str = f" ({_fmt_pct(oi_chg)})" if oi_chg is not None else ""
            lines.append(f"  <b>Open Interest :</b> {oi_str}{_h(chg_str)}")
        if ls:
            lines.append(f"  <b>Long/Short ratio :</b> {_h(f'{ls:.0%}')} longs")
        if mempool:
            lines.append(f"  <b>Mémoire BTC :</b> {_h(str(mempool))} sat/vB")

    lines += [
        "",
        SEP_LIGHT,
        "",
        "<b>📐 Score de direction</b>",
        "",
        _score_line("onchain",   "On-chain ",  "25%"),
        _score_line("cycle",     "Cycle    ",  "25%"),
        _score_line("macro",     "Macro    ",  "20%"),
        _score_line("sentiment", "Sentiment",  "15%"),
        _score_line("momentum",  "Momentum ",  "15%"),
        "",
        f"→ Direction : {_direction_tag(direction)} ({_h(magnitude)})",
        "",
        f"<b>🔄 Ce qui invaliderait cette lecture</b>",
        f"<i>{_h(bear_case)}</i>",
    ]

    if signals:
        for i, sig in enumerate(signals):
            lines += ["", SEP_MED, "", _signal_block(sig, NUMS[i])]

    # Glossaire crypto
    lines.append(_build_glossary([
        "fear & greed", "phase du cycle", "funding rate",
        "open interest", "long/short ratio", "on-chain", "dominance btc",
        "bear case",
    ]))
    lines.append(SEP_HEAVY)

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 3 — MARCHÉS & MACRO
# ══════════════════════════════════════════════════════════════════════════════

def build_msg3(market_data: dict) -> str:
    dashboard  = market_data.get("dashboard", {})
    rec_ind    = market_data.get("recession_indicators", {})
    rec_score  = market_data.get("recession_score", 0)
    regime     = market_data.get("regime", "N/A")
    regime_j   = market_data.get("regime_justification", "")
    signals    = market_data.get("signals", [])[:3]
    hot_stocks = market_data.get("hot_stocks", [])
    crash      = market_data.get("crash", {})

    def _dash_line(key: str, label: str) -> str:
        d     = dashboard.get(key, {})
        price = d.get("price", "N/A")
        chg   = d.get("change_pct", 0)
        if key == "vix":
            interp = _h(d.get("interpretation", ""))
            return f"  <b>{label} :</b> {_h(price)} — <i>{interp}</i>"
        if key == "us_10y":
            bps = _h(d.get("change_bps", ""))
            return f"  <b>{label} :</b> {_h(price)} {bps}"
        arr = _arrow(chg)
        pct = _fmt_pct(chg)
        col = "🟢" if chg >= 0 else "🔴"
        return f"  {col} <b>{label} :</b> {_h(str(price))} {arr} {_h(pct)}"

    def _rec_line(key: str, label: str) -> str:
        ind   = rec_ind.get(key, {})
        emoji = _indicator_tag(ind.get("status", "yellow"))
        note  = _h(ind.get("note", ""))
        return f"  {emoji} <b>{label} :</b> <i>{note}</i>"

    # Score récession couleur
    if rec_score <= 2:   rec_color = "🟢"
    elif rec_score <= 4: rec_color = "🟡"
    else:                rec_color = "🔴"

    lines = [
        SEP_HEAVY,
        "<b>📈 CORTEX — MARCHÉS &amp; MACRO</b>",
        f"<i>📅 {_fr_date()}</i>",
        SEP_HEAVY,
        "",
        "<b>📊 Tableau de bord marchés</b>",
        "",
        _dash_line("sp500",  "S&amp;P 500"),
        _dash_line("nasdaq", "Nasdaq   "),
        _dash_line("gold",   "Or       "),
        _dash_line("oil",    "Pétrole  "),
        _dash_line("dxy",    "DXY      "),
        _dash_line("vix",    "VIX      "),
        _dash_line("us_10y", "US 10Y   "),
        "",
        SEP_LIGHT,
        "",
        f"{rec_color} <b>Risque de récession : {rec_score}/10</b>",
        "<i>0-3 = faible, 4-6 = modéré, 7-10 = élevé</i>",
        "",
        _rec_line("courbe_taux",   "Courbe des taux"),
        _rec_line("emploi",        "Emploi         "),
        _rec_line("ism_manuf",     "ISM Manuf.     "),
        _rec_line("ism_services",  "ISM Services   "),
        _rec_line("conso_conf",    "Confiance conso."),
        _rec_line("credit_spread", "Crédit spreads "),
        _rec_line("earnings_rev",  "Révisions bénéf."),
        "",
        SEP_LIGHT,
        "",
        f"<b>🏛️ Régime de marché : {_h(regime)}</b>",
        "",
        f"<i>{_h(regime_j)}</i>",
    ]

    # Actions chaudes (stock screener)
    if hot_stocks:
        lines += ["", SEP_LIGHT, "", "<b>🔥 Actions en mouvement aujourd'hui</b>", ""]
        for i, stock in enumerate(hot_stocks[:5], 1):
            ticker  = _h(stock.get("ticker", ""))
            name    = _h(stock.get("name", ticker))
            chg1d   = stock.get("change_1d", 0)
            chg5d   = stock.get("change_5d", 0)
            reason  = _h(stock.get("reason", ""))
            arrow1d = "▴" if chg1d >= 0 else "▾"
            arrow5d = "▴" if chg5d >= 0 else "▾"
            col1d   = "🟢" if chg1d >= 0 else "🔴"
            lines.append(
                f"  {col1d} <b>{ticker}</b> — {name}\n"
                f"       Aujourd'hui : {arrow1d} {_fmt_pct(chg1d)}  |  Semaine : {arrow5d} {_fmt_pct(chg5d)}"
                + (f"\n       <i>{reason}</i>" if reason else "")
            )
            if i < len(hot_stocks[:5]):
                lines.append("")

    # Crash / Risque systémique
    if crash:
        crash_score  = crash.get("crash_score", 0)
        crash_color  = crash.get("color", "🟢")
        crash_interp = _h(crash.get("interpretation", ""))
        factors      = crash.get("factors", [])
        lines += [
            "", SEP_LIGHT, "",
            f"{crash_color} <b>Risque crash systémique : {crash_score}/10</b>",
            f"<i>{crash_interp}</i>",
            "",
        ]
        for f in factors:
            ind  = _h(f.get("indicator", ""))
            val  = _h(f.get("value", ""))
            lbl  = _h(f.get("label", ""))
            lines.append(f"  • <b>{ind}</b> {val} — <i>{lbl}</i>")

    if signals:
        for i, sig in enumerate(signals):
            lines += ["", SEP_MED, "", _signal_block(sig, NUMS[i])]

    # Glossaire marchés
    lines.append(_build_glossary([
        "vix", "dxy", "courbe des taux", "ism manuf.", "récession", "momentum", "bear case",
        "spread hy", "courbe des taux",
    ]))
    lines.append(SEP_HEAVY)

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD MSG 4 — DEEPTECH & RUPTURES
# ══════════════════════════════════════════════════════════════════════════════

def build_msg4(deeptech_data: dict) -> str:
    signals = deeptech_data.get("signals", [])[:2]

    lines = [
        SEP_HEAVY,
        "<b>⚡ CORTEX — DEEPTECH &amp; RUPTURES</b>",
        f"<i>📅 {_fr_date()}</i>",
        "<i>Ces signaux peuvent être le prochain Bitcoin — il s'agit de repérer très tôt.</i>",
        SEP_HEAVY,
    ]

    if not signals:
        lines += ["", "<i>Aucun signal deeptech majeur aujourd'hui.</i>"]
    else:
        for i, sig in enumerate(signals):
            if i > 0:
                lines += ["", SEP_MED]
            lines += ["", _signal_block_deeptech(sig, NUMS[i])]

    # Glossaire deeptech
    lines.append(_build_glossary([
        "conviction", "peer-reviewed", "early-stage", "sizing", "invalide_si",
    ]))
    lines.append(SEP_HEAVY)

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
        "<b>🔗 CORTEX — NEXUS</b>",
        f"<i>📅 {_fr_date()}</i>",
        "<i>La connexion cachée entre les 4 secteurs du jour.</i>",
        SEP_HEAVY,
        "",
        "<b>🔗 Connexion du jour</b>",
        "",
    ]

    if has_conn and connexion:
        if secteurs:
            lines.append(f"<i>{_h(' × '.join(secteurs))}</i>")
            lines.append("")
        lines.append(_h(connexion))
    else:
        lines.append("<i>Pas de connexion significative aujourd'hui — les secteurs évoluent indépendamment.</i>")

    # Scorecard (lundi uniquement)
    if scorecard_data:
        total = scorecard_data.get("total", 0)
        conf  = scorecard_data.get("confirmed", 0)
        inv   = scorecard_data.get("invalidated", 0)
        pend  = scorecard_data.get("pending", 0)
        hit   = scorecard_data.get("best_hit", "—")
        miss  = scorecard_data.get("worst_miss", "—")
        biais = scorecard_data.get("biais", "")
        conf_pct = round(conf / total * 100) if total else 0

        lines += [
            "",
            SEP_LIGHT,
            "",
            "<b>📊 Scorecard de la semaine</b>",
            "<i>Combien d'analyses CORTEX se sont révélées justes ?</i>",
            "",
            f"  📈 Signaux remontés : <b>{total}</b>",
            f"  ✅ Confirmés : <b>{conf}</b> ({conf_pct}%)",
            f"  ❌ Invalidés : <b>{inv}</b>",
            f"  ⏳ En attente : <b>{pend}</b>",
            "",
            f"  🏆 Meilleur signal : <i>{_h(hit)}</i>",
            f"  📉 Plus gros miss : <i>{_h(miss)}</i>",
        ]
        if biais:
            lines += ["", f"  🔍 <b>Biais détecté :</b> <i>{_h(biais)}</i>"]

    elif _is_monday():
        lines += [
            "",
            SEP_LIGHT,
            "",
            "<b>📊 Scorecard</b>",
            "<i>Disponible après 7 jours de signaux trackés.</i>",
        ]

    # Question du matin
    lines += [
        "",
        SEP_LIGHT,
        "",
        "<b>☀️ Question du matin</b>",
        "<i>Force-toi à décider — pas juste observer.</i>",
        "",
        f"<b>{_h(question)}</b>",
        "",
        "<i>→ Réponds ici. Ta réponse est sauvegardée dans ton journal.</i>",
        "",
        SEP_HEAVY,
    ]

    return "\n".join(lines)


def _is_monday() -> bool:
    return datetime.now().weekday() == 0


def _split_at_boundary(text: str, max_chars: int = 3800) -> list[str]:
    """Découpe proprement aux séparateurs ▬▬▬ (jamais au milieu d'un signal)."""
    if len(text) <= max_chars:
        return [text]

    parts, current = [], ""
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
    Lance le cycle complet CORTEX v3 :
      1. Collecte parallèle des 4 agents + stock screener
      2. Analyse Claude (Sonnet + Haiku) en parallèle
      3. Génération NEXUS (Haiku)
      4. Construction des 5 messages HTML
      5. Envoi Telegram séquentiel

    Retourne : {messages, ai, crypto, market, deeptech, nexus}
    """
    logger.info("=" * 55)
    logger.info("CORTEX v3 — Démarrage rapport du matin")
    logger.info("=" * 55)

    # ── Étape 1 : Collecte parallèle ──────────────────────────────────────────
    logger.info("Étape 1/3 — Collecte parallèle (4 agents + stock screener)...")

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

    if isinstance(ai_raw,       Exception): ai_raw       = []
    if isinstance(crypto_raw,   Exception): crypto_raw   = {"dashboard": {}, "signals": []}
    if isinstance(market_raw,   Exception): market_raw   = {"dashboard": {}, "signals": [], "hot_stocks": []}
    if isinstance(deeptech_raw, Exception): deeptech_raw = []

    # ── Étape 2 : Analyse Claude en parallèle ─────────────────────────────────
    logger.info("Étape 2/3 — Analyse Claude (Sonnet×4 + Haiku×1) en parallèle...")

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

    # Propagation hot_stocks + crash depuis market_raw → market_analyzed
    if isinstance(market_raw, dict):
        if market_raw.get("hot_stocks"):
            market_analyzed["hot_stocks"] = market_raw["hot_stocks"]
        if market_raw.get("crash"):
            market_analyzed["crash"] = market_raw["crash"]

    logger.info(
        f"  IA: {len(ai_analyzed.get('signals', []))} signaux | "
        f"Crypto: {len(crypto_analyzed.get('signals', []))} | "
        f"Marchés: {len(market_analyzed.get('signals', []))} | "
        f"DeepTech: {len(deeptech_analyzed.get('signals', []))}"
    )

    # ── Étape 3 : NEXUS (Haiku) ───────────────────────────────────────────────
    logger.info("Étape 3/3 — Génération NEXUS (Haiku) + Question du matin...")

    nexus_data = await summarizer.generate_nexus(
        ai_analyzed, crypto_analyzed, market_analyzed, deeptech_analyzed
    )

    # ── Construction des 5 messages HTML ─────────────────────────────────────
    msg1 = build_msg1(ai_analyzed)
    msg2 = build_msg2(crypto_analyzed)
    msg3 = build_msg3(market_analyzed)
    msg4 = build_msg4(deeptech_analyzed)
    msg5 = build_msg5(nexus_data)

    messages = [msg1, msg2, msg3, msg4, msg5]

    logger.info("Messages construits :")
    for i, m in enumerate(messages, 1):
        logger.info(f"  MSG {i}: {len(m)} chars")

    # ── Envoi Telegram (HTML mode) ────────────────────────────────────────────
    if send_telegram:
        try:
            from tgbot.bot import broadcast_message, ask_morning_question

            total_sent = 0
            for i, msg in enumerate(messages, 1):
                parts = _split_at_boundary(msg, max_chars=3800)
                for j, part in enumerate(parts):
                    await broadcast_message(part, parse_mode="HTML")
                    total_sent += 1
                    logger.info(
                        f"  MSG {i}/5"
                        + (f" partie {j+1}/{len(parts)}" if len(parts) > 1 else "")
                        + f" broadcasté ✅ ({len(part)} chars)"
                    )
                    if len(parts) > 1:
                        await asyncio.sleep(1)
                if i < len(messages):
                    await asyncio.sleep(2)

            logger.info(f"Total: {total_sent} broadcasts envoyés")

            question = nexus_data.get("question", "")
            if question:
                await ask_morning_question(question, send=False)

        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")

    logger.info("=" * 55)
    logger.info("CORTEX v3 — Rapport terminé")
    logger.info("=" * 55)

    return {
        "messages":  messages,
        "ai":        ai_analyzed,
        "crypto":    crypto_analyzed,
        "market":    market_analyzed,
        "deeptech":  deeptech_analyzed,
        "nexus":     nexus_data,
    }
