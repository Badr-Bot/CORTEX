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
  France depuis le 07/07/2026, seulement des lettres. **Tranché par Badr le
  25/08 : on attend le retour, pas de remboursement sans colis reçu.**

### RÈGLE REMBOURSEMENT (tranchée par Badr le 25/08/2026) — PRIORITAIRE

**Aucun remboursement sans retour du produit.** Le client doit renvoyer
l'article ; le remboursement est exécuté à réception du colis chez NIVA.

- Client qui n'a **rien reçu** : on n'ouvre pas de remboursement. Il attend
  de recevoir le colis, puis il nous le renvoie, et c'est à ce moment-là
  qu'on rembourse. Pas d'exception « il n'a rien reçu donc on rembourse
  direct » — cette formulation antérieure dans ce fichier est **caduque**.
- Cette règle prime sur toute rédaction plus ancienne du présent document.

### Expéditions en cours (état au 25/08/2026)
- **Cardi #3601** (chemises 3XL) et **Bernard #2349** (chemise blanche
  manche courte 3XL) : préparation en cours côté Badr, **expédition prévue
  le 26/08**. Numéro de suivi promis aux deux clients — à transmettre dès
  qu'il existe.

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

### Audience Klaviyo & délivrabilité — état au 24/08/2026

**Domaine d'envoi** : `envoi.mynivashop.com` — statut **active**, purpose
marketing, DKIM selector `km1`, créé le 20/07/2026. Authentifié (SPF/DKIM).
Compte : `SWVS8q`, fuseau **Europe/Paris**, locale fr-FR, EUR.
Expéditeur par défaut : Niva <contact@mynivashop.com>.

**Tailles des segments (relevé du 24/08)** :
| Segment | ID | Membres |
|---|---|---|
| Safe send hors Gmail \|\|JT\|\| | Rf97Dp | 1 083 |
| safe send Gmail actif \|\|JT\|\| | QXAktB | 351 |
| Engaged 30D \|\|JT\|\| | Unupju | 1 759 |
| Post achat 20j \|\|JT\|\| | XSmhmZ | 729 |
| Exclusion Gmail \|\|JT\|\| | VYstuW | 3 327 |
| Exclusion Gmail et Orange \|\|JT\|\| | UAvFHw | 4 308 |
| Bounce-Unsubscribe-Spams CLEAN \|\|JT\|\| | R9zpNf | 96 |
| Unengaged 90 Days (Sunset) | WwBNif | 0 |

Listes : `Wgu7Z3` Liste d'adresses e-mail (single opt-in) · `SFCkY5` SMS ·
`WbQRDD` Prévisualiser.

**Définition des segments « safe send »** (les deux) : consentement email
SUBSCRIBED + au moins une ouverture/clic dans les 30 derniers jours +
0 bounce sur 30 jours + 0 plainte spam / désabonnement sur 180 jours.
C'est l'audience la plus sûre du compte. Total combiné : **1 434**.

**Nouvelle liste interne** : `ViZeWG` « Équipe NIVA — réception campagnes »
(single opt-in) avec adnane.vtr@hotmail.com, serraj146@gmail.com,
badr.saraj@gmail.com — tous les trois SUBSCRIBED,
can_receive_email_marketing=true, aucune suppression. À inclure dans
l'audience de chaque campagne pour que Badr reçoive le mail comme un client.

### ⚠️ Découverte importante — comment les campagnes NIVA sont réellement envoyées

Analyse des 4 dernières campagnes **envoyées** (05/08, 09/08, 12/08, 16/08) :

- **Audience incluse : `Unupju` (Engaged 30D) uniquement.**
- **Audiences exclues : `QVfVnm`, `R9zpNf` (bounces/désabo/spams) et
  `UAvFHw` (Exclusion Gmail et Orange, 4 308 personnes).**
- Expéditeur : `Niva <contact@mynivashop.com>`
- Envoi : `static`, `is_local: true` (fuseau du destinataire), à **09h30 ou
  09h45** systématiquement. `use_smart_sending: false`.

Autrement dit : le consultant délivrabilité (||JT||) **exclut volontairement
toutes les adresses Gmail et Orange** depuis le début. Le domaine
`envoi.mynivashop.com` n'a qu'un mois (créé le 20/07/2026) — c'est une
stratégie de warm-up classique, Gmail et Orange étant les plus stricts.

Conséquence : envoyer aux 5 500 signifie inclure Gmail + Orange pour la
première fois, en volume, sur un domaine jeune. C'est un changement de
stratégie majeur, pas un simple élargissement.

L'horaire 09h30–09h45 est confirmé comme le créneau retenu par le consultant.

### Campagne créée (BROUILLON — rien n'est envoyé)

`01M0TX2RJFQTSSQ5YCR4RB2VMZ` — « Rentrée 2026 — Blanc Ivoire — RENTREE20
(base complète) », statut **Draft**, `scheduled_at: null`.
- Inclus : liste `Wgu7Z3` (base e-mail) + `ViZeWG` (équipe NIVA)
- Exclu : `R9zpNf`
- Envoi : **throttled 10 %/heure**, départ 25/08 09h30 Paris (07h30 UTC)
  → étalé sur ~10 h au lieu d'un pic unique. Protège un domaine jeune.
- Objet : « 1 acheté = 1 offert, et −20% en plus — jusqu'à mercredi »
- Preview : « Le Blanc Ivoire vient d'arriver. Après mercredi 23h59, tout
  repasse au prix normal. »
- Expéditeur : Niva <contact@mynivashop.com>, reply-to identique
- Tracking : ouvertures + clics + UTM (`utm_source=klaviyo`,
  `utm_medium=email`, `utm_campaign=rentree20-blanc-ivoire`,
  `utm_content=campaign_name_id`)
