"""
Tests de résilience — la panne du 2026-08-12 ne doit pas pouvoir se reproduire.

Contexte : crédit Anthropic épuisé → toutes les analyses retombaient en fallback,
et les fallbacks Crypto/Marchés renvoyaient 0 signal. Résultat : plus aucune news
marché ni crypto dans le rapport, alors que les scouts collectaient bien 40+ news.

Ces tests verrouillent :
  - la cascade multi-fournisseurs (gratuits d'abord, Anthropic en dernier)
  - les fallbacks qui conservent les news brutes
  - la réparation des JSON tronqués
  - l'absence de flux RSS morts
  - le classement thématique e-commerce
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

import pytest


RAW_SIGNALS = [
    {
        "title": "Bitcoin franchit les 100 000 dollars",
        "source_name": "CoinDesk",
        "source_url": "https://coindesk.com/a",
        "raw_content": "Le bitcoin a dépassé les 100 000 dollars pour la première fois.",
        "theme": "marketplace",
    },
    {
        "title": "La Fed laisse ses taux inchangés",
        "source_name": "CNBC",
        "source_url": "https://cnbc.com/b",
        "raw_content": "La Réserve fédérale maintient ses taux.",
    },
    {
        "title": "Shopify lance un agent IA",
        "source_name": "Modern Retail",
        "source_url": "https://modernretail.co/c",
        "raw_content": "Shopify déploie un agent d'achat automatisé.",
        "theme": "automation",
    },
]


# ── Cascade de fournisseurs ───────────────────────────────────────────────────

def test_free_providers_come_first():
    """L'API Anthropic payante ne doit jamais être le premier fournisseur par défaut."""
    from agents.summarizer import PROVIDER_ORDER
    assert PROVIDER_ORDER[0] in ("groq", "gemini"), \
        f"Un fournisseur gratuit doit passer en premier, obtenu: {PROVIDER_ORDER}"
    assert "anthropic" in PROVIDER_ORDER, "Anthropic doit rester en dernier recours"
    assert PROVIDER_ORDER.index("anthropic") == len(PROVIDER_ORDER) - 1


def test_board_models_exist_in_provider_catalog():
    """Les modèles du Board doivent être des identifiants encore servis (pas de 404)."""
    from agents.board import BOARD_MODELS, GROQ_BIG_MODEL, GROQ_FAST_MODEL, GEMINI_MODEL
    dead = ["meta-llama/llama-4-scout-17b-16e-instruct", "gemini-2.0-flash", "gemma2-9b-it"]
    for model in (GROQ_BIG_MODEL, GROQ_FAST_MODEL, GEMINI_MODEL):
        assert model not in dead, f"Modèle retiré par le fournisseur: {model}"
    assert len(BOARD_MODELS) >= 3, "Le board a besoin d'au moins 3 voix"


def test_quota_error_detection():
    from agents.summarizer import _is_quota_error
    assert _is_quota_error("Error code: 413 - Request too large for model")
    assert _is_quota_error("Error code: 429 - Rate limit reached")
    assert _is_quota_error("429 RESOURCE_EXHAUSTED. quota")
    assert not _is_quota_error("Error code: 404 - model does not exist")
    assert not _is_quota_error("connection reset")


class _FakeChoice:
    def __init__(self, content, finish_reason="stop"):
        self.message = type("M", (), {"content": content})()
        self.finish_reason = finish_reason


class _FakeGroq:
    """Client Groq factice : rejoue une séquence d'issues sans appeler le réseau."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.calls.append(kwargs)
                outcome = outer.outcomes.pop(0)
                if isinstance(outcome, Exception):
                    raise outcome
                return type("R", (), {"choices": [_FakeChoice(outcome)]})()

        self.chat = type("C", (), {"completions": _Completions()})()


@pytest.fixture
def no_wait(monkeypatch):
    monkeypatch.setattr("agents.summarizer.RATE_LIMIT_WAIT", 0)
    monkeypatch.setattr("agents.summarizer.time.sleep", lambda s: None)


def test_groq_retries_then_lowers_budget(monkeypatch, no_wait):
    """413 deux fois de suite → on redescend d'un palier de tokens, même modèle."""
    from agents import summarizer

    fake = _FakeGroq([
        Exception("Error code: 413 - Request too large"),
        Exception("Error code: 413 - Request too large"),
        '{"ok": true}',
    ])
    monkeypatch.setattr(summarizer, "_get_groq_client", lambda: fake)

    out = summarizer._call_groq_deep("prompt", max_tokens=8000, system_prompt="sys")
    assert out == '{"ok": true}'
    budgets = [c["max_tokens"] for c in fake.calls]
    assert budgets == [8000, 8000, 6000], f"Paliers inattendus: {budgets}"
    assert fake.calls[0]["model"] == summarizer.GROQ_DEEP_MODEL


