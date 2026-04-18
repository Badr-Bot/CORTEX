"""
CORTEX — Agent SCOUT-MARKET v1
Collecte : dashboard marchés temps réel + signaux news macro

Sources :
  - Yahoo Finance API (gratuit, sans clé) — S&P500, Nasdaq, Or, Pétrole, DXY, VIX, US 10Y
  - RSS : Reuters Markets, FT Markets, MarketWatch, Seeking Alpha, Yahoo Finance
  - Yahoo Finance quoteSummary API : Earnings calendar (7 prochains jours)
  - openinsider.com : Insider trading (achats > $100K, 3 derniers jours)
"""

import asyncio
import feedparser
import httpx
import re
from datetime import datetime, timezone, timedelta
from utils.logger import get_logger

logger = get_logger("scout_ai.market")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

TICKERS = {
    "sp500":   "^GSPC",
    "nasdaq":  "^IXIC",
    "gold":    "GC=F",
    "oil":     "CL=F",
    "dxy":     "DX-Y.NYB",
    "vix":     "^VIX",
    "us_10y":  "^TNX",
}

MARKET_NEWS_FEEDS = [
    {"name": "Reuters Markets",  "url": "https://feeds.reuters.com/reuters/businessNews"},
    {"name": "MarketWatch",      "url": "https://feeds.marketwatch.com/marketwatch/topstories/"},
    {"name": "Yahoo Finance",    "url": "https://finance.yahoo.com/news/rssindex"},
    {"name": "Seeking Alpha",    "url": "https://seekingalpha.com/market_currents.xml"},
    {"name": "FT Markets",       "url": "https://www.ft.com/rss/home/uk"},
]

EARNINGS_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD",
    "NFLX", "CRM", "ORCL", "INTC", "QCOM", "AVGO", "TSM", "ASML",
    "ADBE", "SHOP", "SNOW", "PLTR", "ARM", "SMCI",
]

MARKET_KEYWORDS = [
    "fed", "federal reserve", "rate", "inflation", "gdp", "recession",
    "earnings", "s&p", "nasdaq", "dow", "equity", "bond", "yield",
    "dollar", "dxy", "gold", "oil", "crude", "vix", "volatility",
    "macro", "jobs", "nfp", "cpi", "pce", "fomc", "pivot", "taper",
    "market", "stock", "rally", "selloff", "correction", "bear", "bull",
    "china", "europe", "ecb", "tariff", "trade war", "geopolitical",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_market_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in MARKET_KEYWORDS)


def _vix_interpretation(vix: float) -> str:
    if vix < 15:   return "Complaisance extrême"
    if vix < 20:   return "Calme"
    if vix < 25:   return "Légère nervosité"
    if vix < 30:   return "Volatilité élevée"
    if vix < 40:   return "Stress marché"
    return "Panique"


def _direction_arrow(change_pct: float) -> str:
    return "▴" if change_pct >= 0 else "▾"


def _format_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


# ── Earnings Calendar ─────────────────────────────────────────────────────────

async def collect_earnings_calendar() -> list[dict]:
    """
    Récupère les earnings des 7 prochains jours via Yahoo Finance quoteSummary API.
    Retourne une liste de dicts : ticker, name, date, est_eps, days_until.
    """
    today = datetime.now(timezone.utc).date()
    horizon = today + timedelta(days=7)
    results = []

    async def _fetch_ticker(sym: str, client: httpx.AsyncClient) -> dict | None:
        try:
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}"
            r = await client.get(url, params={"modules": "calendarEvents,quoteType"}, timeout=8)
            if r.status_code != 200:
                return None
            data = r.json().get("quoteSummary", {}).get("result", [{}])[0]
            cal = data.get("calendarEvents", {})
            name = data.get("quoteType", {}).get("longName") or sym
            earnings_obj = cal.get("earnings", {})
            earnings_dates = earnings_obj.get("earningsDate", [])
            for ed_entry in earnings_dates:
                raw = ed_entry.get("fmt") or ed_entry.get("raw")
                if not raw:
                    continue
                try:
                    if isinstance(raw, int):
                        ed_date = datetime.fromtimestamp(raw, tz=timezone.utc).date()
                    else:
                        ed_date = datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
                except Exception:
                    continue
                if today <= ed_date <= horizon:
                    eps_est = None
                    try:
                        avg = earnings_obj.get("earningsAverage", {})
                        eps_est = float(avg.get("raw", 0)) if avg else None
                    except Exception:
                        pass
                    return {
                        "ticker": sym, "name": name,
                        "date": str(ed_date),
                        "est_eps": eps_est,
                        "days_until": (ed_date - today).days,
                    }
        except Exception as e:
            logger.debug(f"Earnings {sym}: {e}")
        return None

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            tasks = [_fetch_ticker(sym, client) for sym in EARNINGS_TICKERS]
            fetched = await asyncio.gather(*tasks, return_exceptions=True)
        results = [r for r in fetched if isinstance(r, dict)]
        results.sort(key=lambda x: x["days_until"])
        logger.info(f"Earnings calendar: {len(results)} résultats dans les 7 prochains jours")
    except Exception as e:
        logger.warning(f"collect_earnings_calendar erreur: {e}")

    return results


