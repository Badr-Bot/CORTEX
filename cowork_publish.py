"""
CORTEX — Publication du rapport rédigé en mode cowork.

Étape 3 sur 3 : tourne dans GitHub Actions (qui détient les secrets), pas dans
l'agent cloud. Elle :

  1. lit le rapport rédigé par Claude + les chiffres collectés le même jour
  2. réinjecte les tableaux de bord chiffrés (cours, indicateurs) — le modèle ne
     retape jamais un prix, donc il ne peut pas en inventer un
  3. applique la déduplication 7 jours
  4. sauvegarde dans Supabase et notifie sur Telegram

Usage :
    python cowork_publish.py [AAAA-MM-JJ] [--dry-run]
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("cowork.publish")

COWORK_DIR = Path(__file__).parent / "data" / "cowork"


def _merge_dashboards(report: dict, donnees: dict) -> dict:
    """
    Réinjecte les chiffres relevés à la collecte.

    Les cours et indicateurs viennent des API, jamais du texte généré : c'est ce
    qui garantit qu'aucun prix affiché n'a été inventé ou périmé.
    """
    report.setdefault("crypto", {})["dashboard"] = donnees.get("crypto_dashboard", {})

    market = report.setdefault("market", {})
    market["dashboard"] = donnees.get("market_dashboard", {})
    market["hot_stocks"] = donnees.get("market_hot_stocks", [])
    market["crash"] = donnees.get("market_crash", {})

    ecom = report.setdefault("ecommerce", {})
    ecom["dashboard"] = donnees.get("ecommerce_dashboard", {})
    ecom["themes"] = donnees.get("ecommerce_themes", {})

    return report


def _dedup(report: dict) -> dict:
    from agents.dedup import filter_signals

    for sector in ("ai", "crypto", "market", "deeptech", "ecommerce"):
        section = report.get(sector)
        if not isinstance(section, dict):
            continue
        signals = section.get("signals", [])
        deduped = filter_signals(signals)
        if len(deduped) != len(signals):
            logger.info(f"Dedup [{sector}] : {len(signals)} → {len(deduped)} signaux")
        section["signals"] = deduped
    return report


def build_messages(report: dict) -> list[str]:
    import morning_report as mr

    return [
        mr.build_msg1(report.get("ai", {})),
        mr.build_msg2(report.get("crypto", {})),
        mr.build_msg3(report.get("market", {})),
        mr.build_msg4(report.get("deeptech", {})),
        mr.build_msg5(report.get("ecommerce", {})),
    ]


async def publish(date: str, dry_run: bool = False) -> int:
    report_path = COWORK_DIR / f"rapport_{date}.json"
    data_path = COWORK_DIR / f"donnees_{date}.json"

    if not report_path.exists():
        logger.error(f"Rapport introuvable : {report_path}")
        return 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    donnees = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else {}

    # Validation avant toute publication : un rapport cassé ne part pas.
    from cowork_check import check, check_donnees, _collect_urls

    for w in check_donnees(donnees):
        logger.warning(f"Chiffres du jour : {w}")

    result = check(report, _collect_urls(COWORK_DIR / f"collecte_{date}.md"))
    if result.errors:
        logger.error(f"Rapport invalide ({len(result.errors)} erreurs) — publication annulée")
        for e in result.errors[:10]:
            logger.error(f"  - {e}")
        return 1

    report = _merge_dashboards(report, donnees)
    report = _dedup(report)

    messages = build_messages(report)
    for i, msg in enumerate(messages, 1):
        logger.info(f"  MSG {i}: {len(msg)} caractères")

    signals_total = sum(
        len(report.get(s, {}).get("signals", []))
        for s in ("ai", "crypto", "market", "deeptech", "ecommerce")
    )
    autres_total = sum(
        len(report.get(s, {}).get("autres_news", []) or [])
        for s in ("ai", "crypto", "market", "deeptech", "ecommerce")
    )
    outils_total = len(report.get("ecommerce", {}).get("outils", []) or [])
    logger.info(f"Contenu : {signals_total} signaux, {autres_total} autres news, {outils_total} outils")

    if dry_run:
        logger.info(f"Essai à blanc — {signals_total} signaux, rien n'a été publié")
        return 0

    try:
        from database.client import save_dashboard_report
        await save_dashboard_report(
            report_date=date,
            ai_data=report.get("ai", {}),
            crypto_data=report.get("crypto", {}),
            market_data=report.get("market", {}),
            deeptech_data=report.get("deeptech", {}),
            ecommerce_data=report.get("ecommerce", {}),
            signals_count=signals_total,
        )
        logger.info("Rapport sauvegardé dans Supabase ✅")
    except Exception as e:
        logger.error(f"Sauvegarde Supabase échouée : {e}")
        return 1

    try:
        from agents.context import save_daily
        save_daily(
            report.get("ai", {}), report.get("crypto", {}), report.get("market", {}),
            report.get("deeptech", {}), report.get("ecommerce", {}),
        )
    except Exception as e:
        logger.warning(f"Sauvegarde du contexte échouée (non bloquant) : {e}")

    try:
        from agents.dedup import mark_sent
        all_signals = [
            sig for s in ("ai", "crypto", "market", "deeptech", "ecommerce")
            for sig in report.get(s, {}).get("signals", [])
        ]
        mark_sent(all_signals)
    except Exception as e:
        logger.warning(f"Marquage dedup échoué (non bloquant) : {e}")

    try:
        import morning_report as mr
        from tgbot.bot import broadcast_message

        msg = (
            f"☀️ <b>Rapport du {mr._fr_date()}</b>\n\n"
            f"⚡️ Ton briefing du matin est prêt.\n\n"
            f"➡️ <a href=\"https://cortex-seven-omega.vercel.app\">Ouvrir CORTEX</a>"
        )
        await broadcast_message(msg, parse_mode="HTML")
        logger.info("Notification Telegram envoyée ✅")
    except Exception as e:
        logger.error(f"Notification Telegram échouée : {e}")

    logger.info(f"Publication terminée — {signals_total} signaux")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    date = args[0] if args else datetime.now().strftime("%Y-%m-%d")
    return asyncio.run(publish(date, dry_run))


if __name__ == "__main__":
    sys.exit(main())