- Message `01M0TX2RJTMG63S55A578NBGZ5`, template cloné `YhbXmW` (clone
  automatique de `YcCXtc` par Klaviyo à l'assignation — normal).

**Pour envoyer il faut appeler `send_campaign` — non fait, en attente de la
validation explicite de Badr.**

### ✅ CAMPAGNE PROGRAMMÉE — validée par Badr le 24/08 à 00h15

Campagne `01M0TX2RJFQTSSQ5YCR4RB2VMZ` — « Rentrée 2026 — Blanc Ivoire —
RENTREE20 (base complète) ».

- Statut : **Queued** (programmée), `scheduled_at` 24/08 22h15 UTC
- **Départ : 25/08 à 07h30 UTC = 09h30 Paris**, throttled **10 %/heure**
  (fin vers 19h30, avant la deadline du 26/08 23h59)
- Inclus : `Wgu7Z3` (base e-mail complète) + `ViZeWG` (équipe NIVA)
- Exclus : `QVfVnm`, `R9zpNf`
- Objet : « 1 acheté = 1 offert, et −20% en plus — jusqu'à mercredi »

**Décision assumée par Badr** : envoyer à toute la base (~5 500), Gmail et
Orange inclus, alors que les 4 campagnes précédentes les excluaient
volontairement (warm-up d'un domaine créé le 20/07). Risque signalé, Badr a
tranché. Le throttling à 10 %/h est la mesure de compensation appliquée.

**Pour annuler avant/pendant l'envoi** : `cancel_campaign_send` sur cet ID.

**À surveiller le 25/08** : taux de bounce et plaintes spam, surtout côté
Gmail et Orange. Si les bounces dépassent ~2 % ou les plaintes ~0,1 %,
annuler l'envoi en cours et repasser aux segments « safe send ».

**Relance proposée (pas encore créée)** : mercredi 26/08 vers 18h, aux
non-ouvreurs uniquement, objet type « Il reste 6 heures ».

## Performance des flows Klaviyo — relevé du 24/08/2026 (30 derniers jours)

Métrique de conversion : `Placed Order` (`Yrs33B`).

| Flow | ID | Destinataires | Ouv. | Clic | Conv. | CA 30j | €/destinataire |
|---|---|---|---|---|---|---|---|
| Welcome Flow | T7JxZT | 3 681 | 40,0 % | 7,4 % | 3,22 % | **7 551 €** | 2,08 € |
| Abandoned Checkout | SgnesH | 1 060 | 43,9 % | 10,8 % | 4,56 % | **3 273 €** | **3,11 €** |
| Browse Abandonment | XZwTsk | 3 101 | 32,9 % | 3,1 % | 0,58 % | 1 359 € | 0,44 € |
| Abandoned Cart | XhNtXV | 1 493 | 36,7 % | 6,7 % | 1,22 % | 1 146 € | 0,78 € |
| Post Purchase | Yq9Gav | 3 419 | 62,9 % | 27,3 % | 0,44 % | 1 041 € | 0,30 € |
| Site Abandonment | UNaq2J | 1 202 | 38,1 % | 4,3 % | 0,42 % | 300 € | 0,25 € |

**Total flows : ~14 670 € sur 30 jours.**

Flows `live` sans aucune donnée sur la période : **Winback** (`VPrHJj`) et
**Sunset** (`RMEGr6`) — ils ne se déclenchent pas.
Flow en **draft** jamais activé : « Page de commande abandonnée Rappel -
Standard (E-mail et SMS) » (`Y6Ezmh`) — doublon de Abandoned Checkout, à
laisser désactivé ou archiver pour éviter les doubles envois.

### Analyse par message — points d'action

- **Le meilleur mail de tout le compte** : `VRdZtF` (Abandoned Checkout) —
  322 destinataires, 30 conversions, 2 127 €, **6,71 €/destinataire**,
  51 % d'ouverture, 18,9 % de clic. C'est le modèle à copier.
- **Le pire** : `RcSwut` (Abandoned Cart, 1er message) — 366 destinataires,
  **1 seule conversion, 48 €**, 0,13 €/destinataire, 3,9 % de clic. Ce
  message ne sert à rien en l'état, à réécrire.
- **Post Purchase = énorme gâchis** : 62,9 % d'ouverture et 27,3 % de clic
  (933 clics !) mais seulement 0,44 % de conversion, 15 commandes. Les gens
  cliquent massivement mais n'achètent pas — les liens pointent
  probablement vers du suivi de colis / avis plutôt que vers des produits.
  C'est le plus gros gisement inexploité du compte.
- **Abandoned Cart vs Abandoned Checkout** : Cart touche 40 % de gens en
  plus (1 493 vs 1 060) mais rapporte 3 fois moins. L'écart vient du
  contenu, pas de l'audience.

## 🔧 DIAGNOSTIC CONFIRMÉ — pourquoi l'Abandoned Cart ne convertit pas (25/08)

Badr soupçonnait des liens cassés. Vérification faite sur les **données
réelles des événements Shopify** :

**Événement `Added to Cart` (`WfbaFR`)** — utilisé par le flow Abandoned Cart :
```
"URL": "https://zmfm0f-ei.myshopify.com/products/e-book-lart-de-sublimer..."
```
Le template `SZipYW` (message E2 « Vous avez laissé quelque chose ») pointe
son bouton « Finaliser ma commande » sur `{{ event.URL }}`. Résultat :
1. domaine technique `zmfm0f-ei.myshopify.com` au lieu de `mynivashop.com` ;
2. c'est une **page produit**, pas un panier — le client arrive avec un
   panier vide et doit tout refaire.

**Événement `Checkout Started` (`XbpVNm`)** — utilisé par Abandoned Checkout :
```
"checkout_url": "https://mynivashop.com/97708671350/checkouts/ac/hWNG3OWHLXBIzM2pF6uNRV7z/recover?key=...&locale=fr-FR"
```
Bon domaine **et panier restauré** (l'événement contient les 3 line_items).

➡️ **C'est toute l'explication de l'écart 3,11 € vs 0,78 € par destinataire.**
Ce n'est pas la rédaction, c'est la destination du bouton.

⚠️ Ne pas conclure trop vite d'un rendu `render_email_template` sans contexte :
`{{ event.URL }}` s'affiche vide dans ce cas, ce qui fait croire à un
`href=""` en dur. J'ai commis cette erreur et l'ai corrigée.

⚠️ Correction d'une autre analyse trop rapide : le Post Purchase qui « clique
sans convertir » (54 % de clic sur `VYGL3p`) n'a PAS de lien cassé — c'est
le message **« E3 - Tracking colis »**, objet « Où en est votre commande ? ».
Les gens cliquent pour suivre leur colis, c'est normal. Il ne faut pas
attendre de ventes de ce message.

**Contrainte technique** : tous les templates de flows sont
`SYSTEM_DRAGGABLE` (éditeur drag & drop). `update_email_template` les refuse
(400). Il faut `update_dnd_email_template` avec la définition JSON complète,
ou passer par des templates clonés.

**Décision de Badr (25/08)** : ne PAS corriger les flows existants. Créer de
nouveaux flows à neuf, avec mes préconisations et les audiences que je
conseille. Validation par mail, puis activation du nouveau et désactivation
de l'ancien.

## 📐 PLAN DE REFONTE DES FLOWS — validé comme document de travail (25/08)

**Artefact publié** :
https://claude.ai/code/artifact/962cca72-052f-43cd-b093-8b7873138895
Source : `scratchpad/plan_flows.html` (republier le même chemin pour mettre à jour).

Badr a demandé de tout réorganiser et de faire un plan commun avant de
construire, en s'inspirant d'**Alex Garcia (Marketing Examined)**.

### Principes éditoriaux retenus
1. L'histoire avant l'offre — le récit d'origine (« aucun polo n'était pensé
   pour les gars qui ont pris quelques kilos ») remonte dans le Bienvenue.
2. Un seul plain-text « voix du fondateur » par séquence — il marche parce
   qu'il détonne.
3. Un mail = une objection (taille / tombé / risque / délai), pas 4× « revenez ».
4. Éduquer coûte moins cher que remiser — la promo seulement au dernier mail.
5. Un seul produit héros : le Polo Marceau.
6. Segmenter par comportement (consulté ≠ ajouté ≠ checkout).
7. L'objet parle du lecteur, pas de nous.

### Priorités et objectifs (à trafic constant)
| # | Flow | Actuel | Cible |
|---|---|---|---|
| 1 | Panier abandonné — refonte totale | 1 146 € | 2 700–3 700 € |
| 2 | Checkout abandonné — amplifier (3→4 mails) | 3 273 € | 4 500–5 500 € |
| 3 | Post-achat — séparer suivi colis / vente, ajouter le rachat J+21 | 1 041 € | 2 000–2 800 € |
| 4 | Bienvenue — ne pas casser, corriger liens + 5e mail | 7 551 € | 8 500–9 500 € |
| 5 | Navigation + Site abandonné — fusionner | 1 659 € | 2 200–2 800 € |
| 6 | Winback + Sunset — reconstruire (déclencheurs morts) | 0 € | 1 200–2 000 € |

Total : **14 670 € → 24–29 k€ / mois** visés.

### Fix technique central
Lien de tous les mails de relance panier :
`https://mynivashop.com/cart/{{ event.VariantID }}:{{ event.Quantity }}`
(reconstruit le panier sur le bon domaine — l'événement Added to Cart ne
fournit aucun checkout_url).
Checkout abandonné : `{{ event.extra.checkout_url }}`.

### Méthode de bascule (validée)
Construire en brouillon → envoyer chaque message par mail à Badr → activer
le nouveau et couper l'ancien à la minute → mesurer 14 jours au €/mail
envoyé → flow suivant. **Un seul flow refondu à la fois.**

### Outils confirmés disponibles
`create_flow` (définition JSON complète), `create_email_template`
(editor_type CODE = maîtrise totale des liens), `clone_email_template`,
`update_dnd_email_template`. Base HTML des nouveaux mails :
`scratchpad/flows/base.html`.

**Prochaine étape** : attendre la validation du plan par Badr, puis
construire le flow Panier abandonné (priorité 1) en brouillon.

## 🚨 CAUSE RACINE DE LA SURCHARGE SAV « où est mon colis » (25/08)

Badr a proposé d'ajouter des mails transactionnels (commande / expédié /
pris en charge transporteur / livré) pour désengorger le SAV. Vérification
des volumes d'événements Klaviyo sur **août 2026** :

| Métrique | ID | Août | Verdict |
|---|---|---|---|
| Placed Order | Yrs33B | **1 070** | ✅ utilisable |
| Fulfilled Order | Udzdq2 | **1 092** | ✅ utilisable (= expédié) |
| Delivered Shipment | U9WCYK | **669** | ✅ utilisable |
| Confirmed Shipment | TuLCRC | **6** | ❌ la donnée n'arrive pas |
| Package in transit | UnSGtA | **4** | ❌ la donnée n'arrive pas |
| Package delayed | RBxAZV | **0** | ❌ aucun événement, jamais |

**1 070 commandes pour 6 événements de prise en charge transporteur.**
L'application de suivi (ParcelPanel — cf. `mynivashop.com/apps/parcelpanel`)
n'est pas connectée à Klaviyo. C'est LA cause du volume de « où est mon
colis » au SAV : les mails de suivi ne peuvent tout simplement pas partir.

### Ce qui est constructible tout de suite
1. **Commande enregistrée** (Placed Order) — adresse affichée en grand pour
   rattraper les erreurs de saisie (cf. dossiers #3207, #4610).
2. **Colis parti** (Fulfilled Order) — n° de suivi + **délai réaliste**.
3. **Retard** — ⚠️ astuce clé : pas besoin de la métrique « Package delayed ».
   Déclencher sur Fulfilled Order → attendre 10 jours → split conditionnel
   « pas de Delivered Shipment depuis le début du flow » → envoyer.
   C'est le mail le plus rentable en heures de SAV économisées.
4. **Colis livré** (Delivered Shipment) — confirmation + conseil d'essayage.

### Bloqué en attendant
5. « Pris en charge par le transporteur local » — nécessite de connecter
   l'appli de suivi à Klaviyo. **Action à faire par Badr.**

### ⚠️ Piège doublons
Shopify envoie déjà nativement sa confirmation de commande et sa
confirmation d'expédition. Si Klaviyo les envoie aussi, le client en reçoit
deux. Il faudra couper l'un des deux côtés — ne jamais laisser partir les deux.

Ces mails sont **transactionnels** : audience = tous les acheteurs, y compris
les désabonnés du marketing ; aucune offre, aucune promo dedans.

Section ajoutée à l'artefact du plan (« Priorité 0 »).

## 📍 POINT D'ÉTAPE — 25/08/2026, ~10h Paris

### Campagne Blanc Ivoire : EN COURS D'ENVOI
`01M0TX2RJFQTSSQ5YCR4RB2VMZ` — statut **`Sending`**, partie à 07h30 UTC
(09h30 Paris), throttled 10 %/h → fin vers 19h30 Paris.

Premiers chiffres (766 envoyés sur ~5 500) :
- Délivrés 765 — **99,87 %**
- Bounces 1 — **0,13 %** (seuil d'alerte : 2 %)
- Plaintes spam **0** (seuil d'alerte : 0,1 %)
- Ouvertures 119 — 15,6 % · Clics 10
- **1 commande, 59,99 €**

➡️ La délivrabilité tient malgré l'ouverture à Gmail + Orange. Continuer à
surveiller jusqu'à la fin de l'envoi.

⚠️ Les 3 adresses de l'équipe (`ViZeWG`) n'avaient rien reçu à 10h : normal,
14 % de la base envoyée, Klaviyo tire dans un ordre non contrôlable.

📌 Découverte : le segment exclu `QVfVnm` s'appelle **« Reputation Repair
Audience »** — le domaine a déjà connu un incident de réputation.

### Décision de séquencement (Badr, 25/08)
**On attend qu'il branche ParcelPanel → Klaviyo avant de commencer les
flows.** Ensuite on attaque **flow par flow**, un seul à la fois.

Marche à suivre transmise à Badr :
1. Klaviyo → Settings → API Keys → *Create Private API Key* (droits
   d'écriture sur les Events).
2. App ParcelPanel dans l'admin Shopify → Integrations / Notifications →
   Klaviyo → coller la clé, activer les statuts d'expédition.
   (⚠️ souvent réservé aux plans payants ; noms de menus variables.)

**Ma vérification une fois branché** : relancer `query_metric_aggregates` sur
`UnSGtA` (Package in transit) et `TuLCRC` (Confirmed Shipment). Si ça passe
de 4 et 6 à plusieurs centaines → OK. Sinon → connexion ratée.

### Ordre de travail convenu ensuite
1. Flow **Suivi de commande** (4 mails constructibles) — visuels générés sur
   Higgsfield dans la charte, montrés à Badr avant intégration.
2. Envoi de chaque mail à Badr via Klaviyo pour validation.
3. Activation du nouveau + coupure de l'ancien, mesure 14 jours.
4. Puis **Panier abandonné**, puis le reste selon le plan.

Badr a validé le plan complet et l'a trouvé « super clair, classe ».

---

## 📍 CONTRÔLE AUTOMATIQUE — 25/08/2026, fin de journée

### 1. Campagne Blanc Ivoire — SAINE, aucune alerte

Chiffres consolidés `01M0TX2RJFQTSSQ5YCR4RB2VMZ` (statut toujours `Sending`,
throttle 10 %/h) :

| Indicateur | Valeur | Seuil d'alerte | État |
|---|---|---|---|
| Destinataires | 2 059 | — | — |
| Délivrés | 2 055 — **99,81 %** | — | ✅ |
| Bounces | 4 — **0,19 %** | 2 % | ✅ |
| Plaintes spam | **0 — 0,00 %** | 0,1 % | ✅ |
| Désabonnements | 11 — 0,53 % | — | normal 1er envoi large |
| Ouvertures uniques | 437 — **21,3 %** | — | ✅ |
| Clics uniques | 48 — **2,34 %** | — | ✅ |
| Commandes | **5 — 251,98 €** (panier moyen 50,40 €) | — | 0,12 €/destinataire |

➡️ La délivrabilité tient sur ~2 000 envois. **Pas d'alerte à déclencher.**

### 2. ParcelPanel — CONNECTÉ MAIS N'ENVOIE RIEN ⛔

Badr a annoncé « c'est bon parcelpanel est connecté à klaviyo » et la tuile
Klaviyo dans ParcelPanel affiche bien **« Actif » / « Déconnexion »**.
**Mais aucun événement n'est arrivé côté Klaviyo.**

Vérification sur 8 jours (18 → 25/08, fuseau Paris) :

| Métrique | ID | Source | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
|---|---|---|---|---|---|---|---|---|---|---|
| Package in transit | `UnSGtA` | Klaviyo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Package picked up | `SeyDCy` | Klaviyo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Confirmed Shipment | `TuLCRC` | Shopify | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Marked Out for Delivery | `T7TB8y` | Shopify | 10 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Package delivered** | `XBQi9Z` | Klaviyo | 15 | 3 | 2 | 2 | 22 | 4 | 5 | **12** |
| **Delivered Shipment** | `U9WCYK` | Shopify | 15 | 3 | 2 | 2 | 23 | 4 | 5 | **12** |

Contrôle complémentaire : `get_metrics` — **aucune nouvelle métrique créée**
depuis le branchement. La plus récente reste `click.shopifyInstallNow`
(05/08). Si ParcelPanel poussait quoi que ce soit, une métrique aurait été
créée ou alimentée aujourd'hui.

**Conclusion : la connexion existe, mais l'envoi des événements n'est pas
activé.** C'est un réglage séparé de la connexion elle-même.

➡️ Action pour Badr : dans l'admin Shopify → **CWILL (Parcel Panel)** →
**Intégration** → bouton engrenage en haut à droite **« CWILL Tracking
événements »**. C'est le seul écran de réglages qu'on n'a pas ouvert. Y
activer les statuts (*In transit / Picked up / Out for delivery / Exception /
Delay*). Puis me le dire — je revérifie `UnSGtA` et `TuLCRC` immédiatement.

### 3. Bonne nouvelle : on n'est pas totalement bloqué

`Delivered Shipment` (`U9WCYK`) **fonctionne** (~65 événements sur 8 jours).
Avec `Placed Order` (`Yrs33B`) et `Fulfilled Order` (`Udzdq2`) qui marchent
déjà, **4 des 5 mails du flow Suivi de commande sont constructibles dès
maintenant** :

1. Commande confirmée → `Placed Order` ✅
2. Colis expédié → `Fulfilled Order` ✅
3. Retard → `Fulfilled Order` + attente 10 j + split conditionnel
   « pas de `Delivered Shipment` » ✅
4. Colis livré → `Delivered Shipment` ✅
5. Remis au transporteur local → **nécessite ParcelPanel** ⛔

Seul le n°5 attend vraiment. Mais Badr a dit « attend que je branche parcel
panel » puis « viens on configure parcel panel d'abord » → **on ne démarre
pas sans son feu vert.**

### ✅ CORRECTION 25/08 17h — ParcelPanel FONCTIONNE

Badr a montré l'écran « CWILL Tracking événements » : les deux interrupteurs
principaux étaient **déjà activés**. Ma conclusion précédente (« l'envoi des
événements n'est pas activé ») était fausse — **je surveillais les mauvaises
métriques**.

ParcelPanel n'alimente PAS les anciennes métriques « Package … » (`UnSGtA`,
`SeyDCy`, `XBQi9Z`… créées le 21/03, vestiges d'un connecteur mort). Il crée
les siennes :

| Métrique | ID | Créée |
|---|---|---|
| **ParcelWILL - Shipment status update** | `UjhQfQ` | 25/08 15:12 UTC |
| **ParcelWILL - Shipment sub-status update** | `W7HHLj` | 25/08 15:12 UTC |

➡️ **C'est `UjhQfQ` qu'il faut surveiller et utiliser comme déclencheur**, pas
`UnSGtA` ni `TuLCRC`.

#### Payload disponible (événement réel, commande #6025)

```
order_number            #6025
shipment_status         In transit
shipment_substatus      In transit
last_check_point        Arrived at sorting center
last_checkpoint_time    24 août 2026 18:22
tracking_number         YT2622600703095290
tracking_link           https://mynivashop.com/apps/parcelpanel?nums=<num>
carrier_name            YunExpress
carrier_url             https://www.yuntrack.com/parcelTracking?id=<num>
last_mile_carrier_name  GOFO France          ← débloque le mail n°5
last_mile_tracking_number / last_mile_carrier_url
expected_delivery_date  (vide sur cet événement)
transit_time / residence_time
order_created_at        13 août 2026 12:22
fulfillment_created_at  14 août 2026 07:17
pickup_date             24 août 2026 18:22
first_name / last_name / customer_email / customer_phone
shipping_address1 / city / zip / province / country
lineitems[]  → product_name, variant_name, price, handle, variant_image
store_name / store_url
```

`tracking_link` pointe sur **mynivashop.com** — bon domaine, pas de redirect.
`lineitems[].variant_image` permet d'afficher les produits dans le mail.

#### 🔴 Découverte majeure : le mail « expédié » part 10 jours trop tôt

Sur #6025 : commande **13/08**, `Fulfilled Order` **14/08**, mais
`pickup_date` réel **24/08**. **Dix jours** entre le « colis expédié » de
Shopify et la prise en charge transporteur.

➡️ Le mail « votre colis est expédié » déclenche exactement l'angoisse qu'il
est censé calmer. **Il doit annoncer la préparation, pas l'acheminement.**
À revérifier sur plusieurs commandes quand le volume sera là.

#### Réglages restant à faire (demandés à Badr)

| Réglage | État | Recommandation |
|---|---|---|
| Mise à jour du statut | ✅ ON | garder |
| Mise à jour du sous-statut | ✅ ON | garder |
| Date d'expiration estimée dépassée | ❌ OFF | **activer** |
| Retard dans le transit (règle `EMK6HSDK`) | ❌ OFF, **20 j** | **activer + passer à 10 j** |
| Expédition bloquée (règle `5JXJQ9MF`) | ❌ OFF, 5 j | **activer**, garder 5 j |

Ces trois-là sont précisément ceux qui vident le SAV.

#### Volume à date
1 seul événement (17h11) : ils ne se déclenchent qu'au **changement** de
statut. Montée attendue sous 24-48 h au fil des scans transporteurs.

➡️ **Le flow Suivi de commande est constructible en entier, les 5 mails.**

---

## 🏗️ FLOW 1 « SUIVI DE COMMANDE » — CONSTRUIT EN BROUILLON (25/08 ~17h35)

### Décisions Badr validées
- Retard ParcelPanel réglé sur **15 j** par Badr (règle EMK6HSDK). Compensé par
  le flow Rassurance à J+10 côté Klaviyo — les deux se complètent.
- Promesse incident : réexpédition si le colis ne repart pas sous **24 h** (Badr).
- Promesse J+10 : délai 10-20 j assumé + **30 j → remboursement ou réexpédition
  au choix** (Badr).
- Mail « Livré » : **100 % service, zéro vente** (le flow est transactionnel ;
  CTA marketing chez des désabonnés = risque CNIL). La vente post-livraison
  ira dans le flow Post-achat.

### Templates créés (CODE, charte NIVA, barre de progression 4 étapes sur A/B/C)
| Mail | Template | Statut déclencheur |
|---|---|---|
| A En route | `UpdQrR` | In transit |
| B En livraison | `RzP8Ev` | Out for delivery |
| C Livré | `W6Mdzv` | Delivered |
| D Incident | `YhwSK9` | Exception |
| D2 Passage manqué | `SAjsSu` | Failed attempt |
| E Rassurance J+10 | `RkSBFA` | (Fulfilled Order + 10 j) |

### Flows créés (statut DRAFT, ne rien activer sans validation Badr)
**`TWLyAc` — NIVA — Suivi de commande (Claude v1)**
Trigger `UjhQfQ` (ParcelWILL Shipment status update) → multi-branches sur
`shipment_status` : In transit→A · Out for delivery→B · Delivered→C ·
Failed attempt→alerte interne+D2 · Exception→alerte interne+D ·
Expired→alerte interne seule · else→rien.
Alertes internes → serraj146@gmail.com avec n° commande + checkpoint + tracking.
From/reply-to : contact@mynivashop.com. Smart sending OFF.

**`Ukv6cZ` — NIVA — Rassurance J+10 (Claude v1)**
Trigger `Udzdq2` (Fulfilled Order) → attente 10 j (envoi à 10h, fuseau profil)
→ mail E avec filtre « 0 événement ParcelWILL shipment_status=Delivered depuis
l'entrée dans le flow ». Réentrée : 30 j.

### ⚠️ À faire avant activation
1. **`transactional` est retombé à `false`** sur tous les mails (l'API
   l'ignore à la création). À cocher dans l'UI Klaviyo par mail (« Mark as
   transactional ») sinon les désabonnés ne reçoivent pas leur suivi.
2. **Vérifier les valeurs réelles de `shipment_status`** sur les événements
   des prochaines 48 h (un seul observé : "In transit"). Si ParcelPanel envoie
   d'autres libellés, corriger les branches.
3. Doublon Shopify : la notif Shopify « expédié » part à J0, le mail A au
   premier scan (~J+10 observé sur #6025) → complémentaires, pas de coupure
   nécessaire a priori.

### Tests envoyés à Badr (17h35)
6 previews (serraj146@gmail.com + badr.saraj@gmail.com) remplis avec les
données réelles de #6025. Attente de sa validation avant toute activation.

### Plan global re-confirmé par Badr (méthode par flow)
Construire en brouillon → tests par mail → validation Badr → désactiver
l'ancien + activer le nouveau → mesurer 14 j → flow suivant.
Ordre : 1 Suivi (ici) · 2 Panier abandonné · 3 Checkout abandonné ·
4 Post-achat · 5 Bienvenue · 6 Navigation+Site fusionnés · 7 Winback+Sunset.

---

## 🏗️ TOUS LES FLOWS CONSTRUITS EN BROUILLON (25/08 ~17h55)

Badr a validé les 6 mails du flow Suivi (« niquel ») et demandé de préparer
tous les flows. **Variables vérifiées sur événements réels avant construction** :
- Added to Cart : `Product Name`/`Variant Name`/`ImageURL`/`Price`/`VariantID`/
  `Quantity` OK ; `URL` = myshopify (jamais utilisée). Lien panier =
  `mynivashop.com/cart/{{ VariantID }}:{{ Quantity }}`.
- Checkout Started : `event.extra.checkout_url` = mynivashop.com/recover ✅,
  `extra.line_items[]` avec images.
- Viewed Product : `URL` déjà sur mynivashop.com ✅, `Name`/`ImageURL`/`Price`.

### Les 8 flows Claude v1 (tous DRAFT)
| Flow | ID | Trigger | Séquence |
|---|---|---|---|
| Suivi de commande | `TWLyAc` | ParcelWILL status (UjhQfQ) | 6 branches, 5 mails + 3 alertes internes |
| Rassurance J+10 | `Ukv6cZ` | Fulfilled Order | J+10 si non livré |
| Panier abandonné | `WF5ZSe` | Added to Cart | 4h P1 (`RrCRXV`) → +20h P2 (`WWKh5Z`) ; filtres PO=0 & CS=0 ; réentrée 7 j |
| Checkout abandonné | `TvXLCA` | Checkout Started | 1h C1 (`SWvYiC`) → +23h C2 (`RQiDDZ`) → +24h C3 (`SphFXA`) ; PO=0 ; réentrée 7 j |
| Post-achat | `STxY4j` | Placed Order | J+2 PA1 (`WPCwxc`) → J+23 PA2 (`Ytp9pf`, si Delivered≥1) ; réentrée 30 j |
| Bienvenue | `Yq5983` | Liste Wgu7Z3 | B1 immédiat (`XizyxK`) → J+2 B2 (`RFZp2u`) → J+4 B3 (`RcP6Yu`) ; B2/B3 si PO=0 ; pas de réentrée |
| Navigation | `TT74d3` | Viewed Product | 20h N1 (`Rkb7yJ`) ; ATC=0 & CS=0 & PO=0 ; réentrée 7 j |
| Winback | `Xsx57Q` | Placed Order | J+60 W1 (`X95MPw`) → J+75 W2 (`VJnrVQ`) ; PO=0 depuis entrée |

Tous les envois marketing : smart sending ON, à 10h heure du profil pour les
délais en jours, UTM par flow (panier-abandonne / checkout-abandonne /
post-achat / bienvenue / navigation / winback / suivi-colis).
Templates clonés par Klaviyo dans chaque flow (IDs locaux ≠ IDs bibliothèque).

### 13 mails test envoyés (17h53, serraj146 + badr.saraj)
Panier×2 · Checkout×3 · Post-achat×2 · Bienvenue×3 · Navigation×1 · Winback×2,
remplis avec données réelles (polo Noir Espresso 3XL, checkout #hWNFji3...).

### Choix éditoriaux à savoir
- **Aucun code promo inventé** : pas de code bienvenue ni d'incitation
  checkout C3 — décision Badr en attente (voir tâches).
- Anciens Winback/Sunset (0 envoi) remplacés par un seul Winback J+60/J+75,
  W2 = demande de feedback + désabo assumé (sunset doux).
- Navigation absorbe Browse+Site abandonment (un seul mail, honnête,
  « on ne relance pas dix fois »).

---

## 🎨 V2 GARCIA + PLANCHE DE MARQUE + CODES PROMO (25/08 ~18h15)

### Décisions Badr
- Mails du flow 1 (Suivi) : validés « niquel ». **Transactional à cocher : il le fera plus tard.**
- Code bienvenue : **oui, 5%** → créé dans Shopify : **BIENVENUE5** (gid 2289516413302, tous produits, sans expiration, tous clients).
- Code dernier rappel checkout : **oui** → créé : **RETOUR10** (−10%, gid 2289516446070). Pourcentage choisi par moi, modifiable.
- Planche de marque reçue (PDF uploads/…Planche_Design___NIVA_V1_1.pdf) :
  **Noir #151515** (logo/texte/signature) · **Ivoire #FAF9F6** (fond site) ·
  **Beige sable #E8E1D4** (packaging, « doux chaleureux artisanal »).
  Demande : **alterner les fonds** (parfois beige).
- « Applique les méthodes Alex Garcia » + « inspire-toi du mail Blanc Ivoire :
  FOMO, gros chiffres » + demande d'un « code valable 10 min ».

### ⚠️ Faux compte à rebours refusé
« Code valable 10 minutes » avec un code permanent = pratique trompeuse.
Fait à la place : FOMO honnête (« envoyé une seule fois, il ne reviendra
pas ») + design v5 (gros −10% blanc sur bloc noir).
**Option proposée à Badr** : vrai code unique expirant par client = Klaviyo
→ Coupons → coupon dynamique lié à Shopify (à créer dans l'UI par Badr),
puis je remplace RETOUR10 par {% coupon_code %}. En attente de sa réponse.

### Apprentissage API
Les templates clonés dans un flow renvoient **404** sur update_email_template.
Méthode qui marche : créer un template v2 en bibliothèque →
`update_flow_action` (id numérique de l'action) avec le message complet
(subject, preview, template_id, additional_filters, links) → Klaviyo re-clone.
⚠️ Toujours renvoyer filters + links dans l'update sinon ils sautent.

### v2 en place (design alterné ivoire/beige + P.S. + preuve sociale « 1 000+ commandes »)
| Mail | Template v2 biblio | Fond | Ajouts |
|---|---|---|---|
| Bienvenue 1 | `R6i6nZ` | **beige** | lettre fondateur signée Badr, bloc noir −5% + BIENVENUE5, P.S., objet annonce le code |
| Bienvenue 2 | `WrFuKp` | ivoire | preuve sociale, P.S. code |
| Bienvenue 3 | `W9ZXA9` | **beige** | P.S. « dernière fois qu'on en parle » |
| Checkout 2 | `TgdfuQ` | **beige** | P.S. preuve sociale |
| Checkout 3 | `WpxJBq` | ivoire | **bloc noir −10% géant + RETOUR10**, objet « −10% pour trancher », P.S. |
| Panier 2 | `XnRyJF` | **beige** | P.S. « 7 jours » |
| Post-achat 1 | `X5hMqn` | **beige** | P.S. « jamais avant 20 jours » |
| Winback 1 | `YjV8FY` | **beige** | P.S. feedback |

Restent en v1 (ivoire, déjà bons, l'alternance tient) : Panier 1, Checkout 1,
Post-achat 2, Bienvenue —, Navigation 1, Winback 2, et tout le flow Suivi.
Alternance par séquence : P1 ivoire→P2 beige · C1 ivoire→C2 beige→C3 ivoire+noir ·
B1 beige→B2 ivoire→B3 beige · PA1 beige→PA2 ivoire · W1 beige→W2 ivoire.

### 7 nouveaux tests envoyés (18h13) — attente validation Badr.

---

## 🚀 BASCULE COMPLÈTE — 25/08/2026, fin de session

Tous les flows redesignés (v5, charte mail.pdf) sont **EN LIGNE**. Les anciens
flows sont **coupés**. Badr a validé : « vas y gooo, envoie le lot des mails
comme ça on lance les nouveaux flow et t'arrête le reste ».

### Flows LIVE (vérifié par API, 9 au total)

| Flow | ID | Statut |
|---|---|---|
| NIVA — Bienvenue (Badr v1) | `Yq5983` | live |
| NIVA — Panier abandonné (Badr v1) | `WF5ZSe` | live |
| NIVA — Checkout abandonné (Badr v1) | `TvXLCA` | live |
| NIVA — Post-achat (Badr v1) | `STxY4j` | live |
| NIVA — Navigation (Badr v1) | `TT74d3` | live |
| NIVA — Winback (Badr v1) | `Xsx57Q` | live |
| NIVA — Suivi de commande (Badr v1) | `TWLyAc` | live |
| NIVA — Rassurance (Badr v1) | `Ukv6cZ` | live — **délai passé à J+14** |
| Sunset - NIVA | `RMEGr6` | live — **ne pas toucher** (délivrabilité) |

### Anciens flows COUPÉS (passés en draft)

`T7JxZT` Welcome · `XhNtXV` Abandoned Cart · `SgnesH` Abandoned Checkout ·
`Yq9Gav` Post Purchase · `XZwTsk` Browse Abandonment · `UNaq2J` Site
Abandonment · `VPrHJj` Winback

### Les 18 templates v5

13 marketing + 5 Suivi. Signatures : **Mathieu Pavard — fondateur** sur les
mails de marque, **Camille Dubois — co-fondatrice** sur les mails service
(Post-achat 1 `X5hMqn` et Post-achat 2 `Ytp9pf`). Les 5 templates Suivi n'ont
volontairement aucune signature.

Délai de livraison partout : **6 à 8 jours ouvrés** (expédition sous 24 h).
Jamais 10-20 jours.

### Lot de test envoyé (serraj146@gmail.com)

Les 13 templates marketing ont été envoyés en preview avec contexte simulé
(panier et checkout rendus avec de vrais visuels produit).

### Limites API Klaviyo confirmées

- `update_flow` n'accepte que `status` — **renommer un flow se fait à la main
  dans l'UI**. Le flow Rassurance s'appelle encore « J+10 » alors que le délai
  est bien à 14 jours : à renommer.
- `update_flow_action` exige l'`id` **dans** l'objet `definition` **et** de
  renvoyer `links` à l'identique, sinon 400 « You cannot change the links ».
- `transactional: true` est ignoré par l'API : c'est une **revue Klaviyo**.
  Suivi 1 est approuvé, les 4 autres sont en attente.
- Pas d'endpoint `update_form` : la popup / roue se modifie uniquement dans l'UI.
- Astuce : passer `fields_template: ["id"]` sur les updates réduit la réponse
  de ~10 000 tokens à ~50.

### Reste à faire par Badr (UI uniquement)

1. Renommer « NIVA — Rassurance J+10 (Badr v1) » → « J+14 ».
2. Écrire les codes en clair sur les 3 écrans gagnants de la roue
   (`BIENVENUE5` / `BIENVENUE10` / `BIENVENUE15`) — le lot gagné n'est **pas**
   enregistré dans Klaviyo, les mails de bienvenue ne peuvent donc pas le citer.
3. Traduire en français les écrans « Cadeau offert » et « Success » + y mettre
   le logo.
4. Unifier la police de la popup (Poppins, ou Jost si dispo).
5. Couper les notifications d'expédition natives Shopify **le lendemain** de la
   confirmation que le flow Suivi tourne bien.
6. Remboursements : Fuzfa #2126 (89,99 €), Verhellen (59,98 €), #6410 et #5919
   à réception du retour.
7. Expédier #3601 Cardi et #2349 Bernard le 26/08 + envoyer les numéros de suivi.

---

## 🔴 DOSSIERS OUVERTS — À RAPPELER À BADR À CHAQUE SESSION

**RÈGLE (posée par Badr le 25/08/2026) :** ces dossiers doivent être
**rappelés à chaque échange**, sans qu'il ait à le demander. On ne retire une
ligne que lorsque **Badr dit explicitement « c'est traité »**. Pas avant, même
si le dossier a l'air résolu côté Shopify.

### A. Adresses — CORRIGÉES dans Shopify le 25/08, reste la réexpédition

Badr a ressaisi les 4 adresses le 25/08. Vérification faite : 2 étaient encore
fausses (le **premier chiffre du numéro de rue avait sauté** dans les deux cas).
Corrigées par API le 25/08, valeurs relues et confirmées :

| Cmd | Adresse finale dans Shopify | Tél. | État colis |
|---|---|---|---|
| **#3207** breton | 327 Chemin des Cancabeaux, 84210 Althen-des-Paluds | +33624603229 | ⚠️ à réexpédier |
| **#6323** langlet | 16 Rue Charles Cattelain, 59127 Walincourt-Selvigny | +33771623264 | ⚠️ **UNFULFILLED**, jamais partie |
| **#4610** DEPOORTERE | 21 Rue Montesquieu, 59115 Leers | +33660822855 | ⚠️ à réexpédier |
| **#5496** Pabois | 71 Route de saint-révérend, 85800 Le Fenouiller | +33617983834 | ⚠️ relance transporteur |

Erreurs qui avaient été rattrapées : #3207 saisie « 27 » au lieu de « 327 » ·
#6323 saisie « 6 » au lieu de « 16 » · #4610 le champ rue contenait le CP et la
ville en doublon (nettoyé).

**IL RESTE À FAIRE (Badr) : les 4 colis doivent être réexpédiés / relancés
auprès du transporteur. L'adresse corrigée ne fait rien partir toute seule.**
#3207 : commande du 04/07, 59,98 €. #6323 : 20/08, 79,98 €, jamais expédiée.
#4610 : 15/07, 59,98 €, premier colis retourné. #5496 : 02/08, 59,98 €.

### B. Adresse OK mais colis bloqué — relance transporteur à faire

| Cmd | Client | État |
|---|---|---|
| **#5496** | Maxime Pabois · pabois.maxime@orange.fr | Adresse corrigée ✅ (71 route de Saint-Révérend, 85800 Le Fenouiller · 0617983834) mais seul tracking = l'ancien colis bloqué du 03/08. Réexpédition à déclencher. |

### C. Relancés plusieurs fois, ZÉRO réponse (vérifié : aucun mail entrant)

| Cmd | Client | Manque | Relances |
|---|---|---|---|
| **#5455** | Berseth · guy.berse@gmail.com | n° de rue (« Route de Longirod ») | 3 — 08/08, 18/08, 20/08 |
| **#5842** | Ponseele · rita.ponseele@icloud.com | n° de rue (« Rue d'Hastière ») | 3 — 12/08, 18/08, 20/08 |
| **#6201** | Janssen · janssa2103@icloud.com | adresse + téléphone | 2 — 18/08, 20/08 |
| **#3161** | Williquet-Thone · gilbertwilliquet@skynet.be | adresse après échec de livraison | 1 — 21/08 |

Proposition en attente de validation Badr : dernier mail avec échéance
(« sans réponse sous 7 jours, remboursement et annulation »).

### D. Traités correctement — ne pas relancer

#6213 De Muynck (corrigée + expédiée 20/08) · #5915 Hublet (corrigée +
expédiée 14/08) · #5610 Barez (réexpédiée 17/08) · #5425 Mertens (en transit)
· #2349 Bernard (colis retrouvé, mail du 24/08).

### Vérification faite le 25/08

Scan des 50 dernières commandes (25/08) et de 50 commandes du début juillet :
**aucune autre adresse placeholder**. Ce n'est pas un bug de checkout qui
tourne en fond, c'est un défaut de suivi manuel. Volume : 50 commandes sur la
seule journée du 25/08.

---

## 📌 RÈGLES PERMANENTES — posées par Badr le 25/08/2026

### 1. Prévenir Badr dès qu'une donnée de commande change
Toute modification d'adresse, de téléphone ou de destinataire doit lui être
signalée **au moment où elle est faite**, avec l'ancienne et la nouvelle valeur.
Il ne doit jamais découvrir un changement après coup.

### 2. Une adresse corrigée dans Shopify ne fait RIEN partir
C'est la leçon la plus coûteuse de la session du 25/08 : quatre commandes
payées (≈ 260 €, la plus vieille du 04/07) étaient bloquées parce que le client
avait envoyé sa bonne adresse, qu'on la lui avait confirmée par mail… et que
personne n'avait ni saisi l'adresse ni relancé l'expédition.

**Donc, à chaque correction d'adresse, la sortie n'est pas « c'est corrigé »
mais « c'est corrigé + le sous-traitant a été relancé avec la nouvelle
adresse ».** Systématiquement rappeler à Badr que la réexpédition ou la relance
transporteur reste à faire, et lui proposer le mail au sous-traitant. Un dossier
n'est clos que quand le colis est reparti.

### 3. Toujours vérifier une ressaisie d'adresse
Ne jamais faire confiance à une adresse retapée à la main, y compris par Badr.
Relire la valeur en base et la comparer **caractère par caractère** à ce que le
client a écrit dans son mail.

Erreur observée deux fois sur quatre le 25/08 : **le premier chiffre du numéro
de rue disparaît** (327 → 27, 16 → 6). Probablement un copier-coller qui mange
le premier caractère. Vérifier ce chiffre en priorité.

### 4. Rappeler les dossiers ouverts à chaque session
Voir « DOSSIERS OUVERTS ». On les ressort **spontanément**, sans que Badr
demande. Une ligne ne disparaît que quand **Badr dit explicitement « c'est
traité »**, dossier par dossier — jamais parce que Shopify a l'air en ordre.

### 5. Ne jamais annoncer une vérification qu'on n'a pas faite
Toujours relire la valeur en base après écriture. Sur les API de cette stack, un
`200 OK` ne prouve rien : Klaviyo renvoie 200 en ignorant silencieusement
`transactional: true` et l'activation des alertes internes. Lire la réponse.

### Notes techniques apprises le 25/08

- **Shopify `orderUpdate`** : `shippingAddress` **écrase** l'adresse entière.
  Toujours renvoyer *tous* les champs (prénom, nom, rue, ville, CP, pays, tél.),
  sinon on efface ce qu'on n'a pas renvoyé.
- **Téléphones** : les passer en E.164 (`+33…`). Les transporteurs ignorent
  souvent un `06…` national, et c'est le téléphone qui débloque la plupart des
  tentatives de livraison ratées.
- **Notifications client Shopify** : absentes de l'Admin API, réglage 100 % UI.
- **Klaviyo** : `update_flow` n'accepte que `status` (renommage = UI) ·
  `update_flow_action` exige l'`id` dans `definition` **et** le renvoi de
  `links` à l'identique · pas d'endpoint `update_form`.

---

## 🔴 INCIDENT 26/08 — les flows envoyaient l'ANCIEN contenu (v2)

### Ce qui s'est passé

Les 8 flows activés le 25/08 au soir **ne pointaient pas sur les templates v5**.
Klaviyo **clone** un template au moment où on l'assigne à un mail de flow : le
flow garde sa propre copie, indépendante de la bibliothèque. Les flows avaient
été construits avec les templates **v2**, puis j'ai réécrit les templates v5
dans la bibliothèque — sans que les flows en voient quoi que ce soit.

Résultat : pendant ~9 h, les clients ont reçu la **v2** — sans les vraies photos
produit, sans la charte du PDF, sans le CTA en haut, avec l'ancienne signature
et l'ancien délai de livraison. Les 13 mails test validés par Badr ne
correspondaient à rien de ce qui partait réellement.

### Correspondance corrigée (26/08)

Chaque `send-email` a été réassigné sur le template v5 ; Klaviyo en a fait un
nouveau clone (colonne de droite), qui porte bien le contenu v5.

| Flow | v2 (avant) | v5 assigné | Clone créé |
|---|---|---|---|
| Bienvenue 1 | Xh3Niz | XdGh72 | VxdBtE |
| Bienvenue 2 | XKwkge | WrFuKp | SRSUin |
| Bienvenue 3 | TqDg7P | W9ZXA9 | XsSZwq |
| Panier 1 | Rdb6Zp | Rr36Pa | R85gYL |
| Panier 2 | WaBdCv | XnRyJF | Unq2Ca |
| Checkout 1 | UFnBws | SWvYiC | R64gQf |
| Checkout 2 | YkanHr | TgdfuQ | WKPWAK |
| Checkout 3 | Y7VBNR | XxnNqM | Yin554 |
| Post-achat 1 | Vfs9MJ | X5hMqn | UVp4VK |
| Post-achat 2 | SNUHGV | Ytp9pf | RD3j9Q |
| Navigation | RtE85V | Rkb7yJ | SQGqdE |
| Winback 1 | TQ9xRG | YjV8FY | WFMWhH |
| Winback 2 | XmTNLs | VJnrVQ | UDuhK4 |

**Le flow Suivi n'était pas touché** : il a été construit après les templates
finaux, il pointe directement sur V8bpu4 / XsZ5fL / Uqx6w3 / VviF4v / TCfxcC.

### ⚠️ Deuxième erreur commise pendant la réparation

Le premier `update_flow_action` (Navigation) a été envoyé **sans**
`additional_filters` → les 3 conditions d'envoi ont été **effacées**. Le mail
serait parti à des gens ayant déjà commandé. Détecté par relecture, restauré
dans la foulée.

**RÈGLE : `update_flow_action` écrase l'objet `message` en entier.** Comme
`shippingAddress` chez Shopify. Toujours renvoyer `additional_filters`,
`preview_text`, `smart_sending_enabled`, `transactional`, `id`, `name` — et
relire derrière. C'est la même leçon que le 25/08, commise une deuxième fois.

### Reste à trancher avec Badr

- Les objets des 3 mails Bienvenue annoncent « votre code **−5%** » alors que la
  roue donne 5, 10 ou 15 %. Le corps du mail dit « le code gagné sur la roue »
  (correct). L'objet est à réécrire sans pourcentage.
- Le template Rassurance (`RV4a5T`) s'appelle encore « J+10 » alors que le délai
  est passé à 14 jours. Vérifier que le corps ne cite pas « 10 jours ».

---

## 🆕 FLOW « 2e COULEUR » — EN LIGNE 26/08

Réponse au constat : **9,1 % de réachat sur 90 jours** (442 clients qui
reviennent sur 4 860) et un flow Post-achat qui fait **940 clics pour 15
commandes** — le trafic le plus chaud du compte, sans rien à vendre au bout.

| | |
|---|---|
| Flow | `WhfUr3` — NIVA — 2e couleur (Badr v1) — **live** |
| Template biblio | `SgEBCK` · clone du flow `TRNYhV` |
| Déclencheur | Placed Order (`Yrs33B`) |
| Délai | J+14, 10 h, fuseau du profil |
| Filtres | Delivered Shipment (`U9WCYK`) ≥ 1 depuis l'entrée **ET** Placed Order = 0 depuis l'entrée |
| Ré-entrée | 30 jours |

**Mécanique** — la taille est déjà validée, donc le seul frein (la coupe en
grande taille) est mort. On propose le même Polo Marceau dans un autre coloris.
Objet : « Votre taille est validée. Il reste six coloris. »
7 coloris réels : Noir Espresso · Blanc Ivoire · Gris Harbour · Bleu Coastal ·
Bleu Nuit · Vert Sage · Rouge Merlot. Grille de 3 photos portées au milieu.
Signé Camille Dubois. P.S. qui invite à signaler un problème de taille **avant**
de recommander.

**Aucune variable d'événement** dans le corps à part `first_name` : le payload
Placed Order n'a pas été vérifié, donc zéro dépendance = zéro merge tag cassé.

## 🔴 Autre correction 26/08 — le mail Rassurance disait « 10 à 20 jours »

Le template en ligne du flow Rassurance contenait encore :
« Le délai réel est de **10 à 20 jours** selon la destination », plus une
explication « petites séries / flux groupé ». C'est exactement ce que Badr avait
fait corriger le 25/08 — ça n'avait été corrigé que dans les autres mails.

Réécrit en v5 : expédition sous 24 h puis **6 à 8 jours ouvrés**, puis
« au-delà, le colis est bloqué quelque part » + ce qu'on fait (relance
transporteur, réexpédition sans demande) + engagement 30 jours.

| | |
|---|---|
| Nouveau template biblio | `RnG3SG` · clone du flow `UQTypK` |
| Action | `115538748`, renommée « Rassurance J+14 » |
| Filtre préservé | ParcelWILL `shipment_status` ≠ Delivered depuis l'entrée |

**RÈGLE : un template appartenant à un flow n'est PAS modifiable.**
`get_email_template` le lit, `update_email_template` renvoie **404 not found**.
Pour corriger le contenu d'un mail de flow : créer un nouveau template dans la
bibliothèque, puis le réassigner à l'action (Klaviyo le clonera).

## Objets Bienvenue corrigés

Les 3 mails annonçaient « votre code −5% » alors que la roue donne 5, 10 ou
15 %. Remplacé par « votre code » / « le code gagné sur la roue » / « votre code
de bienvenue ». Le corps était déjà correct.

---

## 🔴 GOOGLE ADS SUSPENDU — 24/08/2026

**Compte Ads `385-205-3256` (NIVA V2), suspendu le 24/08 à 13 h 45.**

Réponse du support Google (24/08 12 h 51, ticket **1-8849000040870**,
`ads-support@google.com`, adressée à « Adnane El boussaadani ») :

> « Cette suspension est la conséquence directe de graves cas de non-respect
> des règles constatés dans un ou plusieurs de vos comptes Google Merchant
> Center associés. Votre compte Google Ads ne pourra pas être rétabli tant que
> ces problèmes n'auront pas été résolus. »

| | |
|---|---|
| Merchant Center | NIVA V2 — ID `5842314990` |
| Motif | **Déclarations trompeuses ou déceptives** (misrepresentation) |
| Impact | **17 282 produits refusés** |
| Diffusion | Shopping, remarketing dynamique, fiches gratuites, Discovery/Demand Gen, vidéo — **tout coupé** |
| Pays | ~90 |

**Ce n'est pas le compte Ads qu'il faut débloquer, c'est le Merchant Center.**
Corriger d'abord, demander l'examen ensuite — un examen demandé avant
correction complète rallonge le délai.

### Chronologie

| Date | Événement |
|---|---|
| 22/08 15 h 36 | Demande d'association à un compte administrateur « Seif Google ads » (`compteagencegestion@gmail.com`) |
| 22/08 15 h 42-45 | Associations Shopify Google Channel App + Merchant |
| 22/08 16 h 02 | Code promotionnel Google Ads activé |
| 24/08 02 h 41 | Merchant Center : « your products cannot be displayed to customers » |
| 24/08 11 h 08 | Validation en deux étapes activée + n° de téléphone ajouté |
| 24/08 13 h 45 | **Suspension du compte Ads** |
| 24/08 14 h 03 | « Vous avez terminé la validation de l'annonceur » |
| 26/08 02 h 58 | Alerte Merchant Center : chute du nombre d'articles actifs |

### Pistes de correction (misrepresentation — non confirmées par Google)

Google ne dit jamais quel élément précis a déclenché. Les leviers habituels :
mentions légales complètes (raison sociale, SIRET, adresse physique), CGV et
politique de retour/remboursement faciles à trouver, page contact avec
téléphone, délais de livraison affichés **cohérents avec la réalité**, absence
de fausse urgence, et surtout **cohérence des prix barrés** — un prix de
référence jamais pratiqué est un déclencheur classique. À vérifier sur NIVA :
les variantes s'affichent à 79,99 € alors que les commandes se règlent autour
de 30 € l'unité.

## 4 mails adresse envoyés le 26/08

| Cmd | Client | Type | Montant |
|---|---|---|---|
| #6468 | Jossi · fjossi@omedia.ch · CH | 1re demande (rue = « Y ») | 121,80 € |
| #6521 | Detienne · freddo.detienne@skynet.be · BE | 1re demande (n° manquant) | 89,99 € |
| #5455 | Berseth · guy.berse@gmail.com · CH | **4e relance + échéance 02/09** | 60,89 € |
| #5842 | Ponseele · rita.ponseele@icloud.com · BE | **4e relance + échéance 02/09** | 89,99 € |

Total bloqué : **362,67 €**, les quatre en UNFULFILLED.

Jossi et Detienne n'avaient **jamais** été contactés. Tous deux ont un
téléphone au dossier (0041 79 606 10 07 / +32 499 14 70 40) — à appeler si pas
de réponse sous 48 h. Berseth et Ponseele n'ont **aucun** téléphone : c'est
pour ça qu'ils sont injoignables. Sans réponse au 02/09 → annulation +
remboursement intégral.

## 🔁 ALIGNEMENT « 5 À 8 JOURS OUVRÉS » — 26/08, exécuté et vérifié

Badr : « bah aligne tout et gere les pages de politique expédition punaise »
puis « 5-8 jours ouvrés hein ». Le chiffre de référence est donc **5 à 8 jours
ouvrés après expédition, expédition sous 24 h**, partout.

### Balayage exhaustif des 19 templates de flow

Les **19** templates rattachés aux flows live ont été lus un par un (pas de
sondage). Trois seulement portaient un délai chiffré :

| Template | Flow | Avant | Après |
|---|---|---|---|
| X5hMqn | Post-achat 1 | 6 à 8 | **5 à 8** |
| RnG3SG | Rassurance J+14 | 6 à 8 | **5 à 8** |
| Rkb7yJ | Navigation | 6 à 8 | **5 à 8** |

Les 16 autres ne chiffrent aucun délai (Bienvenue 1/2/3, Panier 1/2,
Checkout 1/2/3, Post-achat 2, Winback 1/2, 2e couleur, Suivi 1 à 5). Vérifié,
pas supposé.

### Rappel du piège de clonage (incident du 26/08)

Modifier le template de bibliothèque **ne change rien** au mail envoyé : le
flow sert sa propre copie. Il faut réassigner le template à l'action, ce qui
force Klaviyo à re-cloner. Nouveaux clones créés aujourd'hui :

| Action | Flow | Nouveau clone |
|---|---|---|
| 115540638 | Post-achat 1 | WGhaZB |
| 115538748 | Rassurance | WRirEW |
| 115540601 | Navigation | W38Ccu |
| 115540666 | Bienvenue 3 | ScK6af |
| 115540640 | Post-achat 2 | XzceBT |
| 115540678 | Winback 1 | UV43xj |

**Vérification faite en deux temps** : (1) relecture de chaque action pour
confirmer le `template_id` **et** la survie des `additional_filters` ;
(2) relecture du HTML des clones WGhaZB, WRirEW et W38Ccu — les trois portent
bien « 5 à 8 jours ouvrés ». Aucune condition d'envoi perdue.

### Correction annexe : nombre de coloris

Le Polo Marceau a **7 coloris** en base Shopify (Noir Espresso, Blanc Ivoire,
Gris Harbour, Bleu Coastal, Bleu Nuit, Vert Sage, Rouge Merlot). Trois mails
disaient « six » : Bienvenue 3 (W9ZXA9), Post-achat 2 (Ytp9pf), Winback 1
(YjV8FY). Corrigés en « sept » et réassignés. Le mail « 2e couleur » (TRNYhV)
était déjà juste (« Sept coloris » / « il reste six coloris » après le 1er achat).

### Shopify — ce qui est fait

- **Tarif de livraison au checkout** (`DeliveryMethodDefinition/1177858474358`) :
  « Livraison standard : expédition sous 24h, livraison en 5 à 8 jours ouvrés. »
- **Page Livraison & Retours** (`Page/711151124854`) : déjà en 5 à 8. Vérifiée.
- **Page Politique de remboursement** (`Page/704939098486`) : réécrite. Elle
  promettait encore « nous vous enverrons une étiquette d'expédition de retour »
  — contradiction directe avec la règle « frais de retour à la charge du client ».
  Supprimé. Ajout des frais à notre charge en cas de défaut/erreur.
- **Page Conditions d'utilisation** (`Page/704939622774`) : réécrite. Elle
  contenait 3 marqueurs `[LIEN]` non résolus et des blocs de balisage collés
  par erreur. Ajout : droit applicable français, garanties légales de conformité
  et vices cachés, lien ODR, délai 5 à 8 jours, garantie 30 jours.

### ⛔ Shopify — ce qui reste BLOQUÉ (action de Badr en admin)

Les **politiques de checkout** (Paramètres → Politiques) sont distinctes des
pages. L'API refuse : `write_legal_policies` non accordé. Elles sont encore
**en anglais brut Shopify** et c'est ce que voit un contrôleur Google :

| Politique | Problème |
|---|---|
| REFUND_POLICY | `[INSERT RETURN ADDRESS]` visible · « we'll send you a return shipping label » (faux) · e-mail **myniva@outlook.com** (obsolète) |
| TERMS_OF_SERVICE | `[NOTE TO MERCHANT: …]` visible · 4× `[LINK]` · myniva@outlook.com |
| SHIPPING_POLICY | **N'existe pas.** Aucune politique d'expédition au checkout |

C'est le point le plus visible qui reste sur le dossier Google. Les textes
français à coller sont dans l'artefact de conformité.


## ✅ ÉCHANGE DE TAILLE OFFERT — tranché par Badr le 26/08

Badr : « Bah l'échange offert donc tu peux l'écrire ».

La règle commerciale est donc à trois cas, et elle doit être formulée ainsi
partout — c'est l'écart entre les mails et le site qui posait problème, pas
l'engagement :

| Situation | Qui paie le renvoi |
|---|---|
| **Échange de taille** | **NIVA, dans les deux sens. C'est offert.** |
| Retour pour remboursement | Le client. Pas d'étiquette prépayée. |
| Article défectueux / erreur NIVA | NIVA, intégralement. |

Les mails disaient déjà « échange offert » : ils sont désormais alignés avec le
site, aucun changement Klaviyo nécessaire.

### Pages Shopify mises à jour (26/08)

- **Livraison & Retours** (`Page/711151124854`) : nouvelle section « Échange de
  taille — offert » en H2, et section « Qui paie le renvoi » qui nomme les trois
  cas.
- **Politique de remboursement** (`Page/704939098486`) : idem, avec l'échange
  placé avant la procédure de retour.

### Marche à suivre transmise à Badr pour les 3 règles de checkout

Paramètres → Règles (et non Boutique en ligne → Pages, qui est un autre objet) :
1. Politique de remboursement → tout remplacer par le texte français
2. Politique d'expédition → à créer, elle n'existe pas
3. Conditions d'utilisation → copier depuis `mynivashop.com/pages/terms-of-service`
4. Paramètres → Coordonnées de la boutique → téléphone +1 (315) 862-4976
   (c'est ce champ que Merchant Center lit, pas celui des pages)
5. Contrôle en navigation privée sur `/policies/refund-policy` et
   `/policies/shipping-policy`

