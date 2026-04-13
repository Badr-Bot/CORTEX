-- ============================================================
-- CORTEX — Migration : table agent_learnings
-- Stocke les apprentissages hebdomadaires de CORTEX
-- À coller dans Supabase SQL Editor → Run
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_learnings (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    week_of       DATE        NOT NULL,
    sector        TEXT        NOT NULL,  -- 'ai' | 'crypto' | 'market' | 'deeptech' | 'global'
    learning      TEXT        NOT NULL,  -- ce que CORTEX a appris
    pattern       TEXT,                  -- pattern de pensée détecté chez Badr
    signal_title  TEXT,                  -- signal source du learning
    materialized  BOOLEAN,               -- la prédiction s'est-elle réalisée ?
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learnings_sector  ON agent_learnings (sector);
CREATE INDEX IF NOT EXISTS idx_learnings_week    ON agent_learnings (week_of);
CREATE INDEX IF NOT EXISTS idx_learnings_created ON agent_learnings (created_at DESC);

SELECT 'Table agent_learnings créée ✅' AS status;
