export interface Signal {
  title: string
  en_clair?: string
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

/** Une news de plus, expliquée en une phrase — le tour d'horizon de chaque onglet. */
export interface AutreNews {
  titre: string
  en_clair: string
  source_name: string
  source_url: string
}

/** Repo GitHub ou modèle IA qui monte, avec ce que Badr peut en faire. */
export interface TrendingRepo {
  nom: string
  type: "repo" | "modele" | "space"
  quoi: string
  pour_toi: string
  popularite?: string
  source_url: string
}

export type ToolCategory =
  | "video"
  | "produit_gagnant"
  | "analyse_marche"
  | "scraping"
  | "pub"
  | "fiches_produit"
  | "service_client"
  | "skill_claude"
  | "automatisation"

/** Un outil concret pour la boutique : repo, skill Claude, modèle, app. */
export interface EcomTool {
  nom: string
  categorie: ToolCategory
  quoi: string
  pour_toi: string
  comment_tester: string
  gratuit?: boolean
  source_name?: string
  source_url: string
}

/** Produit repéré par le radar TrendTrack, analysé en profondeur (docs/RADAR.md §6). */
export interface RadarProduit {
  produit: string
  boutique: string
  niche?: string
  prix?: string
  statut: "BANGER" | "EXPLOSE" | "SANS TRAFIC" | "A SURVEILLER"
  signal: string
  stade_marche: string
  notoriete: string
  ca_jour_estime: string
  difficulte: "facile" | "moyen" | "difficile"
  difficulte_pourquoi: string
  marche_fr: "LIBRE" | "PRIS" | "PARTIEL" | "A VERIFIER"
  marche_fr_detail?: string
  marches?: Record<string, "LIBRE" | "PRIS" | "PARTIEL" | "A VERIFIER">
  stade_sophistication?: number
  awareness?: "inconnu ici" | "déjà connu ici"
  angle_recommande?: string
  tam?: string
  angle_concurrent?: string
  pain_points?: { douleur: string; intensite: "forte" | "moyenne"; preuve: string; source_url: string }[]
  angles_non_exploites?: { angle: string; douleur_ciblee: string; pourquoi_personne: string }[]
  /** Chiffres TrendTrack réinjectés à la publication (jamais retapés). */
  chiffres?: {
    ads_actives?: number
    courbe_ads?: string
    acceleration?: number | null
    delta_ads_7j?: number | null
    age_jours?: number | null
    cree_le?: string
    semaines_diffusion?: number
    visites_mois?: number | null
    pays_pub?: string
    fr_dans_leurs_pubs?: string
    marches_libres?: string
    nb_skus?: number | null
    prix?: string
    prix_eur?: number | null
    statut?: string
    reseau?: string
  }
  ou_lancer?: string
  criteres_ok?: string[]
  criteres_ko?: string[]
  verdict: "GO TEST" | "A SURVEILLER" | "ECARTER"
  verdict_pourquoi: string
  budget_test: string
  lien_boutique: string
  lien_adlibrary?: string
}

/** Produit vérifié puis refusé par le radar (marché FR pris, ingérable…). */
export interface RadarEcarte {
  produit: string
  boutique: string
  raison: string
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

export type EcomTheme = "marketplace" | "automation" | "emailing" | "creatives" | "operations"

export interface EcomSignal extends Signal {
  theme?: EcomTheme
}

export interface EcomStock {
  nom: string
  ticker: string
  price: number
  change_pct: number
}

export interface EcomNouveaute {
  theme: EcomTheme
  titre: string
  quoi: string
  pourquoi: string
  source_name: string
  source_url: string
}

export interface EcommerceData {
  dashboard?: {
    stocks?: EcomStock[]
    secteur?: {
      pct_hausse: number
      moyenne_pct: number
      sentiment: string
      meilleur?: EcomStock
      pire?: EcomStock
    }
  }
  tendance_globale?: string
  outils?: EcomTool[]
  radar_produits?: RadarProduit[]
  radar_ecartes?: RadarEcarte[]
  nouveautes?: EcomNouveaute[]
  signals?: EcomSignal[]
  autres_news?: AutreNews[]
  actions_semaine?: string[]
  themes?: Record<string, number>
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
    trending_repos?: TrendingRepo[]
    autres_news?: AutreNews[]
  }
  crypto: {
    dashboard: CryptoDashboard
    phase: string
    direction: string
    magnitude: string
    bear_case: string
    score: Record<string, { value: number; note: string }>
    signals: Signal[]
    autres_news?: AutreNews[]
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
    autres_news?: AutreNews[]
  }
  deeptech: {
    signals: DeeptechSignal[]
    autres_news?: AutreNews[]
  }
  ecommerce?: EcommerceData
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
