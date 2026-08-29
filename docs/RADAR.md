# Radar produits — mode d'emploi pour l'agent

Porté de l'outil de Badr (`D:/MasterEcom`, repo `KindredM-Numbers`, skill `/radar`).
Objectif : chaque matin, **3 produits** repérés sur TrendTrack, chacun avec une
**analyse approfondie** que Badr peut lire sans être expert : combien ça peut
faire par jour, c'est dur ou pas, à quel stade est le marché, est-ce que les
gens connaissent déjà le produit.

Tout ce qui vient de la formation MASTER est sourcé `fichier:ligne`. Ce qui
n'en vient pas est étiqueté **calibration maison**. Aucun seuil ne définit un
« winning product » : `02-master-product-formulatm.md:212` — « Le "winning
product" n'existe pas. Il n'existe que : un produit logique + de bonnes
mathématiques + un bon marketer. »

---

## 1. Le budget TrendTrack — vérifier AVANT tout appel

```
check_credits
```

- Chaque page de 100 boutiques coûte ~100 crédits. Le scan du jour = **2 pages
  = ~200 crédits**, plus 0 à 3 contrôles `search_ads`.
- Si `totalRemaining` < 1 000 : **ne lance rien**, mets `radar_produits: []`
  et signale-le dans ton résumé. Badr décide de recharger.
- Jamais `find_winning_products` : testé le 25/08, il remonte des marques
  installées (JOVS, 1 116 ads) — aucun filtre de fraîcheur.

## 2. Les passes du jour (la passe G — « le filtre secret sans trafic »)

`05-ecom-data-2.md:56` est un chapitre entier : « 25:04 - Filtre secret sans
trafic ». `:219` : « on voit vraiment zéro visiteur mais on voit qu'il a 150 ad
active et du coup ça c'est vraiment banger, là on peut les catcher avant
qu'elles soient visibles sur les autres spy tools ». Le 0 est un **délai de
données** (`:143`) — c'est ce délai qui ouvre la fenêtre de copie.

Cette passe **ne filtre pas sur la date de création**, et c'est tout son
intérêt : elle fait sortir les vieux domaines dont la *diffusion* est neuve
(cas vérifié : getwildnest.com, domaine de 205 jours, diffusion de 5 semaines).

```
search_shops  max_monthly_visits=100  min_active_ads=100  sort_by=activeAds  limit=100  page=1
search_shops  max_monthly_visits=100  min_active_ads=100  sort_by=activeAds  limit=100  page=2
```

Le lundi seulement, si le solde le permet (> 3 000), ajoute la passe fraîcheur :
```
search_shops  creation_date_from=<J-120>  min_active_ads=100  max_products_count=40  sort_by=activeAds  limit=100
```

**Ne lis pas les réponses** : elles sont trop longues et sont rangées
automatiquement dans le dossier `tool-results` de la session. Le script les y
retrouve tout seul. Si une réponse revient en ligne (petite), enregistre son
JSON tel quel dans `data/radar/raw/AAAA-MM-JJ-N.json`.

Puis :
```
python -m agents.radar_produits extract AAAA-MM-JJ
```
Ça écrit `data/radar/AAAA-MM-JJ.json`, met à jour `data/radar/suivi.json`
et produit `data/radar/candidats_AAAA-MM-JJ.md` — **c'est ce fichier que tu lis**.

## 3. Les statuts (deux axes de MASTER RESEARCH, croisés)

| | courbe d'ads ×2+ | courbe plate |
|---|---|---|
| **trafic affiché 0** | 🔴 **BANGER** | 🟣 **SANS TRAFIC** — la fenêtre est ouverte, on attend le départ |
| **trafic visible** | 🟢 **EXPLOSE** (`04-ecom-data-1.md:291`, `:295`) | ⬛ STABLE (≥ 150 ads, `:187` « une boutique rentable ») / 🔵 A SURVEILLER (50-149, `:213`) |

- 🟠 EN BAISSE : courbe ≤ ×0,8 — anti-signal `04-ecom-data-1.md:285` « ça se met en rouge, c'est en train de baisser, j'aime un peu moins ».
- 🟡 SOUS LE FILTRE : < 50 ads — `04-ecom-data-1.md:271`, **la seule règle chiffrée de la formation**.
- Calibrations maison (à dire comme telles) : « ×2 en 4 semaines = explose », « ≤ 60 jours = récente », la colonne PRIO, les ALERTES.

## 4. Choisir les 3 produits

Dans `candidats_AAAA-MM-JJ.md`, dans cet ordre :
1. les **movers** (grosse montée de rang depuis le dernier scan) ;
2. les **BANGER** puis **EXPLOSE** ;
3. **variété** : pas deux produits de la même niche, pas deux fois le même opérateur (colonne réseau) ;
4. jamais un produit marqué INGERABLE, jamais un produit analysé dans les 7 derniers jours (le script les a déjà retirés) ;
5. préfère un prix vu ≥ 30 $ : l'AOV réel de Badr est de **65-70 €** (mémoire business) — un produit à 20 $ ne passe qu'en pack.

