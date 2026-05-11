"""
Script de régénération ciblée : Crypto + Marché uniquement.
Met à jour le rapport du jour dans Supabase sans toucher IA/DeepTech/Nexus.
"""
import asyncio, json, sys, os
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from agents.scout_crypto import collect_dashboard as crypto_dashboard, collect_signals as crypto_signals
from agents.scout_market  import collect_dashboard as market_dashboard, collect_signals as market_signals
from agents.summarizer    import analyze_crypto, analyze_market

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

async def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    today = date.today().isoformat()

    # --- Charger le rapport existant ---
    res = sb.table("daily_reports").select("*").eq("report_date", today).execute()
    if not res.data:
        print(f"[ERR] Aucun rapport trouvé pour {today}")
        return
    report = res.data[0]
    rj = report["report_json"]
    print(f"[OK] Rapport trouvé: {report['id']} — {report['signals_count']} signaux")

    # --- Crypto ---
    print("\n[...] Collecte données Crypto...")
    c_dash, c_sigs = await asyncio.gather(
        crypto_dashboard(),
        crypto_signals(),
    )
    print(f"   Dashboard BTC: ${c_dash.get('btc_price', 'N/A')}")
    print(f"   Signaux bruts: {len(c_sigs)}")

    print("[AI] Analyse Crypto (Claude)...")
    crypto_data = await analyze_crypto({"dashboard": c_dash, "signals": c_sigs})
    print(f"   Phase: {crypto_data.get('phase')} | Direction: {crypto_data.get('direction')}")
    print(f"   Signaux retenus: {len(crypto_data.get('signals', []))}")

    # --- Marché ---
    print("\n[...] Collecte données Marché...")
    m_dash, m_sigs = await asyncio.gather(
        market_dashboard(),
        market_signals(),
    )
    sp = m_dash.get("sp500", {})
    print(f"   S&P500: {sp.get('price')} ({sp.get('change_pct', 0):+.2f}%)")

    print("[AI] Analyse Marché (Claude)...")
    market_data = await analyze_market({"dashboard": m_dash, "signals": m_sigs})
    print(f"   Recession score: {market_data.get('recession_score')}/10")
    print(f"   Indicateurs: {len(market_data.get('recession_indicators', {}))}")
    print(f"   Signaux retenus: {len(market_data.get('signals', []))}")

    # --- Mettre à jour le report_json ---
    rj["crypto"] = crypto_data
    rj["market"] = market_data

    new_count = (
        len(rj.get("ai", {}).get("signals", []))
        + len(crypto_data.get("signals", []))
        + len(market_data.get("signals", []))
        + len(rj.get("deeptech", {}).get("signals", []))
    )

    sb.table("daily_reports").update({
        "report_json":   rj,
        "signals_count": new_count,
    }).eq("id", report["id"]).execute()

    print(f"\n[OK] Rapport mis à jour — {new_count} signaux total")
    print("[>>] Rechargez le dashboard dans votre navigateur.")

if __name__ == "__main__":
    asyncio.run(main())
