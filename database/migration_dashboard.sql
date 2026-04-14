-- ============================================================
-- CORTEX — Migration Dashboard v4
-- Nouvelles colonnes + tables pour le dashboard Vercel
-- À coller dans Supabase SQL Editor → Run
-- ============================================================

-- 1. Enrichir daily_reports pour le dashboard
ALTER TABLE daily_reports
  ADD COLUMN IF NOT EXISTS report_date  DATE         DEFAULT CURRENT_DATE,
  ADD COLUMN IF NOT EXISTS question     TEXT,
  ADD COLUMN IF NOT EXISTS report_json  JSONB        DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_daily_reports_date
  ON daily_reports (report_date DESC);

-- 2. Table weekly_debrief — bilans du dimanche
CREATE TABLE IF NOT EXISTS weekly_debrief (
  id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  week_of         DATE        NOT NULL,
  evaluation_json JSONB       NOT NULL DEFAULT '{}',
  message_html    TEXT,
  score_total     INTEGER     DEFAULT 0,
  taux_reussite   INTEGER     DEFAULT 0,
  focus_semaine   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (week_of)
);

CREATE INDEX IF NOT EXISTS idx_weekly_debrief_week
  ON weekly_debrief (week_of DESC);

SELECT 'Migration dashboard v4 OK ✅' AS status;
