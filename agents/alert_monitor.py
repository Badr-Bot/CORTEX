"""
CORTEX — Agent ALERT-MONITOR
Surveille les seuils critiques de marché et envoie des alertes Telegram.
Tournée toutes les 30 minutes par le scheduler.

Seuils surveillés :
  - VIX spike  : hausse > 20% en séance
  - BTC crash  : variation 24h < -10%
  - SP500 chute : variation 24h < -3%
  - Or spike   : variation 24h > +3% (refuge)
  - DXY spike  : variation 24h > +1.5% (pression liquidités)
Cooldown : 2h par alerte (évite le spam)
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx

from utils.logger import get_logger

logger = get_logger("alert_monitor")

_STATE_FILE = Path(__file__).parent.parent / "data" / "alert_state.json"

THRESHOLDS = {
    "vix_spike":    {"label": "VIX SPIKE",   "condition": "vix_change_pct >= 20",  "emoji": "🔥"},
    "btc_crash":    {"label": "BTC CRASH",   "condition": "btc_change_24h <= -10", "emoji": "🚨"},
    "btc_rally":    {"label": "BTC RALLY",   "condition": "btc_change_24h >= 10",  "emoji": "🚀"},
    "sp500_chute":  {"label": "S&P CHUTE",   "condition": "sp500_change <= -3",    "emoji": "📉"},
    "or_refuge":    {"label": "OR REFUGE",   "condition": "gold_change >= 3",      "emoji": "🥇"},
    "dxy_spike":    {"label": "DXY SPIKE",   "condition": "dxy_change >= 1.5",     "emoji": "💵"},
}

COOLDOWN_HOURS = 2


def _load_state() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logger.warning(f"Impossible de sauver alert_state: {e}")


def _is_in_cooldown(state: dict, alert_key: str) -> bool:
    last_str = state.get(alert_key)
    if not last_str:
        return False
    try:
        last = datetime.fromisoformat(last_str)
        return datetime.now(timezone.utc) - last < timedelta(hours=COOLDOWN_HOURS)
    except Exception:
        return False


async def _fetch_market_snapshot() -> dict:
    """Récupère les données temps réel pour comparaison seuils."""
    snapshot = {}
    headers = {"User-Agent": "Mozilla/5.0"}

    async def _get(client: httpx.AsyncClient, key: str, symbol: str) -> None:
        try:
            r = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "5d"}, timeout=8,
            )
            if r.status_code != 200:
                return
            meta = r.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice") or 0
            prev = (meta.get("chartPreviousClose")
                    or meta.get("regularMarketPreviousClose")
                    or price)
            change = round((price - prev) / prev * 100, 2) if prev else 0
            snapshot[key] = {"price": price, "change_pct": change}
        except Exception as e:
            logger.debug(f"Alert fetch {symbol}: {e}")

    tickers = {
        "vix":   "^VIX",
        "sp500": "^GSPC",
        "gold":  "GC=F",
        "dxy":   "DX-Y.NYB",
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        await asyncio.gather(*[_get(client, k, v) for k, v in tickers.items()])

    # BTC via CoinGecko
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "CORTEX/1.0"}) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"},
                timeout=8,
            )
            btc = r.json().get("bitcoin", {})
            snapshot["btc"] = {
                "price": btc.get("usd", 0),
                "change_pct": round(btc.get("usd_24h_change", 0), 2),
            }
    except Exception as e:
        logger.debug(f"Alert fetch BTC: {e}")

    return snapshot


def _build_alert_message(alert_key: str, snapshot: dict) -> str:
    cfg = THRESHOLDS[alert_key]
    emoji = cfg["emoji"]
    label = cfg["label"]
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")

    lines = [f"{emoji} *ALERTE CORTEX — {label}* ({now})"]

    vix  = snapshot.get("vix", {})
    sp   = snapshot.get("sp500", {})
    btc  = snapshot.get("btc", {})
    gold = snapshot.get("gold", {})
    dxy  = snapshot.get("dxy", {})

    if "vix" in alert_key:
        lines.append(f"VIX : {vix.get('price', '?'):.1f} ({vix.get('change_pct', 0):+.1f}%)")
    if "btc" in alert_key:
        lines.append(f"BTC : ${btc.get('price', 0):,.0f} ({btc.get('change_pct', 0):+.1f}%)")
    if "sp500" in alert_key:
        lines.append(f"S&P 500 : {sp.get('price', 0):,.0f} ({sp.get('change_pct', 0):+.1f}%)")
    if "or" in alert_key:
        lines.append(f"Or : ${gold.get('price', 0):,.0f} ({gold.get('change_pct', 0):+.1f}%)")
    if "dxy" in alert_key:
        lines.append(f"DXY : {dxy.get('price', 0):.2f} ({dxy.get('change_pct', 0):+.1f}%)")

    lines.append("➡️ Ouvrir CORTEX")
    return "\n".join(lines)


async def check_and_send_alerts() -> list[str]:
    """
    Vérifie les seuils et envoie les alertes Telegram si déclenchées.
    Retourne la liste des alertes envoyées.
    """
    sent = []

    try:
        snapshot = await _fetch_market_snapshot()
        state = _load_state()
        now_iso = datetime.now(timezone.utc).isoformat()

        vix_change  = snapshot.get("vix",   {}).get("change_pct", 0)
        btc_change  = snapshot.get("btc",   {}).get("change_pct", 0)
        sp_change   = snapshot.get("sp500", {}).get("change_pct", 0)
        gold_change = snapshot.get("gold",  {}).get("change_pct", 0)
        dxy_change  = snapshot.get("dxy",   {}).get("change_pct", 0)

        triggers = {
            "vix_spike":   vix_change   >= 20,
            "btc_crash":   btc_change   <= -10,
            "btc_rally":   btc_change   >= 10,
            "sp500_chute": sp_change    <= -3,
            "or_refuge":   gold_change  >= 3,
            "dxy_spike":   dxy_change   >= 1.5,
        }

        from tgbot.bot import send_message

        for key, triggered in triggers.items():
            if not triggered:
                continue
            if _is_in_cooldown(state, key):
                logger.debug(f"Alert {key} en cooldown — skip")
                continue

            msg = _build_alert_message(key, snapshot)
            try:
                await send_message(msg, parse_mode="Markdown")
                state[key] = now_iso
                sent.append(key)
                logger.info(f"Alerte envoyée : {key}")
            except Exception as e:
                logger.error(f"Erreur envoi alerte {key}: {e}")

        if sent:
            _save_state(state)

        logger.info(
            f"Alert check: VIX {vix_change:+.1f}% | BTC {btc_change:+.1f}% | "
            f"SP500 {sp_change:+.1f}% | Alertes: {sent or 'aucune'}"
        )

    except Exception as e:
        logger.error(f"check_and_send_alerts erreur: {e}")

    return sent