def test_groq_switches_model_on_non_quota_error(monkeypatch, no_wait):
    """Erreur non liée au quota (modèle retiré) → on passe au modèle suivant."""
    from agents import summarizer

    fake = _FakeGroq([
        Exception("Error code: 404 - model does not exist"),
        '{"ok": 1}',
    ])
    monkeypatch.setattr(summarizer, "_get_groq_client", lambda: fake)

    out = summarizer._call_groq_deep("prompt", max_tokens=8000)
    assert out == '{"ok": 1}'
    models = [c["model"] for c in fake.calls]
    assert models[0] != models[1], "Le second appel doit viser un autre modèle"


def test_llm_cascade_falls_through_to_next_provider(monkeypatch, no_wait):
    """Groq muet → Gemini prend le relais, sans jamais toucher Anthropic."""
    from agents import summarizer

    called = []
    monkeypatch.setattr(summarizer, "_call_groq_deep", lambda *a, **k: called.append("groq") or None)
    monkeypatch.setattr(summarizer, "_call_gemini_deep", lambda *a, **k: called.append("gemini") or '{"x":1}')
    monkeypatch.setattr(summarizer, "_call_anthropic", lambda *a, **k: called.append("anthropic") or "NOPE")

    out = summarizer._call_llm("prompt", system_prompt="sys")
    assert out == '{"x":1}'
    assert called == ["groq", "gemini"], f"Cascade inattendue: {called}"


def test_llm_returns_none_when_everything_fails(monkeypatch, no_wait):
    from agents import summarizer

    monkeypatch.setattr(summarizer, "_call_groq_deep", lambda *a, **k: None)
    monkeypatch.setattr(summarizer, "_call_gemini_deep", lambda *a, **k: None)
    monkeypatch.setattr(summarizer, "_call_anthropic", lambda *a, **k: None)
    assert summarizer._call_llm("prompt") is None


# ── Fallbacks : jamais de section vide ────────────────────────────────────────

def test_fallback_crypto_keeps_news():
    from agents.summarizer import _fallback_crypto
    out = _fallback_crypto({"btc_price": 100000}, RAW_SIGNALS)
    assert len(out["signals"]) == 3, "Le fallback crypto doit conserver les news brutes"
    assert out["signals"][0]["source_url"] == "https://coindesk.com/a"


def test_fallback_market_keeps_news_and_all_indicators():
    from agents.summarizer import _fallback_market
    out = _fallback_market({}, RAW_SIGNALS)
    assert len(out["signals"]) == 3, "Le fallback marché doit conserver les news brutes"
    assert len(out["recession_indicators"]) == 10, "Le schéma attend 10 indicateurs"


def test_fallback_ecommerce_keeps_news_and_themes():
    from agents.summarizer import _fallback_ecommerce
    out = _fallback_ecommerce({}, RAW_SIGNALS)
    assert out["signals"], "Le fallback e-commerce doit conserver les news brutes"
    assert out["nouveautes"], "Le fallback e-commerce doit lister des nouveautés"
    assert out["signals"][0]["theme"] == "marketplace", "Le thème doit survivre au fallback"


def test_degraded_signals_have_all_required_fields():
    """Un signal dégradé reste affichable par le dashboard et Telegram."""
    from agents.summarizer import _degraded_signals
    for sig in _degraded_signals(RAW_SIGNALS, 3):
        for field in ("title", "fait", "action", "sizing", "conviction", "invalide_si"):
            assert sig.get(field), f"Champ '{field}' vide dans un signal dégradé"
        assert sig["sizing"] in {"Fort", "Moyen", "Faible"}
        assert 1 <= sig["conviction"] <= 5


