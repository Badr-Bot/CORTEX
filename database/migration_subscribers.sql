-- ============================================================
-- CORTEX — Migration : table subscribers
-- À coller dans Supabase SQL Editor → Run
-- ============================================================

CREATE TABLE IF NOT EXISTS subscribers (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  chat_id       BIGINT      UNIQUE NOT NULL,
  username      TEXT,
  first_name    TEXT,
  subscribed_at TIMESTAMPTZ DEFAULT NOW(),
  approved      BOOLEAN     DEFAULT false,
  approved_at   TIMESTAMPTZ,
  approved_by   BIGINT
);

-- Index pour les requêtes par chat_id et statut
CREATE INDEX IF NOT EXISTS idx_subscribers_chat_id ON subscribers (chat_id);
CREATE INDEX IF NOT EXISTS idx_subscribers_approved ON subscribers (approved);

-- Vérification
SELECT 'Table subscribers créée ✅' AS status;
