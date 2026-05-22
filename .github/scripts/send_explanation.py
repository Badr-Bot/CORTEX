import asyncio
import os
from telegram import Bot

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

MSG1 = (
    "CORTEX - Comment ca fonctionne (1/5)\n"
    "Vue d ensemble\n\n"
    "CORTEX est ton systeme d intelligence quotidienne automatise.\n"
    "Chaque matin a 06h00, il :\n\n"
    "1 Collecte des centaines de signaux (news IA, crypto, marches, science)\n"
    "2 Les filtre via un debat entre plusieurs IA gratuites\n"
    "3 Fait analyser les meilleurs par Claude\n"
    "4 Te genere un briefing structure sur Telegram\n\n"
    "Il tourne 100% en autonome sur GitHub Actions - tu n as rien a faire.\n\n"
    "Les workflows actifs :\n"
    "- Rapport du matin : tous les jours a 06h00\n"
    "- Alertes marches : toutes les 30 minutes (24h/24)\n"
    "- Portfolio update : chaque soir a 18h00\n"
    "- Bilan hebdo : dimanche soir"
)

MSG2 = (
    "CORTEX - Les Scouts (2/5)\n"
    "Etape 1 : Collecte des signaux\n\n"
    "5 agents Scout collectent en parallele :\n\n"
    "Scout IA - Medias tech (TechCrunch, MIT Review, OpenAI Blog, DeepMind, AWS...)\n"
    "  -> ~30 articles/jour\n\n"
    "Scout Marche - S&P 500, VIX, earnings, insider trades, secteurs\n"
    "  -> donnees temps reel + FRED macro (Fed, inflation, taux)\n\n"
    "Scout Crypto - News crypto/blockchain, prix BTC, Fear & Greed, flux exchange\n"
    "  -> ~44 news (24h)\n\n"
    "Scout DeepTech - arXiv (40+ papiers/jour), GitHub Trending, HackerNews, HuggingFace\n"
    "  -> signaux de recherche avant qu ils soient grand public\n\n"
    "Scout Faibles Signaux - Reddit (r/MachineLearning, r/LocalLLaMA...), tweets titans IA\n"
    "  -> ~100+ posts/jour\n\n"
    "En plus : un Crash Monitor (score /10) surveille le risque de crash\n"
    "via yield curve, VIX, spreads obligataires.\n\n"
    "Resultat : 200 a 250 signaux bruts collectes en moins de 20 secondes."
)

MSG3 = (
    "CORTEX - Le Board (3/5)\n"
    "Etape 2 : Le debat multi-IA\n\n"
    "C est ici que la magie opere. Les 200+ signaux sont d abord\n"
    "pre-filtres par Groq (Llama 3.3) : 200 -> 12 signaux par secteur.\n\n"
    "Ensuite, 2 IA gratuites debattent en 2 rounds pour chaque secteur\n"
    "(IA, Crypto, Marche, DeepTech) :\n\n"
    "ROUND 1 - Plaidoirie :\n"
    "  Llama 3.3 70B (Groq) vote ses 3 meilleurs signaux + justification\n"
    "  Gemma 2 (Groq) vote ses 3 meilleurs + justification\n\n"
    "ROUND 2 - Debat :\n"
    "  Chaque modele lit les picks des autres\n"
    "  Il SOUTIENT ou CHALLENGE les choix adverses avec des arguments\n\n"
    "ARBITRAGE (Claude Haiku) :\n"
    "  Lit tout le debat complet\n"
    "  Selectionne les 3-4 signaux les plus robustes\n"
    "  Criteres : consensus fort + meilleurs arguments\n\n"
    "Resultat : 12 signaux -> 3-4 signaux par secteur, les plus solides.\n"
    "Tout ca GRATUITEMENT via les IA open-source de Groq."
)

MSG4 = (
    "CORTEX - L Analyse (4/5)\n"
    "Etape 3 : Redaction par Claude\n\n"
    "Une fois les meilleurs signaux selectionnes par le Board,\n"
    "Claude Haiku analyse chaque secteur en parallele :\n\n"
    "Section IA - Analyse les 3-4 signaux IA retenus\n"
    "  implications business et technologiques\n\n"
    "Section Crypto - Direction marche (BULLISH/BEARISH/NEUTRE)\n"
    "  analyse on-chain, sentiment, risques\n\n"
    "Section Marche - Regime (BULL/BEAR/NEUTRE)\n"
    "  indicateurs macro FRED (Fed, inflation, taux US)\n\n"
    "Section DeepTech - Percees scientifiques\n"
    "  papiers arXiv a surveiller, implications futures\n\n"
    "Puis Claude SONNET genere le NEXUS - la synthese cross-sectorielle :\n"
    "  -> Y a-t-il un signal commun entre l IA, la crypto et les marches ?\n"
    "  -> Une question strategique pour orienter tes decisions du jour\n\n"
    "Resultat : 5 messages Telegram structures\n"
    "avec donnees temps reel + analyses detaillees."
)

MSG5 = (
    "CORTEX - Couts et Architecture (5/5)\n\n"
    "COUTS MENSUELS (apres optimisation) :\n"
    "  Claude Haiku - 4 analyses/jour + board arbitrage : ~1.50$/mois\n"
    "  Claude Sonnet - NEXUS uniquement (1 appel/jour) : ~1.00$/mois\n"
    "  Groq - Llama 3.3 + Gemma 2 + pre-filtrage : 0 euros (gratuit)\n"
    "  Gemini Flash - board 3eme membre : 0 euros (gratuit)\n"
    "  GitHub Actions - execution des workflows : 0 euros (repo public)\n"
    "  Supabase - base de donnees : 0 euros (free tier)\n"
    "  Telegram Bot - envoi des messages : 0 euros (gratuit)\n"
    "  TOTAL : 3 a 5 dollars par mois\n\n"
    "L intelligence principale est GRATUITE.\n"
    "Le board Groq/Llama fait le vrai travail de selection.\n"
    "Claude ne redige que depuis des signaux deja tries.\n\n"
    "CE QUE TU PEUX FAIRE :\n"
    "  Recevoir le rapport automatiquement chaque matin\n"
    "  Consulter le dashboard web\n"
    "  Gerer tes paper portfolios (PW/PM/PA)\n"
    "  /rapport - relire le dernier rapport\n"
    "  /help - toutes les commandes disponibles\n\n"
    "CORTEX tourne 24h/24, 7j/7, sans intervention.\n"
    "Le systeme est entierement autonome."
)


async def main():
    bot = Bot(token=TOKEN)
    for msg in [MSG1, MSG2, MSG3, MSG4, MSG5]:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        await asyncio.sleep(1)
    print("Explication envoyee avec succes")


asyncio.run(main())
