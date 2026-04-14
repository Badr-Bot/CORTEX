"""
CORTEX — Client Supabase
Gère toutes les interactions avec la base de données PostgreSQL
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from supabase import create_client, Client
from utils.logger import get_logger

logger = get_logger("database")


def get_supabase_client() -> Client:
    """
    Crée et retourne un client Supabase authentifié.

    Returns:
        Client Supabase configuré
    Raises:
        ValueError si les variables d'environnement manquent
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL ou SUPABASE_SERVICE_KEY manquant dans .env")

    return create_client(url, key)


async def init_db() -> bool:
    """
    Initialise la base de données en exécutant schema.sql.
    Appelé au premier démarrage de CORTEX.

    Returns:
        True si succès, False sinon
    """
    try:
        logger.info("Initialisation de la base de données...")

        # Lecture du fichier schema.sql
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            logger.error(f"Fichier schema.sql introuvable : {schema_path}")
            return False

        schema_sql = schema_path.read_text(encoding="utf-8")

        # Connexion au client Supabase
        client = get_supabase_client()

        # Exécution du schema via l'API REST Supabase (rpc)
        # Note : Supabase ne permet pas l'exécution SQL directe via SDK Python
        # On utilise la fonction rpc ou on vérifie si les tables existent
        try:
            # Test : vérifier si la table signals existe
            result = client.table("signals").select("id").limit(1).execute()
            logger.info("Tables déjà présentes — schema.sql ignoré")
            return True
        except Exception:
            # Les tables n'existent pas encore
            logger.warning(
                "Tables absentes. Exécute schema.sql manuellement dans Supabase SQL Editor : "
                f"{schema_path}"
            )
            # On continue quand même — les tables peuvent être créées via l'interface Supabase
            return True

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation DB : {e}")
        return False


async def test_connection() -> bool:
    """
    Teste la connexion à Supabase.

    Returns:
        True si connexion OK, False sinon
    """
    try:
        client = get_supabase_client()
        # Requête légère pour vérifier la connexion
        client.table("signals").select("id").limit(1).execute()
        logger.info("Connexion Supabase : OK")
        return True
    except Exception as e:
        err_str = str(e)
        # PGRST205 = table absente mais connexion OK — schema.sql pas encore exécuté
        if "PGRST205" in err_str or "schema cache" in err_str:
            logger.warning("Supabase connecté mais tables absentes — exécute schema.sql dans Supabase SQL Editor")
            return True
        logger.error(f"Connexion Supabase échouée : {e}")
        return False


# ============================================================
# CRUD — TABLE signals
# ============================================================

async def insert_signal(
    sector: str,
    title: str,
    source_url: str = None,
    source_name: str = None,
    raw_content: str = None,
    stars_count: int = 0,
    category: str = "weak",
    metadata: dict = None
) -> Optional[dict]:
    """
    Insère un nouveau signal dans la base de données.

    Args:
        sector: Secteur ('ai' | 'crypto' | 'market' | 'deeptech')
        title: Titre du signal
        source_url: URL source
        source_name: Nom de la source
        raw_content: Contenu brut
        stars_count: Nombre d'étoiles GitHub / likes
        category: Catégorie ('weak' | 'viral' | 'emerging')
        metadata: Métadonnées supplémentaires en JSON

    Returns:
        Enregistrement créé ou None en cas d'erreur
    """
    try:
        client = get_supabase_client()

        data = {
            "sector": sector,
            "title": title,
            "source_url": source_url,
            "source_name": source_name,
            "raw_content": raw_content,
            "stars_count": stars_count,
            "category": category,
            "metadata": metadata or {}
        }

        result = client.table("signals").insert(data).execute()
        logger.info(f"Signal inséré : [{sector}] {title[:60]}...")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur insert_signal : {e}")
        return None


async def get_recent_signals(
    hours: int = 24,
    sector: str = None,
    category: str = None,
    limit: int = 50
) -> list:
    """
    Récupère les signaux récents avec filtres optionnels.

    Args:
        hours: Fenêtre temporelle en heures
        sector: Filtre par secteur (optionnel)
        category: Filtre par catégorie (optionnel)
        limit: Nombre max de résultats

    Returns:
        Liste de signaux
    """
    try:
        client = get_supabase_client()

        query = client.table("signals").select("*")

        if sector:
            query = query.eq("sector", sector)
        if category:
            query = query.eq("category", category)

        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()

        logger.info(f"Signaux récupérés : {len(result.data)} entrées")
        return result.data or []

    except Exception as e:
        logger.error(f"Erreur get_recent_signals : {e}")
        return []


# ============================================================
# CRUD — TABLE analyses
# ============================================================

