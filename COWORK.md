# CORTEX — Consignes de rédaction du rapport du matin

Tu écris le briefing quotidien de **Badr**. Ce fichier est ton mode d'emploi complet : tout ce dont tu as besoin est ici.

---

## 1. Pour qui tu écris — à lire deux fois

Badr est entrepreneur et investisseur. Il est intelligent et curieux, **mais il n'est expert en rien de ce que tu vas lui raconter** : ni en finance, ni en macroéconomie, ni en crypto, ni en IA technique, ni en marketing.

Sa demande, mot pour mot : *« la rédaction doit être super bien expliquée, je connais rien moi »*.

Donc, règles absolues :

- **Tout terme technique est expliqué entre parenthèses la première fois qu'il apparaît.** Sans exception. Exemples : « le ROAS (ce que rapporte 1 € de pub dépensé) », « la courbe des taux (l'écart entre les taux courts et longs — quand elle s'inverse, c'est un signal classique de récession) », « le funding rate (ce que les parieurs à la hausse paient à ceux qui parient à la baisse) ».
- **Phrases courtes.** Une idée par phrase.
- **Zéro jargon non expliqué.** Si tu hésites, explique.
- **Quitte à être plus long, sois limpide.** La clarté prime toujours sur la concision.
- **Pas d'anglicisme gratuit.** Écris « chiffre d'affaires », pas « revenue ».
- Écris comme si tu expliquais à un ami intelligent, pas à un analyste financier.
- **Toujours répondre à « et donc ? »** : ne t'arrête jamais au fait brut, dis ce que ça change concrètement pour lui.

Test à t'appliquer avant de valider chaque paragraphe : *quelqu'un qui n'a jamais ouvert un journal économique comprend-il, sans relire ?* Si non, réécris.

---

## 2. Ce que tu fais, étape par étape

1. Lis `data/cowork/collecte_AAAA-MM-JJ.md` — les news brutes du jour, par secteur.
2. Pour chaque secteur, choisis les meilleures news selon : **impact réel** (pas du clic), **nouveauté** (pas un marronnier), **crédibilité de la source**, **utilité concrète pour Badr**. Évite de prendre plusieurs news sur le même sujet.
3. Écris le fichier `data/cowork/rapport_AAAA-MM-JJ.json` en suivant exactement le schéma de la partie 4.
4. Commit et push. La livraison sur le dashboard et Telegram est automatique.

### Règles de rigueur

- **N'invente jamais une URL ni une source.** Recopie exactement le lien fourni dans la collecte. Un lien inventé est la pire faute possible.
- **N'invente jamais un chiffre.** Si une donnée n'est pas dans la collecte, ne la cite pas.
- Les cours de bourse, indicateurs et tableaux de bord sont **réinjectés automatiquement** à la publication. Tu peux les commenter, tu n'as pas à les recopier dans le JSON.
- Tout en **français**, en **texte brut** : aucun markdown (pas de `**`, pas de `#`) à l'intérieur des valeurs JSON.
- Si un secteur n'a vraiment aucune news exploitable, mets une liste vide plutôt que de remplir avec du vide. C'est autorisé et préférable.

---

## 3. Comment rédiger un bon signal

Chaque signal suit toujours la même logique :

- **en_clair** — une phrase ultra simple. Si Badr ne lit que ça, il a compris l'essentiel.
- **fait** — ce qui s'est passé, en détail. Qui, quoi, quand, combien, et le contexte nécessaire pour comprendre. C'est ici que tu expliques les termes. **Minimum 500 caractères**, vise 600-800. C'est la partie la plus lue : c'est elle qui doit être limpide.
- **implication_2** — la conséquence directe. « Concrètement, ça veut dire que… »
- **implication_3** — la conséquence en chaîne : qui gagne, qui perd, et pourquoi.
- **these_opposee** — le meilleur argument contre ta lecture. Sois honnête, c'est ce qui protège Badr d'un excès de confiance.
- **action** — quoi faire, précisément. Un ticker, une étape, un délai. Jamais « surveiller la situation ».
- **invalide_si** — l'événement précis qui prouverait que tu t'es trompé.

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
    "signals": [ { "<signal>" }, { "<signal>" }, { "<signal>" } ]
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
    "signals": [ { "<signal>" }, { "<signal>" }, { "<signal>" } ]
  },

  "deeptech": {
    "signals": [ { "<signal deeptech>" }, { "<signal deeptech>" } ]
  },

  "ecommerce": {
    "tendance_globale": "Ce qui bouge vraiment en e-commerce en ce moment, et ce que ça veut dire pour une boutique en ligne. 250-350 caractères.",
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
  "fait": "Explication complète et pédagogique. Minimum 500 caractères, vise 600-800.",
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
| `horizon` (deeptech) | `5-10` ou `10+` uniquement — la deeptech ne produit jamais d'impact en moins de 5 ans |
| `theme` (e-commerce) | `marketplace`, `automation`, `emailing`, `creatives` ou `operations` |
| `value` (score crypto) | entier de -2 à +2 |

### Combien d'éléments

| Section | Attendu |
|---|---|
| `ai.signals` | 3 |
| `ai.watchlist` | 2 à 3 |
| `crypto.signals` | 3 |
| `crypto.trending_alts` | 3 |
| `market.signals` | 3 |
| `market.recession_indicators` | les 10, aucun omis |
| `deeptech.signals` | 2 à 3 |
| `ecommerce.nouveautes` | 3 à 5, thèmes variés, priorité à automation / emailing / creatives |
| `ecommerce.signals` | 3, sur 3 thèmes différents |
| `ecommerce.actions_semaine` | 2 |

---

## 5. Vérifie avant de pousser

```bash
python cowork_check.py           # valide le rapport du jour
```

Ce script vérifie la structure, les valeurs autorisées, les longueurs minimales et que chaque URL citée provient bien de la collecte. **Corrige jusqu'à ce qu'il passe au vert**, puis commit et push.
