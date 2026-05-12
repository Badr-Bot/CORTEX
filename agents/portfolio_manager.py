"""
CORTEX V3 — Portfolio Manager
Crée et gère des portefeuilles fictifs de $1000 (PW/PM/PA).

Intelligence utilisée pour l'allocation :
  - Analyses sectorielles du jour (IA, Crypto, Marchés)
  - Long memory : résumés hebdo + patterns permanents appris
  - Décisions passées : historique WIN/LOSS par secteur
  - Semantic search : journées passées similaires à aujourd'hui
  - Indicateurs marché : BTC cycle, FRED macro, Fear & Greed

Conventions de nommage :
  PW1, PW2...  → Weekly  (7 jours)
  PM1, PM2...  → Monthly (30 jours)
  PA1, PA2...  → Annual  (365 jours)
"""

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

import anthropic

from utils.logger import get_logger

logger = get_logger("portfolio_manager")

_client_anthropic = None


def _get_anthropic():
    global _client_anthropic
    if _client_anthropic is None:
        _client_anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    return _client_anthropic


# ── Fetch prix spot ────────────────────────────────────────────────────────────

async def _fetch_price(ticker: str, asset_type: str) -> Optional[float]:
    """Fetch le prix spot d'un ticker (crypto ou action/ETF)."""
    import httpx
    try:
        if asset_type == "crypto":
            # CoinGecko ID mapping
            cg_ids = {
                "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
                "BNB": "binancecoin", "XRP": "ripple", "ADA": "cardano",
                "AVAX": "avalanche-2", "DOT": "polkadot", "LINK": "chainlink",
                "UNI": "uniswap", "MATIC": "matic-network", "ATOM": "cosmos",
            }
            cg_id = cg_ids.get(ticker.upper(), ticker.lower())
            async with httpx.AsyncClient(timeout=10) as http:
                r = await http.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": cg_id, "vs_currencies": "usd"},
                )
            data = r.json()
            if cg_id in data:
                return float(data[cg_id]["usd"])
            # Fallback Binance
            sym = f"{ticker.upper()}USDT"
            async with httpx.AsyncClient(timeout=8) as http:
                r = await http.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}")
            return float(r.json()["price"])

        else:
            # Yahoo Finance pour actions/ETF
            sym = ticker.upper()
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as http:
                r = await http.get(
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                    params={"interval": "1d", "range": "1d"},
                )
            data = r.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return float(price)
    except Exception as e:
        logger.warning(f"Prix {ticker} indisponible: {e}")
        return None


async def _fetch_sp500() -> Optional[float]:
    """Fetch le prix actuel du S&P 500 (via SPY ETF)."""
    return await _fetch_price("SPY", "etf")


# ── Chargement du contexte complet ────────────────────────────────────────────

