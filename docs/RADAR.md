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

- Chaque page de 100 boutiques coûte ~100 crédits. Le scan du jour = **3 pages
  = ~300 crédits**, plus 0 à 3 contrôles `search_ads`.
- Si `totalRemaining` < 1 000 : **ne lance rien**, mets `radar_produits: []`
  et signale-le dans ton résumé. Badr décide de recharger.
- Jamais `find_winning_products` : testé le 25/08, il remonte des marques
  installées (JOVS, 1 116 ads) — aucun filtre de fraîcheur.

## 2. Les passes du jour

Quatre passes, complémentaires (~400 crédits). Le scan complet de Badr en
compte 13 (~1 400 crédits) ; on garde chaque jour celles qui trouvent des
choses différentes — et en premier celle qui trouve **les bangers qui explosent
maintenant** :

| Passe | Ce qu'elle trouve | Appel |
|---|---|---|
| **D — explosion 7 jours** (`04-ecom-data-1.md:287` « elle explose direct et elle a beaucoup d'ad active, là ça c'est vraiment lourd ») | les boutiques dont le nombre d'ads a au moins doublé cette semaine | `search_shops creation_date_from=<J-180> min_active_ads=100 max_products_count=40 ads_growth=[{"period":"last7d","comparison":"greater","value":100}] sort_by=activeAds limit=100 page=1` |
| **A1 — fraîcheur** (`03-marche-retour-d-experience-complet.md:180` « quelques jours qu'ils commencent à run […] ça produit Pépite ») | les boutiques récentes qui ont déjà beaucoup d'ads | `search_shops creation_date_from=<J-120> min_active_ads=100 max_products_count=40 sort_by=activeAds limit=100 page=1` |
| **B1 — toutes neuves** | les plus jeunes, dès 50 ads | `search_shops creation_date_from=<J-90> min_active_ads=50 max_products_count=40 sort_by=createdAt limit=100 page=1` |
| **G1 — filtre secret sans trafic** (ci-dessous) | les vieux domaines à diffusion neuve, invisibles ailleurs | `search_shops max_monthly_visits=100 min_active_ads=100 sort_by=activeAds limit=100 page=1` |

Sources à venir (Badr les branchera) : **BrandSearch** (« le plus complet »,
`04-ecom-data-1.md:305`, vivier bien plus grand que TrendTrack) et **Kalodata**
(TikTok Shop). Elles alimenteront le même `extract` : toute réponse au format
`{"data": [{"domain": …}]}` déposée dans `data/radar/raw/` est dépouillée.

⚠️ Sans A1/B1, la passe G seule (triée par nombre d'ads) remonte surtout des
annonceurs installés depuis 6 mois : le 29/08, 0 boutique fraîche sur 155.

### La passe G — « le filtre secret sans trafic »

`05-ecom-data-2.md:56` est un chapitre entier : « 25:04 - Filtre secret sans
trafic ». `:219` : « on voit vraiment zéro visiteur mais on voit qu'il a 150 ad
active et du coup ça c'est vraiment banger, là on peut les catcher avant
qu'elles soient visibles sur les autres spy tools ». Le 0 est un **délai de
données** (`:143`) — c'est ce délai qui ouvre la fenêtre de copie.

Cette passe **ne filtre pas sur la date de création**, et c'est tout son
intérêt : elle fait sortir les vieux domaines dont la *diffusion* est neuve
(cas vérifié : getwildnest.com, domaine de 205 jours, diffusion de 5 semaines).

Le lundi seulement, si le solde le permet (> 3 000), ajoute la page 2 de G et
la passe Triple Whale (`shopify_app_ids=[2982]`, `creation_date_from=<J-120>`,
`min_active_ads=50`) : le filtre de la leçon elle-même (`05-ecom-data-2.md:203-205`,
« généralement c'est qu'on commence à scaler »).

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

Le script a déjà appliqué **les règles de qualification de Badr** (sa feuille
WINNERS du 26/08/2026, 186 lignes : 56 qualifiés, 130 écartés). Un produit est
écarté avant analyse si : prix bas vs AOV 65-70 € (< 30 $) · il cible déjà la
France · devise/pays hors Big Five · pays de diffusion non indexés (une absence
de donnée n'est jamais une preuve de marché libre) · catalogue généraliste
(> 20 SKU : « une boutique de volume, pas un produit à copier ») · ingérable
(compléments, gummies, drops : hors France, arbitrage Badr du 25/08 — la
réglementation novel food / allégations santé bloque, `⚠️ Hors formation`).

Il écarte aussi les lignes « (catalogue non indexé) » ou sans prix (on
n'analyse pas un produit qu'on ne peut pas nommer) et **tout ce qui n'est pas
récent** : domaine > 60 jours ET diffusion > 8 semaines. C'est le profil pépite
de `03-marche-retour-d-experience-complet.md:180` — « ça fait juste quelques
jours qu'ils commencent à run » — et de `04-ecom-data-1.md:299` « moins de deux
mois ». Les prix sont convertis en euros avant le filtre (199 DKK ≠ 199 €).

### La règle qui tranche : personne ne l'a lancé sur TON marché

`03-marche-retour-d-experience-complet.md:180` : « Juste chercher en France,
il n'y a pas de personnes qui ont lancé. Et si ce n'est pas le cas, ça produit
Pépite. » La France est le marché principal de Badr (90 % du volume), mais il a
**4 boutiques : FR, ES, UK, DE** — et son rapport GroundGuard du 24/08 applique
la règle marché par marché : France prise par Solina → « meilleur combiné
DE + AT + CH ». La concurrence n'est pas un mal en soi : `02-master-product-
formulatm.md:270` demande même ≥ 5 concurrents à ≥ 100 ads pour prouver le TAM.
Ce qui compte, c'est **être le premier sur le marché où tu lances**. Donc :

1. Contrôle **FR** d'abord. `LIBRE` ou `PARTIEL` → pépite, on lance en France.
2. FR `PRIS` → contrôle **DE**, puis **ES**, puis **GB** (même règle : un mot
   dans la langue du pays, `trend_signal="reach"`, `country="DE"`…). Le
   premier marché `LIBRE`/`PARTIEL` devient le marché de lancement
   (`ou_lancer`), et le produit reste une pépite **pour ce marché**.
3. FR, DE, ES et GB tous `PRIS` → **écarté**. Passe au candidat suivant
   (jusqu'à ~10 contrôles `search_ads` par jour, ~30 crédits chacun).
4. **`LIBRE`** exige la preuve (la requête a tourné, aucun annonceur sur le
   produit) ; **`A VERIFIER`** si le contrôle n'a pas pu être fait — jamais
   `LIBRE` sur un 0 résultat.
5. Le jour où aucun candidat ne passe, **le rapport dit 0 produit** et liste ce
   qui a été vérifié et écarté (`radar_ecartes`). Une pépite est rare, et un
   faux GO coûte 200-600 € de test.

### Lire le contrôle avec la sophistication (leçon 33, « Sophistication simplifié »)

`0-to-1-master-one/33-sophistication-simplifie-base-a-connaitre.md` : « la
sophistication c'est le nombre de concurrents que vous avez sur un certain
produit-marché » (`:153`). « S'il y a genre 3 concurrents qui viennent juste de
commencer, c'est totalement OK » (`:152`) ; « des dizaines et même 15 qui
utilisent littéralement le même message marketing, en tant que débutant, c'est
pas ce qu'on conseille » (`:166`). **Cible du débutant : stade 2 à 3** (`:47`).

| Ce que montre `search_ads` sur le mot-clé, dans le pays | Stade | État à écrire |
|---|---|---|
| aucun annonceur sur le produit | 1 — tu es le premier | `LIBRE` |
| 1 à 4 annonceurs **récents** (< 6 mois) ou qui exécutent mal (< ~10 pubs, copie sale — cas Solina) | 2 — la concurrence arrive | `PARTIEL` → **OK pour lancer**, on peut copier leurs messages qui marchent |
| ≥ 5 annonceurs, ou un acteur qui **domine** le mot-clé (> 100 pubs actives, ou plusieurs millions de personnes touchées) | 3-4 — tout le monde dit la même chose | `PRIS` → il faudrait un nouveau mécanisme : pas un test de 48 h |
| 15+ annonceurs avec le même message | 5 — saturé | `PRIS` (vendre une identité, réservé aux expérimentés) |

Écris le stade dans `stade_sophistication` (1 à 5, pour le marché de
lancement) avec la preuve : combien d'annonceurs, depuis quand, combien de pubs.

### L'awareness : comment vendre le produit sur le marché de lancement

Même leçon, `:150-158` (exemple du shilajit) : « la façon dont on vendait le
shilajit au début aux États-Unis, c'était la même façon dont il fallait le
vendre en France. Beaucoup ont fait l'erreur de prendre le marketing du
présent aux États-Unis, où les clients étaient déjà aware du produit […] ils ne
parlaient que d'offres, que de prix, et n'expliquaient pas l'histoire ». Donc :

- **Le marché de lancement ne connaît pas encore le produit** (unaware /
  problem aware) → copier les **premières** pubs du marché d'origine :
  raconter le problème, expliquer ce que c'est et comment ça marche, preuve.
  Audience large, pas de ciblage fin. Champ `awareness` = « inconnu ici ».
- **Le marché de lancement connaît déjà le produit** (solution / product
  aware — les pubs concurrentes le montrent directement, l'offre et le prix
  dominent) → il faut un **nouvel angle** ou un **mécanisme unique**
  (`master-acquisition/02`, lexique : « recréer un océan bleu même sur un
  marché saturé »), ou une différenciation prouvée (stade 4). Champ
  `awareness` = « déjà connu ici ».
- Dans `angle_recommande` : l'angle, l'avatar et le stade de conscience à
  attaquer, en une ou deux phrases concrètes (ex. « problème → mécanisme
  ultrasons expliqué → preuve, audience large 30-60 ans propriétaires »).

### La preuve de TAM (`02-master-product-formulatm.md:270`)

« Grand minimum 5 concurrents qui ont minimum 100 ads actifs » et « 50 à 100k
visiteurs mensuels chez vos concurrents » — **mesuré sur le marché d'origine /
mondial**, pas sur le marché de lancement (où l'on veut justement peu de
monde). Compte, dans les résultats `search_ads` déjà obtenus (FR, DE, ES, GB,
et au besoin US), les annonceurs dont `liveAdsCount ≥ 100` ; écris-le dans
`tam` : « TAM prouvé : 7 annonceurs à 100+ pubs (US/GB/DE), catégorie maison »
ou « TAM incertain : 2 annonceurs à 100+ pubs seulement ». Un TAM faible
n'écarte pas une pépite de test, mais limite le scaling (`:285` « une micro
niche qui limite votre spend »).

Dans l'analyse, remplis `marches` : `{"FR": "PRIS", "DE": "LIBRE", "ES": "A VERIFIER", "GB": "A VERIFIER"}`
et dis dans `marche_fr_detail` / `ou_lancer` qui occupe quoi (nom, pubs
actives, ancienneté). ⚠️ Allemagne : ~90 % des ventes via PayPal
(`03-…:182`), les Allemands aiment l'écologique et la santé (`03-…:22:00`).

### Lire le vrai produit avant de juger

Ouvre `https://<boutique>/products.json` (WebFetch, si le réseau le permet) :
le titre TrendTrack ne dit pas tout. « TrueForm Fascial Release » est un
complément (page « Supplement Facts ») ; « Cairn » d'aureasole.com est de
l'huile de graines de courge en gélules ; « Cordless Vacuum Sealer » était un
kit de sacs de compression pour valise. Un ingérable découvert à cette étape
est écarté, même s'il a passé le filtre automatique.

Dans `candidats_AAAA-MM-JJ.md` (déjà trié dans cet ordre) :
1. les **movers** (grosse montée de rang depuis le dernier scan) ;
2. les boutiques **FRAÎCHES** (domaine ≤ 60 j ou diffusion ≤ 10 semaines) — c'est la fenêtre de copie, `04-ecom-data-1.md:299` « moins de deux mois et qui a beaucoup d'ad active » ;
3. les **BANGER** puis **EXPLOSE** ;
3. **variété** : pas deux produits de la même niche, pas deux fois le même opérateur (colonne réseau) ;
4. jamais un produit analysé dans les 7 derniers jours (déjà retiré) ;
5. à signal égal, préfère le **mono-produit** (≤ 5 SKU) et le **consommable / réachat** (résilient).

### Lire une courbe comme Badr la lit (exemples de ses rapports)

- « 62 → 264 → 549 → 616 : la courbe **plafonne**, la phase d'explosion est finie » — un plateau après explosion n'est plus une fenêtre, c'est un opérateur installé.
- « 3 604 → 3 163 ads : volume très élevé mais en léger recul, pas une pépite fraîche ».
- « 787 produits au catalogue : magasin généraliste, à écarter sauf si un SKU précis se détache ».
- « Callie France diffuse le même angle depuis 468 jours avec 411 ads : ce n'est plus "être le premier", c'est affronter un acteur rentable sur son terrain » — une concurrence **installée** n'est pas une concurrence **saine** (MASTER RESEARCH · 2 exige les deux : TAM énorme ET concurrence saine).
- « 0 visiteur SimilarWeb + des centaines d'ads = exactement le profil à choper avant les autres ».
- « Le set de 2 résout d'emblée le problème d'AOV » — quand le prix unitaire est bas, raisonne pack/bundle.

### Où lancer (`ou_lancer`)

Badr a **4 boutiques : FR (~90 % du volume), ES, UK, DE** ; le pays n'est pas un obstacle (boutique créée à la demande), les COGS DE/ES/GB sont connus. Règle qu'il applique :
- marché FR `LIBRE` ou `PARTIEL` → **FR en premier** ;
- FR `PRIS` → **DE en priorité** (plus gros marché d'Europe, boutique et COGS déjà en place), puis AT/CH avec les mêmes créas allemandes, puis ES ; ⚠️ Allemagne : ~90 % des ventes passent par PayPal (`03-marche-retour-d-experience-complet.md:182`) ;
- utilise `marches_libres` du brief (pays que la boutique ne cible pas encore) pour proposer l'ordre.

## 4bis. L'enquête : la vraie fiche produit + les vraies douleurs

Leçon `master-acquisition/08-analyse-marketing.md` : avant d'écrire une pub,
scraper les avis et les forums pour trouver les vrais angles, les objections,
les douleurs. Ton bac à sable n'a pas de réseau : GitHub Actions le fait pour
toi.

1. Dès que tu as tes 3 à 6 candidats (après le tri, avant les contrôles
   France), écris `data/radar/enquete_request_AAAA-MM-JJ.json` :
   ```json
   [{"boutique": "pestprohome.com", "produit": "PestPro — répulsif à ultrasons",
     "mots_cles_fr": ["cafards appartement", "souris dans les murs"],
     "mots_cles_en": ["cockroaches apartment can't sleep", "ultrasonic pest repeller does it work"]}]
   ```
   Les mots-clés sont des **situations vécues** (« cafards appartement »,
   « souris dans les murs la nuit »), pas des noms de produit : on cherche la
   douleur, pas la fiche.
2. `git add data/radar/ && git commit -m "enquête du AAAA-MM-JJ" && git push`
   — le workflow `radar_enquete.yml` démarre sur ce push.
3. Attends et tire : `for i in $(seq 1 12); do sleep 30; git pull -q; [ -f data/radar/enquete_AAAA-MM-JJ.md ] && break; done`
   (en général 2 à 4 minutes). Si le fichier n'arrive pas après 6 minutes,
   continue sans, en le disant dans le résumé, et compense par WebSearch
   (forums, avis Amazon/Trustpilot, « site:reddit.com … »).
4. Lis `data/radar/enquete_AAAA-MM-JJ.md` : pour chaque candidat, la fiche
   Shopify réelle (titre, prix, description — c'est là qu'on découvre qu'un
   « Fascial Release » est un complément) puis les posts Reddit classés par
   intensité (🔴 forte = les gens paient pour que ça s'arrête ; ⚪ faible =
   simple curiosité). Ne retiens que les **douleurs fortes**, avec citation
   et lien.

Ce que ça alimente dans chaque fiche pépite :

- `angle_concurrent` : l'angle que le ou les concurrents utilisent, **cité
  depuis leurs vraies pubs** (les copies sont dans les réponses `search_ads` :
  `python -m agents.radar_produits pubs AAAA-MM-JJ <mot>` les affiche) — qui,
  combien de pubs, le hook, la promesse, l'offre.
- `pain_points` : 3 à 5 douleurs **fortes**, chacune avec la citation exacte et
  l'URL du post ou de l'avis. Une douleur = quelque chose qui empêche de
  dormir, fait honte, coûte cher, dure depuis des mois — pas « c'est agaçant ».
- `angles_non_exploites` : 2 à 3 angles que **personne** ne pousse dans les
  pubs vues, chacun adossé à une douleur forte de la liste (« le propriétaire
  ne fait rien → reprends le contrôle sans attendre »). C'est là que se joue
  la différenciation (leçon 33, stade 2-3).

## 5. Le contrôle « déjà en France ? » — Meta Ad Library d'abord (gratuit), TrendTrack ensuite

### 5a. Meta Ad Library (connecteur META) — 0 crédit, autant de contrôles que nécessaire

Charge l'outil : ToolSearch `"select:mcp__META__ads_library_search"`. Pour chaque
produit retenu et chaque marché (FR d'abord, puis DE, ES, GB si FR est PRIS) :
```
ads_library_search  search_terms="<2-3 mots qui décrivent LE PRODUIT, dans la langue du pays>"
                    countries=["FR"]  ad_active_status="ACTIVE"  limit=50
                    client_conversation_id="<20 caractères, le même pour toute la session>"
                    advertiser_request="vérifier si <produit> est déjà vendu en pubs en <pays>"
```
- **2-3 mots précis**, pas un seul : « ultrasons » seul en FR renvoie 2 400 pubs
  (lipocavitation, colliers anti-aboiement…) ; « répulsif ultrasons » renvoie le
  vrai marché. En allemand/espagnol/anglais, traduis (« Ultraschall Schädlinge »,
  « repelente ultrasonidos », « ultrasonic pest repeller »).
- Enregistre la réponse **telle quelle** dans `data/radar/raw/meta_<PAYS>_<mots-en-minuscules-sans-accents-avec-tirets>.json`
  (« répulsif ultrasons » → `meta_FR_repulsif-ultrasons.json`)
  puis : `python -m agents.radar_produits marche FR "répulsif ultrasons"` → il agrège
  par annonceur (nb de pubs, ancienneté de la première pub, exemple de titre) et
  tranche : **LIBRE** = 0 pub · **PARTIEL** = 1-4 annonceurs sans dominant (stade 2,
  OK pour lancer) · **PRIS** = ≥ 5 annonceurs ou un acteur à ≥ 20 pubs dans
  l'échantillon (stade 3+). Recopie le verdict et sa raison dans `marches` et
  cite les annonceurs dans `angle_concurrent`.
- Si un acteur domine, tu peux compter ses pubs exactes avec `page_ids=[<page_id>]`
  (utile pour le TAM : ≥ 100 pubs = gros annonceur).
- L'outil ne rend ni le texte complet des pubs ni la portée : pour **lire** les
  pubs du concurrent (angle, promesse), utilise `ad_snapshot_url` (WebFetch) ou
  TrendTrack `search_ads` ci-dessous.

### 5b. TrendTrack `search_ads` — seulement pour les copies de pubs (30 crédits)

Réservé aux 1-3 pépites finales, pour citer l'angle exact du concurrent :
```
search_ads  query="<UN seul mot, le produit>"  country="FR"  trend_signal="reach"
```
Règles (`FILTRES.md` §6, pièges vérifiés le 25/08) :
- **toujours** `trend_signal="reach"` — la valeur par défaut exige une croissance de reach et renvoie 0 sur des marchés pourtant occupés ;
- un mot, jamais une phrase ;
- **0 résultat ne s'écrit jamais LIBRE** : ça s'écrit `A VERIFIER`. LIBRE seulement si la requête tourne et ne remonte aucun annonceur sérieux ; PRIS si un concurrent y est avec des ads (dis qui) ; PARTIEL si un annonceur existe mais exécute mal.
- Si le connecteur META n'est pas disponible dans la session, `search_ads` redevient le contrôle pays (limite-toi à ~10 contrôles).

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
| `marches` | état par marché de Badr : `{"FR": …, "DE": …, "ES": …, "GB": …}` avec les mêmes valeurs ; si FR est `PRIS`, au moins un autre doit être `LIBRE` ou `PARTIEL` (sinon le produit est écarté) |
| `stade_sophistication` | entier 1 à 5 pour le marché de lancement (tableau §4), avec la preuve dans `marche_fr_detail` |
| `awareness` | « inconnu ici » ou « déjà connu ici » : le marché de lancement connaît-il le produit ? (§4) |
| `angle_recommande` | l'angle, l'avatar et le stade de conscience à attaquer, concret. 120-300 caractères. |
| `tam` | preuve de TAM chiffrée (§4) : annonceurs à 100+ pubs, catégorie. 80-200 caractères. |
| `angle_concurrent` | l'angle des concurrents, cité depuis leurs pubs réelles (§4bis). 150-400 caractères. |
| `pain_points` | 3 à 5 objets `{"douleur": "…", "intensite": "forte"|"moyenne", "preuve": "citation exacte", "source_url": "https://…"}` — douleurs fortes d'abord |
| `angles_non_exploites` | 2 à 3 objets `{"angle": "…", "douleur_ciblee": "…", "pourquoi_personne": "…"}` — chaque angle adossé à une douleur de `pain_points` |
| `chiffres` | **ne pas remplir** : réinjecté automatiquement à la publication depuis `data/radar/AAAA-MM-JJ.json` (ads actives, courbe, ×4 semaines, âge, semaines de diffusion, visites, pays des pubs, SKU, prix) — le modèle ne retape jamais un chiffre |
| `marche_fr_detail` | ce que la requête a montré (qui, combien d'ads, depuis quand), ou « non vérifié — solde TrendTrack » |
| `ou_lancer` | le ou les marchés recommandés et pourquoi (règle §4 « Où lancer ») : « FR d'abord car libre », ou « pas la France (pris par X) → DE puis AT/CH ». 100-250 caractères. |
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

### Les écartés (`ecommerce.radar_ecartes`)

Liste courte de ce qui a été vérifié et refusé aujourd'hui, pour que Badr voie
le travail et ne le refasse pas : `[{"produit": "…", "boutique": "…", "raison":
"marché FR pris — Nuizoff, 77 pubs actives depuis 53 jours"}]`. 3 à 8 lignes,
une phrase par raison.

## 6bis. La base de winners (leçon MASTER RESEARCH · 10 « fichier d'organisation »)

Une seule liste, en deux endroits qui disent la même chose :

- **la vérité** : `data/radar/base_winners.json` **sur main** (tes branches n'y
  sont jamais fusionnées : c'est le workflow de publication qui l'alimente avec
  les pépites du rapport, et qui reporte la base rafraîchie si tu l'as commitée
  sur ta branche) ;
- **la vue vivante de Badr** : la base Notion « 🏆 BASE WINNERS — CORTEX »
  (`https://app.notion.com/p/6b156b50a295410081c94286cf34321c`, data source
  `collection://76f47e8d-dae2-428b-843d-2f6f22305e09`), une ligne par boutique.
  C'est LÀ que Badr met son verdict. Les colonnes « MON VERDICT » et « MES NOTES »
  lui appartiennent : tu ne les écris jamais. Un produit qu'il a marqué « écarté »
  ou « testé - mort » n'est plus proposé (le script `candidats` l'exclut et
  `est_testable` le refuse).

### Tous les jours : synchroniser Notion (connecteur Notion, ~6 appels)

Charge les outils : ToolSearch
`"select:mcp__Notion__notion-query-data-sources,mcp__Notion__notion-create-pages,mcp__Notion__notion-update-page"`.

1. **Avant le radar — relire les verdicts de Badr** : `notion-query-data-sources`
   en mode SQL sur la data source ci-dessus :
   `SELECT url, "Boutique", "🎯 MON VERDICT", "📝 MES NOTES" FROM "collection://76f47e8d-dae2-428b-843d-2f6f22305e09"`
   (les colonnes et les options portent des emojis — « 🚫 écarté », « 🔥 BANGER » — ;
   le script les retire tout seul).
   Écris la réponse telle quelle (la liste de lignes) dans
   `data/radar/notion_verdicts_AAAA-MM-JJ.json`, puis
   `python -m agents.base_winners import-verdicts-notion data/radar/notion_verdicts_AAAA-MM-JJ.json`
   (relit les verdicts et mémorise l'id de page de chaque boutique).
2. **Après le rapport (étape 5, avant le push)** :
   `python -m agents.base_winners add AAAA-MM-JJ` puis
   `python -m agents.base_winners notion-export AAAA-MM-JJ` →
   `data/radar/notion_push_AAAA-MM-JJ.json`, une entrée par page à pousser avec
   `action`, `notion_page_id`, `icon` (🔥 banger, 🚀 explose, 💀 mort…),
   `properties` (prêtes pour Notion : noms de colonnes avec emoji, options avec
   emoji, dates déjà éclatées en `date:…:start`) et `content` (la fiche en Markdown).
   - `action = create` → `notion-create-pages` avec
     `parent = {"type": "data_source_id", "data_source_id": "76f47e8d-dae2-428b-843d-2f6f22305e09"}`,
     `icon`, `properties` et `content` tels quels ;
   - `action = update` → `notion-update-page` `command = update_properties`
     avec `page_id`, `icon` et `properties` ; puis `command = replace_content` avec
     `new_str = content` (la fiche est courte, on la remplace).
   Ne touche jamais MON VERDICT / MES NOTES (ils ne sont pas dans `properties`).
3. `git add data/radar/` avec le reste : la publication reporte la base sur main.

### Le lundi : la passe hebdomadaire

1. **Scan élargi** en plus des 4 passes : G page 2, la passe Triple Whale
   (`shopify_app_ids=[2982]`, `creation_date_from=<J-120>`, `min_active_ads=50`)
   et la croissance 30 jours (`creation_date_from=<J-180>`, `min_active_ads=100`,
   `ads_growth=[{"period":"last30d","comparison":"greater","value":100}]`,
   `sort_by=growth30d`). Coût réel = nombre de résultats renvoyés (une page
   pleine de 100 = ~100 crédits ; un filtre serré qui rend 30 boutiques = 30).
2. **Rafraîchir la base** : pour chaque boutique de `base_winners.json`,
   `search_shops query=<domaine> match_mode=exact limit=1` (~2 crédits chacune,
   la réponse est petite et revient en ligne : enregistre-la telle quelle dans
   `data/radar/raw/AAAA-MM-JJ-<domaine>.json`). Puis
   `python -m agents.radar_produits extract AAAA-MM-JJ` et
   `python -m agents.base_winners refresh AAAA-MM-JJ` : statuts mis à jour
   (BANGER → STABLE → EN BAISSE → MORT), les morts sortent de WINNERS.
3. **Top 10 de la semaine** : parmi les candidats de la semaine (le suivi
   garde les rangs), choisis jusqu'à 10 produits qui passent tous les filtres
   et écris-les dans `ecommerce.radar_produits` du rapport du lundi (même
   format ; l'enquête et les contrôles France pour chacun — budget crédits
   oblige, priorise les 3 meilleurs pour l'enquête complète).
4. La synchro Notion quotidienne (ci-dessus) pousse alors toutes les lignes
   rafraîchies : statuts à jour, les morts passent `Testable` à non et restent
   visibles dans Notion (Badr filtre la vue comme il veut).

## 7. Après avoir écrit le rapport

```
python -m agents.radar_produits mark AAAA-MM-JJ boutique1.com boutique2.com boutique3.com
git add data/radar/
```
Le suivi évite de reproposer les mêmes produits pendant 7 jours et garde les
rangs pour repérer les movers demain.
