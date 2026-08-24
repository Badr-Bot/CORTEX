# SAV NIVA — Mémoire de contexte (automatisation Gmail/Shopify)

Ce fichier sert à garder le contexte entre les exécutions de la routine SAV NIVA
(contact@mynivashop.com / myniva@outlook.com), en complément des règles du prompt
système. À relire en début de session si le contexte a été perdu.

## Règle corrigée par Badr le 24/08/2026 — IMPORTANT

**Les Options 1 / 2 (garder l'article + cadeau/-20%, ou garder l'article + remboursement
20%) ne s'appliquent QUE si le client a déjà REÇU son colis.**

Pour toute commande en retard / non reçue, AVANT de répondre :
1. Vérifier le tracking réel (Shopify `graphql_query` sur `order.fulfillments` :
   champs `displayStatus`, `deliveredAt`, `events`) — pas seulement le statut
   Shopify "FULFILLED" qui ne prouve pas la livraison.
2. **Si marqué livré** (`deliveredAt` rempli ou event "DELIVERED") mais le client
   dit ne rien avoir reçu → c'est un litige transporteur : **c'est le problème
   du client, il doit voir directement avec le transporteur local** (ex : Colis
   Privé). PAS de compensation (ni Option 1, ni Option 2, ni remboursement) de
   la part de NIVA dans ce cas — rediriger le client vers le transporteur.
   (Règle précisée par Badr le 24/08/2026, suite au cas Jullien #5395 ci-dessous.)
3. **Si PAS marqué livré** :
   - Statut normal (en transit, < 30j) → informer le client du statut réel +
     lien de suivi, ne rien promettre de plus, rester en brouillon si J+15.
   - **> 30 jours et toujours pas livré** → ne PAS proposer Option 1/2. Informer
     le client qu'il sera remboursé intégralement (pas de garder-l'article ici,
     il n'a rien reçu), et flag Badr pour exécuter le remboursement réel dans
     Shopify (aucun outil de remboursement automatique n'est utilisé par l'IA).
   - Si un événement de tracking indique un problème d'adresse ("adresse
     introuvable", tentative de livraison échouée) → NE PAS proposer de
     compensation, dire que c'est "en cours", et demander au client de
     reconfirmer son adresse complète (le colis n'est pas perdu, juste bloqué).

## Dossiers en cours (au 24/08/2026)

### Commande #4610 — Marie-Line Depoortere (marie-line.depoortere@wanadoo.fr)
- Commandée 15/07, expédiée 16/07 (YunExpress YT2619700706149543), **jamais
  marquée livrée** (deliveredAt null, aucun event de tracking) — 39 jours.
- Mail correctif envoyé le 24/08 : remboursement intégral annoncé au client,
  aucune option proposée.
- **ACTION BADR REQUISE : exécuter le remboursement intégral dans Shopify
  admin (commande #4610).**
- Décision Badr : le remboursement client n'est pas à la charge de NIVA mais
  du fournisseur (réclamation transporteur/fournisseur en cours, voir
  section "Colis non livrés — réclamation fournisseur" ci-dessous).

### Commande #5496 — Maxime Pabois (pabois.maxime@orange.fr)
- Commandée 02/08, expédiée 03/08 (YunExpress YT2621500706682972).
- Tracking : 2 tentatives de livraison échouées ("Address could not be found" /
  "Incorrect address"), transporteur mentionné dans les events = GOFO. Colis
  bloqué, pas perdu.
- Adresse en fichier incomplète : "Route De St Reverend, Le Fenouiller 85800"
  — **pas de numéro de rue**, probable cause de l'échec de livraison.
- Mail correctif envoyé le 24/08 : statut "en cours" expliqué, demande de
  reconfirmation d'adresse complète, aucune compensation proposée (colis pas
  reçu).
- Mail complémentaire envoyé le 24/08 : demande aussi son numéro de téléphone
  (absent de la commande, nécessaire pour que le livreur le recontacte).
- **À SUIVRE : si le client renvoie adresse complète + téléphone, relancer le
  transporteur / mettre à jour l'adresse de livraison.**

### Commande #3611 — Romain Babu (romainbabu83@gmail.com)
- Échange 4XL→5XL. Le client a renvoyé son colis à l'ANCIENNE adresse de
  retour (SARAJ - NIVA, 6 rue du Bel Ébat, 78170 La Celle-Saint-Cloud) au lieu
  de la nouvelle (NIVA - El Boussadani, 4 rue Erik Satie, 94400
  Vitry-sur-Seine) — erreur provenant de mon tout premier mail du 06/08 (avant
  mise à jour de l'adresse de retour).
- Signalé à Badr par DM Slack le 23/08.
- Client informé qu'on se renseigne en interne.
- **ACTION BADR REQUISE : vérifier si le colis est récupérable à l'ancienne
  adresse (La Celle-Saint-Cloud), puis relancer le client.**

## ⚠️ Corrections majeures suite au retour du fournisseur (24/08/2026, plus tard)

1. **L'agent fournisseur expédie ~2h après la commande, indépendamment du
   statut Shopify.** Une commande peut rester `UNFULFILLED` dans Shopify
   alors qu'elle est déjà physiquement partie chez le fournisseur. Donc pour
   une demande d'annulation/rétractation : NE PAS se fier uniquement au
   fulfillmentStatus Shopify pour dire "pas encore expédié, on annule" — au
   -delà de 2h après la commande, considérer que c'est déjà expédié et
   irréversible (cas Arnoult #6410 : Shopify montrait UNFULFILLED, mais
   Badr confirme que l'agent avait déjà expédié).
2. **Les events de tracking Shopify (`order.fulfillments.events`) ne sont
   PAS fiables pour ce fournisseur — un fulfillment sans event ni
   `deliveredAt` n'est PAS une preuve fiable de non-livraison.** Le
   fournisseur a confirmé que 3 des 4 commandes signalées "jamais livrées"
   (#4863, #5588, #5749) avaient en fait bien été livrées (7, 20 et 15 août
   respectivement), alors que Shopify ne montrait aucune preuve. Seule #4610
   était un vrai cas (retournée pour erreur ville/code postal, puis
   réexpédiée). **Avant toute promesse de remboursement pour non-livraison,
   il faut maintenant vérifier auprès du fournisseur/transporteur, pas
   seulement via GraphQL Shopify.**
3. Corrections envoyées aux clients suite à ces infos :
   - **#4610 Depoortere** : le colis était en fait retourné (erreur
     ville/CP), puis réexpédié le 24/08 avec un nouveau tracking
     (YT2623600710498510). Le remboursement annoncé la veille a été annulé,
     client informée qu'elle va bien recevoir sa commande.
   - **#4863 Behier** : livrée le 7 août confirmé par le transporteur. Le
     remboursement promis a dû être annulé/corrigé — client redirigée vers
     le transporteur en cas de contestation (feux de Gironde compliquent la
     situation mais ne changent pas la politique : livré confirmé = litige
     transporteur, pas de compensation NIVA).
   - **#5588 Fouet et #5749 Saurine** : livrées (20/08 et 15/08). Aucun
     message erroné n'avait été envoyé à ces deux clients dans ce dossier,
     rien à corriger.
   - **#6410 Arnoult** : déjà expédié par l'agent malgré le statut Shopify.
     Client informé que l'annulation n'est plus possible, droit de
     rétractation maintenu via retour + remboursement après réception.

## Nettoyage massif Escalade/Réexpédition/Brouillon (24/08/2026, en cours)

Badr a validé "option 1" pour la simplification des dossiers : on arrête
d'utiliser les sous-libellés (Escalade/Brouillon/Remboursement/Réexpédition/
Withdrawal/Ignoré) au quotidien — tout ce qui est traité va dans Label_3
"Traité" — mais on NE SUPPRIME PAS les libellés existants (l'automatisation
stockée ailleurs s'appuie encore dessus).

Méthode de balayage utilisée (le filtre `label:` de search_threads est peu
fiable) : `search_threads` avec `newer_than:60d -in:sent -in:chat is:unread
-in:inbox`, paginé, pour retrouver les fils avec un message client non
répondu même si Gmail ne les a pas remis en boîte de réception.

Cas traités dans cette passe (liste non exhaustive, voir l'historique Gmail
pour le détail) :
- Cordier/Coquard (delivered-disputed) : offre retirée, conforme à la
  nouvelle règle "livré confirmé = problème transporteur, pas nous".
- Schneider/eurocomfrance #2664 : déjà résolu (remboursement en cours,
  client patiente), juste archivé.
- Gouillart #5127, Paradis #3690, Bergeret, Grondin #5471, Lemaire #4685,
  Biver/Delamarne, Dissenykim/Sangenís #1152 : confirmations d'articles
  gratuits déjà négociés, envoyées et closes.
- Steenkiste : caleçon offert EST disponible à la vente sur le site
  (`nivafit-calecon-ultra-extensible`, 11,99€) — lien envoyé.
- Beaucoup de bruit (Facebook Ads, Google Ads, judge.me, alertes Google
  Workspace) archivé directement en Traité.

**Reste à traiter** : le solde du balayage 60 jours (~150+ fils sur cette
seule page), les fils Label_7 antérieurs à 60 jours (196 fils au total dans
ce libellé), et le reste de Label_4/6/9. Travail en cours, repris par
itérations.

## Colis non livrés — réclamation fournisseur (24/08/2026)

Vérification élargie (`graphql_query` sur `order.fulfillments.events`) sur les
commandes en litige de retard connues : 4 commandes ont un `displayStatus`
FULFILLED mais **aucun event de tracking et `deliveredAt: null`**, malgré des
délais très dépassés — aucune preuve de dépôt/tentative/livraison remontée
par le transporteur. Message rédigé pour le fournisseur (à envoyer par Badr,
contact fournisseur non détenu par l'IA) demandant réexpédition ou
remboursement à NIVA :

| Commande | Client | Expédié le | Jours écoulés (au 24/08) | Tracking |
|---|---|---|---|---|
| #4610 | Marie-Line Depoortere | 16/07 | 39 j | YT2619700706149543 |
| #4863 | Sabine Behier | 20/07 | 36 j | YT2620100709380111 |
| #5588 | Michel Fouet | 05/08 | 20 j | YT2621700702859307 |
| #5749 | Xavier Saurine | 07/08 | 18 j | YT2621900703349858 |

Remarque #5749 (Saurine) : on lui avait dit le 13/08 que son colis était
"marqué comme livré par le transporteur", mais la vérification GraphQL du
24/08 ne montre AUCUN event ni `deliveredAt` — l'info donnée précédemment était
donc probablement erronée ou basée sur une autre source (ParcelPanel ?) non
cohérente avec l'API Shopify. À clarifier avec le fournisseur.

Cas différent, PAS à inclure dans la réclamation : **#5395 (David Jullien)**
— celui-ci est bien `displayStatus: DELIVERED`, `deliveredAt: 2026-08-12`
confirmé par le transporteur (Colis Privé) ; le client conteste ne rien avoir
reçu, a fourni une attestation sur l'honneur, réclamation Colis Privé fermée
sans solution = litige transporteur classique. Règle Badr (24/08) : dans ce
cas, le client doit voir directement avec le transporteur local, pas de
compensation NIVA.

Décision Badr (24/08) : revenir vers lui pour retirer l'offre et le
rediriger vers Colis Privé. Fait le 24/08 — mail envoyé expliquant que le
problème relève du transporteur local, excuses pour la confusion causée par
le précédent message, aucune compensation. Dossier considéré clos côté NIVA
sauf nouvelle relance du client.

**#6072 (Damien Robin)** — FULFILLED, pas d'event, mais seulement 10 jours
(expédié 15/08) : pas encore critique, à resurveiller si toujours rien sous
peu.

## Adresses en attente — vérifié le 24/08/2026

Recherche faite sur tous les fils "adresse incomplète / mauvaise adresse /
confirmation d'adresse" des 20 derniers jours : **aucun fil n'est actuellement
en attente d'une réponse du client.** Tous les cas récents (Langlet #6323,
De Muynck #6213, Oberson, Richer, Hublet #5915, Lenain #5971, Bertieaux
Beugnies #5967, Dagenais #5848, Mertens #5425) ont été résolus : le client a
donné son adresse, on l'a confirmée / la commande est partie.

Seul cas d'adresse encore ouvert : **Pabois #5496** (voir ci-dessus, on
attend sa confirmation d'adresse complète).

## Erreurs identifiées à ne pas reproduire

1. **`update_draft` sans `replyToMessageId`** : le champ n'existe pas dans le
   schéma `update_draft` (uniquement dans `create_draft`). Modifier le corps
   d'un brouillon existant via `update_draft` peut détacher le brouillon du
   fil d'origine (nouveau `threadId` = messageId du brouillon). Pour corriger
   un brouillon existant tout en gardant le fil, préférer `create_draft` avec
   `replyToMessageId` pointant vers le dernier message du client, puis
   ignorer/laisser l'ancien brouillon orphelin (pas d'outil de suppression de
   brouillon disponible actuellement).
2. **Règle J+15 (Règle Absolue N°0quater)** : les cas de retard critique
   (commande passée depuis ≥15 jours, non livrée) doivent TOUJOURS rester en
   brouillon, jamais être auto-envoyés — y compris quand on corrige un
   brouillon existant. Le 23/08/2026, deux mails J+15 (Depoortere #4610 et
   Pabois #5496) ont été envoyés par erreur au lieu de rester en brouillon
   pour validation humaine — corrigé le 24/08 avec l'aide de Badr.

## Nettoyage massif — session du 24/08/2026 (suite)

Boîte de réception (INBOX) entièrement vidée à nouveau après le pic de
messages en fin de matinée : tous les fils traités et déplacés vers
Label_3 (Traité), plus aucun `in:inbox` non lu ni lu restant à ce
checkpoint.

Cas traités dans cette passe :
- **Fouet #5588** : a confirmé réception + demandé le polo Rouge Merlot XL
  promis en dédommagement → confirmé, envoi programmé.
- **Grondin #5471** : a précisé couleur/taille (Rouge Merlot 3XL) pour
  l'option 3 → confirmé, envoi + remboursement 30% programmés.
- **Cordier** : a réitéré son mécontentement + menace d'avis négatif après
  la rétractation de l'offre (colis marqué livré) → réponse ferme mais
  empathique, aucune compensation, dossier clos conformément à la décision
  de Badr du 24/08.
- **Rolland #6367** : a demandé à modifier/annuler sa commande (mix
  couleurs erroné) → trop tard, déjà expédiée ; retour gratuit + échange
  proposé à réception.
- **Sannwald #4456** (ex-Escalade) : a confirmé vouloir retourner l'article
  taille incorrecte → adresse de retour + remboursement à réception
  envoyés.
- **claude_bragoni@yahoo.fr / commande #5945** : 5 messages en double sur
  4 fils différents en ~40 min, dont un contenant un lien de "notification
  de livraison" suspect (`Notice1185n.m186886414.pro`, PAS un domaine
  transporteur légitime — probable tentative de phishing). Vérifié dans
  Shopify : commande réelle #5945, expédiée 12/08 via YunExpress
  (YT2622400706738917), actuellement en transit (12 jours). Réponse
  unique envoyée avec le vrai lien de suivi + avertissement explicite de
  ne pas cliquer sur le lien suspect. Les 4 fils doublons archivés sans
  réponse individuelle (pour éviter de spammer le client).
- **Jullien #5395** : déjà clos par Badr le 24/08 (rétractation de
  l'offre suite à statut "livré" confirmé par le transporteur) — fil
  archivé.
- **Nalbandyan #3191** : a envoyé des photos/justificatifs du retour
  (option 3, retour choisi le 20/08) sans texte d'accompagnement → accusé
  réception, remboursement confirmé dès réception du colis.

### État des lieux du backlog restant (vérifié par sondage, pas exhaustif)

Un balayage `is:unread` sur l'ensemble de la boîte (hors Sent/Chat/Trash)
remonte encore ~201 fils non lus au total, mais l'immense majorité sont de
vieux messages **déjà traités** (Label_3 ou Label_5) dont un message
individuel est resté marqué non-lu sans qu'il y ait de nouvelle action
requise — pas un vrai backlog actif. Un sondage ciblé sur Label_7
(Réexpédition) n'a remonté que les 2 cas ci-dessus (Jullien, Nalbandyan),
tous deux maintenant traités. Label_4 (Escalade) et Label_6
(Remboursement) n'ont pas encore été sondés spécifiquement dans cette
passe — à vérifier au prochain check-in.

**Piste à investiguer avec Badr** : pourquoi autant de messages restent
"non lus" dans des fils déjà archivés en Label_3 — possible qu'un filtre
Gmail marque certains messages entrants comme lus automatiquement sans
les remettre en INBOX, ce qui explique aussi pourquoi Badr voit des
réponses clients "disparaître" sans revenir en boîte de réception. Aucun
outil d'inspection des filtres Gmail disponible pour diagnostiquer plus
avant.

### CORRECTIF IMPORTANT — le "bruit" n'était pas que du bruit

En continuant le sondage `is:unread` page par page (pages 4-5, remontant
jusqu'au 11-13/08), découverte d'un **vrai backlog de ~30 mails clients
jamais étiquetés du tout** (aucun label, ni Label_3 ni Label_4 ni rien) —
des demandes de retour, problèmes de livraison, articles manquants,
questions produit, restées sans réponse pendant 10+ jours. Ce n'était donc
pas que des flags non-lus résiduels sur de vieux fils déjà traités : il y a
un vrai angle mort dans le tri automatique quelque part avant le 13/08.

Cas les plus notables traités dans cette passe :
- **Fuzfa (#2126, commande du 23/06, jamais reçue, 2 mois)** : menaçait de
  signaler à la DGCCRF faute de réponse. Remboursement intégral (89,99€)
  confirmé par mail. **⚠️ Badr doit exécuter le remboursement réel dans
  Shopify — aucun outil de remboursement automatique disponible.**
- Richer #5997 : pensait son adresse erronée, en fait l'adresse Shopify
  correspondait déjà à ce qu'il demandait — juste rassuré + lien de suivi.
- ~10 demandes de retour simples (Lassalle, Capron, Collardeau, Bastille,
  Guglielmi, Dissenykim ES) → adresse de retour standard envoyée.
- Jourdan #5204 et Collin #5553 : e-book manquant → renvoyé vers
  vérification spam, proposé renvoi du lien si besoin.
- Steve (Niva-UK #1038) : remplacement XXXXL promis le 14/07, jamais
  parti — relancé en interne, excuses envoyées.
- Soriano #5362 : simple statut/lien de suivi (pas encore 30j).
- Juanferparca (Niva-ES #1156... en fait un autre client, Chabot,
  commande différente trouvée sous le même numéro dans Shopify —
  attention, la numérotation des sous-boutiques UK/ES ne correspond PAS à
  la même base de commandes que le store principal, les lookups via
  `get-order #XXXX` pour ces sous-boutiques peuvent remonter la mauvaise
  commande. À vérifier manuellement avant de se fier au résultat.) :
  options standard proposées en espagnol.
- modolbec et pruneole11 : messages trop courts/sans contexte → demande de
  numéro de commande envoyée, en attente de réponse.

**Action recommandée pour Badr** : il est probable que ce même angle mort
(mails jamais étiquetés) existe aussi sur des pages antérieures au 11/08 —
à sonder au prochain passage. Le nombre total de non-lus dans la boîte
(`is:unread` hors Sent/Chat/Trash) reste affiché à 201 par l'API Gmail
même après traitement, l'estimate ne semble pas se rafraîchir en temps
réel — ne pas se fier à ce chiffre pour mesurer la progression, mieux vaut
sonder page par page.

### Suite du sondage (page 6) — 24/08/2026

Nouvelle passe sur une page suivante du sondage `is:unread`, avec cette
fois filtrage sur "dernier message du fil vient du client" plutôt que sur
l'absence totale de label (les fils de cette page avaient déjà un Label_3
résiduel mais un nouveau message client non traité par-dessus). ~10 fils
réels traités : Ferme #5765 (adresse de retour), Gicquel (pas d'erreur,
offre 1+1 ne s'applique qu'à 2 articles identiques, réponse de clôture
envoyée), Coutisse/Godfrind/Babu (déjà résolus, juste nettoyage de labels).

**⚠️ 2 déclarations de rétractation légale (Label_8/Withdrawal) trouvées,
non closes, remboursement à exécuter par Badr dans Shopify :**
- **Arnoult #6410** (wil.5550@hotmail.fr) — même client que le cas
  d'annulation refusée plus tôt (commande déjà expédiée par l'agent). Il a
  maintenant soumis une rétractation légale formelle via le widget EU —
  ceci doit être honoré indépendamment du fait que la commande soit déjà
  partie (droit de rétractation légal, pas une simple demande d'annulation).
- **Charreau #5919** (fernand.charreau@gmail.com) — rétractation formelle,
  aucune interaction email préalable trouvée dans la boîte.

Ces déclarations passent par un service externe (widerruf-service /
euwiderrufsbutton.com) et non par un simple e-mail client — je n'ai pas
d'outil pour les traiter/clôturer dans cette app, ni pour initier le
remboursement dans Shopify. Lien direct vers chaque dossier dans le mail
original (déjà en Label_8, juste laissé non-lu retiré).

---

## Campagne marketing « Blanc Ivoire — Rentrée 2026 » (24/08/2026)

**Objectif Badr** : mailer les clients Shopify pour annoncer le nouveau
coloris Blanc Ivoire du Polo Marceau, avec code promo **RENTREE20** (−20%
tout le site, cumulable avec le 2 achetés = 2 offerts), expiration
**mercredi 26 août 23h59**, tracking des clics, sans finir en spam.

### Assets

- Photo mannequin d'origine (Shopify) :
  `https://cdn.shopify.com/s/files/1/0977/0867/1350/files/Polo_blanc_1.png?v=1787077693` (1760×2352)
- Upscale 4K (Higgsfield, bytedance) sur CDN Shopify :
  `.../hf_20260824_164215_2534687f-8616-4035-a8c6-e793bd069500.png` (3072×4096)
- **Version servie dans le mail — CDN Klaviyo** :
  `https://d3k81ch9hvuctc.cloudfront.net/company/SWVS8q/images/c7e26db2-eecf-491a-9679-5f2153c4d4a7.jpeg`
  (JPEG 170 601 o, image ID Klaviyo `362029703`)
- URL produit / CTA :
  `https://mynivashop.com/products/nivafit-polo-ultra-confortable-pour-homme?variant=58483484230006`
  (⚠️ Shopify exige l'ID numérique de variante, pas le nom du coloris)

### Template Klaviyo

`YcCXtc` — « NIVA — Ivoire (Rentrée 2026) — RENTREE20 », editor_type `CODE`,
version texte incluse, désabonnement via `{% unsubscribe 'Se désabonner' %}`.
Édition : https://www.klaviyo.com/email-editor/YcCXtc/edit

Charte respectée : Noir `#151515`, Ivoire `#FAF9F6`, Beige sable `#E8E1D4`
(le blanc pur est banni). Logo `— ◆ —` / `NIVA` / `PARIS`. Sans-serif
géométrique light (Jost/Century Gothic/Futura), graisses 200–300.
Tout le contenu commercial est en **texte HTML vivant**, rien n'est cuit
dans l'image : le mail reste lisible même images bloquées.

### Leçons / pièges rencontrés

1. **Héberger les images sur le CDN Klaviyo**, pas Shopify. C'était la
   cause de la non-apparition des images. Outil : `upload_image_from_url`.
2. **« Redirect Notice » Google** = Gmail qui enrobe les liens des mails de
   test (`google.com/url?q=`). N'existe pas en campagne Klaviyo, qui passe
   par `klclick.com` (et qui fournit le tracking des clics demandé).
3. Le Gmail de Badr **bloque les images externes** (réglage client). Valider
   le rendu dans l'éditeur Klaviyo, pas dans sa boîte.
4. Les images collées dans le chat **n'arrivent jamais sur le disque** —
   passer par Shopify > Contenu > Fichiers puis transmettre l'URL.
5. Egress local bloqué vers `cdn.shopify.com` et `mynivashop.com` (403 sur
   CONNECT via le proxy). Contourner par des outils côté serveur
   (Higgsfield `media_import_url`, Shopify GraphQL, Klaviyo
   `upload_image_from_url`), jamais en désactivant TLS.
6. **« Stock limité » refusé** : Shopify affiche ~10 000 unités par taille
   en Blanc Ivoire. Ce serait une fausse rareté / pratique commerciale
   trompeuse, d'autant plus risquée après la menace DGCCRF reçue le matin
   même (dossier Fuzfa #2126). L'urgence du mail repose uniquement sur la
   vraie date limite.
7. **Ciblage** : segment ayant consenti au marketing, PAS la totalité des
   e-mails Shopify — sinon plaintes spam et délivrabilité du domaine
   dégradée, y compris pour les confirmations de commande.

### En attente de Badr

- [ ] Validation du rendu (éditeur Klaviyo).
- [ ] URL de la photo à plat des polos pliés (optionnelle) → à insérer sous
      le bloc 01/02/03.
- [ ] **Heure d'envoi** : immédiat ou programmé (mardi 10h ou 18h).
- [ ] Puis : `create_campaign` + `assign_template_to_campaign_message`.

---

## ⚠️ RÈGLES SAV MISES À JOUR — 24/08/2026 (Badr, en direct)

Ces règles **remplacent** toutes les consignes SAV antérieures.

1. **PLUS AUCUN BROUILLON.** Interdiction de créer des drafts, quel que soit
   le cas (y compris les retards J+15, les litiges, les rétractations).
   Si un cas est ambigu → **poser la question à Badr dans le chat**, obtenir
   sa réponse, puis **envoyer directement**. Le dossier Brouillons doit
   rester vide en permanence.
2. **PLUS DE TRI PAR DOSSIER / LIBELLÉ.** Ne plus appliquer Label_3 à
   Label_9 (Traité, Escalade, Ignoré, Remboursement, Réexpédition,
   Withdrawal, Brouillon). On répond et on archive, point.
3. Conséquence : l'ancienne règle « les cas de retard critique J+15 doivent
   TOUJOURS rester en brouillon, jamais envoyés automatiquement » est
   **annulée par Badr**. Il assume le risque ; on demande d'abord, on envoie
   ensuite.

Restent valables : Options 1/2 uniquement après réception du colis par le
client ; colis marqué « livré » = problème client/transporteur local, pas
NIVA ; rétractations = retour du colis avec un mot indiquant le numéro de
commande, remboursement à réception.

### Vidage du dossier Brouillons — 24/08/2026, 21h15

15 brouillons trouvés → **0 restant**. 13 envoyés, 2 supprimés (doublons).

Envoyés : Vialette #5932 (pas de double prélèvement + suivi) · Cardi #3601
(retour reçu ? vérification entrepôt) · Guglielmi #3881 (option 1, XXL
offert) · Pardo #1156 ES (opción 1, 4XL azul marino) · Bastille #5368
(garde les polos) · Verhellen #3489/#4983 (2e remboursement relancé) ·
Bezanger (demande n° de commande) · Pabois (mode de dépôt = transporteur) ·
Charreau #5919 (rétractation : adresse retour + mot avec n° de commande) ·
Keane #4377 (retour impossible depuis son pays, on attend) · Bernard #2349
(adresse de retour unique + enquête colis du 7 août) · Jourdan #5204
(l'article offert = e-book envoyé par mail séparé) · Sallenave #4203
(2 options proposées, pas d'étiquette retour).

Supprimés : doublon Vialette (même réponse sur 2 fils) et doublon Bernard
(version « Fwd: » identique).

**Correctif appliqué** : le brouillon Vialette contenait un lien de suivi
enrobé par Gmail (`google.com/url?q=`) qui aurait affiché un « Redirect
Notice » au client. Remplacé par l'URL directe
`https://mynivashop.com/apps/parcelpanel?nums=YT2622400706542194`.
**À vérifier systématiquement avant tout envoi.**

### Actions que Badr doit exécuter lui-même dans Shopify
- Fuzfa #2126 — remboursement 89,99 € (menace DGCCRF).
- Verhellen #3489 / #4983 — 2e remboursement de 59,98 € (un seul des deux
  a été effectué, les 2 colis sont revenus dans le même envoi).
- Arnoult #6410 et Charreau #5919 — remboursement à réception du retour.
- Bernard #2349 — retrouver le colis expédié le 7 août à l'ancienne adresse
  (Résidence Bel Ébat, La Celle-Saint-Cloud). Réponse envoyée promettant un
  retour d'information : il faut trancher.
- Keane #4377 (Irlande ?) — dit ne plus pouvoir expédier de colis vers la
  France depuis le 07/07/2026, seulement des lettres. Question ouverte :
  rembourse-t-on sans retour, ou attend-on ?

### Source de vérité pour les retours/réexpéditions : le Drive

Fichier : **`NIVA_Reshipment_Tracker V1.xlsx`**
(Drive ID `1IFMeQphR1epPbioZHN83YsTPSoEsNFLP`, propriétaire contact.myniva@gmail.com)

Colonnes : Order Number · Shop · Customer · Email · Country · Reason ·
Item(s) to Send · **Status** (Shipped / Not Shipped / Pending / Cancelled) ·
Reshipping Address · New Tracking Number · Notes.

**Règle Badr (24/08/2026)** : on cherche la commande dans ce fichier. Si elle
n'y est pas notée « Shipped » ou « Not Shipped », c'est qu'on n'a rien reçu.
C'est ce fichier qu'on consulte pour répondre aux clients qui demandent où en
est leur retour / leur réexpédition.

### Suites du 24/08 au soir

- **Cardi #3601** → tracker = `Not Shipped`, aucune réception enregistrée.
  Réponse envoyée : rien reçu à ce jour, demande du numéro de suivi et de la
  date de dépôt du retour pour faire tracer le colis.
- **Keane #4377** → Badr : « on n'y peut rien pour lui, propose-lui les deux
  options ». Envoyé : pas de remboursement sans retour, mais choix entre
  Option 1 (il garde tout + 2 polos offerts à la bonne taille + code -20%,
  rien à renvoyer) et Option 2 (retour quand il pourra, puis remboursement,
  sans délai imposé).
- **Bernard #2349** → EN ATTENTE DE DÉCISION DE BADR. Le tracker le note
  `Not Shipped` avec la mention « this order does not include this product ».
  Mais le client a expédié son retour le 07/08 à *SARAJ-NIVA, 6 rue du Bel
  Ébat, 78170 La Celle St Cloud* — **une adresse que NIVA lui avait
  elle-même donnée** — et le colis ne lui est jamais revenu, donc il a bien
  été livré là-bas. Dossier ouvert depuis 2 mois, client très remonté.

### ⚠️ CORRECTIF — sens réel du statut « Not Shipped » dans le tracker

**Je m'étais trompé.** Badr a corrigé le 24/08 :

> « not shipped ça veut dire que l'agent a enregistré l'expédition et le
> colis est prêt pour shipping »

Donc dans `NIVA_Reshipment_Tracker V1.xlsx` :
- **La commande figure dans le fichier** = le retour du client **a bien été
  réceptionné** et la réexpédition est **enregistrée et préparée**.
- **`Not Shipped`** = colis prêt, **en attente de départ** — ce n'est PAS
  « on n'a rien reçu ».
- **`Shipped`** = parti, avec numéro de suivi dans la colonne dédiée.
- **`Pending`** = en attente d'une information (souvent la taille/couleur).
- **Absent du fichier** = là seulement, on n'a rien reçu.

Ne jamais dire à un client « nous n'avons rien reçu » si sa commande
apparaît dans ce fichier.

### Correctifs envoyés dans la foulée
- **Cardi #3601** : j'avais envoyé à tort « nous n'avons rien reçu » et lui
  avais demandé son numéro de suivi. Mail de rectification envoyé : retour
  bien réceptionné, chemise 3XL préparée, en attente d'expédition, aucune
  démarche de sa part.
- **Bernard #2349** : son retour du 07/08 à l'ancienne adresse (Bel Ébat) a
  bien été réceptionné. Chemise blanche manche courte 3XL préparée, en
  attente d'expédition. Excuses formelles pour les 2 mois et les adresses
  contradictoires. Dossier clos côté client.
- **Verhellen #3489/#4983** : questions envoyées à la cliente à la demande
  de Badr — date d'expédition du colis retour (+ n° de suivi si conservé)
  et origine des deux commandes séparées.

### À expédier concrètement (Badr / l'agent d'expédition)
- #3601 Cardi — chemises 3XL
- #2349 Bernard — chemise blanche manche courte 3XL
Les deux clients attendent le numéro de suivi, promis par mail.

### Campagne v5 — validée sur le fond, test envoyé (24/08, 23h46)

Retour de Badr sur la v4 : « pas mal, ça manque de FOMO, 1 acheté 1 offert,
deadline en grand ». Corrections appliquées dans la v5 :

- **Bloc deadline géant** au milieu du mail : « IL NE VOUS RESTE QUE » +
  **2 JOURS** en 104px + « MERCREDI 26 AOÛT · 23H59 » + « Passé cette heure,
  le code ne fonctionne plus et tout repasse au prix normal. »
- **« 1 ACHETÉ / 1 OFFERT »** en 56px comme titre d'offre (remplace
  « 2 achetés = 2 offerts »). Le −20% devient un bonus secondaire.
- FOMO ajouté : bandeau haut, CTA « J'EN PROFITE AVANT MERCREDI », et bloc
  de clôture « Mercredi 23h59, c'est terminé. » en 38px.

**Règle promo confirmée par Badr (24/08)** : le 1 acheté = 1 offert permet de
choisir **n'importe quel article de la boutique** en cadeau (pas seulement un
article identique), **et** les −20% s'appliquent en plus. Formulation retenue
dans le mail : « L'article offert est libre : la taille et le coloris de votre
choix. » — contredit l'explication donnée à Gicquel, à garder en tête si ce
dossier revient.

Template Klaviyo `YcCXtc` mis à jour (« NIVA — Ivoire (Rentrée 2026) —
RENTREE20 — v5 FOMO »), version texte incluse.
Aperçu image v5 :
`https://d3k81ch9hvuctc.cloudfront.net/company/SWVS8q/images/e89e4964-1e28-48f3-a935-6a2b51c59520.png`
Sources locales : `scratchpad/niva_v5_src.html` (avec placeholders __F__ /
__U__ / __UNSUB__) et `scratchpad/klaviyo_v5.html` (version finale).

Test envoyé via Klaviyo à serraj146@gmail.com (job
`d6fe3c0859f04ae085bab5550d2105e3`). Reste à obtenir : validation finale +
heure d'envoi, puis `create_campaign` + `assign_template_to_campaign_message`
sur le segment consenti marketing.

### Méthode pour montrer un rendu de mail à Badr (à réutiliser)
Son Gmail bloque les images externes → ne jamais valider un design par mail.
Pipeline qui marche : construire le HTML → le rendre en PNG pleine page dans
le sandbox Higgsfield (`node` + `playwright` via
`NODE_PATH=/usr/local/lib/node_modules`, viewport 640, deviceScaleFactor 2,
`fullPage:true`) → `media_upload` + PUT + `media_confirm` → puis
`Klaviyo upload_image_from_url` pour un lien stable → envoyer le lien dans le
chat. Attention : l'egress local est bloqué vers cdn.shopify.com,
mynivashop.com et les CloudFront ; tout passe par le sandbox.
