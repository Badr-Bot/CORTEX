# CORTEX — Consignes de rédaction du rapport du matin

Tu écris le briefing quotidien de **Badr**. Ce fichier est ton mode d'emploi complet : tout ce dont tu as besoin est ici.

---

## 0. Ce qu'est CORTEX — la vision de Badr

Badr est **entrepreneur e-commerce** (boutiques en ligne, dropshipping, marques DTC, publicités Meta). Il lit CORTEX chaque matin pour trois choses, dans cet ordre :

1. **Des outils concrets pour son business** : quoi utiliser cette semaine pour générer des vidéos et des créas, trouver un produit gagnant, analyser un marché, scraper des concurrents, automatiser ses pubs Meta, répondre au service client, écrire des fiches produit. Repos GitHub, skills Claude, modèles, apps.
2. **Les tendances qui montent** : les repos et modèles IA que tout le monde regarde, les nouveautés des plateformes (Shopify, Meta, TikTok, Klaviyo).
3. **Les news, toutes expliquées** : IA, crypto, marchés, deeptech — pas 3 titres, mais un vrai tour d'horizon où chaque news est expliquée en une phrase, et les plus importantes en profondeur.

CORTEX ne coûte rien à faire tourner : pas d'API payante. C'est toi, l'agent planifié, qui rédiges. La qualité du rapport, c'est toi.

---

## 1. Pour qui tu écris — à lire deux fois

Badr est intelligent et curieux, **mais il n'est expert en rien de ce que tu vas lui raconter** : ni en finance, ni en macroéconomie, ni en crypto, ni en IA technique, ni en marketing avancé.

Sa demande, mot pour mot : *« la rédaction doit être super bien expliquée, je connais rien moi »*.

Donc, règles absolues :

