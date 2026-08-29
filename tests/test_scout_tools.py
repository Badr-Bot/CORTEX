"""
Tests du scout "boîte à outils" — sans réseau : on teste le classement par
usage et le filtrage du bruit, les deux endroits où un outil inutile pourrait
finir dans le rapport de Badr (ou un bon outil en être écarté).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.scout_tools import (
    USAGES, classify_usage, is_tool_relevant, dedupe_and_sort, _tool,
)


def test_classement_video():
    assert classify_usage("Open-source text-to-video model for short-form ads") == "video"


def test_classement_produit_gagnant():
    assert classify_usage("Find winning products on AliExpress and TikTok") == "produit_gagnant"


def test_classement_scraping():
    assert classify_usage("Fast Amazon product scraper with Playwright") == "scraping"


def test_classement_pub_meta():
    assert classify_usage("Automate Meta Ads reporting and budget rules") == "pub"


def test_skill_claude_prime_a_egalite():
    """Un skill Claude pour les pubs doit être rangé comme skill, demande explicite de Badr."""
    text = "Claude Code skill: generate ad creative briefs (SKILL.md)"
    assert classify_usage(text) == "skill_claude"


def test_texte_sans_mot_cle_retombe_sur_defaut():
    assert classify_usage("Just a random hello world project", default="automatisation") == "automatisation"


def test_tous_les_usages_ont_des_mots_cles():
    for usage in USAGES:
        assert classify_usage(f"placeholder {usage.replace('_', ' ')}") in USAGES


def test_bruit_ecarte():
    assert not is_tool_relevant("Awesome list of interview questions for shopify developers")
    assert not is_tool_relevant("My portfolio website")


def test_outil_pertinent_garde():
    assert is_tool_relevant("Shopify app that automates abandoned cart email flows")


def test_dedoublonnage_et_tri_par_popularite():
    tools = [
        _tool("a", "https://x/a", "GitHub", "s", "video", popularity=10),
        _tool("b", "https://x/b", "GitHub", "s", "video", popularity=500),
        _tool("a-bis", "https://x/a", "GitHub", "s", "video", popularity=999),
        _tool("sans-url", "", "GitHub", "s", "video", popularity=1),
    ]
    result = dedupe_and_sort(tools)
    assert [t["title"] for t in result] == ["b", "a"]


def test_les_usages_alternent_en_tete_de_liste():
    """Dix modèles vidéo très populaires ne doivent pas enterrer l'unique outil de scraping."""
    tools = [_tool(f"v{i}", f"https://x/v{i}", "HF", "s", "video", popularity=1000 - i) for i in range(10)]
    tools.append(_tool("scrap", "https://x/s", "GitHub", "s", "scraping", popularity=5))
    tools.append(_tool("ads", "https://x/p", "GitHub", "s", "pub", popularity=50))
    result = dedupe_and_sort(tools)
    assert {t["title"] for t in result[:3]} == {"v0", "scrap", "ads"}


def test_variantes_quantifiees_ecartees():
    from agents.scout_tools import is_hf_variant
    assert is_hf_variant("orcarouter/Qwen3.8-27B-Uncensored-FP8")
    assert is_hf_variant("unsloth/Qwen3.8-Flash-Next-GGUF")
    assert not is_hf_variant("Lightricks/LTX-2.5")


def test_structure_outil():
    t = _tool("n", "https://x", "GitHub", "résumé", "pub", popularity=3, free=False)
    for field in ("sector", "source_name", "source_url", "title", "raw_content", "usage", "gratuit"):
        assert field in t
    assert t["gratuit"] is False and t["usage"] == "pub"