async def insert_analysis(
    signal_id: str,
    full_analysis: str,
    score_precocity: float = 0,
    score_impact: float = 0,
    score_actionability: float = 0,
    score_confidence: float = 0,
    score_total: float = 0,
    key_themes: list = None,
    action_items: list = None
) -> Optional[dict]:
    """
    Insère une analyse SHERLOCK pour un signal donné.

    Args:
        signal_id: UUID du signal analysé
        full_analysis: Texte complet de l'analyse
        score_*: Scores de 0 à 1
        key_themes: Thèmes clés identifiés
        action_items: Actions recommandées

    Returns:
        Enregistrement créé ou None en cas d'erreur
    """
    try:
        client = get_supabase_client()

        data = {
            "signal_id": signal_id,
            "full_analysis": full_analysis,
            "score_precocity": score_precocity,
            "score_impact": score_impact,
            "score_actionability": score_actionability,
            "score_confidence": score_confidence,
            "score_total": score_total,
            "key_themes": key_themes or [],
            "action_items": action_items or []
        }

        result = client.table("analyses").insert(data).execute()
        logger.info(f"Analyse insérée pour signal {signal_id[:8]}... (score: {score_total:.2f})")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur insert_analysis : {e}")
        return None


# ============================================================
# CRUD — TABLE journal
# ============================================================

async def insert_journal_entry(
    question_asked: str,
    your_response: str = None,
    claude_comment: str = None,
    mood_signal: str = None,
    response_received_at: datetime = None
) -> Optional[dict]:
    """
    Insère une entrée dans le journal personnel de Badr.
    Ce journal n'est jamais supprimé.

    Args:
        question_asked: Question posée ce matin
        your_response: Réponse de Badr
        claude_comment: Commentaire de Claude sur la réponse
        mood_signal: 'action' | 'observation' | 'doubt' | 'conviction'
        response_received_at: Timestamp de la réponse

    Returns:
        Enregistrement créé ou None en cas d'erreur
    """
    try:
        client = get_supabase_client()

        data = {
            "question_asked": question_asked,
            "your_response": your_response,
            "claude_comment": claude_comment,
            "mood_signal": mood_signal,
            "response_received_at": response_received_at.isoformat() if response_received_at else None
        }

        result = client.table("journal").insert(data).execute()
        logger.info(f"Entrée journal créée (mood: {mood_signal or 'non défini'})")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur insert_journal_entry : {e}")
        return None


async def get_recent_journal_entries(limit: int = 7) -> list:
    """
    Récupère les dernières entrées du journal.

    Args:
        limit: Nombre d'entrées à récupérer

    Returns:
        Liste d'entrées journal
    """
    try:
        client = get_supabase_client()
        result = (
            client.table("journal")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        logger.info(f"Journal récupéré : {len(result.data)} entrées")
        return result.data or []

    except Exception as e:
        logger.error(f"Erreur get_recent_journal_entries : {e}")
        return []


# ============================================================
# CRUD — TABLE signal_tracking
# ============================================================

async def update_signal_tracking(
    signal_id: str,
    stars_count: int = 0,
    mentions_count: int = 0,
    went_viral_at: datetime = None,
    viral_threshold_reached: int = None
) -> Optional[dict]:
    """
    Met à jour le suivi d'évolution d'un signal.

    Args:
        signal_id: UUID du signal suivi
        stars_count: Nombre d'étoiles actuel
        mentions_count: Nombre de mentions actuelles
        went_viral_at: Timestamp si devenu viral
        viral_threshold_reached: Seuil de stars atteint au moment viral

    Returns:
        Enregistrement créé ou None en cas d'erreur
    """
    try:
        client = get_supabase_client()

        data = {
            "signal_id": signal_id,
            "stars_count": stars_count,
            "mentions_count": mentions_count,
            "went_viral_at": went_viral_at.isoformat() if went_viral_at else None,
            "viral_threshold_reached": viral_threshold_reached
        }

        result = client.table("signal_tracking").insert(data).execute()
        logger.info(
            f"Tracking mis à jour pour signal {signal_id[:8]}... "
            f"(stars: {stars_count}, mentions: {mentions_count})"
        )
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur update_signal_tracking : {e}")
        return None


# ============================================================
# CRUD — Compression et synthèses
# ============================================================

async def get_signals_for_compression(days_old: int = 30) -> list:
    """
    Récupère les signaux éligibles à la compression.
    Signaux de plus de N jours sans synthèse.

    Args:
        days_old: Âge minimum en jours pour compression

    Returns:
        Liste de signaux à compresser
    """
    try:
        client = get_supabase_client()

        # Signaux plus vieux que N jours
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)

        result = (
            client.table("signals")
            .select("*")
            .lt("created_at", cutoff.isoformat())
            .order("created_at", desc=False)
            .execute()
        )

        logger.info(f"Signaux pour compression : {len(result.data)} éligibles (>{days_old}j)")
        return result.data or []

    except Exception as e:
        logger.error(f"Erreur get_signals_for_compression : {e}")
        return []