# ── Insider Trading SEC EDGAR ──────────────────────────────────────────────────

async def collect_insider_trades() -> list[dict]:
    """
    Récupère les achats d'initiés (Form 4 SEC) via openinsider.com.
    Filtre : uniquement BUY, montant > $100K, dans les 3 derniers jours.
    """
    # openinsider screener : achats (xp=1), valeur > $100K (vl=100), 3 derniers jours (fd=3)
    url = (
        "http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=3&fdr=&td=0&tdr=&"
        "fdlyl=&fdlyh=&daysago=&xp=1&vl=100&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&"
        "grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&"
        "sortcol=0&cnt=20&Action=0"
    )
    trades = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            r = await client.get(url, timeout=10)
            r.raise_for_status()

        # Parse HTML — tableau openinsider
        from html.parser import HTMLParser
        class TableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_td = False; self.rows = []; self.current = []; self.cell = []
            def handle_starttag(self, tag, attrs):
                if tag == "tr": self.current = []
                if tag == "td": self.in_td = True; self.cell = []
            def handle_endtag(self, tag):
                if tag == "td":
                    self.in_td = False
                    self.current.append(" ".join(self.cell).strip())
                if tag == "tr" and len(self.current) >= 13:
                    self.rows.append(self.current[:])
            def handle_data(self, data):
                if self.in_td and data.strip(): self.cell.append(data.strip())

        parser = TableParser()
        parser.feed(r.text)

        for row in parser.rows:
            try:
                # Colonnes réelles openinsider: [0]=DM [1]=Filing Date [2]=Trade Date
                # [3]=Ticker [4]=Company [5]=Insider [6]=Title [7]=Trade Type
                # [8]=Price [9]=Qty [10]=Owned [11]=ΔOwn [12]=Value
                if len(row) < 13: continue
                trade_type = row[7].strip().upper()
                if "P - PURCHASE" not in trade_type: continue
                ticker  = row[3].strip()
                company = row[4].strip()
                insider = row[5].strip()
                date    = row[2].strip()
                value_raw = row[12].replace("$","").replace(",","").replace("+","").strip()
                value_usd = int(float(value_raw)) if value_raw else 0
                if value_usd < 100_000: continue
                shares_raw = row[9].replace(",","").replace("+","").strip()
                shares = int(float(shares_raw)) if shares_raw else 0
                trades.append({
                    "insider": insider, "company": company, "ticker": ticker,
                    "type": "BUY", "shares": shares, "value_usd": value_usd, "date": date,
                })
            except Exception:
                continue

        trades.sort(key=lambda x: x["value_usd"], reverse=True)
        logger.info(f"Insider trades: {len(trades)} achats > $100K (3 derniers jours)")
    except Exception as e:
        logger.warning(f"collect_insider_trades erreur: {e}")
    return trades


# ── Collecte dashboard (Yahoo Finance) ───────────────────────────────────────

async def _fetch_ticker(client: httpx.AsyncClient, key: str, symbol: str) -> tuple[str, dict]:
    """Récupère prix actuel + variation 1j pour un ticker Yahoo Finance."""
    try:
        r = await client.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={"interval": "1d", "range": "5d"},
            timeout=10,
        )
        data = r.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})

        price = meta.get("regularMarketPrice", 0)

        # Priorité : chartPreviousClose > regularMarketPreviousClose > previousClose
        # Évite le bug weekend où previousClose = regularMarketPrice → change_pct = 0
        prev = (
            meta.get("chartPreviousClose") or
            meta.get("regularMarketPreviousClose") or
            meta.get("previousClose")
        )

        if prev and prev != price:
            change_pct = (price - prev) / prev * 100
        else:
            # Fallback : last two closes from historical data (fonctionne même le weekend)
            quotes = result.get("indicators", {}).get("quote", [{}])
            closes = [c for c in (quotes[0].get("close") or []) if c is not None] if quotes else []
            if len(closes) >= 2 and closes[-2]:
                change_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
            else:
                change_pct = 0.0

        # Formatting selon le ticker
        if key == "gold":
            price_str = f"${price:,.0f}"
        elif key == "oil":
            price_str = f"${price:.1f}"
        elif key in ("dxy",):
            price_str = f"{price:.1f}"
        elif key == "vix":
            price_str = f"{price:.1f}"
        elif key == "us_10y":
            price_str = f"{price:.2f}%"
        else:
            price_str = f"{price:,.0f}"

        return key, {
            "price":      price_str,
            "change_pct": change_pct,
            "raw_price":  price,
        }
    except Exception as e:
        logger.warning(f"Yahoo Finance {symbol}: {e}")
        return key, {"price": "N/A", "change_pct": 0.0, "raw_price": 0}