## 5. Le contrôle « déjà en France ? » (0 à 3 appels)

Pour chaque produit retenu, si le solde le permet :
```
search_ads  query="<UN seul mot, le produit>"  country="FR"  trend_signal="reach"
```
Règles (`FILTRES.md` §6, pièges vérifiés le 25/08) :
- **toujours** `trend_signal="reach"` — la valeur par défaut exige une croissance de reach et renvoie 0 sur des marchés pourtant occupés ;
- un mot, jamais une phrase ;
- **0 résultat ne s'écrit jamais LIBRE** : ça s'écrit `A VERIFIER`. LIBRE seulement si la requête tourne et ne remonte aucun annonceur sérieux ; PRIS si un concurrent y est avec des ads (dis qui) ; PARTIEL si un annonceur existe mais exécute mal.

## 6. L'analyse approfondie — le format de chaque produit

Chaque produit de `ecommerce.radar_produits` est un objet avec ces clés
(toutes en texte brut, français, termes expliqués) :

| Clé | Contenu |
|---|---|
| `produit`, `boutique`, `niche`, `prix` | repris du brief (prix tel quel, ex. « 38.99 USD ») |
| `statut` | `BANGER`, `EXPLOSE`, `SANS TRAFIC` ou `A SURVEILLER` |
| `signal` | ce que disent les chiffres, en clair : la courbe d'ads (expliquer : « nombre de publicités actives, semaine par semaine »), le ×N, l'âge, les semaines de diffusion, le trafic à 0 et ce que ça veut dire. 250-500 caractères. |
| `stade_marche` | où en est le marché : « fenêtre de copie encore ouverte » / « en train d'exploser, déjà visible » / « marché installé » / « déjà éduqué par X ». Cite les pays où ils diffusent. 150-350 caractères. |
| `notoriete` | est-ce que les gens connaissent déjà ce produit ? (pays des pubs, France ciblée ou non, marchés libres, concurrents FR trouvés) 120-300 caractères. |
| `ca_jour_estime` | fourchette **étiquetée estimation**, avec la méthode. Trafic affiché ×5 à ×10 (`03-marche-retour-d-experience-complet.md:178`, `13-afterlib.md:96`) × taux de conversion 2-3 % × prix. Si trafic = 0 : « non estimable — trafic pas encore indexé ; ordre de grandeur d'après le nombre d'ads : … » et reste prudent. Jamais un chiffre sec sans « estimation ». |
| `difficulte` | `facile`, `moyen` ou `difficile` |
| `difficulte_pourquoi` | prix vs AOV 65-70 €, réglementaire (cosmétique, ingérable, contrefaçon), créas nécessaires (VSL longue ou vidéo 30 s ?), concurrence FR, logistique (poids, liquide). 150-350 caractères. |
| `marche_fr` | `LIBRE`, `PRIS`, `PARTIEL` ou `A VERIFIER` (règles §5) |
| `marche_fr_detail` | ce que la requête a montré, ou « non vérifié — solde TrendTrack » |
| `criteres_ok` / `criteres_ko` | parmi les 9 critères (`master-research/09-criteres-produit.md:60-78`) : besoin fort · effet visuel · marge ×3-×4 · preuve sociale · simple à utiliser · légal/douane OK · introuvable en magasin · compréhension immédiate · upsell possible. Listes courtes, ce que tu peux juger d'après le brief. |
| `verdict` | `GO TEST`, `A SURVEILLER` ou `ECARTER` |
| `verdict_pourquoi` | la raison en 2-3 phrases simples. 150-350 caractères. |
| `budget_test` | rappel du protocole : « CBO 100-300 € par jour, décision à 48 h, soit 200-600 € pour savoir » (`PROTOCOLE-DECISION.md` §1, budget journalier tranché par Badr le 24/08). |
| `lien_boutique`, `lien_adlibrary` | repris du brief |

Non négociables à garder en tête (`02-master-product-formulatm.md`, « Les Vraies
Règles ») : TAM · intensité du problème · résolution réelle · economics · AOV ·
qualité · résilience. Un produit de décoration est un « nice to have », un
produit qui soulage une douleur est un « need to have » — le scaling n'est pas
le même.

## 7. Après avoir écrit le rapport

```
python -m agents.radar_produits mark AAAA-MM-JJ boutique1.com boutique2.com boutique3.com
git add data/radar/
```
Le suivi évite de reproposer les mêmes produits pendant 7 jours et garde les
rangs pour repérer les movers demain.