async def _load_full_context() -> dict:
    """
    Charge toute l'intelligence disponible de CORTEX :
    analyses du jour, long memory, patterns, décisions passées,
    données marché, semantic search.
    """
    from database.client import (
        get_week_analyses, get_open_decisions, get_portfolio_history,
    )
    from agents.long_memory import (
        get_all_weekly_summaries, get_all_patterns, semantic_search,
        format_long_memory_context,
    )
    from agents.memory import get_agent_learnings, format_learnings_context

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Chargement parallèle de tout le contexte
    (
        analyses_week,
        open_decisions,
        pf_history_w,
        pf_history_m,
        pf_history_a,
        summaries_ai,
        summaries_crypto,
        summaries_market,
        patterns_ai,
        patterns_crypto,
        patterns_market,
        learnings_ai,
        learnings_crypto,
        learnings_market,
    ) = await asyncio.gather(
        get_week_analyses(days_back=3),
        get_open_decisions(days_back=30),
        asyncio.to_thread(get_portfolio_history, "weekly", 5),
        asyncio.to_thread(get_portfolio_history, "monthly", 5),
        asyncio.to_thread(get_portfolio_history, "annual", 3),
        get_all_weekly_summaries("ai", limit=6),
        get_all_weekly_summaries("crypto", limit=6),
        get_all_weekly_summaries("market", limit=6),
        get_all_patterns("ai"),
        get_all_patterns("crypto"),
        get_all_patterns("market"),
        get_agent_learnings("ai", limit=3),
        get_agent_learnings("crypto", limit=3),
        get_agent_learnings("market", limit=3),
    )

    # Analyse du jour (plus récente par secteur)
    ai_analysis     = next((a for a in analyses_week if a.get("sector") == "ai"),     None)
    crypto_analysis = next((a for a in analyses_week if a.get("sector") == "crypto"), None)
    market_analysis = next((a for a in analyses_week if a.get("sector") == "market"), None)

    # Semantic search basé sur le contexte du jour
    today_summary = ""
    if ai_analysis:
        aj = ai_analysis.get("analysis_json", {})
        today_summary += f"IA: {aj.get('synthese', '')[:200]} "
    if crypto_analysis:
        cj = crypto_analysis.get("analysis_json", {})
        today_summary += f"CRYPTO: {cj.get('synthese', '')[:200]} "
    if market_analysis:
        mj = market_analysis.get("analysis_json", {})
        today_summary += f"MARCHÉS: {mj.get('synthese', '')[:200]}"

    similar_ai, similar_crypto, similar_market = await asyncio.gather(
        semantic_search(today_summary[:500], "ai", top_k=2),
        semantic_search(today_summary[:500], "crypto", top_k=2),
        semantic_search(today_summary[:500], "market", top_k=2),
    )

    long_ctx_ai     = format_long_memory_context(summaries_ai,     patterns_ai,     similar_ai)
    long_ctx_crypto = format_long_memory_context(summaries_crypto, patterns_crypto, similar_crypto)
    long_ctx_market = format_long_memory_context(summaries_market, patterns_market, similar_market)

    learnings_ai_str     = format_learnings_context(learnings_ai,     "IA")
    learnings_crypto_str = format_learnings_context(learnings_crypto, "Crypto")
    learnings_market_str = format_learnings_context(learnings_market, "Marchés")

    # Données marché temps réel
    sp500_price = await _fetch_sp500()

    return {
        "today": today,
        "ai_analysis": ai_analysis,
        "crypto_analysis": crypto_analysis,
        "market_analysis": market_analysis,
        "open_decisions": open_decisions,
        "pf_history_w": pf_history_w,
        "pf_history_m": pf_history_m,
        "pf_history_a": pf_history_a,
        "long_ctx_ai": long_ctx_ai,
        "long_ctx_crypto": long_ctx_crypto,
        "long_ctx_market": long_ctx_market,
        "learnings_ai": learnings_ai_str,
        "learnings_crypto": learnings_crypto_str,
        "learnings_market": learnings_market_str,
        "sp500_price": sp500_price,
    }


# ── Construction du prompt d'allocation ───────────────────────────────────────

