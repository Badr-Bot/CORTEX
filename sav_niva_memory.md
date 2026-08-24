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

⚠️ **Point en attente de décision Badr (24/08/2026)** : AVANT cette règle,
un envoi automatique du 22/08 avait déjà proposé Option 1/Option 2 à
Jullien pour ce même dossier #5395, et il a déjà répondu qu'il choisissait
l'Option 1 (article gratuit + code -20%) et demande le renvoi de sa
commande d'origine. Rien n'a été envoyé depuis — décision à prendre :
honorer l'engagement déjà pris, ou revenir vers lui pour le rediriger vers
Colis Privé.

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
