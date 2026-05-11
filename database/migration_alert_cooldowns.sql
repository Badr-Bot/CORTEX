-- CORTEX — Migration : table alert_cooldowns
-- Stocke le cooldown des alertes (marché + news breaking)
-- Nécessaire pour GitHub Actions (pas de fichier local persistant)

CREATE TABLE IF NOT EXISTS alert_cooldowns (
    key        TEXT PRIMARY KEY,
    last_sent  TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now()
);
