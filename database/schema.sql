-- ============================================================
-- CORTEX — Schéma de base de données Supabase
-- Créé pour le système multi-agents de surveillance sectorielle
-- ============================================================

-- Extension vectorielle pour la déduplication sémantique
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE : signals
-- Signaux collectés par les agents SCOUTs
-- ============================================================
CREATE TABLE IF NOT EXISTS signals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  sector TEXT NOT NULL,
    -- 'ai' | 'crypto' | 'market' | 'deeptech'
  source_url TEXT,
  source_name TEXT,
  title TEXT NOT NULL,
  raw_content TEXT,
  stars_count INTEGER DEFAULT 0,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  category TEXT DEFAULT 'weak',
    -- 'weak' | 'viral' | 'emerging'
  embedding vector(1536),
    -- pour la déduplication sémantique
  metadata JSONB DEFAULT '{}'
);

-- ============================================================
-- TABLE : analyses
-- Analyses produites par l'agent SHERLOCK
-- ============================================================
CREATE TABLE IF NOT EXISTS analyses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  signal_id UUID REFERENCES signals(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  full_analysis TEXT,
  score_precocity FLOAT DEFAULT 0,
  score_impact FLOAT DEFAULT 0,
  score_actionability FLOAT DEFAULT 0,
  score_confidence FLOAT DEFAULT 0,
  score_total FLOAT DEFAULT 0,
  key_themes TEXT[],
  action_items TEXT[]
);

-- ============================================================
-- TABLE : daily_reports
-- Rapports envoyés chaque matin par Telegram
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  signals_count INTEGER DEFAULT 0,
  report_content TEXT,
  telegram_message_id TEXT,
  sectors_covered TEXT[]
);

-- ============================================================
-- TABLE : journal
-- Journal personnel Badr — jamais supprimé
-- ============================================================
CREATE TABLE IF NOT EXISTS journal (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  date DATE DEFAULT CURRENT_DATE,
  question_asked TEXT,
  your_response TEXT,
  claude_comment TEXT,
  response_received_at TIMESTAMPTZ,
  mood_signal TEXT,
    -- 'action' | 'observation' | 'doubt' | 'conviction'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : signal_tracking
-- Suivi de l'évolution des signaux dans le temps
-- ============================================================
CREATE TABLE IF NOT EXISTS signal_tracking (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  signal_id UUID REFERENCES signals(id),
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  stars_count INTEGER DEFAULT 0,
  mentions_count INTEGER DEFAULT 0,
  went_viral_at TIMESTAMPTZ,
    -- null jusqu'au jour où ça explose
  viral_threshold_reached INTEGER
    -- nb de stars au moment où c'est devenu viral
);

-- ============================================================
-- TABLE : summaries
-- Synthèses compressées après 30 jours
-- ============================================================
CREATE TABLE IF NOT EXISTS summaries (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  period_start DATE,
  period_end DATE,
  period_type TEXT,
    -- 'weekly' | 'monthly'
  top_signals JSONB DEFAULT '[]',
  key_themes TEXT[],
  your_patterns TEXT,
  claude_assessment TEXT,
    -- analyse honnête de tes patterns de pensée
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : daily_analyses
-- Analyses CORTEX quotidiennes par secteur (mémoire court-terme 7j)
-- Permet à Claude d'éviter les répétitions et détecter les tendances
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_analyses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  report_date DATE NOT NULL,
  sector TEXT NOT NULL,
    -- 'ai' | 'crypto' | 'market' | 'deeptech' | 'nexus'
  analysis_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (report_date, sector)
);

-- Index pour accélération des lectures par secteur + date
CREATE INDEX IF NOT EXISTS idx_daily_analyses_sector_date
  ON daily_analyses (sector, report_date DESC);

-- ============================================================
-- TABLE : subscribers
-- Abonnés Telegram approuvés par Badr
-- ============================================================
CREATE TABLE IF NOT EXISTS subscribers (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  chat_id BIGINT UNIQUE NOT NULL,
  username TEXT,
  first_name TEXT,
  subscribed_at TIMESTAMPTZ DEFAULT NOW(),
  approved BOOLEAN DEFAULT false,
  approved_at TIMESTAMPTZ,
  approved_by BIGINT
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  snapshot_date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
  total_value   NUMERIC(14,2) NOT NULL,
  stocks_value  NUMERIC(14,2) NOT NULL,
  crypto_value  NUMERIC(14,2) NOT NULL,
  total_invested NUMERIC(14,2),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RÈGLES DE RÉTENTION DES DONNÉES :
-- signals + analyses : 30 jours complets
-- 30-90 jours : compression hebdomadaire
-- > 90 jours : archive mensuelle
-- journal : JAMAIS supprimé ni compressé
-- ============================================================
