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
