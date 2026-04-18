-- ============================================================
-- CORTEX — Long-Term Memory Migration
-- Exécuter dans le SQL Editor de Supabase
-- ============================================================

-- 1. Activer l'extension pgvector (si pas déjà fait)
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- TABLE 1 : weekly_summaries
-- Une ligne par semaine × secteur (compression ~200 mots Gemini Pro)
-- ============================================================
CREATE TABLE IF NOT EXISTS weekly_summaries (
    id         BIGSERIAL    PRIMARY KEY,
    week_of    DATE         NOT NULL,        -- lundi de la semaine (ex: 2026-04-14)
    sector     TEXT         NOT NULL,        -- 'ai' | 'crypto' | 'market' | 'deeptech'
    summary    TEXT         NOT NULL,        -- texte compressé ~200 mots par Gemini Pro
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT weekly_summaries_week_sector_unique UNIQUE (week_of, sector)
);

-- Index pour les lectures par secteur (triées par date)
CREATE INDEX IF NOT EXISTS weekly_summaries_sector_week_idx
    ON weekly_summaries (sector, week_of DESC);


-- ============================================================
-- TABLE 2 : agent_patterns
-- Bibliothèque permanente de patterns de marché
-- Incrémentée chaque dimanche si un pattern se répète
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_patterns (
    id             BIGSERIAL    PRIMARY KEY,
    sector         TEXT         NOT NULL,        -- 'ai' | 'crypto' | 'market' | 'deeptech' | 'global'
    pattern        TEXT         NOT NULL,        -- description du pattern (max 120 chars)
    occurrences    INT          NOT NULL DEFAULT 1,
    first_seen     DATE         NOT NULL,        -- semaine de première détection
    last_confirmed DATE         NOT NULL,        -- semaine de dernière confirmation
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT agent_patterns_sector_pattern_unique UNIQUE (sector, pattern)
);

-- Index pour les lectures par secteur (triées par fréquence)
CREATE INDEX IF NOT EXISTS agent_patterns_sector_occ_idx
    ON agent_patterns (sector, occurrences DESC);


-- ============================================================
-- TABLE 3 : signal_embeddings
-- Vecteurs des signaux analysés chaque jour (768 dims)
-- Permet la recherche sémantique via pgvector
-- ============================================================
CREATE TABLE IF NOT EXISTS signal_embeddings (
    id          BIGSERIAL    PRIMARY KEY,
    report_date DATE         NOT NULL,        -- date de l'analyse (ex: 2026-04-18)
    sector      TEXT         NOT NULL,        -- 'ai' | 'crypto' | 'market' | 'deeptech'
    content     TEXT         NOT NULL,        -- texte qui a été vectorisé
    embedding   vector(768)  NOT NULL,        -- vecteur text-embedding-004 (768 dims)
    metadata    JSONB,                        -- direction, regime, signals_count, etc.
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT signal_embeddings_date_sector_unique UNIQUE (report_date, sector)
);

-- Index IVFFlat pour la recherche de similarité cosinus (rapide)
-- Note : IVFFlat recommandé pour < 1M vecteurs. Augmenter lists si > 100K lignes.
CREATE INDEX IF NOT EXISTS signal_embeddings_embedding_idx
    ON signal_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Index pour les lectures par secteur/date
CREATE INDEX IF NOT EXISTS signal_embeddings_sector_date_idx
    ON signal_embeddings (sector, report_date DESC);


-- ============================================================
-- FONCTION RPC : search_similar_signals
-- Recherche les N journées passées les plus similaires
-- Appelée depuis Python via supabase.rpc(...)
-- ============================================================
CREATE OR REPLACE FUNCTION search_similar_signals(
    query_embedding  vector(768),
    match_sector     TEXT,
    match_count      INT DEFAULT 3
)
RETURNS TABLE (
    report_date  DATE,
    content      TEXT,
    similarity   FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        se.report_date,
        se.content,
        1 - (se.embedding <=> query_embedding) AS similarity
    FROM signal_embeddings se
    WHERE se.sector = match_sector
    ORDER BY se.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- ============================================================
-- Vérification post-migration
-- ============================================================
SELECT
    'weekly_summaries'  AS table_name, COUNT(*) AS rows FROM weekly_summaries
UNION ALL
SELECT
    'agent_patterns',  COUNT(*) FROM agent_patterns
UNION ALL
SELECT
    'signal_embeddings', COUNT(*) FROM signal_embeddings;