def _build_allocation_prompt(portfolio_type: str, ctx: dict) -> str:
    horizon_label = {"weekly": "7 jours", "monthly": "30 jours", "annual": "365 jours"}[portfolio_type]
    prefix        = {"weekly": "PW", "monthly": "PM", "annual": "PA"}[portfolio_type]

    lines = [
        f"Tu es CORTEX, système de veille IA/Crypto/Marchés. Tu dois construire un portefeuille fictif de $1 000 USD.",
        f"Horizon d'investissement : {horizon_label} ({prefix}x).",
        f"Date : {ctx['today']}",
        "",
        "═══ CONTEXTE MARCHÉ DU JOUR ═══",
    ]

    # Analyses sectorielles du jour
    for sector, key, label in [
        ("ai",     "ai_analysis",     "INTELLIGENCE ARTIFICIELLE"),
        ("crypto", "crypto_analysis", "CRYPTO & WEB3"),
        ("market", "market_analysis", "MARCHÉS & MACRO"),
    ]:
        analysis = ctx.get(key)
        if analysis:
            aj = analysis.get("analysis_json", {})
            lines.append(f"\n[{label}]")
            if aj.get("synthese"):
                lines.append(f"Synthèse: {aj['synthese'][:400]}")
            if aj.get("conviction"):
                lines.append(f"Conviction globale: {aj['conviction']}")
            # Signaux top
            signals = aj.get("signals", [])[:3]
            for s in signals:
                lines.append(f"  • {s.get('titre', s.get('title', ''))[:100]}")
            # Dashboard crypto
            if sector == "crypto" and aj.get("dashboard"):
                d = aj["dashboard"]
                btc = d.get("btc_price") or d.get("prix_btc")
                cycle = d.get("cycle", {})
                if btc:
                    lines.append(f"  BTC: ${btc:,.0f}" + (f" [{cycle.get('phase','')}]" if cycle else ""))
                fg = d.get("fear_greed_index") or d.get("fear_greed")
                if fg:
                    lines.append(f"  Fear & Greed: {fg}")
            # Dashboard market
            if sector == "market" and aj.get("dashboard"):
                d = aj["dashboard"]
                if d.get("vix"):
                    lines.append(f"  VIX: {d['vix']}")
                if d.get("sp500_change_pct"):
                    lines.append(f"  S&P500 variation: {d['sp500_change_pct']:+.1f}%")
                fred = aj.get("fred", {})
                if fred:
                    t10y2y = fred.get("T10Y2Y", {})
                    if t10y2y.get("value") is not None:
                        lines.append(f"  Courbe taux (T10Y2Y): {t10y2y['value']:.2f}%")

    # Long memory
    for lbl, key in [
        ("IA",      "long_ctx_ai"),
        ("CRYPTO",  "long_ctx_crypto"),
        ("MARCHÉS", "long_ctx_market"),
    ]:
        ctx_txt = ctx.get(key, "")
        if ctx_txt and ctx_txt.strip():
            lines.append(f"\n═══ MÉMOIRE LONG-TERME [{lbl}] ═══")
            lines.append(ctx_txt[:600])

    # Learnings
    for lbl, key in [
        ("IA",      "learnings_ai"),
        ("CRYPTO",  "learnings_crypto"),
        ("MARCHÉS", "learnings_market"),
    ]:
        ctx_txt = ctx.get(key, "")
        if ctx_txt and ctx_txt.strip():
            lines.append(f"\n═══ EXPERTISE APPRISE [{lbl}] ═══")
            lines.append(ctx_txt[:400])

    # Historique décisions trading
    open_dec = ctx.get("open_decisions", [])
    if open_dec:
        lines.append("\n═══ DÉCISIONS TRADING RÉCENTES ═══")
        for d in open_dec[:6]:
            outcome = d.get("outcome", "EN COURS")
            pnl = f" ({d['pnl_pct']:+.1f}%)" if d.get("pnl_pct") is not None else ""
            lines.append(f"  [{d['sector'].upper()}] {d['direction']} {d['ticker']} → {outcome}{pnl}")

    # Historique portefeuilles passés
    for type_lbl, hist_key in [
        ("WEEKLY",  "pf_history_w"),
        ("MONTHLY", "pf_history_m"),
        ("ANNUAL",  "pf_history_a"),
    ]:
        hist = ctx.get(hist_key, [])
        if hist:
            lines.append(f"\n═══ HISTORIQUE PORTEFEUILLES {type_lbl} ═══")
            for h in hist[:3]:
                beat = "✅ BATTU S&P500" if h.get("beat_sp500") else "❌ SOUS S&P500"
                lines.append(
                    f"  {h['code']}: {h.get('pnl_pct', 0):+.1f}% "
                    f"vs S&P500 {h.get('benchmark_pnl_pct', 0):+.1f}% → {beat}"
                )

    lines += [
        "",
        "═══ INSTRUCTIONS ═══",
        f"Construis un portefeuille de $1 000 USD avec horizon {horizon_label}.",
        "Règles :",
        "  - 4 à 7 positions maximum",
        "  - Mix crypto + actions/ETF autorisé (selon conviction)",
        "  - Somme des allocations = exactement 100%",
        "  - Utilise ta mémoire longue terme ET les signaux du jour pour décider",
        "  - Apprends de tes erreurs passées (portefeuilles précédents)",
        "  - Adapte le risque à l'horizon (weekly = plus agressif, annual = plus défensif)",
        "",
        "Réponds UNIQUEMENT en JSON valide avec ce format exact :",
        """
{
  "rationale": "Raisonnement global de 3-4 phrases expliquant la stratégie et ce que la mémoire t'a appris",
  "market_context": "Résumé court du contexte macro/crypto/IA aujourd'hui",
  "positions": [
    {
      "ticker": "BTC",
      "asset_type": "crypto",
      "allocation_pct": 30,
      "conviction": "forte",
      "reasoning": "Pourquoi ce ticker maintenant"
    }
  ]
}""",
    ]
    return "\n".join(lines)


