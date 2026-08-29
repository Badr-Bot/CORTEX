"""
CORTEX — Radar produits (porté de D:/MasterEcom, skill /radar).

Dépouille les réponses TrendTrack `search_shops` que l'agent a lancées, classe
chaque boutique selon les deux axes de MASTER RESEARCH (voir docs/RADAR.md),
tient un suivi cumulé, et propose à l'agent rédacteur les meilleurs candidats
du jour — ceux qu'il analysera en profondeur pour Badr.

Aucun réseau ici : les appels TrendTrack sont faits par l'agent (connecteur
MCP), ce script ne lit que des fichiers.

Commandes :
    python -m agents.radar_produits extract  AAAA-MM-JJ [--src DOSSIER ...]
    python -m agents.radar_produits candidats AAAA-MM-JJ [--n 12]
    python -m agents.radar_produits mark     AAAA-MM-JJ domaine1 domaine2 ...

Fichiers (data/radar/) :
    raw/*.json          réponses brutes sauvegardées à la main par l'agent (optionnel)
    AAAA-MM-JJ.json     les boutiques du jour, classées et triées
    suivi.json          cumul par domaine : rangs vus, statut, dates d'analyse
    candidats_AAAA-MM-JJ.md   le brief lisible que l'agent lit avant de choisir
"""

import argparse
import glob
import json
import os
import re
import sys
import time
from datetime import date as _date, datetime
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("radar_produits")

RADAR_DIR = Path(__file__).parent.parent / "data" / "radar"
RAW_DIR = RADAR_DIR / "raw"
SUIVI_PATH = RADAR_DIR / "suivi.json"

# Où Claude Code range les réponses d'outils trop longues pour rester en ligne.
DEFAULT_TOOL_RESULT_GLOBS = [
    "~/.claude/projects/*/*/tool-results",
    "/tmp/claude-0/*/*/tool-results",
    "/tmp/claude-*/*/*/tool-results",
]

# Vocabulaire de FILTRES.md §3 critère 6 (liquides / ingérables) et cosmétiques
INGERABLE = re.compile(
    r"\b(cleanse|detox|d[ée]tox|colon|supplement|suplemento|supl[ée]ment|complement|compl[ée]ment|gummies|gummy|"
    r"capsul|g[ée]lule|tablet|drops|tincture|extract|vitamin|collagen|collag[èe]ne|"
    r"probiotic|powder|protein|prot[ée]ine|whey|creatine|burner|shred|nutrition|"
    r"organics|sirop|serum buvable|mushroom|ashwagandha|magnesium|melatonin|"
    r"electrolyte|tea |thé |infusion)\b", re.I)
COSMETIQUE = re.compile(r"\b(cream|serum|oil|balm|lotion|gel|mask|shampoo|creme|huile)\b", re.I)
DEVISES_OK = {"USD", "EUR", "GBP", "CAD", "AUD", "CHF", "SEK", "DKK", "NOK"}
# Taux approximatifs vers l'euro, pour comparer un prix vu à l'AOV de Badr.
# 199 DKK n'est pas 199 € : sans conversion le filtre prix laissait tout passer.
TAUX_EUR = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CAD": 0.68, "AUD": 0.61,
            "CHF": 1.05, "SEK": 0.087, "DKK": 0.134, "NOK": 0.086}


def prix_en_euros(prix, devise: str):
    if prix is None:
        return None
    return round(prix * TAUX_EUR.get((devise or "").upper(), 1.0), 2)
UPSELL = re.compile(
    r"(vip|membership|abonnement|subscription|assurance|insurance|priorit|priority|"
    r"protection|warranty|garantie|shipping|livraison|expedition|tip|pourboire|"
    r"donation|gift card|carte cadeau|extension|add-?on|bundle upgrade|bonus|gratuit|"
    r"free gift|money-back|guarantee|guide)", re.I)

# Seuils : 50 ads = la seule règle chiffrée de la formation (04-ecom-data-1.md:271).
# ×2 = "explose", ≤ 0,8 = "en baisse", 60 jours = "récente" : calibrations maison.
MIN_ADS = 50
BRAND_ADS = 150
EXPLOSE_X = 2.0
BAISSE_X = 0.8
RECENTE_JOURS = 60

