// ── Configuration statique du portefeuille de Badr ──────────────────────────
// Mettre à jour manuellement après chaque achat significatif

export const PORTFOLIO_START_DATE = new Date("2026-04-05") // Date début du suivi
export const EUR_TO_USD = 1.08

export interface Position {
  ticker: string
  name: string
  type: "stock" | "crypto"
  qty: number
  avgCost: number // prix moyen d'achat en USD
}

export const POSITIONS: Position[] = [
  // Actions (Brokerage)
  { ticker: "NVDA",  name: "NVIDIA",       type: "stock",  qty: 75.04,  avgCost: 199.89    },
  { ticker: "GOOGL", name: "Alphabet",     type: "stock",  qty: 38.49,  avgCost: 337.71    },
  { ticker: "MSFT",  name: "Microsoft",    type: "stock",  qty: 14.12,  avgCost: 424.71    },
  { ticker: "META",  name: "Meta",         type: "stock",  qty: 7.37,   avgCost: 678.37    },
  { ticker: "PDD",   name: "Pinduoduo",    type: "stock",  qty: 9.28,   avgCost: 107.83    },
  // Cryptos
  { ticker: "BTC",   name: "Bitcoin",      type: "crypto", qty: 0.16,   avgCost: 76766.70  },
  { ticker: "ETH",   name: "Ethereum",     type: "crypto", qty: 0.83,   avgCost: 2385.21   },
  { ticker: "SOL",   name: "Solana",       type: "crypto", qty: 11.065, avgCost: 90.01     },
]

// DCA mensuel actuel (le 5 de chaque mois)
export const DCA_PHASE1: { ticker: string; amountUsd: number }[] = [
  { ticker: "NVDA",  amountUsd: 150 },
  { ticker: "GOOGL", amountUsd: 150 },
  { ticker: "META",  amountUsd: 100 },
  { ticker: "BTC",   amountUsd: 100 },
]

// À partir d'avril 2029 : +€830/mois, même répartition %
export const DCA_PHASE2_START = new Date("2029-04-05")
export const DCA_PHASE2_BONUS_EUR = 830

export function computeDCAMonthly(date: Date): number {
  const phase1Total = DCA_PHASE1.reduce((s, d) => s + d.amountUsd, 0) // $500
  if (date < DCA_PHASE2_START) return phase1Total
  return phase1Total + DCA_PHASE2_BONUS_EUR * EUR_TO_USD
}

// Calcule la projection sur N mois à partir d'une valeur initiale
export function computeProjection(
  startValue: number,
  annualRate: number,
  totalMonths: number = 168
): number[] {
  const monthlyRate = Math.pow(1 + annualRate, 1 / 12) - 1
  const phase1Months = 36 // Apr 2026 → Mar 2029
  const dca1 = 500
  const dca2 = 500 + DCA_PHASE2_BONUS_EUR * EUR_TO_USD

  let val = startValue
  const results: number[] = [val]
  for (let m = 1; m <= totalMonths; m++) {
    const dca = m <= phase1Months ? dca1 : dca2
    val = val * (1 + monthlyRate) + dca
    results.push(Math.round(val))
  }
  return results
}

// Trouve le mois où on atteint un milestone
export function findMilestoneMonth(projection: number[], target: number): number | null {
  const idx = projection.findIndex((v) => v >= target)
  return idx === -1 ? null : idx
}