async def get_last_daily_report() -> Optional[dict]:
    """
    Récupère le dernier rapport journalier envoyé.

    Returns:
        Dernier rapport ou None
    """
    try:
        client = get_supabase_client()
        result = (
            client.table("daily_reports")
            .select("*")
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur get_last_daily_report : {e}")
        return None


# ============================================================
# CRUD — TABLE subscribers
# ============================================================

async def subscribe_user(
    chat_id: int,
    username: str = None,
    first_name: str = None
) -> Optional[dict]:
    """
    Inscrit un utilisateur comme abonné (en attente d'approbation).
    Retourne l'enregistrement existant si déjà inscrit.
    """
    try:
        client = get_supabase_client()

        # Vérifie si déjà inscrit
        existing = client.table("subscribers").select("*").eq("chat_id", chat_id).execute()
        if existing.data:
            return existing.data[0]

        data = {
            "chat_id": chat_id,
            "username": username,
            "first_name": first_name,
            "approved": False,
        }
        result = client.table("subscribers").insert(data).execute()
        logger.info(f"Nouvel abonné inscrit : chat_id={chat_id} (@{username})")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur subscribe_user : {e}")
        return None


async def unsubscribe_user(chat_id: int) -> bool:
    """Supprime un abonné de la liste."""
    try:
        client = get_supabase_client()
        client.table("subscribers").delete().eq("chat_id", chat_id).execute()
        logger.info(f"Abonné supprimé : chat_id={chat_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur unsubscribe_user : {e}")
        return False


async def approve_subscriber(chat_id: int, approved_by: int) -> Optional[dict]:
    """Approuve un abonné en attente."""
    try:
        client = get_supabase_client()
        result = client.table("subscribers").update({
            "approved": True,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": approved_by,
        }).eq("chat_id", chat_id).execute()

        if result.data:
            logger.info(f"Abonné approuvé : chat_id={chat_id}")
            return result.data[0]
        return None

    except Exception as e:
        logger.error(f"Erreur approve_subscriber : {e}")
        return None


async def get_approved_subscribers() -> list:
    """Retourne tous les abonnés approuvés (hors admin)."""
    try:
        client = get_supabase_client()
        result = (
            client.table("subscribers")
            .select("*")
            .eq("approved", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Erreur get_approved_subscribers : {e}")
        return []


async def list_all_subscribers() -> list:
    """Retourne tous les abonnés (approuvés + en attente)."""
    try:
        client = get_supabase_client()
        result = (
            client.table("subscribers")
            .select("*")
            .order("subscribed_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Erreur list_all_subscribers : {e}")
        return []


async def insert_daily_report(
    signals_count: int,
    report_content: str,
    telegram_message_id: str = None,
    sectors_covered: list = None
) -> Optional[dict]:
    """
    Enregistre un rapport journalier envoyé.

    Args:
        signals_count: Nombre de signaux couverts
        report_content: Contenu complet du rapport
        telegram_message_id: ID du message Telegram
        sectors_covered: Secteurs inclus dans le rapport

    Returns:
        Enregistrement créé ou None en cas d'erreur
    """
    try:
        client = get_supabase_client()

        data = {
            "signals_count": signals_count,
            "report_content": report_content,
            "telegram_message_id": telegram_message_id,
            "sectors_covered": sectors_covered or []
        }

        result = client.table("daily_reports").insert(data).execute()
        logger.info(f"Rapport journalier enregistré ({signals_count} signaux)")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur insert_daily_report : {e}")
        return None


# ============================================================
# CRUD — TABLE agent_learnings (système d'apprentissage)
# ============================================================

async def save_learning(
    week_of: str,
    sector: str,
    learning: str,
    pattern: str = None,
    signal_title: str = None,
    materialized: bool = None,
) -> Optional[dict]:
    """
    Sauvegarde un apprentissage hebdomadaire dans agent_learnings.

    Args:
        week_of       : Date de début de semaine (YYYY-MM-DD)
        sector        : 'ai' | 'crypto' | 'market' | 'deeptech' | 'global'
        learning      : Ce que CORTEX a appris cette semaine
        pattern       : Biais/pattern de pensée détecté chez Badr
        signal_title  : Titre du signal source
        materialized  : True si la prédiction s'est réalisée
    """
    try:
        client = get_supabase_client()
        result = client.table("agent_learnings").insert({
            "week_of":      week_of,
            "sector":       sector,
            "learning":     learning,
            "pattern":      pattern,
            "signal_title": signal_title,
            "materialized": materialized,
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Erreur save_learning: {e}")
        return None


async def get_recent_learnings(sector: str = None, limit: int = 10) -> list:
    """
    Récupère les derniers apprentissages (toutes semaines confondues).
    Si sector fourni, filtre par secteur.

    Returns:
        Liste de dicts {week_of, sector, learning, pattern, signal_title, materialized}
    """
    try:
        client = get_supabase_client()
        query = (
            client.table("agent_learnings")
            .select("week_of, sector, learning, pattern, signal_title, materialized")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if sector:
            query = query.eq("sector", sector)
        result = query.execute()
        return result.data or []
    except Exception as e:
        logger.warning(f"Erreur get_recent_learnings: {e}")
        return []


async def get_week_journal(days_back: int = 7) -> list:
    """
    Récupère les entrées journal des N derniers jours.
    Utilisé par le bilan du dimanche.

    Returns:
        Liste d'entrées avec question, réponse, date
    """
    try:
        from datetime import timedelta
        client  = get_supabase_client()
        cutoff  = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
        result  = (
            client.table("journal")
            .select("id, question_asked, your_response, created_at")
            .gte("created_at", cutoff)
            .order("created_at", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Erreur get_week_journal: {e}")
        return []


async def get_week_analyses(days_back: int = 7) -> list:
    """
    Récupère les analyses quotidiennes de la semaine.
    Utilisé par le bilan du dimanche pour évaluer les prédictions.

    Returns:
        Liste de {report_date, sector, analysis_json}
    """
    try:
        from datetime import timedelta
        client = get_supabase_client()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        result = (
            client.table("daily_analyses")
            .select("report_date, sector, analysis_json")
            .gte("report_date", cutoff)
            .order("report_date", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Erreur get_week_analyses: {e}")
        return []


# ============================================================
# DASHBOARD VERCEL — Rapport structuré JSON
# ============================================================

async def save_dashboard_report(
    report_date: str,
    ai_data: dict,
    crypto_data: dict,
    market_data: dict,
    deeptech_data: dict,
    nexus_data: dict,
    signals_count: int = 0,
    question: str = "",
) -> Optional[dict]:
    """
    Sauvegarde le rapport du matin en JSON structuré pour le dashboard Vercel.
    Met à jour si un rapport existe déjà pour cette date.
    """
    try:
        client = get_supabase_client()

        report_json = {
            "ai":       ai_data,
            "crypto":   crypto_data,
            "market":   market_data,
            "deeptech": deeptech_data,
            "nexus":    nexus_data,
        }

        # Vérifier si un rapport existe déjà pour cette date
        existing = (
            client.table("daily_reports")
            .select("id")
            .eq("report_date", report_date)
            .execute()
        )

        if existing.data:
            result = (
                client.table("daily_reports")
                .update({
                    "report_json":    report_json,
                    "signals_count":  signals_count,
                    "question":       question,
                    "report_date":    report_date,
                })
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            result = (
                client.table("daily_reports")
                .insert({
                    "report_date":    report_date,
                    "report_json":    report_json,
                    "signals_count":  signals_count,
                    "question":       question,
                    "report_content": "",
                    "sectors_covered": ["ai", "crypto", "market", "deeptech", "nexus"],
                })
                .execute()
            )

        logger.info(f"Dashboard report sauvegardé — {report_date}")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur save_dashboard_report: {e}")
        return None


# ============================================================
# DASHBOARD VERCEL — Weekly Debrief
# ============================================================

async def save_weekly_debrief(
    week_of: str,
    evaluation_json: dict,
    taux_reussite: int = 0,
    focus_semaine: str = "",
) -> Optional[dict]:
    """
    Sauvegarde le débrief hebdomadaire du dimanche dans Supabase.
    Utilisé par le dashboard pour afficher la page /debrief.
    """
    try:
        client = get_supabase_client()

        data = {
            "week_of":          week_of,
            "evaluation_json":  evaluation_json,
            "taux_reussite":    taux_reussite,
            "focus_semaine":    focus_semaine,
        }

        # Upsert : remplace si la semaine existe déjà
        result = (
            client.table("weekly_debrief")
            .upsert(data, on_conflict="week_of")
            .execute()
        )

        logger.info(f"Débrief hebdomadaire sauvegardé — semaine du {week_of}")
        return result.data[0] if result.data else None

    except Exception as e:
        logger.error(f"Erreur save_weekly_debrief: {e}")
        return None
