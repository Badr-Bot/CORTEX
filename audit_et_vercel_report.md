# CORTEX V1 — Audit & Rapport de Déploiement Vercel

**Date :** 14 Avril 2026  
**Agent :** Antigravity (Claude Sonnet 4.5 Thinking)  
**Statut final :** ✅ BUILD RÉUSSI — Prêt pour Vercel

---

## 🐛 Bugs Critiques Corrigés

### Bug #1 — Erreur ESM URL Scheme (CRITIQUE)
**Fichier :** `dashboard/postcss.config.mjs` → `dashboard/postcss.config.js`  
**Erreur :** `ERR_UNSUPPORTED_ESM_URL_SCHEME: Only URLs with a scheme in: file, data, and node are supported`  
**Cause :** Sur Windows, les chemins absolus commençant par `D:\` sont incompatibles avec le loader ESM de Node.js. Le fichier `.mjs` forçait l'importation ESM du plugin PostCSS, ce qui bloquait le traitement de `globals.css` lors du build.  
**Fix :** Conversion de `postcss.config.mjs` → `postcss.config.js` (CommonJS avec `module.exports`).

---

### Bug #2 — `supabaseUrl is required` lors du Pre-rendering (CRITIQUE)
**Fichier :** `dashboard/lib/supabase.ts`  
**Erreur :** `Error: supabaseUrl is required` lors de la collecte de données pour `/archive`, `/debrief`, `/`  
**Cause :** Le client Supabase était instancié au **niveau module** (à l'import du fichier). Lors du build Next.js, la phase de collecte de données statiques s'exécute sans les variables d'environnement disponibles.  
**Fix :** Remplacement par un **lazy singleton** — `getClient()` crée le client seulement à la première requête réelle.

---

### Bug #3 — Supabase Client dans la Route API (CRITIQUE)
**Fichier :** `dashboard/app/api/answer/route.ts`  
**Erreur :** Même problème que #2 — le client était créé au niveau module dans la route API.  
**Fix :** Déplacement de l'instanciation du client à l'intérieur du handler `POST()`.

---

### Bug #4 — Static Pre-rendering sur des pages dynamiques (CRITIQUE)
**Fichiers :** `app/page.tsx`, `app/archive/page.tsx`, `app/debrief/page.tsx`, `app/report/[date]/page.tsx`  
**Erreur :** Next.js tentait de pré-rendre les pages en statique au build, ce qui appelait les fonctions Supabase sans env vars.  
**Fix :** Ajout de `export const dynamic = 'force-dynamic'` sur toutes les pages SSR. Ces pages récupèrent des données en temps réel — elles ne doivent jamais être pre-rendues.

---

### Bug #5 — next.config.mjs → next.config.js (POTENTIEL)
**Fichier :** `dashboard/next.config.mjs` → `dashboard/next.config.js`  
**Cause :** Même risque ESM URL que pour PostCSS.  
**Fix :** Conversion CJS + suppression de `output: 'standalone'` qui est incompatible avec Vercel.

---

### Vulnérabilité #6 — Next.js 14.2.0 (CVE)
**Action :** Mise à jour de `next@14.2.0` → `next@14.2.29`  
**Note :** Une vulnérabilité subsiste selon npm audit (liée aux versions 14.x). La version 15.3.2+ est la correction complète, mais nécessite des adaptations breaking changes (params async). Pour l'instant, 14.2.29 est utilisé dans un contexte dashboard privé/interne.

---

## ✅ Résultat du Build

```
Route (app)                              Size     First Load JS
┌ ƒ /                                    1.56 kB        97.5 kB
├ ○ /_not-found                          873 B            88 kB
├ ƒ /api/answer                          0 B                0 B
├ ƒ /archive                             821 B          96.7 kB
├ ƒ /debrief                             805 B          96.7 kB
└ ƒ /report/[date]                       821 B          96.7 kB

ƒ (Dynamic) server-rendered on demand

Exit code: 0 ✅
```

Toutes les routes sont en mode **dynamique** (`ƒ`) — elles s'exécutent en SSR à chaque requête, avec les env vars disponibles.

---

## 🚀 Instructions de Déploiement Vercel

### Configuration du projet Vercel

1. **Root Directory :** `dashboard` (⚠️ IMPORTANT : pointer vers le sous-dossier)
2. **Framework :** Next.js (détecté automatiquement)
3. **Build Command :** `npm run build` (ou laisser le défaut Vercel)
4. **Install Command :** `npm install`

### Variables d'Environnement à Configurer dans Vercel

```env
NEXT_PUBLIC_SUPABASE_URL=https://dihmyscfeihwjmfsauoa.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...votre_clé_anon...
SUPABASE_SERVICE_KEY=eyJ...votre_clé_service...
```

> ⚠️ **Important :** `SUPABASE_SERVICE_KEY` (sans `NEXT_PUBLIC_`) est utilisée uniquement dans la route API server-side `/api/answer`. Elle ne doit JAMAIS être préfixée `NEXT_PUBLIC_` car elle serait exposée au client.

### Commandes Git pour pousser

```bash
cd "d:\Cortex V1\dashboard"
git add .
git commit -m "fix: build Vercel — PostCSS CJS, lazy Supabase client, force-dynamic SSR pages"
git push origin main
```

---

## 📋 Améliorations Identifiées (Non-Bloquantes)

| Priorité | Axe | Description |
|----------|-----|-------------|
| Haute | Sécurité | Migrer vers Next.js 15.3.2+ pour corriger la CVE définitivement |
| Moyenne | Perf | Réactiver `revalidate` avec ISR une fois les env vars configurées côté Vercel (pages archive + report + debrief peuvent être mises en cache) |
| Moyenne | UX | Ajouter un squelette de chargement (skeleton) pour les cartes SignalCard |
| Faible | DX | Ajouter `.env.local` avec les vraies valeurs pour les builds locaux |
| Faible | SEO | Ajouter des meta tags Open Graph sur chaque page |

---

## 📁 Fichiers Modifiés

| Fichier | Type de modification |
|---------|---------------------|
| `dashboard/postcss.config.mjs` | ❌ Supprimé (remplacé par `.js`) |
| `dashboard/postcss.config.js` | ✅ Créé (CJS) |
| `dashboard/next.config.mjs` | ❌ Supprimé (remplacé par `.js`) |
| `dashboard/next.config.js` | ✅ Créé (CJS, sans `standalone`) |
| `dashboard/lib/supabase.ts` | 🔧 Refactorisé (lazy singleton) |
| `dashboard/app/api/answer/route.ts` | 🔧 Fix (client dans handler) |
| `dashboard/app/page.tsx` | 🔧 `force-dynamic` |
| `dashboard/app/archive/page.tsx` | 🔧 `force-dynamic` |
| `dashboard/app/debrief/page.tsx` | 🔧 `force-dynamic` |
| `dashboard/app/report/[date]/page.tsx` | 🔧 `force-dynamic` |
| `memory.md` | ✅ Créé (référence future) |

---

*Rapport généré automatiquement par Antigravity — session du 14/04/2026*