# ── Réparation JSON ───────────────────────────────────────────────────────────

def test_parse_json_repairs_truncated_response():
    """Une réponse coupée par la limite de tokens doit être partiellement sauvée."""
    from agents.summarizer import _parse_json
    truncated = (
        '{"tendance_globale": "Le commerce bouge.", "nouveautes": ['
        '{"theme": "automation", "titre": "Agents IA", "quoi": "Des agents achètent.",'
        ' "pourquoi": "Change le trafic.", "source_name": "SEJ", "source_url": "https://b.com"},'
        '{"theme": "creatives", "titre": "TikTok Shop mon'
    )
    out = _parse_json(truncated)
    assert out is not None, "Le JSON tronqué doit être réparé"
    assert out["tendance_globale"] == "Le commerce bouge."
    assert len(out["nouveautes"]) == 1, "Seul l'item complet doit être conservé"


def test_parse_json_still_handles_clean_and_invalid():
    from agents.summarizer import _parse_json
    assert _parse_json('{"a": 1}') == {"a": 1}
    assert _parse_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert _parse_json("pas du json") is None
    assert _parse_json("") is None


# ── Flux RSS ──────────────────────────────────────────────────────────────────

def test_no_dead_feeds_referenced():
    """Flux constatés morts le 2026-08-12 — ils ne doivent plus être utilisés."""
    from agents.scout_crypto import CRYPTO_NEWS_FEEDS
    from agents.scout_market import MARKET_NEWS_FEEDS
    from agents.scout_ecommerce import ECOM_NEWS_FEEDS

    dead = ["feeds.reuters.com", "cryptopanic.com", "marketplacepulse.com"]
    for feeds in (CRYPTO_NEWS_FEEDS, MARKET_NEWS_FEEDS, ECOM_NEWS_FEEDS):
        for feed in feeds:
            for bad in dead:
                assert bad not in feed["url"], f"Flux mort référencé: {feed['name']}"


def test_feeds_helper_uses_browser_user_agent():
    """Sans User-Agent navigateur, plusieurs sources répondent 403 ou vide."""
    from utils.feeds import HEADERS
    assert "Mozilla" in HEADERS["User-Agent"]


# ── E-commerce ────────────────────────────────────────────────────────────────

def test_ecommerce_theme_classification():
    from agents.scout_ecommerce import _classify_theme
    assert _classify_theme(
        "Klaviyo improves email marketing deliverability for SMS campaigns"
    ) == "emailing"
    assert _classify_theme(
        "New AI agent automation workflow for agentic commerce checkout"
    ) == "automation"
    assert _classify_theme(
        "Meta ads creative testing with UGC video ad improves ROAS"
    ) == "creatives"
    # Sous le seuil de mots-clés → on garde le thème du flux d'origine
    assert _classify_theme("A story about a brand", default="marketplace") == "marketplace"


def test_ecommerce_noise_is_filtered():
    from agents.scout_ecommerce import _is_ecom_relevant
    assert _is_ecom_relevant("Shopify launches new checkout for online store")
    assert not _is_ecom_relevant("THE 2026 Meta Ads MASTER Course (Beginner To Pro)")
    assert not _is_ecom_relevant("Un sujet totalement hors contexte")


def test_ecommerce_report_section_renders_without_llm():
    """Le message e-commerce doit se construire même en mode dégradé."""
    from agents.summarizer import _fallback_ecommerce
    from morning_report import build_msg5

    data = _fallback_ecommerce(
        {"stocks": [{"nom": "Shopify", "ticker": "SHOP", "price": 120.5, "change_pct": 2.1}],
         "secteur": {"pct_hausse": 60, "moyenne_pct": 0.4, "sentiment": "mitigé"}},
        RAW_SIGNALS,
    )
    msg = build_msg5(data)
    assert "E-COMMERCE" in msg
    assert "Shopify" in msg
    assert len(msg) > 500