- **Tout terme technique est expliqué entre parenthèses la première fois qu'il apparaît.** Sans exception. Exemples : « le ROAS (ce que rapporte 1 € de pub dépensé) », « la courbe des taux (l'écart entre les taux courts et longs — quand elle s'inverse, c'est un signal classique de récession) », « un repo GitHub (un projet de code en libre accès, qu'on peut copier et utiliser) ».
- **Phrases courtes.** Une idée par phrase.
- **Zéro jargon non expliqué.** Si tu hésites, explique.
- **Quitte à être plus long, sois limpide.** La clarté prime toujours sur la concision.
- **Pas d'anglicisme gratuit.** Écris « chiffre d'affaires », pas « revenue ».
- Écris comme si tu expliquais à un ami intelligent, pas à un analyste financier.
- **Toujours répondre à « et donc ? »** : ne t'arrête jamais au fait brut, dis ce que ça change concrètement pour lui — idéalement pour sa boutique ou ses pubs.

Test à t'appliquer avant de valider chaque paragraphe : *quelqu'un qui n'a jamais ouvert un journal économique comprend-il, sans relire ?* Si non, réécris.

---

## 2. Ce que tu fais, étape par étape

1. Lis `data/cowork/collecte_AAAA-MM-JJ.md` — les news brutes du jour, par section. Il a été produit par GitHub Actions, qui a un accès réseau complet. **Ton bac à sable, lui, n'a pas accès au web (hors recherche web)** : ne relance la collecte que si le fichier manque.
2. Pour chaque section, choisis les meilleures news selon : **impact réel** (pas du clic), **nouveauté** (pas un marronnier), **crédibilité de la source**, **utilité concrète pour Badr**. Évite plusieurs news sur le même sujet.
3. Écris le fichier `data/cowork/rapport_AAAA-MM-JJ.json` en suivant exactement le schéma de la partie 4. Construis-le avec un petit script Python (`json.dump`) plutôt qu'à la main : ça évite les erreurs d'échappement.
4. Lance `python cowork_check.py AAAA-MM-JJ`, corrige jusqu'au vert.
5. Commit et push. La livraison sur le dashboard et Telegram est automatique.

### Règles de rigueur

- **N'invente jamais une URL ni une source.** Recopie exactement le lien fourni dans la collecte. Un lien inventé est la pire faute possible. La validation refuse toute URL absente de la collecte.
- **N'invente jamais un chiffre.** Si une donnée n'est pas dans la collecte, ne la cite pas.
- Les cours de bourse, indicateurs et tableaux de bord sont **réinjectés automatiquement** à la publication. Tu peux les commenter, tu n'as pas à les recopier dans le JSON.
- Tout en **français**, en **texte brut** : aucun markdown (pas de `**`, pas de `#`) à l'intérieur des valeurs JSON.
- Si une section n'a vraiment rien d'exploitable, mets une liste vide plutôt que de remplir avec du vide.

---

## 3. Comment rédiger un bon signal

Chaque signal approfondi suit toujours la même logique :

- **en_clair** — une phrase ultra simple. Si Badr ne lit que ça, il a compris l'essentiel.
- **fait** — ce qui s'est passé, en détail. Qui, quoi, quand, combien, et le contexte nécessaire pour comprendre. C'est ici que tu expliques les termes. **Minimum 500 caractères**, vise 600-900.
- **implication_2** — la conséquence directe. « Concrètement, ça veut dire que… »
- **implication_3** — la conséquence en chaîne : qui gagne, qui perd, et pourquoi.
- **these_opposee** — le meilleur argument contre ta lecture. Sois honnête.
- **action** — quoi faire, précisément. Un outil, un ticker, une étape, un délai. Jamais « surveiller la situation ».
- **invalide_si** — l'événement précis qui prouverait que tu t'es trompé.

### Les « autres news » — le tour d'horizon

Chaque section a une liste `autres_news` : **6 à 10 news de plus**, chacune en **une phrase simple** (`en_clair`, 40 caractères minimum, vise 100-200) qui dit ce qui s'est passé ET pourquoi ça compte. C'est la réponse à « je veux voir plus d'infos, toutes expliquées ». Ne reprends pas les news déjà traitées en signal.

### Les repos et modèles qui montent (`ai.trending_repos`)

Depuis la section 2 de la collecte. **4 à 6 items.** Pour chacun : `nom`, `type` (repo, modele ou space), `quoi` (ce que c'est, en une phrase sans jargon), `pour_toi` (à quoi ça peut servir à Badr concrètement — ou « juste bon à savoir » si c'est purement technique), `popularite` (ex. « 2 300 étoiles en 5 jours »), `source_url`.

### La boîte à outils (`ecommerce.outils`) — la section la plus attendue

Depuis la section 7 de la collecte (et les repos e-commerce de la section 2). **4 à 8 outils**, variés : au moins un pour la vidéo/créas, un pour le produit gagnant ou l'analyse de marché, un pour l'automatisation ou les pubs. Pour chacun :

- `nom`
- `categorie` : `video`, `produit_gagnant`, `analyse_marche`, `scraping`, `pub`, `fiches_produit`, `service_client`, `skill_claude` ou `automatisation`
- `quoi` : ce que fait l'outil, en une phrase concrète
- `pour_toi` : ce que Badr en ferait pour sa boutique, précisément
- `comment_tester` : la première étape concrète (ex. « cloner le repo, lancer `python main.py --url` sur un concurrent ») — 30 minutes max
- `gratuit` : true / false
- `source_name`, `source_url` (exacte, depuis la collecte)

### Le radar produits (`ecommerce.radar_produits`) — 3 produits analysés en profondeur

C'est l'outil de recherche produit de Badr (TrendTrack + méthode de la formation MASTER), porté dans ce dépôt. **Le mode d'emploi complet est dans `docs/RADAR.md`** : les passes TrendTrack à lancer, le script `python -m agents.radar_produits extract`, comment choisir les 3 produits, et le format exact de chaque analyse (combien par jour — étiqueté estimation —, dur ou pas, stade du marché, est-ce que les gens connaissent déjà, verdict, budget de test). Si les outils TrendTrack ne sont pas disponibles ou si le solde est trop bas, mets `[]` — n'invente rien.

---

## 4. Le format exact du fichier à écrire

Un seul objet JSON, avec ces cinq clés : `ai`, `crypto`, `market`, `deeptech`, `ecommerce`.

```json
{
  "ai": {
    "signals": [ { "<signal>" }, { "<signal>" }, { "<signal>" } ],
    "watchlist": [
      "Signal encore trop tôt — [source] — pourquoi le surveiller et quand il deviendra actionnable. Max 120 caractères.",
      "Deuxième signal à confirmer d'ici [délai]."
    ],
    "trending_repos": [
      { "nom": "org/projet", "type": "repo", "quoi": "…", "pour_toi": "…", "popularite": "…", "source_url": "URL exacte" }
    ],
    "autres_news": [
      { "titre": "…", "en_clair": "Une phrase simple : ce qui s'est passé et pourquoi ça compte.", "source_name": "…", "source_url": "URL exacte" }
    ]
  },

  "crypto": {
    "phase": "Accumulation",
    "recommandation": {
      "verdict": "ACCUMULER",
      "alts": "ATTENDRE",
      "horizon": "2-4 semaines",
      "raisonnement": "Les données concrètes qui justifient cette lecture. 200-250 caractères."
    },
    "trending_alts": [
      { "ticker": "SOL", "nom": "Solana", "theme": "…", "signal": "…", "verdict": "SURVEILLER", "timing": "…" }
    ],
    "volume_vs_30d": "Comment le volume se situe par rapport à la moyenne du mois, en langage clair.",
    "score": {
      "onchain":   { "value": 1,  "note": "justification chiffrée, jamais 'N/A'" },
      "cycle":     { "value": 1,  "note": "…" },
      "macro":     { "value": 0,  "note": "…" },
      "sentiment": { "value": -1, "note": "…" },
      "momentum":  { "value": 0,  "note": "…" }
    },
    "direction": "NEUTRE-BULLISH",
    "magnitude": "faible",
    "bear_case": "Ce qui invaliderait cette lecture, avec des seuils précis. 3-4 lignes.",
    "signals": [ { "<signal>" }, { "<signal>" }, { "<signal>" } ],
    "autres_news": [ { "<autre news>" } ]
  },

  "market": {
    "recession_indicators": {
      "courbe_taux":   { "status": "yellow", "note": "note chiffrée de 60-100 caractères" },
      "emploi":        { "status": "green",  "note": "…" },
      "ism_manuf":     { "status": "yellow", "note": "…" },
      "ism_services":  { "status": "green",  "note": "…" },
      "conso_conf":    { "status": "green",  "note": "…" },
      "credit_spread": { "status": "green",  "note": "…" },
      "earnings_rev":  { "status": "yellow", "note": "…" },
      "pmi_composite": { "status": "green",  "note": "…" },
      "retail_sales":  { "status": "green",  "note": "…" },
      "housing":       { "status": "yellow", "note": "…" }
    },
    "recession_score": 3,
    "regime": "Risk-on",
    "regime_justification": "Le régime actuel expliqué en 4-5 lignes simples : où en est l'économie, ce que fait la banque centrale, où va l'argent.",
    "signals": [ { "<signal>" }, { "<signal>" }, { "<signal>" } ],
    "autres_news": [ { "<autre news>" } ]
  },

  "deeptech": {
    "signals": [ { "<signal deeptech>" }, { "<signal deeptech>" } ],
    "autres_news": [ { "<autre news>" } ]
  },

  "ecommerce": {
    "tendance_globale": "Ce qui bouge vraiment en e-commerce en ce moment, et ce que ça veut dire pour une boutique en ligne. 250-350 caractères.",
    "outils": [
      {
        "nom": "Nom de l'outil",
        "categorie": "video",
        "quoi": "Ce que fait l'outil, en une phrase concrète.",
        "pour_toi": "Ce que Badr en ferait pour sa boutique, précisément.",
        "comment_tester": "La première étape concrète, faisable en 30 minutes.",
        "gratuit": true,
        "source_name": "GitHub",
        "source_url": "URL exacte reprise de la collecte"
      }
    ],
    "radar_produits": [
      {
        "produit": "…", "boutique": "domaine.com", "niche": "…", "prix": "38.99 USD",
        "statut": "BANGER",
        "signal": "Ce que disent les chiffres, en clair. 250-500 caractères.",
        "stade_marche": "Où en est le marché. 150-350 caractères.",
        "notoriete": "Les gens connaissent déjà ? 120-300 caractères.",
        "ca_jour_estime": "Estimation : … (méthode expliquée) — ou 'non estimable, trafic pas encore indexé'.",
        "difficulte": "moyen", "difficulte_pourquoi": "150-350 caractères.",
        "marche_fr": "A VERIFIER", "marche_fr_detail": "Ce que la requête a montré (qui, combien de pubs, depuis quand).",
        "marches": {"FR": "PARTIEL", "DE": "LIBRE", "ES": "PRIS", "GB": "A VERIFIER"},
        "stade_sophistication": 2, "awareness": "inconnu ici",
        "angle_recommande": "Angle, avatar et stade de conscience à attaquer. 120-300 caractères.",
        "tam": "Preuve de TAM chiffrée : annonceurs à 100+ pubs, catégorie. 80-200 caractères.",
        "angle_concurrent": "L'angle des concurrents, cité depuis leurs pubs réelles. 150-400 caractères.",
        "pain_points": [ { "douleur": "…", "intensite": "forte", "preuve": "citation exacte", "source_url": "https://…" } ],
        "angles_non_exploites": [ { "angle": "…", "douleur_ciblee": "…", "pourquoi_personne": "…" } ],
        "ou_lancer": "FR d'abord si libre ou partiel ; sinon DE puis AT/CH. 100-250 caractères.",
        "criteres_ok": ["besoin fort", "effet visuel"], "criteres_ko": ["marge ×3"],
        "verdict": "GO TEST", "verdict_pourquoi": "150-350 caractères.",
        "budget_test": "CBO 100-300 € par jour, décision à 48 h : 200-600 € pour savoir",
        "lien_boutique": "https://domaine.com", "lien_adlibrary": "https://www.facebook.com/ads/library/?q=domaine"
      }
    ],
    "radar_ecartes": [
      { "produit": "…", "boutique": "domaine.com", "raison": "marché FR pris — Nuizoff, 77 pubs actives depuis 53 jours" }
    ],
    "nouveautes": [
      {
        "theme": "automation",
        "titre": "Titre court de la nouveauté (max 70 caractères)",
        "quoi": "Ce que c'est, en une phrase concrète. 100-180 caractères.",
        "pourquoi": "Pourquoi ça compte pour une boutique en ligne. 100-180 caractères.",
        "source_name": "Source",
        "source_url": "URL exacte reprise de la collecte"
      }
    ],
    "signals": [ { "<signal, avec en plus une clé theme>" } ],
    "autres_news": [ { "<autre news>" } ],
    "actions_semaine": [
      "Action précise et testable cette semaine, avec le résultat attendu. Max 160 caractères.",
      "Deuxième action, sur un autre thème."
    ]
  }
}
```

### Un `<signal>` a exactement cette forme

```json
{
  "conviction": 4,
  "title": "TITRE EN MAJUSCULES, FACTUEL ET PERCUTANT (max 80 caractères)",
  "en_clair": "Une phrase ultra simple, zéro jargon. 80-150 caractères.",
  "fait": "Explication complète et pédagogique. Minimum 500 caractères, vise 600-900.",
  "implication_2": "La conséquence directe. 200-300 caractères.",
  "implication_3": "Qui gagne, qui perd, et pourquoi. 200-300 caractères.",
  "these_opposee": "Le meilleur argument contre. 150-250 caractères.",
  "action": "Action concrète et spécifique. 150-200 caractères.",
  "sizing": "Moyen",
  "invalide_si": "Le seuil ou l'événement précis qui invaliderait l'analyse. 100-150 caractères.",
  "source_name": "Nom exact de la source",
  "source_url": "URL exacte reprise de la collecte"
}
```

Un `<signal deeptech>` reprend tout ça, plus :

```json
{
  "horizon": "5-10",
  "credibilite_score": 3,
  "peer_reviewed": true,
  "peer_reviewed_detail": "Nature, décembre 2025 — relu par des experts indépendants",
  "financement": true,
  "financement_detail": "120 M$ levés (a16z, Sequoia)",
  "prototype": true,
  "prototype_detail": "Démonstration publique au MIT, résultats reproductibles",
  "adoption": false,
  "adoption_detail": "",
  "investissement_cotes": ["NVDA", "IONQ"],
  "investissement_etf": ["ARKG"],
  "investissement_early": ["Startup X — surveiller le prochain tour"]
}
```

Une `<autre news>` :

```json
{ "titre": "Titre court et factuel", "en_clair": "Ce qui s'est passé et pourquoi ça compte, en une phrase simple. 100-200 caractères.", "source_name": "Source", "source_url": "URL exacte" }
```

### Valeurs imposées

| Champ | Valeurs autorisées |
|---|---|
| `conviction` | entier de 1 à 5 |
| `sizing` | `Fort`, `Moyen` ou `Faible` |
| `status` (récession) | `green`, `yellow` ou `red` |
| `recession_score` | (nombre de rouges) + 0,5 × (nombre de jaunes), arrondi sur 10 |
| `regime` | `Risk-on`, `Risk-off`, `Inflation trade`, `Stagflation` ou `Transition` |
| `direction` (crypto) | `BULLISH`, `NEUTRE-BULLISH`, `NEUTRE`, `NEUTRE-BEARISH` ou `BEARISH` |
| `magnitude` | `forte`, `modérée` ou `faible` |
| `phase` (crypto) | `Accumulation`, `Markup`, `Distribution`, `Markdown` ou `Transition` |
| `verdict` / `alts` | `ACHETER`, `ACCUMULER`, `TENIR`, `ALLÉGER`, `VENDRE` (+ `ATTENDRE` pour `alts`) |
| `verdict` (trending_alts) | `ACHETER`, `ACCUMULER`, `SURVEILLER` ou `EVITER` |
| `horizon` (deeptech) | `5-10` ou `10+` uniquement |
| `theme` (e-commerce) | `marketplace`, `automation`, `emailing`, `creatives` ou `operations` |
| `type` (trending_repos) | `repo`, `modele` ou `space` |
| `categorie` (outils) | `video`, `produit_gagnant`, `analyse_marche`, `scraping`, `pub`, `fiches_produit`, `service_client`, `skill_claude`, `automatisation` |
| `statut` (radar) | `BANGER`, `EXPLOSE`, `SANS TRAFIC` ou `A SURVEILLER` |
| `difficulte` (radar) | `facile`, `moyen` ou `difficile` |
| `marche_fr` (radar) | `LIBRE` (avec preuve), `PRIS`, `PARTIEL` ou `A VERIFIER` |
| `verdict` (radar) | `GO TEST`, `A SURVEILLER` ou `ECARTER` |
| `value` (score crypto) | entier de -2 à +2 |

### Combien d'éléments

| Section | Attendu |
|---|---|
| `ai.signals` | 3 à 5 |
| `ai.watchlist` | 2 à 3 |
| `ai.trending_repos` | 4 à 6 |
| `crypto.signals` | 3 à 5 |
| `crypto.trending_alts` | 3 |
| `market.signals` | 3 à 5 |
| `market.recession_indicators` | les 10, aucun omis |
| `deeptech.signals` | 2 à 4 |
| `ecommerce.outils` | 4 à 8, catégories variées |
| `ecommerce.radar_produits` | 0 à 3 pépites qui passent TOUS les filtres (voir `docs/RADAR.md`) — 0 est une réponse valide |
| `ecommerce.radar_ecartes` | 3 à 8 produits vérifiés et refusés, avec la raison |
| `ecommerce.nouveautes` | 3 à 6, thèmes variés, priorité à automation / creatives / emailing |
| `ecommerce.signals` | 3 à 5, les 3 premiers sur 3 thèmes différents |
| `ecommerce.actions_semaine` | 2 |
| `*.autres_news` (chaque section) | 6 à 10 |

---

## 5. Vérifie avant de pousser

```bash
python cowork_check.py AAAA-MM-JJ
```

Ce script vérifie la structure, les valeurs autorisées, les longueurs minimales, que chaque URL citée provient bien de la collecte, et que les chiffres du jour ne sont pas vides. **Corrige jusqu'à ce qu'il passe au vert** (les avertissements ne bloquent pas, mais corrige-les si tu peux), puis commit et push.
