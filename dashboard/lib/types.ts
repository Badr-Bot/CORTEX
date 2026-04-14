export interface Signal {
  title: string
  fait: string
  implication_2: string
  implication_3: string
  these_opposee?: string
  action: string
  sizing: "Fort" | "Moyen" | "Faible"
  invalide_si: string
  conviction: number
  source_name: string
  source_url: string
}

export interface DeeptechSignal extends Signal {
  horizon: "1-2" | "3-5" | "5-10" | "10+"
  credibilite_score: number
  peer_reviewed: boolean
  financement: boolean
  prototype: boolean
  adoption: boolean
  investissement_cotes?: string[]
  investissement_etf?: string[]
  investissement_early?: string[]
}

export interface CryptoDashboard {
  btc_price?: number
  btc_change_24h?: number
  fear_greed_score?: string
  fear_greed_label?: string
  btc_dominance?: string
  funding_description?: string
  open_interest_btc?: number
  long_short_ratio?: number
}

export interface MarketDashboard {
  sp500?: { price: string; change_pct: number }
  nasdaq?: { price: string; change_pct: number }
  gold?: { price: string; change_pct: number }
  oil?: { price: string; change_pct: number }
  dxy?: { price: string; change_pct: number }
  vix?: { price: string; interpretation: string }
  us_10y?: { price: string; change_bps: string }
}

export interface HotStock {
  ticker: string
  name: string
  change_1d: number
  change_5d: number
  reason: string
}

export interface ReportJSON {
  ai: {
    signals: Signal[]
    watchlist: string[]
  }
  crypto: {
    dashboard: CryptoDashboard
    phase: string
    direction: string
    magnitude: string
    bear_case: string
    score: Record<string, { value: number; note: string }>
    signals: Signal[]
  }
  market: {
    dashboard: MarketDashboard
    recession_score: number
    recession_indicators: Record<string, { status: string; note: string }>
    regime: string
    regime_justification: string
    signals: Signal[]
    hot_stocks: HotStock[]
    crash?: { crash_score: number; color: string; interpretation: string; factors: unknown[] }
  }
  deeptech: {
    signals: DeeptechSignal[]
  }
  nexus: {
    has_connexion: boolean
    connexion: string
    secteurs_lies: string[]
    question: string
  }
}

export interface DailyReport {
  id: string
  sent_at: string
  report_date: string
  signals_count: number
  question: string
  report_json: ReportJSON
}

export interface JournalEntry {
  id: string
  date: string
  question_asked: string
  your_response: string | null
  claude_comment: string | null
  created_at: string
}

export interface WeeklyDebrief {
  id: string
  week_of: string
  evaluation_json: {
    score: { correct: number; partiel: number; incorrect: number; total: number; taux_reussite: number }
    evaluations: Array<{
      date: string
      question: string
      reponse_badr: string
      verdict: "correct" | "partiel" | "incorrect"
      reponse_correcte: string
      pourquoi: string
      learning: string
    }>
    patterns: string[]
    signal_manque: string
    meilleur_coup: string
    learnings_cles: string[]
    focus_semaine: string
  }
  taux_reussite: number
  focus_semaine: string
  created_at: string
}