# ── Appel Claude ───────────────────────────────────────────────────────────────

def _call_claude_portfolio(prompt: str) -> Optional[dict]:
    """Appel Claude pour générer l'allocation du portefeuille."""
    try:
        client = _get_anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=(
                "Tu es CORTEX, un système d'analyse financière expert. "
                "Tu gères des portefeuilles fictifs pour valider ta capacité prédictive. "
                "Réponds TOUJOURS en JSON valide uniquement, sans markdown ni texte avant/après."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Extraire JSON si entouré de backticks
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        raw = m.group(1) if m else raw
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur Claude allocation: {e}")
        return None


# ── Création d'un portefeuille ─────────────────────────────────────────────────

async def create_portfolio(portfolio_type: str) -> Optional[dict]:
    """
    Crée un nouveau portefeuille PW/PM/PA avec allocation intelligente.
    Utilise toute la mémoire et l'expertise de CORTEX.
    """
    from database.client import (
        save_portfolio, save_position, save_portfolio_snapshot,
    )

    logger.info(f"Création portefeuille {portfolio_type}...")

    # 1. Charger tout le contexte
    ctx = await _load_full_context()
    sp500_now = ctx.get("sp500_price")

    # 2. Demander l'allocation à Claude
    prompt = _build_allocation_prompt(portfolio_type, ctx)
    allocation = _call_claude_portfolio(prompt)

    if not allocation or "positions" not in allocation:
        logger.error("Allocation invalide reçue de Claude")
        return None

    positions = allocation["positions"]
    rationale = allocation.get("rationale", "")
    logger.info(f"Allocation reçue : {len(positions)} positions")

    # 3. Fetch les prix d'entrée en parallèle
    price_tasks = [_fetch_price(p["ticker"], p["asset_type"]) for p in positions]
    prices = await asyncio.gather(*price_tasks)

    # 4. Créer le portefeuille en DB
    portfolio = save_portfolio(
        portfolio_type=portfolio_type,
        rationale=rationale,
        benchmark_start=sp500_now,
    )
    if not portfolio:
        logger.error("Impossible de créer le portfolio en DB")
        return None

    pf_id   = portfolio["id"]
    pf_code = portfolio["code"]

    # 5. Sauvegarder les positions
    total_allocated = 0
    saved_positions = []
    for pos, entry_price in zip(positions, prices):
        if entry_price is None:
            logger.warning(f"Prix introuvable pour {pos['ticker']}, position ignorée")
            continue

        alloc_pct = float(pos["allocation_pct"])
        alloc_usd = round(1000.0 * alloc_pct / 100, 2)
        quantity  = round(alloc_usd / entry_price, 6)

        saved = save_position(
            portfolio_id=pf_id,
            ticker=pos["ticker"],
            asset_type=pos["asset_type"],
            allocation_pct=alloc_pct,
            allocation_usd=alloc_usd,
            entry_price=entry_price,
            quantity=quantity,
            conviction=pos.get("conviction", "moyenne"),
            reasoning=pos.get("reasoning", ""),
        )
        if saved:
            total_allocated += alloc_usd
            saved_positions.append(saved)

    # 6. Snapshot initial
    save_portfolio_snapshot(
        portfolio_id=pf_id,
        snapshot_date=ctx["today"],
        portfolio_value=1000.0,
        sp500_value=sp500_now or 0,
        pnl_pct=0.0,
        sp500_pnl_pct=0.0,
    )

    logger.info(
        f"Portfolio {pf_code} créé : {len(saved_positions)} positions, "
        f"${total_allocated:.2f} alloués"
    )

    # 7. Résumé Telegram
    await _notify_portfolio_created(portfolio, saved_positions, allocation)

    return {**portfolio, "positions": saved_positions}


# ── Mise à jour quotidienne des prix ──────────────────────────────────────────

async def update_all_portfolios() -> dict:
    """
    Met à jour les prix de toutes les positions actives.
    Prend un snapshot quotidien et clôture les portefeuilles en fin de période.
    """
    from database.client import (
        get_active_portfolios, update_position_price,
        update_portfolio_value, save_portfolio_snapshot,
        close_portfolio, save_portfolio,
    )

    portfolios = get_active_portfolios()
    if not portfolios:
        logger.info("Aucun portefeuille actif à mettre à jour")
        return {"updated": 0, "closed": 0, "created": 0}

    today       = datetime.now(timezone.utc).date()
    sp500_now   = await _fetch_sp500()
    stats       = {"updated": 0, "closed": 0, "created": 0}

    for pf in portfolios:
        pf_id    = pf["id"]
        pf_code  = pf["code"]
        pf_type  = pf["portfolio_type"]
        end_date = datetime.fromisoformat(pf["end_date"]).date()
        init_val = float(pf["initial_value"])
        bm_start = float(pf.get("benchmark_start") or 0)
        positions = pf.get("paper_positions", [])

        # Fetch tous les prix en parallèle
        open_pos    = [p for p in positions if p["status"] == "open"]
        price_tasks = [_fetch_price(p["ticker"], p["asset_type"]) for p in open_pos]
        prices      = await asyncio.gather(*price_tasks)

        # Mettre à jour chaque position
        portfolio_value = 0.0
        for pos, current_price in zip(open_pos, prices):
            if current_price is None:
                # Conserver le dernier prix connu
                current_price = float(pos.get("current_price") or pos["entry_price"])

            qty       = float(pos["quantity"])
            entry     = float(pos["entry_price"])
            alloc_usd = float(pos["allocation_usd"])
            pnl_usd   = round((current_price - entry) * qty, 2)
            pnl_pct   = round((current_price - entry) / entry * 100, 2) if entry else 0

            update_position_price(pos["id"], current_price, pnl_usd, pnl_pct)
            portfolio_value += alloc_usd + pnl_usd

        # Calcul P&L portefeuille
        portfolio_pnl_pct = round((portfolio_value - init_val) / init_val * 100, 2)

        # P&L S&P500 depuis démarrage
        sp500_pnl_pct = 0.0
        if sp500_now and bm_start and bm_start > 0:
            sp500_pnl_pct = round((sp500_now - bm_start) / bm_start * 100, 2)

        update_portfolio_value(pf_id, portfolio_value)

        save_portfolio_snapshot(
            portfolio_id=pf_id,
            snapshot_date=today.isoformat(),
            portfolio_value=portfolio_value,
            sp500_value=sp500_now or 0,
            pnl_pct=portfolio_pnl_pct,
            sp500_pnl_pct=sp500_pnl_pct,
        )

        stats["updated"] += 1
        logger.info(
            f"{pf_code}: ${portfolio_value:.2f} ({portfolio_pnl_pct:+.1f}%) "
            f"vs S&P500 {sp500_pnl_pct:+.1f}%"
        )

        # Clôture si fin de période
        if today >= end_date:
            close_portfolio(
                portfolio_id=pf_id,
                final_value=portfolio_value,
                benchmark_end=sp500_now or 0,
                pnl_pct=portfolio_pnl_pct,
                benchmark_pnl_pct=sp500_pnl_pct,
            )
            stats["closed"] += 1
            await _notify_portfolio_closed(pf_code, portfolio_pnl_pct, sp500_pnl_pct, portfolio_value)

            # Créer automatiquement le suivant (sauf annual)
            if pf_type in ("weekly", "monthly"):
                logger.info(f"Création automatique du prochain {pf_type}...")
                new_pf = await create_portfolio(pf_type)
                if new_pf:
                    stats["created"] += 1

    return stats


# ── Notifications Telegram ────────────────────────────────────────────────────

async def _notify_portfolio_created(portfolio: dict, positions: list, allocation: dict):
    """Envoie une notification Telegram à la création d'un portefeuille."""
    try:
        from tgbot.bot import send_message

        code      = portfolio["code"]
        pf_type   = portfolio["portfolio_type"]
        end_date  = portfolio["end_date"]
        rationale = allocation.get("rationale", "")
        market_ctx = allocation.get("market_context", "")

        type_emoji = {"weekly": "📅", "monthly": "🗓️", "annual": "📆"}.get(pf_type, "📊")
        type_label = {"weekly": "Hebdomadaire (7j)", "monthly": "Mensuel (30j)", "annual": "Annuel (365j)"}.get(pf_type, pf_type)

        lines = [
            f"{type_emoji} <b>CORTEX — Nouveau Portefeuille {code}</b>",
            f"<i>{type_label} · Échéance : {end_date}</i>",
            "",
            f"💡 <b>Stratégie :</b>",
            f"{rationale}",
            "",
        ]

        if market_ctx:
            lines += [f"📊 <b>Contexte :</b> {market_ctx}", ""]

        lines.append("<b>Allocation ($1 000) :</b>")
        for pos in positions:
            conv_emoji = {"forte": "🔥", "moyenne": "⚡", "faible": "👀"}.get(pos.get("conviction", ""), "•")
            lines.append(
                f"  {conv_emoji} <b>{pos['ticker']}</b> — "
                f"{pos['allocation_pct']:.0f}% (${pos['allocation_usd']:.0f}) "
                f"@ ${float(pos['entry_price']):,.2f}"
            )

        lines += ["", f"📈 Suivi quotidien activé. Résultats au bilan du dimanche."]

        await send_message("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Notification création portfolio échouée: {e}")


async def _notify_portfolio_closed(code: str, pnl_pct: float, sp500_pnl_pct: float, final_value: float):
    """Envoie une notification Telegram à la clôture d'un portefeuille."""
    try:
        from tgbot.bot import send_message

        beat    = pnl_pct > sp500_pnl_pct
        verdict = "✅ S&P 500 BATTU" if beat else "❌ SOUS S&P 500"
        emoji   = "🏆" if beat else "📉"

        msg = (
            f"{emoji} <b>CORTEX — Clôture {code}</b>\n\n"
            f"Résultat : <b>{pnl_pct:+.1f}%</b> (${final_value:.2f})\n"
            f"S&P 500   : <b>{sp500_pnl_pct:+.1f}%</b>\n\n"
            f"Verdict : {verdict}\n\n"
            f"🔄 Nouveau portefeuille en cours de création..."
        )
        await send_message(msg, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"Notification clôture portfolio échouée: {e}")


# ── Résumé pour le bilan hebdomadaire ─────────────────────────────────────────

def get_portfolios_summary() -> str:
    """Retourne un résumé HTML des portefeuilles actifs pour le bilan."""
    from database.client import get_active_portfolios, get_portfolio_history

    active  = get_active_portfolios()
    history = get_portfolio_history(limit=6)

    if not active and not history:
        return ""

    lines = ["<b>📊 PORTEFEUILLES PAPER TRADING</b>", ""]

    if active:
        lines.append("<b>Actifs :</b>")
        for pf in active:
            pnl    = float(pf.get("current_value", 1000)) - 1000
            pnl_pct = (pnl / 1000) * 100
            lines.append(
                f"  • <b>{pf['code']}</b> : ${pf['current_value']:.2f} "
                f"({pnl_pct:+.1f}%) — échéance {pf['end_date']}"
            )
        lines.append("")

    if history:
        wins  = sum(1 for h in history if h.get("beat_sp500"))
        total = len(history)
        lines.append(f"<b>Historique ({wins}/{total} beat S&P500) :</b>")
        for h in history[:4]:
            beat   = "✅" if h.get("beat_sp500") else "❌"
            lines.append(
                f"  {beat} <b>{h['code']}</b> {h.get('pnl_pct', 0):+.1f}% "
                f"vs S&P500 {h.get('benchmark_pnl_pct', 0):+.1f}%"
            )

    return "\n".join(lines)


# ── Points d'entrée ───────────────────────────────────────────────────────────

async def run_create_initial_portfolios():
    """Crée PW1 + PM1 + PA1 — à appeler une seule fois au lancement."""
    logger.info("Création des portefeuilles initiaux PW1 + PM1 + PA1...")
    pw, pm, pa = await asyncio.gather(
        create_portfolio("weekly"),
        create_portfolio("monthly"),
        create_portfolio("annual"),
    )
    logger.info(f"Portefeuilles créés : PW={bool(pw)}, PM={bool(pm)}, PA={bool(pa)}")
    return {"pw": pw, "pm": pm, "pa": pa}


async def run_daily_update():
    """Mise à jour quotidienne des prix + snapshots + clôtures."""
    logger.info("Mise à jour quotidienne des portefeuilles...")
    stats = await update_all_portfolios()
    logger.info(f"Update terminé : {stats}")
    return stats
