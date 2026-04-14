# CORTEX V1 — Mémoire du Projet

## Architecture Générale

CORTEX V1 est un système de veille quotidienne IA composé de :
- **Backend Python** (Railway) : agents d'analyse, bot Telegram, scheduler
- **Dashboard Next.js** (Vercel) : interface web de consultation des rapports

## Stack Technique

### Backend (root + agents/ + tgbot/ + database/ + utils/)
- Python 3.x
- Anthropic Claude (via ANTHROPIC_API_KEY)
- Groq (via GROQ_API_KEY)
- Supabase (base de données)
- Telegram Bot (via python-telegram-bot)
- Railway pour le déploiement

### Dashboard (dashboard/)
- Next.js 14.2.29 (App Router)
- TypeScript
- Tailwind CSS 3.4.x
- Supabase JS Client @supabase/supabase-js ^2.39.0
- Déployé sur Vercel

## Base de Données Supabase

Tables principales (voir database/schema.sql) :
- `daily_reports` : rapports quotidiens (report_json, report_date, signals_count, question, sent_at)
- `journal` : réponses utilisateur aux questions du matin
- `weekly_debrief` : débrief hebdomadaire évalué par Claude

## Variables d'Environnement

### Backend (Railway)
- TELEGRAM_BOT_TOKEN
- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- ANTHROPIC_API_KEY
- GROQ_API_KEY
- TELEGRAM_CHAT_ID

### Dashboard (Vercel)
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- SUPABASE_SERVICE_KEY (pour la route /api/answer — accès service)

## Patterns Importants

### Supabase Client dans le Dashboard
Le client Supabase doit être instancié dans un **lazy singleton** (lib/supabase.ts) —
jamais au niveau module. Cela évite l'erreur "supabaseUrl is required" lors du 
pre-rendering statique de Next.js au build.

Toutes les pages SSR qui requêtent Supabase doivent avoir :
```typescript
export const dynamic = 'force-dynamic'
```

### Route API /api/answer
Le client Supabase est instancié DANS le handler POST (pas au niveau module).
Utilise SUPABASE_SERVICE_KEY (pas la clé anon) pour bypasser le Row Level Security.

## Pages du Dashboard

| Route | Description | Données |
|-------|-------------|---------|
| `/` | Dashboard principal, rapport du jour, tabs IA/Crypto/Marchés/DeepTech/Nexus | daily_reports + journal |
| `/archive` | Historique des 60 derniers rapports | daily_reports |
| `/report/[date]` | Vue complète d'un rapport archivé | daily_reports |
| `/debrief` | Débrief hebdomadaire avec score | weekly_debrief + journal |
| `/api/answer` | POST — sauvegarde la réponse quotidienne | journal |

## Configuration Vercel
- Root Directory: `dashboard/`
- Build Command: `npm run build`
- Framework: Next.js (détecté automatiquement)
- vercel.json à la racine de `dashboard/`
