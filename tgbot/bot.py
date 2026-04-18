"""
CORTEX — Bot Telegram
Gère l'envoi de messages, rapports et questions matinales
Sécurité : répond UNIQUEMENT au TELEGRAM_CHAT_ID autorisé
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Optional

from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

from utils.logger import get_logger

logger = get_logger("telegram")

# Limite de caractères Telegram par message
TELEGRAM_MAX_CHARS = 4096


def get_bot_token() -> str:
    """Retourne le token du bot depuis les variables d'environnement."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN manquant dans .env")
    return token


def get_authorized_chat_id() -> int:
    """Retourne le chat ID autorisé depuis les variables d'environnement."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID manquant dans .env")
    return int(chat_id)


# ============================================================
# Fonctions d'envoi de messages
# ============================================================

async def send_message(text: str, parse_mode: str = "Markdown") -> Optional[str]:
    """
    Envoie un message simple au chat autorisé.

    Args:
        text: Texte du message
        parse_mode: Format ('Markdown' ou 'HTML')

    Returns:
        ID du message Telegram ou None en cas d'erreur
    """
    try:
        bot = Bot(token=get_bot_token())
        chat_id = get_authorized_chat_id()

        # Découpe automatique si le message dépasse la limite
        if len(text) <= TELEGRAM_MAX_CHARS:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            logger.info(f"Message envoyé (ID: {msg.message_id}, {len(text)} chars)")
            return str(msg.message_id)
        else:
            # Envoi en plusieurs parties
            parts = _split_message(text, TELEGRAM_MAX_CHARS)
            last_msg_id = None
            for i, part in enumerate(parts):
                msg = await bot.send_message(
                    chat_id=chat_id,
                    text=part,
                    parse_mode=parse_mode
                )
                last_msg_id = str(msg.message_id)
                logger.info(f"Message partie {i+1}/{len(parts)} envoyée (ID: {msg.message_id})")
                await asyncio.sleep(0.5)  # Évite le rate limiting
            return last_msg_id

    except TelegramError as e:
        logger.error(f"Erreur Telegram lors de l'envoi : {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue send_message : {e}")
        return None


async def broadcast_message(text: str, parse_mode: str = "Markdown") -> int:
    """
    Envoie un message à Badr ET à tous les abonnés approuvés.
    Retourne le nombre de destinataires ayant reçu le message.

    Args:
        text: Texte du message
        parse_mode: Format ('Markdown' ou 'HTML')

    Returns:
        Nombre de messages envoyés avec succès
    """
    try:
        from database.client import get_approved_subscribers

        bot = Bot(token=get_bot_token())
        admin_id = get_authorized_chat_id()

        # Liste complète : admin + abonnés approuvés (sans doublons)
        subscribers = await get_approved_subscribers()
        subscriber_ids = {s["chat_id"] for s in subscribers}
        all_recipients = {admin_id} | subscriber_ids

        sent_count = 0
        for chat_id in all_recipients:
            try:
                parts = _split_message(text, TELEGRAM_MAX_CHARS)
                for part in parts:
                    await bot.send_message(chat_id=chat_id, text=part, parse_mode=parse_mode)
                    await asyncio.sleep(0.3)
                sent_count += 1
            except TelegramError as e:
                logger.warning(f"Échec envoi à chat_id={chat_id} : {e}")

        logger.info(f"Broadcast envoyé à {sent_count}/{len(all_recipients)} destinataires")
        return sent_count

    except Exception as e:
        logger.error(f"Erreur broadcast_message : {e}")
        # Fallback : envoi admin uniquement
        await send_message(text, parse_mode)
        return 1


async def send_report(sections: list[dict]) -> Optional[str]:
    """
    Formate et envoie le rapport du matin.
    Chaque section a : emoji, title, content.
    Découpe automatiquement si trop long.

    Args:
        sections: Liste de dicts avec clés 'emoji', 'title', 'content'

    Returns:
        ID du dernier message envoyé ou None en cas d'erreur

    Exemple de section:
        {'emoji': '🤖', 'title': 'IA & Machine Learning', 'content': 'Résumé...'}
    """
    try:
        # Construction du rapport formaté
        lines = []
        lines.append(f"📊 *RAPPORT CORTEX — {datetime.now().strftime('%d/%m/%Y')}*")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")

        for section in sections:
            emoji = section.get("emoji", "•")
            title = section.get("title", "Section")
            content = section.get("content", "")

            lines.append(f"\n{emoji} *{title}*")
            lines.append(content)
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"_Généré par CORTEX à {datetime.now().strftime('%H:%M')}_")

        full_report = "\n".join(lines)

        # Envoi (avec découpage automatique si nécessaire)
        msg_id = await send_message(full_report)
        logger.info(f"Rapport envoyé ({len(sections)} sections, {len(full_report)} chars)")
        return msg_id

    except Exception as e:
        logger.error(f"Erreur send_report : {e}")
        return None


async def ask_morning_question(question: str, send: bool = True) -> Optional[str]:
    """
    Enregistre la question du matin dans le journal Supabase.
    Si send=True, envoie aussi le message Telegram (utile si la question
    n'est pas déjà incluse dans le rapport).

    Args:
        question: Question à poser
        send: Si True, envoie le message Telegram (défaut: True)

    Returns:
        None
    """
    try:
        from database.client import insert_journal_entry

        if send:
            await send_message(question)
            logger.info(f"Question du matin envoyée : {question[:60]}...")
        else:
            logger.info(f"Question du matin enregistrée (dans rapport) : {question[:60]}...")

        # Création de l'entrée journal — la réponse de Badr sera captée
        # automatiquement via handle_journal_response() en mode polling
        await insert_journal_entry(question_asked=question)
        return None

    except Exception as e:
        logger.error(f"Erreur ask_morning_question : {e}")
        return None


# ============================================================
# Handlers de commandes Telegram
# ============================================================

def _is_authorized(update: Update) -> bool:
    """
    Vérifie si le message vient du chat autorisé.
    Sécurité : toute autre source est ignorée et loguée.

    Args:
        update: Mise à jour Telegram

    Returns:
        True si autorisé, False sinon
    """
    authorized_id = get_authorized_chat_id()
    sender_id = update.effective_chat.id

    if sender_id != authorized_id:
        logger.warning(
            f"Message ignoré — source non autorisée : chat_id={sender_id} "
            f"(autorisé: {authorized_id})"
        )
        return False
    return True


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /status → État du système, dernière exécution, nb de signaux ce mois.
    """
    if not _is_authorized(update):
        return

    try:
        from database.client import get_recent_signals, get_last_daily_report

        # Nombre de signaux ce mois
        signals = await get_recent_signals(hours=720)  # ~30 jours
        last_report = await get_last_daily_report()

        last_report_time = "Aucun rapport envoyé"
        if last_report:
            sent_at = last_report.get("sent_at", "")
            last_report_time = sent_at[:16].replace("T", " ") if sent_at else "Inconnu"

        status_msg = (
            "🟢 *CORTEX — Statut système*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📡 Système : opérationnel\n"
            f"🗄️ Database : connectée\n"
            f"🤖 Agents : en construction 🔧\n\n"
            f"📊 Signaux ce mois : *{len(signals)}*\n"
            f"📅 Dernier rapport : {last_report_time}\n\n"
            f"_Interrogé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}_"
        )

        await update.message.reply_text(status_msg, parse_mode="Markdown")
        logger.info("Commande /status exécutée")

    except Exception as e:
        logger.error(f"Erreur cmd_status : {e}")
        await update.message.reply_text("❌ Erreur lors de la récupération du statut.")


async def cmd_rapport(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /rapport → Renvoie le dernier rapport.
    Accessible à Badr ET à tous les abonnés approuvés.
    """
    from database.client import get_last_daily_report, get_approved_subscribers

    chat_id  = update.effective_chat.id
    admin_id = get_authorized_chat_id()

    # Vérifie que l'appelant est admin ou abonné approuvé
    if chat_id != admin_id:
        subscribers = await get_approved_subscribers()
        approved_ids = {s["chat_id"] for s in subscribers}
        if chat_id not in approved_ids:
            await update.message.reply_text(
                "⛔ Accès refusé.\nUtilise /abonner pour t'inscrire à CORTEX.",
                parse_mode="Markdown"
            )
            return

    try:
        last_report = await get_last_daily_report()

        if not last_report:
            await update.message.reply_text(
                "📭 Aucun rapport disponible pour l'instant.\n"
                "Le prochain rapport sera envoyé demain à 6h00.",
                parse_mode="Markdown"
            )
            return

        report_content = last_report.get("report_content", "Contenu indisponible")
        sent_at = last_report.get("sent_at", "")[:16].replace("T", " ")

        header = f"📋 *Dernier rapport — {sent_at}*\n\n"
        # Envoyer uniquement à ce chat (pas broadcast — c'est une demande individuelle)
        bot = Bot(token=get_bot_token())
        parts = _split_message(header + report_content, TELEGRAM_MAX_CHARS)
        for part in parts:
            await bot.send_message(chat_id=chat_id, text=part, parse_mode="Markdown")
            await asyncio.sleep(0.5)

        logger.info(f"Commande /rapport exécutée pour chat_id={chat_id}")

    except Exception as e:
        logger.error(f"Erreur cmd_rapport : {e}")
        await update.message.reply_text("❌ Erreur lors de la récupération du rapport.")


async def cmd_journal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /journal → Résumé des 7 dernières réponses du journal.
    """
    if not _is_authorized(update):
        return

    try:
        from database.client import get_recent_journal_entries

        entries = await get_recent_journal_entries(limit=7)

        if not entries:
            await update.message.reply_text(
                "📓 Journal vide pour l'instant.\n"
                "Les entrées apparaîtront après le premier rapport du matin.",
                parse_mode="Markdown"
            )
            return

        lines = ["📓 *Ton journal — 7 dernières entrées*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]

        for i, entry in enumerate(entries, 1):
            date = entry.get("date", "")
            response = entry.get("your_response") or "_Pas encore répondu_"
            mood = entry.get("mood_signal") or "non défini"

            # Tronque les réponses longues
            if len(response) > 200:
                response = response[:200] + "..."

            lines.append(f"*{i}. {date}* ({mood})")
            lines.append(response)
            lines.append("")

        journal_text = "\n".join(lines)
        await send_message(journal_text)
        logger.info(f"Commande /journal exécutée — {len(entries)} entrées envoyées")

    except Exception as e:
        logger.error(f"Erreur cmd_journal : {e}")
        await update.message.reply_text("❌ Erreur lors de la récupération du journal.")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /help → Liste des commandes disponibles.
    """
    if not _is_authorized(update):
        return

    is_admin = update.effective_chat.id == get_authorized_chat_id()

    base_help = (
        "🤖 *CORTEX — Commandes disponibles*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "/abonner — S'abonner aux rapports quotidiens\n"
        "/desabonner — Se désabonner\n"
        "/rapport — Demander le dernier rapport\n"
        "/help — Cette aide\n\n"
        "_IA \u2022 Crypto \u2022 March\u00e9s \u2022 DeepTech_"
    )

    admin_help = (
        "🤖 *CORTEX — Commandes disponibles*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑 *Admin*\n"
        "/status — État du système\n"
        "/rapport — Dernier rapport\n"
        "/journal — 7 dernières réponses\n"
        "/abonnes — Liste des abonnés\n"
        "/approuver <id> — Approuver un abonné\n\n"
        "👥 *Tous*\n"
        "/abonner — S'abonner aux rapports\n"
        "/desabonner — Se désabonner\n"
        "/help — Cette aide\n\n"
        "_IA \u2022 Crypto \u2022 March\u00e9s \u2022 DeepTech_"
    )

    help_text = admin_help if is_admin else base_help

    await update.message.reply_text(help_text, parse_mode="Markdown")
    logger.info("Commande /help exécutée")


async def cmd_abonner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /abonner → S'inscrire pour recevoir les rapports CORTEX.
    Envoie une demande d'approbation à Badr.
    """
    from database.client import subscribe_user

    user = update.effective_user
    chat_id = update.effective_chat.id
    admin_id = get_authorized_chat_id()

    # Badr n'a pas besoin de s'abonner (il reçoit tout par défaut)
    if chat_id == admin_id:
        await update.message.reply_text(
            "👑 Tu es l'admin CORTEX — tu reçois déjà tous les rapports.",
            parse_mode="Markdown"
        )
        return

    record = await subscribe_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name or user.full_name,
    )

    if record is None:
        await update.message.reply_text("❌ Erreur lors de l'inscription. Réessaie plus tard.")
        return

    if record.get("approved"):
        await update.message.reply_text(
            "✅ Tu es déjà abonné à CORTEX !\nTu reçois les rapports chaque matin à 6h00.",
            parse_mode="Markdown"
        )
        return

    # Déjà en attente mais pas approuvé
    already_pending = record.get("subscribed_at") and not record.get("approved")

    await update.message.reply_text(
        "📬 *Demande d'abonnement envoyée !*\n\n"
        "En attente d'approbation. Tu recevras une notification dès que Badr valide.",
        parse_mode="Markdown"
    )

    # Notifie Badr
    name = user.first_name or user.username or str(chat_id)
    username_str = f"@{user.username}" if user.username else "sans @"
    notif = (
        f"🔔 *Nouvelle demande d'abonnement CORTEX*\n\n"
        f"👤 {name} ({username_str})\n"
        f"🆔 `{chat_id}`\n\n"
        f"Pour approuver :\n`/approuver {chat_id}`\n\n"
        f"Pour refuser (ne pas approuver, il restera en attente) : ignore."
    )
    try:
        bot = Bot(token=get_bot_token())
        await bot.send_message(chat_id=admin_id, text=notif, parse_mode="Markdown")
    except TelegramError as e:
        logger.error(f"Impossible de notifier l'admin : {e}")

    logger.info(f"Demande d'abonnement : chat_id={chat_id} ({username_str})")


async def cmd_desabonner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /desabonner → Se désinscrire de CORTEX.
    """
    from database.client import unsubscribe_user

    chat_id = update.effective_chat.id
    admin_id = get_authorized_chat_id()

    if chat_id == admin_id:
        await update.message.reply_text(
            "👑 Tu es l'admin, tu ne peux pas te désabonner.",
            parse_mode="Markdown"
        )
        return

    success = await unsubscribe_user(chat_id)
    if success:
        await update.message.reply_text(
            "👋 Tu t'es désabonné de CORTEX.\n"
            "Tu ne recevras plus les rapports du matin.\n\n"
            "_Utilise /abonner pour te réinscrire._",
            parse_mode="Markdown"
        )
        logger.info(f"Désabonnement : chat_id={chat_id}")
    else:
        await update.message.reply_text("❌ Erreur lors de la désinscription.")


async def cmd_abonnes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /abonnes → (Admin uniquement) Liste tous les abonnés.
    """
    if not _is_authorized(update):
        await update.message.reply_text("⛔ Commande réservée à l'admin.")
        return

    from database.client import list_all_subscribers

    subscribers = await list_all_subscribers()

    if not subscribers:
        await update.message.reply_text(
            "📋 Aucun abonné pour l'instant.\n\n"
            "_Partage le bot avec tes amis et dis-leur d'envoyer /abonner_",
            parse_mode="Markdown"
        )
        return

    lines = ["👥 *Liste des abonnés CORTEX*\n━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    approved_count = 0
    pending_count = 0

    for sub in subscribers:
        name = sub.get("first_name") or sub.get("username") or "Inconnu"
        username = f"@{sub['username']}" if sub.get("username") else "sans @"
        chat_id = sub["chat_id"]
        status = "✅ Approuvé" if sub.get("approved") else "⏳ En attente"

        if sub.get("approved"):
            approved_count += 1
        else:
            pending_count += 1

        lines.append(f"{status} — {name} ({username})")
        if not sub.get("approved"):
            lines.append(f"  ↳ `/approuver {chat_id}`")

    lines.append(f"\n_Total: {approved_count} approuvé(s), {pending_count} en attente_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    logger.info(f"Commande /abonnes : {len(subscribers)} abonnés listés")


async def cmd_approuver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /approuver <chat_id> → (Admin uniquement) Approuve un abonné.
    """
    if not _is_authorized(update):
        await update.message.reply_text("⛔ Commande réservée à l'admin.")
        return

    from database.client import approve_subscriber

    if not context.args:
        await update.message.reply_text(
            "Usage : `/approuver <chat_id>`\n\nExemple : `/approuver 123456789`",
            parse_mode="Markdown"
        )
        return

    try:
        target_chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ chat_id invalide. Utilise un nombre entier.")
        return

    admin_id = get_authorized_chat_id()
    record = await approve_subscriber(chat_id=target_chat_id, approved_by=admin_id)

    if record is None:
        await update.message.reply_text(
            f"❌ Aucun abonné trouvé avec chat_id `{target_chat_id}`.\n"
            "Vérifie avec /abonnes.",
            parse_mode="Markdown"
        )
        return

    name = record.get("first_name") or record.get("username") or str(target_chat_id)
    await update.message.reply_text(
        f"✅ *{name}* est maintenant abonné à CORTEX !\nIl recevra les prochains rapports.",
        parse_mode="Markdown"
    )

    # Notifie l'abonné approuvé
    try:
        bot = Bot(token=get_bot_token())
        await bot.send_message(
            chat_id=target_chat_id,
            text=(
                "✅ *Ton abonnement CORTEX est approuvé !*\n\n"
                "Tu recevras désormais les rapports de veille chaque matin à 6h00.\n\n"
                "🧠 IA • 💰 Crypto • 📈 Marchés • ⚡ DeepTech\n\n"
                "_Utilise /desabonner pour te désinscrire à tout moment._"
            ),
            parse_mode="Markdown"
        )
    except TelegramError as e:
        logger.warning(f"Impossible de notifier l'abonné {target_chat_id} : {e}")

    logger.info(f"Abonné approuvé par admin : chat_id={target_chat_id}")


async def handle_journal_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Capture les réponses textuelles libres.
    - Admin (Badr) : stocke la réponse dans le journal
    - Abonnés approuvés : redirige vers /help
    - Inconnus : ignorés silencieusement
    """
    chat_id  = update.effective_chat.id
    admin_id = get_authorized_chat_id()

    # Abonnés et inconnus : réponse générique, pas d'accès au journal
    if chat_id != admin_id:
        try:
            from database.client import get_approved_subscribers
            subscribers   = await get_approved_subscribers()
            approved_ids  = {s["chat_id"] for s in subscribers}

            if chat_id in approved_ids:
                await update.message.reply_text(
                    "👋 Message reçu. Utilise /help pour voir les commandes disponibles.",
                    parse_mode="Markdown"
                )
            # Inconnus ignorés silencieusement
        except Exception:
            pass
        return

    # Admin uniquement — journal
    try:
        from database.client import get_recent_journal_entries, get_supabase_client

        response_text = update.message.text
        logger.info(f"Réponse journal reçue de Badr ({len(response_text)} chars)")

        entries = await get_recent_journal_entries(limit=1)

        if entries and not entries[0].get("your_response"):
            client = get_supabase_client()
            client.table("journal").update({
                "your_response":        response_text,
                "response_received_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", entries[0]["id"]).execute()

            logger.info(f"Réponse journal enregistrée (ID: {entries[0]['id'][:8]}...)")
            await update.message.reply_text(
                "✅ Noté. Bonne journée Badr.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "👋 Message reçu. Utilise /help pour voir les commandes.",
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Erreur handle_journal_response : {e}")


# ============================================================
# Construction et démarrage du bot
# ============================================================

def build_application() -> Application:
    """
    Construit l'application Telegram avec tous les handlers.

    Returns:
        Application Telegram configurée
    """
    token = get_bot_token()
    app = Application.builder().token(token).build()

    # Enregistrement des commandes
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("rapport", cmd_rapport))
    app.add_handler(CommandHandler("journal", cmd_journal))
    app.add_handler(CommandHandler("help", cmd_help))

    # Commandes abonnés
    app.add_handler(CommandHandler("abonner", cmd_abonner))
    app.add_handler(CommandHandler("desabonner", cmd_desabonner))
    app.add_handler(CommandHandler("abonnes", cmd_abonnes))
    app.add_handler(CommandHandler("approuver", cmd_approuver))

    # Handler pour les messages textuels libres (réponses journal)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_journal_response))

    logger.info("Bot Telegram configuré avec 8 commandes")
    return app


async def test_connection() -> bool:
    """
    Teste la connexion au bot Telegram.

    Returns:
        True si connexion OK, False sinon
    """
    try:
        bot = Bot(token=get_bot_token())
        bot_info = await bot.get_me()
        logger.info(f"Connexion Telegram : OK — Bot @{bot_info.username}")
        return True
    except TelegramError as e:
        logger.error(f"Connexion Telegram échouée : {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue test Telegram : {e}")
        return False


# ============================================================
# Utilitaires internes
# ============================================================

def _split_message(text: str, max_length: int) -> list[str]:
    """
    Découpe un message long en parties de max_length caractères.
    Tente de couper aux sauts de ligne pour préserver le formatage.

    Args:
        text: Texte à découper
        max_length: Longueur maximale par partie

    Returns:
        Liste de parties du message
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current = ""

    for line in text.split("\n"):
        # Si ajouter cette ligne dépasse la limite
        if len(current) + len(line) + 1 > max_length:
            if current:
                parts.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"

    if current.strip():
        parts.append(current.strip())

    return parts