async def collect_dashboard() -> dict:
    """Récupère tous les indicateurs marché en parallèle via Yahoo Finance."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [_fetch_ticker(client, k, v) for k, v in TICKERS.items()]
        ticker_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Récupérer earnings + insider en parallèle avec les tickers
    earnings_result, insider_result = await asyncio.gather(
        collect_earnings_calendar(),
        collect_insider_trades(),
        return_exceptions=True,
    )

    dashboard = {}
    for r in ticker_results:
        if isinstance(r, tuple):
            key, data = r
            dashboard[key] = data

    # Calculer variation 10Y en bps
    if "us_10y" in dashboard:
        chg = dashboard["us_10y"].get("change_pct", 0)
        raw = dashboard["us_10y"].get("raw_price", 4.0)
        bps = round(raw * chg / 100 * 100, 1)  # approximate bps
        dashboard["us_10y"]["change_bps"] = f"{'+' if bps >= 0 else ''}{bps:.0f}bps"

    # VIX interprétation
    if "vix" in dashboard:
        vix_val = dashboard["vix"].get("raw_price", 20)
        dashboard["vix"]["interpretation"] = _vix_interpretation(vix_val)

    # Earnings calendar (7 prochains jours)
    dashboard["earnings_week"] = earnings_result if isinstance(earnings_result, list) else []

    # Insider buys (3 derniers jours, > $100K)
    dashboard["insider_buys"] = insider_result if isinstance(insider_result, list) else []

    logger.info(
        f"Dashboard marché: S&P {dashboard.get('sp500', {}).get('price', 'N/A')}, "
        f"VIX {dashboard.get('vix', {}).get('price', 'N/A')} | "
        f"Earnings: {len(dashboard['earnings_week'])} | "
        f"Insiders: {len(dashboard['insider_buys'])}"
    )
    return dashboard


# ── Collecte signaux news ─────────────────────────────────────────────────────

async def _fetch_rss_feed(feed_info: dict, hours: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    signals = []
    try:
        feed = await asyncio.to_thread(feedparser.parse, feed_info["url"])
        for entry in feed.entries[:15]:
            pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub:
                try:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            title   = entry.get("title", "").strip()
            url     = entry.get("link", "")
            content = entry.get("summary", entry.get("description", ""))[:400]

            if not title or not url:
                continue
            if not _is_market_relevant(title + " " + content):
                continue

            signals.append({
                "title":       title,
                "source_name": feed_info["name"],
                "source_url":  url,
                "raw_content": content,
                "sector":      "market",
                "category":    "media",
            })
    except Exception as e:
        logger.warning(f"Market RSS {feed_info['name']}: {e}")
    return signals


async def collect_signals(hours: int = 24) -> list[dict]:
    """Collecte les signaux news marchés depuis tous les flux RSS."""
    results = await asyncio.gather(
        *[_fetch_rss_feed(f, hours) for f in MARKET_NEWS_FEEDS],
        return_exceptions=True,
    )
    signals = []
    for r in results:
        if isinstance(r, list):
            signals.extend(r)

    # Déduplication
    seen, unique = set(), []
    for s in signals:
        if s["source_url"] not in seen:
            seen.add(s["source_url"])
            unique.append(s)

    logger.info(f"SCOUT-MARKET signaux: {len(unique)} news ({hours}h)")
    return unique


# ── Point d'entrée principal ──────────────────────────────────────────────────

async def collect(hours: int = 24) -> dict:  # noqa: E302
    """
    Lance la collecte complète SCOUT-MARKET.
    Retourne : {dashboard: dict, signals: list[dict], hot_stocks: list[dict], crash: dict}
    """
    from agents.sources.stock_screener import collect as collect_stocks
    from agents.sources.crash_monitor import collect as collect_crash

    dashboard, signals, hot_stocks = await asyncio.gather(
        collect_dashboard(),
        collect_signals(hours),
        collect_stocks(hours),
    )

    # Passe le VIX déjà collecté pour éviter une double requête
    vix_raw = dashboard.get("vix", {}).get("raw_price") if isinstance(dashboard, dict) else None
    crash = await collect_crash(vix=vix_raw)

    logger.info(
        f"SCOUT-MARKET: {len(hot_stocks)} actions chaudes | "
        f"crash score={crash.get('crash_score', '?')}/10 {crash.get('color', '')}"
    )
    return {"dashboard": dashboard, "signals": signals, "hot_stocks": hot_stocks, "crash": crash}
