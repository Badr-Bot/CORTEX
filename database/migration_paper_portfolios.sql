-- ============================================================
-- CORTEX V3 — Migration : Paper Trading Portfolios
-- Appliquer dans Supabase SQL Editor
-- ============================================================

-- TABLE : paper_portfolios
-- Métadonnées de chaque portefeuille fictif
CREATE TABLE IF NOT EXISTS paper_portfolios (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
    -- 'PW1', 'PW2', 'PM1', 'PM2', 'PA1', 'PA2', ...
  portfolio_type TEXT NOT NULL,
    -- 'weekly' | 'monthly' | 'annual'
  horizon_days INTEGER NOT NULL,
    -- 7 | 30 | 365
  initial_value NUMERIC(10,2) NOT NULL DEFAULT 1000.00,
  current_value NUMERIC(10,2) NOT NULL DEFAULT 1000.00,
  start_date DATE NOT NULL DEFAULT CURRENT_DATE,
  end_date DATE NOT NULL,
  benchmark_start NUMERIC(10,4),
    -- valeur S&P 500 au démarrage (pour comparaison)
  benchmark_end NUMERIC(10,4),
    -- valeur S&P 500 à la clôture
  pnl_pct NUMERIC(6,2),
    -- % gain/perte total à clôture
  benchmark_pnl_pct NUMERIC(6,2),
    -- % gain S&P 500 sur même période
  beat_sp500 BOOLEAN,
    -- TRUE si CORTEX > S&P 500
  status TEXT NOT NULL DEFAULT 'active',
    -- 'active' | 'closed'
  rationale TEXT,
    -- raisonnement de CORTEX pour cette allocation
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_portfolios_type
  ON paper_portfolios (portfolio_type, start_date DESC);

CREATE INDEX IF NOT EXISTS idx_paper_portfolios_status
  ON paper_portfolios (status, end_date);

-- TABLE : paper_positions
-- Positions individuelles dans chaque portefeuille
CREATE TABLE IF NOT EXISTS paper_positions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  portfolio_id UUID NOT NULL REFERENCES paper_portfolios(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
    -- 'BTC', 'ETH', 'NVDA', 'SPY', etc.
  asset_type TEXT NOT NULL,
    -- 'crypto' | 'stock' | 'etf'
  direction TEXT NOT NULL DEFAULT 'LONG',
    -- 'LONG' (seul supporté en paper trading)
  allocation_pct NUMERIC(5,2) NOT NULL,
    -- % du portefeuille alloué (somme = 100%)
  allocation_usd NUMERIC(10,2) NOT NULL,
    -- montant en $ alloué
  entry_price NUMERIC(14,4),
    -- prix d'entrée
  current_price NUMERIC(14,4),
    -- dernier prix connu
  exit_price NUMERIC(14,4),
    -- prix de sortie (null si ouvert)
  quantity NUMERIC(14,6),
    -- quantité (shares ou BTC/ETH/etc.)
  pnl_usd NUMERIC(10,2) DEFAULT 0,
  pnl_pct NUMERIC(6,2) DEFAULT 0,
  conviction TEXT,
    -- 'forte' | 'moyenne' | 'faible'
  reasoning TEXT,
    -- pourquoi CORTEX a choisi ce ticker
  status TEXT NOT NULL DEFAULT 'open',
    -- 'open' | 'closed'
  opened_at TIMESTAMPTZ DEFAULT NOW(),
  closed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_positions_portfolio
  ON paper_positions (portfolio_id, status);

CREATE INDEX IF NOT EXISTS idx_paper_positions_ticker
  ON paper_positions (ticker, status);

-- TABLE : paper_snapshots
-- Valeur quotidienne du portefeuille (pour courbe d'évolution)
CREATE TABLE IF NOT EXISTS paper_snapshots (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  portfolio_id UUID NOT NULL REFERENCES paper_portfolios(id) ON DELETE CASCADE,
  snapshot_date DATE NOT NULL,
  portfolio_value NUMERIC(10,2) NOT NULL,
  sp500_value NUMERIC(10,4),
    -- valeur S&P 500 ce jour (pour courbe comparative)
  pnl_pct NUMERIC(6,2) DEFAULT 0,
    -- % gain depuis le départ
  sp500_pnl_pct NUMERIC(6,2) DEFAULT 0,
    -- % gain S&P 500 depuis le départ du portefeuille
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (portfolio_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_paper_snapshots_portfolio_date
  ON paper_snapshots (portfolio_id, snapshot_date DESC);
