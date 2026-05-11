"""
CORTEX — Rapport de comparaison v2 → v3
Envoie sur Telegram un résumé de toutes les améliorations apportées.
"""
import asyncio
import os
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("version_report")


REPORT = """🚀 <b>CORTEX v3 — Rapport de mise à jour</b>
<i>Comparaison v2 → v3 · {date}</i>

━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ <b>INFRASTRUCTURE</b>

❌ <b>Avant :</b> Railway always-on (quota épuisé, app morte)
✅ <b>Après :</b> GitHub Actions cron (100% gratuit, sans carte bancaire)
→ Rapport matin 06h00 · Alertes toutes les 30min · Bilan dimanche 20h00

━━━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>ALERTES TELEGRAM</b>

❌ <b>Avant :</b> Envoi d'un lien vers le dashboard, pas de contenu réel
✅ <b>Après :</b> Vraie news traduite en français avec résumé + contexte
→ Seuil : uniquement les news ≥ 9/10 (impact macro/micro majeur)
→ Traduction automatique via Groq Llama 3.3 70B

━━━━━━━━━━━━━━━━━━━━━━━━

📡 <b>SOURCES IA (Phase 1)</b>

❌ <b>Avant :</b> GitHub trending + quelques RSS génériques
✅ <b>Après :</b> +7 sources officielles ajoutées :
  • Google AI Blog
  • Microsoft Research AI
  • Apple Machine Learning Research
  • AWS AI Blog
  • Hugging Face Blog
  • (+ CoinDesk, BBC, Reuters, CNBC, MarketWatch pour les alertes)

🏷️ <b>Tags signaux :</b> NOUVEAU MODÈLE · PARTNERSHIP/FUNDING · RECHERCHE · GITHUB/HUGGINGFACE · VIRAL COMMUNAUTÉ · BLOG OFFICIEL · NEWS IA

━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>CRYPTO & BTC (Phase 2)</b>

❌ <b>Avant :</b> Prix BTC via CoinGecko uniquement (échecs fréquents → $0 affiché)
✅ <b>Après :</b> Triple fallback automatique : CoinGecko → Binance → CryptoCompare

🔄 <b>Nouveau : Cycle BTC</b>
→ Détection automatique de phase : Accumulation / Markup / Distribution / Markdown
→ Score de cycle + conseil d'action

💥 <b>Nouveau : Liquidations</b>
→ Données Coinglass (fallback Binance forceOrders)
→ Long liq + Short liq en temps réel

━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>MACRO & MARCHÉS (Phase 3)</b>

❌ <b>Avant :</b> Données macro basiques (VIX, S&P, DXY)
✅ <b>Après :</b> 6 indicateurs FRED en temps réel :
  • T10Y2Y — Courbe des taux (inversion/normalisation)
  • ICSA — Inscriptions chômage hebdo
  • HOUST — Mises en chantier logement
  • UMCSENT — Confiance consommateurs Michigan
  • BAMLH0A0HYM2EY — Spread obligations high yield
  • RETAILSL — Ventes au détail USA

🎯 <b>Nouveau : CME FedWatch</b>
→ Probabilité hold/cut taux Fed à chaque rapport

━━━━━━━━━━━━━━━━━━━━━━━━

🎲 <b>DÉCISIONS DE TRADING (Phase 4)</b>

❌ <b>Avant :</b> Analyses sans suite, pas de tracking
✅ <b>Après :</b> Système complet de décisions :
  → 1 décision par secteur (IA, Crypto, Marchés) par jour
  → Direction : LONG ou WATCH
  → Horizon : 1W / 2W / 1M
  → Conviction : 0-100%
  → Suivi WIN/LOSS/NEUTRAL avec P&L%
  → Évaluation hebdo dans le Bilan du dimanche
  → CORTEX apprend de ses erreurs dans le temps

━━━━━━━━━━━━━━━━━━━━━━━━

📅 <b>BILAN HEBDOMADAIRE</b>

✅ Intègre maintenant les décisions ouvertes de la semaine
✅ Score global des décisions (% win rate)
✅ Compression mémoire longue après chaque bilan

━━━━━━━━━━━━━━━━━━━━━━━━

🏆 <b>RÉSUMÉ</b>

<b>CORTEX v3 est opérationnel.</b>
App gratuite · 4 phases livrées · Décisions trackées
Prochain rapport : demain 06h00 🌅
"""


async def send_version_report():
    from tgbot.bot import send_message

    date_str = datetime.now().strftime("%d/%m/%Y")
    msg = REPORT.format(date=date_str)

    logger.info("Envoi rapport version CORTEX v3...")
    result = await send_message(msg, parse_mode="HTML")
    if result:
        logger.info(f"Rapport envoyé ✅ (msg_id={result})")
    else:
        logger.error("Échec envoi rapport")


if __name__ == "__main__":
    asyncio.run(send_version_report())
