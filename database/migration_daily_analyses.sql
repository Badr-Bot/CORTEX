-- ============================================================
-- CORTEX — Migration : daily_analyses + trading_decisions
-- Appliquer dans Supabase SQL Editor
-- ============================================================

-- TABLE : daily_analyses
-- Analyses CORTEX quotidiennes par secteur (mémoire court-terme 7j)
CREATE TABLE IF NOT EXISTS daily_analyses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  report_date DATE NOT NULL,
  sector TEXT NOT NULL,
    -- 'ai' | 'crypto' | 'market' | 'deeptech' | 'nexus'
  analysis_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (report_date, sector)
);

CREATE INDEX IF NOT EXISTS idx_daily_analyses_sector_date
  ON daily_analyses (sector, report_date DESC);

-- TABLE : trading_decisions
-- Décisions de trading générées par CORTEX (1 par secteur par jour)
CREATE TABLE IF NOT EXISTS trading_decisions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  decision_date DATE NOT NULL DEFAULT CURRENT_DATE,
  sector TEXT NOT NULL,
    -- 'ai' | 'crypto' | 'market'
  ticker TEXT NOT NULL,
  direction TEXT NOT NULL,
    -- 'LONG' | 'WATCH'
  horizon TEXT,
    -- '1W' | '2W' | '1M' etc.
  conviction_pct INTEGER,
    -- 0-100
  reasoning TEXT,
  outcome TEXT,
    -- NULL (ouvert) | 'WIN' | 'LOSS' | 'NEUTRAL'
  outcome_date DATE,
  pnl_pct FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_decisions_date
  ON trading_decisions (decision_date DESC);

CREATE INDEX IF NOT EXISTS idx_trading_decisions_sector
  ON trading_decisions (sector, decision_date DESC);