STATUT_ORDRE = ["BANGER", "EXPLOSE", "SANS TRAFIC", "A SURVEILLER", "STABLE", "EN BAISSE", "SOUS LE FILTRE"]
STATUTS_CANDIDATS = {"BANGER", "EXPLOSE", "SANS TRAFIC", "A SURVEILLER"}
JOURS_SANS_REPROPOSER = 7


# ── Lecture des réponses ────────────────────────────────────────────────────

def _looks_like_search_shops(payload) -> bool:
    return (isinstance(payload, dict) and isinstance(payload.get("data"), list)
            and payload["data"] and isinstance(payload["data"][0], dict)
            and "domain" in payload["data"][0])


def _load_payload(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    start = text.find("{")
    if start < 0:
        return None
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        return None


def iter_responses(src_dirs: list[str] | None = None, max_age_hours: float = 24) -> list[tuple[dict, bool]]:
    """Toutes les réponses search_shops trouvées (payload, passe Triple Whale ?)."""
    dirs = []
    for pattern in (src_dirs or DEFAULT_TOOL_RESULT_GLOBS):
        dirs.extend(glob.glob(os.path.expanduser(pattern)))
    dirs.append(str(RAW_DIR))

    cutoff = time.time() - max_age_hours * 3600
    found: list[tuple[dict, bool]] = []
    for d in dirs:
        for path in sorted(Path(d).glob("*")):
            if path.suffix not in (".txt", ".json") or not path.is_file():
                continue
            if path.stat().st_mtime < cutoff:
                continue
            payload = _load_payload(path)
            if not _looks_like_search_shops(payload):
                continue
            request = ((payload.get("raw") or {}).get("request") or {})
            args = request.get("parsedArgs") or request
            techno = bool(args.get("shopifyAppIds") or args.get("shopify_app_ids"))
            found.append((payload, techno))
    logger.info(f"Réponses search_shops trouvées : {len(found)}")
    return found


# ── Classement d'une boutique ───────────────────────────────────────────────

def _pct(a, b):
    return round((a - b) / b * 100) if b else None


def classify(row: dict, techno: bool, today: _date) -> dict | None:
    """Une boutique TrendTrack → une ligne du radar, statut compris."""
    dom = row.get("domain")
    if not dom:
        return None
    adv = row.get("advertising") or {}
    cat = row.get("catalog") or {}
    traf = row.get("traffic") or {}
    prof = row.get("profile") or {}

    ads = adv.get("activeAds") or 0
    hist = [h.get("value") or 0 for h in (adv.get("history") or [])]
    h = hist[-5:] if hist else []
    accel = round(h[-1] / h[0], 1) if len(h) >= 2 and h[0] else None

    created = (row.get("createdAt") or "")[:10]
    try:
        age = (today - _date.fromisoformat(created)).days if created else None
    except ValueError:
        age = None

    sem_diff = 0
    for v in reversed(hist):
        if v and v > 0:
            sem_diff += 1
        else:
            break

    visites = traf.get("monthlyVisits")
    sans_trafic = (visites or 0) == 0
    explose = accel is not None and accel >= EXPLOSE_X
    baisse = accel is not None and accel <= BAISSE_X

    if ads < MIN_ADS:
        statut = "SOUS LE FILTRE"
    elif baisse:
        statut = "EN BAISSE"
    elif sans_trafic and explose:
        statut = "BANGER"
    elif sans_trafic:
        statut = "SANS TRAFIC"
    elif explose:
        statut = "EXPLOSE"
    elif ads < BRAND_ADS:
        statut = "A SURVEILLER"
    else:
        statut = "STABLE"

    bs = cat.get("bestSellers") or []
    b0 = bs[0] if bs else {}
    for b in bs:
        if (b.get("price") or 0) >= 10 and not UPSELL.search(b.get("title") or ""):
            b0 = b
            break
    produit = (b0.get("title") or "").strip() or "(catalogue non indexé)"
    prix = b0.get("price")
    devise = b0.get("currency") or prof.get("currency") or ""

    ads_countries = adv.get("topCountries") or []
    pays_pub = ", ".join(f"{c['countryCode']} {round(c['share'] * 100)}%"
                         for c in ads_countries[:6] if c.get("share", 0) >= 0.03)
    part_fr = next((c["share"] for c in ads_countries if c.get("countryCode") == "FR"), 0)
    if not ads_countries:
        fr_pub, libres_txt = "inconnu - non indexé", "inconnu"
    else:
        fr_pub = f"OUI - {round(part_fr * 100)}% de leurs pubs" if part_fr >= 0.01 else "non ciblée"
        libres = [x for x in ("FR", "ES", "DE", "IT", "GB")
                  if not any(c.get("countryCode") == x and c.get("share", 0) >= 0.02 for c in ads_countries)]
        libres_txt = "/".join(libres) if libres else "aucun des 5"

    nb_prod = cat.get("productsCount")
    alertes = []
    # Le nom de domaine trahit souvent la boutique de compléments (…nutrition.co,
    # …organics.com) même quand le best-seller a un titre neutre ("Shred").
    if any(INGERABLE.search(t or "") for t in (produit, row.get("name"), dom.replace(".", " "))):
        alertes.append("INGERABLE - critère 6")
    elif COSMETIQUE.search(produit):
        alertes.append("cosmétique - réglementaire à vérifier")
    if nb_prod is not None and nb_prod > 20:
        alertes.append(f"catalogue {nb_prod} SKU - généraliste")
    if age is not None and age > 150:
        alertes.append(f"boutique de {age} j - la diffusion peut être plus jeune")
    if prix is None:
        alertes.append("prix non indexé")
    if devise and devise.upper() not in DEVISES_OK:
        alertes.append(f"devise {devise} - hors Big Five")
    if not pays_pub:
        alertes.append("pays de diffusion non indexés")
    if UPSELL.search(produit):
        alertes.append("titre = upsell, pas le produit")

    recente = (age is not None and age <= RECENTE_JOURS) or (0 < sem_diff <= 8)
    prio = 0
    if accel:
        prio += min(30, round(accel * 6))
    if sans_trafic:
        prio += 15
    if recente:
        prio += 25 if (age or 999) <= RECENTE_JOURS else 18
    elif age is not None and age <= 120:
        prio += 12
    prio += 15 if ads >= 500 else (10 if ads >= BRAND_ADS else 5)
    if techno:
        prio += 10
    if nb_prod is not None and nb_prod <= 10:
        prio += 5
    if part_fr < 0.02:
        prio += 5
    if INGERABLE.search(produit):
        prio -= 25

    return {
        "_sig": (ads, tuple(hist)) if (ads >= MIN_ADS and any(hist)) else None,
        "priorite": max(0, prio),
        "statut": statut,
        "produit": produit[:90],
        "boutique": dom,
        "marque": row.get("name") or "",
        "niche": cat.get("mainCategory") or "",
        "ads_actives": ads,
        "courbe_ads": " > ".join(str(v) for v in h),
        "acceleration": accel,
        "delta_ads_7j": _pct(h[-1], h[-2]) if len(h) >= 2 else None,
        "semaines_diffusion": sem_diff,
        "age_jours": age,
        "cree_le": created,
        "nb_skus": nb_prod,
        "visites_mois": visites,
        "invisible": sans_trafic,
        "techno_scaling": techno,
        "pays_pub": pays_pub,
        "fr_dans_leurs_pubs": fr_pub,
        "marches_libres": libres_txt,
        "prix": f"{prix} {devise}" if prix is not None else "",
        "prix_num": prix,
        "prix_eur": prix_en_euros(prix, devise),
        "pays_boutique": prof.get("countryCode") or "",
        "alertes": " | ".join(alertes),
        "reseau": "",
        "lien_boutique": "https://" + dom,
        "lien_adlibrary": ("https://www.facebook.com/ads/library/?active_status=active"
                           "&ad_type=all&country=ALL&q=" + dom.split(".")[0]),
    }


def fusionner_reseaux(lignes: list[dict]) -> list[dict]:
    """Un même annonceur sur plusieurs domaines porte la même courbe d'ads :
    on garde le domaine le plus récent et on note les miroirs."""
    groupes: dict = {}
    for p in lignes:
        if p.get("_sig"):
            groupes.setdefault(p["_sig"], []).append(p)
    garde = []
    for p in lignes:
        g = groupes.get(p.get("_sig") or ())
        if not g or len(g) == 1:
            garde.append(p)
            continue
        chef = sorted(g, key=lambda x: (x["age_jours"] if x["age_jours"] is not None else 9999,
                                        x["nb_skus"] or 999))[0]
        if p is not chef:
            continue
        autres = [x["boutique"] for x in g if x is not chef]
        p["reseau"] = f"{len(g)} domaines miroirs : {', '.join(autres)}"
        p["alertes"] = (p["alertes"] + " | " if p["alertes"] else "") + \
            f"même courbe d'ads sur {len(g)} domaines - un seul annonceur"
        garde.append(p)
    return garde


def build_day(responses: list[tuple[dict, bool]], today: _date) -> list[dict]:
    vus: dict[str, dict] = {}
    techno_par_dom: dict[str, bool] = {}
    for payload, techno in responses:
        for row in payload.get("data", []):
            dom = row.get("domain")
            if not dom:
                continue
            if techno:
                techno_par_dom[dom] = True
            if dom in vus and (row.get("advertising") or {}).get("activeAds") is None:
                continue
            vus[dom] = row

    lignes = [c for dom, row in vus.items()
              if (c := classify(row, techno_par_dom.get(dom, False), today))]
    lignes = fusionner_reseaux(lignes)
    ordre = {s: i for i, s in enumerate(STATUT_ORDRE)}
    lignes.sort(key=lambda p: (-p["priorite"], ordre.get(p["statut"], 9), -(p["ads_actives"] or 0)))
    for i, p in enumerate(lignes, 1):
        p["rang"] = i
        p.pop("_sig", None)
    return lignes


# ── Suivi cumulé ─────────────────────────────────────────────────────────────

def load_suivi() -> dict:
    if SUIVI_PATH.exists():
        try:
            return json.loads(SUIVI_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def update_suivi(suivi: dict, day: list[dict], date: str) -> dict:
    """Retourne un nouveau suivi : rangs par date, statut courant, analyses préservées."""
    nouveau = {k: dict(v) for k, v in suivi.items()}
    for p in day:
        dom = p["boutique"].lower()
        entree = dict(nouveau.get(dom, {"premiere_vue": date, "analyse_le": []}))
        entree["derniere_vue"] = date
        entree["statut"] = p["statut"]
        entree["produit"] = p["produit"]
        entree["rangs"] = {**entree.get("rangs", {}), date: p["rang"]}
        nouveau[dom] = entree
    return nouveau


CHIFFRES_KEYS = (
    "ads_actives", "courbe_ads", "acceleration", "delta_ads_7j", "age_jours", "cree_le",
    "semaines_diffusion", "visites_mois", "pays_pub", "fr_dans_leurs_pubs", "marches_libres",
    "nb_skus", "prix", "prix_eur", "statut", "priorite", "reseau", "techno_scaling",
)


def chiffres_pour(boutique: str, date: str) -> dict | None:
    """Les chiffres TrendTrack relevés pour une boutique, tels quels — c'est ce
    que la publication réinjecte dans la fiche produit, jamais retapé."""
    path = RADAR_DIR / f"{date}.json"
    if not path.exists():
        return None
    dom = boutique.lower().replace("https://", "").strip("/")
    for p in json.loads(path.read_text(encoding="utf-8")):
        if p.get("boutique", "").lower() == dom:
            return {k: p.get(k) for k in CHIFFRES_KEYS if k in p}
    return None


def mark_analysed(suivi: dict, date: str, domaines: list[str]) -> dict:
    nouveau = {k: dict(v) for k, v in suivi.items()}
    for dom in domaines:
        dom = dom.lower().replace("https://", "").strip("/")
        entree = dict(nouveau.get(dom, {"premiere_vue": date, "derniere_vue": date, "rangs": {}}))
        entree["analyse_le"] = sorted(set(entree.get("analyse_le", []) + [date]))
        nouveau[dom] = entree
    return nouveau


def _mover(entree: dict, date: str) -> int | None:
    """Gain de rang depuis la dernière observation (positif = monte)."""
    rangs = entree.get("rangs", {})
    dates = sorted(d for d in rangs if d < date)
    if not dates:
        return None
    return rangs[dates[-1]] - rangs.get(date, rangs[dates[-1]])


# Prix plancher : l'AOV réel de Badr est de 65-70 € ; sous ~30 $ un produit ne
# passe qu'en pack (feuille WINNERS du 26/08 : "prix bas vs AOV 65-70").
PRIX_MIN = 30


def qualifie(p: dict) -> tuple[bool, str]:
    """Les règles de qualification de Badr (feuille WINNERS du 26/08/2026) :
    ce qui écarte un produit avant même de l'analyser."""
    raisons = []
    if p["statut"] not in STATUTS_CANDIDATS:
        raisons.append(p["statut"].lower())
    a = p.get("alertes", "")
    if "INGERABLE" in a:
        raisons.append("ingérable — hors France (arbitrage Badr 25/08)")
    if "hors Big Five" in a:
        raisons.append("hors Big Five")
    if "non indexés" in a:
        raisons.append("pays de diffusion non indexés")
    if "catalogue" in a:
        raisons.append("catalogue généraliste")
    if str(p.get("fr_dans_leurs_pubs", "")).startswith("OUI"):
        raisons.append("cible déjà la France")
    if p.get("produit", "").startswith("(catalogue non indexé)") or p.get("prix_num") is None:
        raisons.append("produit ou prix non indexé — rien à analyser")
    prix = p.get("prix_eur", p.get("prix_num"))
    if prix is not None and prix < PRIX_MIN:
        raisons.append(f"prix bas ({p.get('prix')} ≈ {prix} €) vs AOV 65-70")
    if not est_fraiche(p):
        raisons.append("pas récente (domaine > 60 j et diffusion > 8 semaines)")
    return (not raisons, " + ".join(raisons))


def est_fraiche(p: dict) -> bool:
    """Le profil pépite de MASTER RESEARCH · 3 (:180 « ça fait juste quelques
    jours qu'ils commencent à run ») et 04-ecom-data-1.md:299 « moins de deux
    mois » : domaine ≤ 60 j, OU diffusion ≤ 8 semaines (extension de Badr pour
    les vieux domaines à diffusion neuve, cas getwildnest.com)."""
    age = p.get("age_jours")
    sem = p.get("semaines_diffusion") or 0
    return (age is not None and age <= RECENTE_JOURS) or (0 < sem <= 8)


def candidats(day: list[dict], suivi: dict, date: str, n: int = 12) -> list[dict]:
    """Les meilleures lignes à proposer à l'agent : qualifiées selon les règles
    de Badr, pas déjà analysées dans la semaine. Les movers montent."""
    limite = datetime.fromisoformat(date).date()
    out = []
    for p in day:
        ok, _ = qualifie(p)
        if not ok:
            continue
        entree = suivi.get(p["boutique"].lower(), {})
        recent = [d for d in entree.get("analyse_le", [])
                  if (limite - datetime.fromisoformat(d).date()).days < JOURS_SANS_REPROPOSER]
        if recent:
            continue
        mover = _mover(entree, date)
        out.append({**p, "mover": mover, "deja_vu": entree.get("premiere_vue", date) != date,
                    "fraiche": est_fraiche(p)})
    # Ordre : movers, puis fraîcheur (la fenêtre de copie), puis explosion, puis prio.
    out.sort(key=lambda p: (
        -(p["mover"] or 0) if (p["mover"] or 0) > 5 else 0,
        0 if p["fraiche"] else 1,
        0 if p["statut"] in ("BANGER", "EXPLOSE") else 1,
        -p["priorite"],
    ))
    return out[:n]


def raisons_ecart(day: list[dict]) -> dict[str, int]:
    compte: dict[str, int] = {}
    for p in day:
        ok, raison = qualifie(p)
        if not ok:
            compte[raison] = compte.get(raison, 0) + 1
    return dict(sorted(compte.items(), key=lambda kv: -kv[1]))


def format_candidats(cands: list[dict], date: str, total: int, par_statut: dict,
                     ecartes: dict[str, int] | None = None) -> str:
    lines = [
        f"# Radar produits — candidats du {date}",
        "",
        f"{total} boutiques dépouillées. Statuts : "
        + ", ".join(f"{k} {v}" for k, v in par_statut.items()) + ".",
        "",
    ]
    if ecartes:
        lines += ["Écartés avant analyse (règles de Badr) : "
                  + " · ".join(f"{k} : {v}" for k, v in list(ecartes.items())[:8]) + ".", ""]
    lines += [
        "Choisis 3 produits ci-dessous (règles dans docs/RADAR.md) et analyse-les en profondeur.",
        "",
    ]
    for p in cands:
        tags = [p["statut"]]
        if p.get("fraiche"):
            tags.append("FRAÎCHE")
        if p.get("mover"):
            tags.append(f"mover +{p['mover']} places")
        if p.get("techno_scaling"):
            tags.append("Triple Whale")
        if p.get("deja_vu"):
            tags.append("déjà vu")
        lines += [
            f"## {p['rang']}. {p['produit']} — {p['boutique']}  [{' · '.join(tags)}]",
            f"- niche : {p['niche'] or '?'} | prix vu : {p['prix'] or '?'} | SKU : {p['nb_skus']} | boutique : {p['pays_boutique'] or '?'}",
            f"- ads actives : {p['ads_actives']} | courbe 5 sem. : {p['courbe_ads']} | ×{p['acceleration']} en 4 sem. | {p['semaines_diffusion']} sem. de diffusion | âge {p['age_jours']} j",
            f"- trafic affiché : {p['visites_mois']} visites/mois (0 = fenêtre encore ouverte) | pays de leurs pubs : {p['pays_pub'] or 'non indexés'}",
            f"- France ciblée par eux : {p['fr_dans_leurs_pubs']} | marchés pas encore ciblés : {p['marches_libres']}",
            f"- alertes : {p['alertes'] or 'aucune'}" + (f" | réseau : {p['reseau']}" if p['reseau'] else ""),
            f"- liens : {p['lien_boutique']} · {p['lien_adlibrary']}",
            "",
        ]
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def cmd_extract(date: str, src: list[str] | None, max_age_hours: float) -> int:
    today = datetime.fromisoformat(date).date()
    responses = iter_responses(src, max_age_hours)
    if not responses:
        logger.error("Aucune réponse search_shops trouvée — lance les passes TrendTrack d'abord "
                     "(ou dépose les réponses JSON dans data/radar/raw/)")
        return 1
    day = build_day(responses, today)
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    (RADAR_DIR / f"{date}.json").write_text(json.dumps(day, ensure_ascii=False, indent=1), encoding="utf-8")

    suivi = update_suivi(load_suivi(), day, date)
    SUIVI_PATH.write_text(json.dumps(suivi, ensure_ascii=False, indent=1), encoding="utf-8")

    par_statut = {}
    for p in day:
        par_statut[p["statut"]] = par_statut.get(p["statut"], 0) + 1
    par_statut = {s: par_statut[s] for s in STATUT_ORDRE if s in par_statut}
    cands = candidats(day, suivi, date)
    (RADAR_DIR / f"candidats_{date}.md").write_text(
        format_candidats(cands, date, len(day), par_statut, raisons_ecart(day)), encoding="utf-8")
    logger.info(f"Radar {date} : {len(day)} boutiques — {par_statut} — {len(cands)} candidats")
    return 0


def cmd_candidats(date: str, n: int) -> int:
    path = RADAR_DIR / f"{date}.json"
    if not path.exists():
        logger.error(f"{path} introuvable — lance 'extract' d'abord")
        return 1
    day = json.loads(path.read_text(encoding="utf-8"))
    par_statut = {}
    for p in day:
        par_statut[p["statut"]] = par_statut.get(p["statut"], 0) + 1
    print(format_candidats(candidats(day, load_suivi(), date, n), date, len(day), par_statut,
                           raisons_ecart(day)))
    return 0


def cmd_pubs(mot: str, src: list[str] | None, max_age_hours: float) -> int:
    """Affiche les pubs concurrentes (copies réelles) trouvées par search_ads
    dont la requête contient `mot` — pour citer l'angle du concurrent."""
    dirs = []
    for pattern in (src or DEFAULT_TOOL_RESULT_GLOBS):
        dirs.extend(glob.glob(os.path.expanduser(pattern)))
    dirs.append(str(RAW_DIR))
    cutoff = time.time() - max_age_hours * 3600
    trouve = 0
    for d in dirs:
        for path in sorted(Path(d).glob("*search_ads*")):
            if not path.is_file() or path.stat().st_mtime < cutoff:
                continue
            payload = _load_payload(path)
            if not isinstance(payload, dict):
                continue
            meta = payload.get("meta") or {}
            if mot.lower() not in str(meta.get("query", "")).lower():
                continue
            print(f"=== requête « {meta.get('query')} » · pays {meta.get('country')} · {payload.get('pagination', {}).get('total')} pubs au total")
            vus = set()
            for r in payload.get("data", []):
                adv = r.get("advertiser") or {}
                body = ((r.get("content") or {}).get("body") or "").strip()
                key = (adv.get("name"), body[:80])
                if not body or key in vus:
                    continue
                vus.add(key)
                trouve += 1
                print(f"--- {adv.get('name')} | {adv.get('liveAdsCount')} pubs actives | {r.get('daysRunning')} j | "
                      f"{(r.get('metrics') or {}).get('reach')} touchés | {(r.get('content') or {}).get('landingPageDomain') or ''}")
                print("   " + body[:700].replace("\n", " ⏎ "))
    if not trouve:
        print(f"Aucune pub trouvée pour « {mot} » — lance d'abord search_ads avec ce mot.")
        return 1
    return 0


# ── Contrôle pays par la Meta Ad Library (gratuit, connecteur META) ──────────
# L'agent enregistre la réponse de ads_library_search dans
# data/radar/raw/meta_<PAYS>_<mot>.json ; ici on la lit et on tranche.

SEUIL_PAGES_PRIS = 5          # ≥ 5 annonceurs = marché PRIS (stade 3+)
SEUIL_ADS_DOMINANT = 20       # une page avec ≥ 20 pubs dans l'échantillon de 50 = acteur dominant
JOURS_RECENT = 60             # concurrent « récent » = première pub ≤ 60 jours


def _payload_meta(payload) -> dict:
    """Le connecteur renvoie {"results": "<json>"} ; on accepte aussi le JSON déjà décodé."""
    if isinstance(payload, dict) and isinstance(payload.get("results"), str):
        try:
            return json.loads(payload["results"])
        except json.JSONDecodeError:
            return {}
    return payload if isinstance(payload, dict) else {}


def analyser_marche_meta(payload, aujourd_hui: float | None = None) -> dict:
    """Agrège une réponse Meta Ad Library par annonceur et rend le verdict de marché
    (MASTER RESEARCH · 3 lu avec la leçon 33) : LIBRE = personne ; PARTIEL = 1-4
    annonceurs, aucun dominant ; PRIS = ≥ 5 annonceurs ou un acteur dominant."""
    data = _payload_meta(payload)
    ads = data.get("ads") or []
    total = int(data.get("estimated_total_count") or len(ads))
    now = aujourd_hui or time.time()
    pages: dict[str, dict] = {}
    for a in ads:
        pid = str(a.get("page_id") or a.get("page_name") or "")
        if not pid:
            continue
        p = pages.setdefault(pid, {"page": a.get("page_name") or pid, "ads": 0, "premiere_pub": None, "exemple": ""})
        p["ads"] += 1
        t = a.get("ad_creation_time") or a.get("ad_delivery_start_time")
        if t and (p["premiere_pub"] is None or t < p["premiere_pub"]):
            p["premiere_pub"] = t
        if not p["exemple"] and a.get("ad_creative_link_title"):
            p["exemple"] = a["ad_creative_link_title"]
    annonceurs = sorted(pages.values(), key=lambda p: -p["ads"])
    for p in annonceurs:
        p["age_jours"] = int((now - p["premiere_pub"]) / 86400) if p["premiere_pub"] else None
        p["recent"] = p["age_jours"] is not None and p["age_jours"] <= JOURS_RECENT
    dominant = [p for p in annonceurs if p["ads"] >= SEUIL_ADS_DOMINANT]
    if not annonceurs and total == 0:
        verdict, raison = "LIBRE", "aucune pub active ne contient ces mots"
    elif len(annonceurs) >= SEUIL_PAGES_PRIS or dominant:
        qui = ", ".join(f"{p['page']} ({p['ads']} pubs)" for p in (dominant or annonceurs)[:3])
        verdict, raison = "PRIS", f"{len(annonceurs)} annonceurs" + (f", dominant : {qui}" if dominant else f" : {qui}")
    else:
        qui = ", ".join(f"{p['page']} ({p['ads']} pubs{', récent' if p['recent'] else ''})" for p in annonceurs)
        verdict, raison = "PARTIEL", f"{len(annonceurs)} annonceur(s) sans dominant : {qui}"
    return {"verdict": verdict, "raison": raison, "total_pubs": total, "nb_annonceurs": len(annonceurs),
            "annonceurs": annonceurs, "stade": 1 if verdict == "LIBRE" else 2 if verdict == "PARTIEL" else 3}


def cmd_marche(pays: str, mot: str) -> int:
    """Lit data/radar/raw/meta_<PAYS>_<mot>.json et imprime le verdict de marché."""
    slug = re.sub(r"[^a-z0-9]+", "-", mot.lower()).strip("-")
    candidats = sorted(RAW_DIR.glob(f"meta_{pays.upper()}_{slug}*.json"))
    if not candidats:
        print(f"Aucun fichier data/radar/raw/meta_{pays.upper()}_{slug}.json — enregistre d'abord la réponse de ads_library_search.")
        return 1
    res = analyser_marche_meta(_load_payload(candidats[-1]))
    print(f"=== {pays.upper()} · « {mot} » · {res['total_pubs']} pubs actives estimées · {res['nb_annonceurs']} annonceurs dans l'échantillon")
    print(f"VERDICT : {res['verdict']} (stade {res['stade']}) — {res['raison']}")
    for p in res["annonceurs"][:12]:
        age = f"{p['age_jours']} j" if p["age_jours"] is not None else "?"
        print(f"  - {p['page']:<40} {p['ads']:>3} pubs · première pub il y a {age}{' · RÉCENT' if p['recent'] else ''}"
              + (f" · « {p['exemple'][:60]} »" if p["exemple"] else ""))
    return 0


def cmd_mark(date: str, domaines: list[str]) -> int:
    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    suivi = mark_analysed(load_suivi(), date, domaines)
    SUIVI_PATH.write_text(json.dumps(suivi, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"{len(domaines)} boutique(s) marquée(s) analysée(s) le {date}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ext = sub.add_parser("extract")
    p_ext.add_argument("date")
    p_ext.add_argument("--src", nargs="*", default=None, help="dossiers tool-results (glob)")
    p_ext.add_argument("--max-age-hours", type=float, default=24)

    p_cand = sub.add_parser("candidats")
    p_cand.add_argument("date")
    p_cand.add_argument("--n", type=int, default=12)

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("date")
    p_mark.add_argument("domaines", nargs="+")

    p_pubs = sub.add_parser("pubs", help="copies réelles des pubs concurrentes (search_ads)")
    p_pubs.add_argument("date")
    p_pubs.add_argument("mot")
    p_pubs.add_argument("--src", nargs="*", default=None)
    p_pubs.add_argument("--max-age-hours", type=float, default=24)

    p_marche = sub.add_parser("marche", help="verdict LIBRE/PARTIEL/PRIS depuis une réponse Meta Ad Library enregistrée")
    p_marche.add_argument("pays")
    p_marche.add_argument("mot")

    args = parser.parse_args(argv)
    if args.cmd == "extract":
        return cmd_extract(args.date, args.src, args.max_age_hours)
    if args.cmd == "marche":
        return cmd_marche(args.pays, args.mot)
    if args.cmd == "candidats":
        return cmd_candidats(args.date, args.n)
    if args.cmd == "pubs":
        return cmd_pubs(args.mot, args.src, args.max_age_hours)
    return cmd_mark(args.date, args.domaines)


if __name__ == "__main__":
    sys.exit(main())
