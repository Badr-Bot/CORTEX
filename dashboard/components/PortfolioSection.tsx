"use client"

import { useState, useEffect, useMemo, useCallback } from "react"
import {
  POSITIONS,
  DCA_PHASE1,
  DCA_PHASE2_BONUS_EUR,
  EUR_TO_USD,
  PORTFOLIO_START_DATE,
  SCENARIOS,
  computeProjection,
  findMilestoneMonth,
  type Position,
  type Scenario,
} from "@/lib/portfolio-config"

// ── Types ─────────────────────────────────────────────────────────────────────

interface EnrichedPosition extends Position {
  currentPrice: number
  invested: number
  currentValue: number
  pnl: number
  pnlPct: number
  weight: number
}

interface Snapshot {
  snapshot_date: string
  total_value: number
  stocks_value: number
  crypto_value: number
  total_invested: number | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt$ = (v: number) =>
  v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })
const fmtSmall$ = (v: number) =>
  v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 })
const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`
const pnlColor = (v: number) =>
  v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400"
const TICKER_EMOJI: Record<string, string> = {
  NVDA: "🟢", GOOGL: "🔵", MSFT: "🔷", META: "🟣", PDD: "🟠",
  BTC: "🟡", ETH: "🔵", SOL: "🟣",
}

// Calcule le nombre de mois entre PORTFOLIO_START_DATE et une date
function monthsSinceStart(date: Date): number {
  const s = PORTFOLIO_START_DATE
  return (date.getFullYear() - s.getFullYear()) * 12 + (date.getMonth() - s.getMonth())
}

// ── Projection Chart ──────────────────────────────────────────────────────────

function ProjectionChart({
  currentValue,
  snapshots,
  activeScenarios,
}: {
  currentValue: number
  snapshots: Snapshot[]
  activeScenarios: Set<string>
}) {
  const TOTAL_MONTHS = 168 // 14 ans depuis start
  const now = new Date()
  const currentMonth = monthsSinceStart(now)

  // Trajectoire réelle : convertit les snapshots en points (mois depuis start, valeur)
  const realPoints = useMemo(() => {
    const pts: { m: number; v: number }[] = []
    // Point de départ initial (aujourd'hui si pas de snapshot)
    for (const s of snapshots) {
      const d = new Date(s.snapshot_date)
      const m = monthsSinceStart(d)
      if (m >= 0 && m <= TOTAL_MONTHS) {
        pts.push({ m, v: s.total_value })
      }
    }
    // Toujours ajouter le point courant
    if (!pts.find((p) => p.m === currentMonth)) {
      pts.push({ m: currentMonth, v: currentValue })
    }
    return pts.sort((a, b) => a.m - b.m)
  }, [snapshots, currentValue, currentMonth])

  // Projections par scénario — depuis la valeur actuelle
  const projections = useMemo(() => {
    const remainingMonths = TOTAL_MONTHS - currentMonth
    return SCENARIOS.map((s) => ({
      ...s,
      points: computeProjection(currentValue, s.annualRate, remainingMonths, currentMonth),
    }))
  }, [currentValue, currentMonth])

  // Échelle
  const W = 900, H = 420
  const PAD = { l: 80, r: 90, t: 32, b: 52 }
  const cW = W - PAD.l - PAD.r
  const cH = H - PAD.t - PAD.b

  const maxVal = Math.max(
    ...projections.filter((p) => activeScenarios.has(p.id)).flatMap((p) => p.points),
    currentValue * 1.2,
  ) * 1.05

  const xS = (m: number) => (m / TOTAL_MONTHS) * cW
  const yS = (v: number) => cH - Math.min((v / maxVal) * cH, cH)

  const toPath = (points: number[], startMonth: number) =>
    points
      .map((v, i) => `${i === 0 ? "M" : "L"} ${xS(startMonth + i).toFixed(1)} ${yS(v).toFixed(1)}`)
      .join(" ")

  const realPath = realPoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xS(p.m).toFixed(1)} ${yS(p.v).toFixed(1)}`)
    .join(" ")

  // Labels X — tous les 2 ans
  const xLabels = Array.from({ length: 8 }, (_, i) => ({
    m: i * 24,
    label: String(PORTFOLIO_START_DATE.getFullYear() + i * 2),
  }))

  // Y grid — milestones
  const milestones = [100_000, 250_000, 500_000, 1_000_000].filter((m) => m < maxVal * 0.98)

  // Phase 2 marker
  const phase2Month = 36

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" overflow="visible" style={{ minWidth: 480 }}>
        <defs>
          {SCENARIOS.map((s) => (
            <linearGradient key={s.id} id={`grad_${s.id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity="0.12" />
              <stop offset="100%" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        <g transform={`translate(${PAD.l},${PAD.t})`}>
          {/* Milestone horizontals */}
          {milestones.map((m) => (
            <g key={m}>
              <line x1={0} y1={yS(m)} x2={cW} y2={yS(m)}
                stroke="#f59e0b" strokeOpacity={0.18} strokeDasharray="4 4" strokeWidth={0.8} />
              <text x={-6} y={yS(m) + 4} textAnchor="end" fontSize={11} fill="#f59e0b" opacity={0.7}>
                {m >= 1_000_000 ? `$${m / 1_000_000}M` : `$${m / 1_000}K`}
              </text>
            </g>
          ))}

          {/* Phase 2 DCA marker */}
          {phase2Month <= TOTAL_MONTHS && (
            <>
              <line x1={xS(phase2Month)} y1={0} x2={xS(phase2Month)} y2={cH}
                stroke="#60a5fa" strokeOpacity={0.25} strokeDasharray="3 3" strokeWidth={1} />
              <text x={xS(phase2Month) + 4} y={14} fontSize={10} fill="#60a5fa" opacity={0.7}>
                +€830 DCA
              </text>
            </>
          )}

          {/* Today marker */}
          <line x1={xS(currentMonth)} y1={0} x2={xS(currentMonth)} y2={cH}
            stroke="#94a3b8" strokeOpacity={0.2} strokeWidth={1} />

          {/* Scenario fills + lines */}
          {projections.filter((p) => activeScenarios.has(p.id)).map((s) => (
            <g key={s.id}>
              <path
                d={`${toPath(s.points, currentMonth)} L ${xS(currentMonth + s.points.length - 1)} ${cH} L ${xS(currentMonth)} ${cH} Z`}
                fill={`url(#grad_${s.id})`}
              />
              <path
                d={toPath(s.points, currentMonth)}
                fill="none"
                stroke={s.color}
                strokeWidth={s.strokeWidth}
                strokeDasharray={s.dashed ? "5 4" : undefined}
                opacity={0.85}
              />
              {/* Label fin de courbe */}
              {(() => {
                const endM = currentMonth + s.points.length - 1
                const endV = s.points[s.points.length - 1]
                if (endM > TOTAL_MONTHS - 2) return null
                return (
                  <text
                    x={xS(endM) + 5}
                    y={yS(endV) - 5}
                    fontSize={11}
                    fill={s.color}
                    opacity={0.85}
                    fontWeight="600"
                  >
                    {fmt$(endV)}
                  </text>
                )
              })()}
            </g>
          ))}

          {/* Trajectoire réelle */}
          {realPoints.length > 0 && (
            <>
              <path d={realPath} fill="none" stroke="#fff" strokeWidth={3} opacity={0.95} />
              {realPoints.map((p, i) => (
                <circle key={i} cx={xS(p.m)} cy={yS(p.v)} r={4} fill="#fff" opacity={0.95} />
              ))}
              {/* Label dernier point réel */}
              <text
                x={xS(realPoints[realPoints.length - 1].m) + 6}
                y={yS(realPoints[realPoints.length - 1].v) - 8}
                fontSize={12}
                fill="#fff"
                fontWeight="700"
              >
                {fmt$(realPoints[realPoints.length - 1].v)} réel
              </text>
            </>
          )}

          {/* Milestone dots sur les scénarios actifs */}
          {[100_000, 500_000, 1_000_000].map((target) =>
            projections
              .filter((p) => activeScenarios.has(p.id))
              .map((s) => {
                const idx = findMilestoneMonth(s.points, target)
                if (idx === null) return null
                const absM = currentMonth + idx
                const v = s.points[idx]
                return (
                  <circle
                    key={`${s.id}_${target}`}
                    cx={xS(absM)}
                    cy={yS(v)}
                    r={4}
                    fill={s.color}
                    opacity={0.8}
                  />
                )
              })
          )}

          {/* X axis */}
          <line x1={0} y1={cH} x2={cW} y2={cH} stroke="#1e293b" strokeWidth={0.5} />
          {xLabels.map(({ m, label }) => (
            <text key={m} x={xS(m)} y={cH + 20} textAnchor="middle" fontSize={11} fill="#64748b">
              {label}
            </text>
          ))}
        </g>
      </svg>
    </div>
  )
}

// ── Zoom Chart (−12 mois / +12 mois) ─────────────────────────────────────────

function ZoomChart({
  currentValue,
  snapshots,
  activeScenarios,
}: {
  currentValue: number
  snapshots: Snapshot[]
  activeScenarios: Set<string>
}) {
  const now = new Date()
  const currentMonth = monthsSinceStart(now)
  const WINDOW_PAST = 12
  const WINDOW_FUTURE = 12
  const TOTAL_WINDOW = WINDOW_PAST + WINDOW_FUTURE
  const startM = Math.max(0, currentMonth - WINDOW_PAST)
  const endM = currentMonth + WINDOW_FUTURE

  // Trajectoire réelle dans la fenêtre
  const realPoints = useMemo(() => {
    const pts: { m: number; v: number }[] = []
    for (const s of snapshots) {
      const d = new Date(s.snapshot_date)
      const m = monthsSinceStart(d)
      if (m >= startM && m <= currentMonth) pts.push({ m, v: s.total_value })
    }
    if (!pts.find((p) => p.m === currentMonth)) pts.push({ m: currentMonth, v: currentValue })
    return pts.sort((a, b) => a.m - b.m)
  }, [snapshots, currentValue, currentMonth, startM])

  // Projections : seulement 12 mois depuis aujourd'hui
  const projections = useMemo(() =>
    SCENARIOS.map((s) => ({
      ...s,
      points: computeProjection(currentValue, s.annualRate, WINDOW_FUTURE, currentMonth),
    })), [currentValue, currentMonth])

  const W = 900, H = 360
  const PAD = { l: 80, r: 90, t: 28, b: 52 }
  const cW = W - PAD.l - PAD.r
  const cH = H - PAD.t - PAD.b

  // Min/max Y sur la fenêtre
  const allVals = [
    ...realPoints.map((p) => p.v),
    ...projections.filter((p) => activeScenarios.has(p.id)).flatMap((p) => p.points),
  ]
  const minVal = Math.max(0, Math.min(...allVals) * 0.92)
  const maxVal = Math.max(...allVals) * 1.08

  const xS = (m: number) => ((m - startM) / TOTAL_WINDOW) * cW
  const yS = (v: number) => cH - Math.min(((v - minVal) / (maxVal - minVal)) * cH, cH)

  const toPath = (points: number[], fromM: number) =>
    points
      .map((v, i) => `${i === 0 ? "M" : "L"} ${xS(fromM + i).toFixed(1)} ${yS(v).toFixed(1)}`)
      .join(" ")

  const realPath = realPoints
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xS(p.m).toFixed(1)} ${yS(p.v).toFixed(1)}`)
    .join(" ")

  // Labels X : tous les 2 mois
  const xLabels = Array.from({ length: TOTAL_WINDOW + 1 }, (_, i) => {
    const absM = startM + i
    const yr = PORTFOLIO_START_DATE.getFullYear() + Math.floor(absM / 12)
    const mo = (PORTFOLIO_START_DATE.getMonth() + absM) % 12
    const moLabel = ["jan","fév","mar","avr","mai","jun","jul","aoû","sep","oct","nov","déc"][mo]
    return { i, label: `${moLabel} ${String(yr).slice(2)}` }
  }).filter((_, i) => i % 2 === 0)

  // Y grid
  const range = maxVal - minVal
  const step = Math.pow(10, Math.floor(Math.log10(Math.max(range / 4, 1))))
  const gridLines: number[] = []
  for (let v = Math.ceil(minVal / step) * step; v <= maxVal; v += step) {
    gridLines.push(Math.round(v))
  }

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" overflow="visible" style={{ minWidth: 480 }}>
        <defs>
          {SCENARIOS.map((s) => (
            <linearGradient key={`z_${s.id}`} id={`zgrad_${s.id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity="0.22" />
              <stop offset="100%" stopColor={s.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>

        <g transform={`translate(${PAD.l},${PAD.t})`}>
          {/* Y grid */}
          {gridLines.map((v) => (
            <g key={v}>
              <line x1={0} y1={yS(v)} x2={cW} y2={yS(v)} stroke="#334155" strokeWidth={0.7} />
              <text x={-8} y={yS(v) + 4} textAnchor="end" fontSize={11} fill="#64748b">
                {v >= 1_000_000 ? `$${(v/1_000_000).toFixed(1)}M` : v >= 1000 ? `$${(v/1000).toFixed(0)}K` : `$${v}`}
              </text>
            </g>
          ))}

          {/* Today line */}
          <line x1={xS(currentMonth)} y1={0} x2={xS(currentMonth)} y2={cH}
            stroke="#94a3b8" strokeOpacity={0.4} strokeWidth={1.5} strokeDasharray="4 3" />
          <text x={xS(currentMonth) + 4} y={14} fontSize={10} fill="#94a3b8" opacity={0.8}>
            Aujourd'hui
          </text>

          {/* Scenario fills + lines */}
          {projections.filter((p) => activeScenarios.has(p.id)).map((s) => (
            <g key={s.id}>
              <path
                d={`${toPath(s.points, currentMonth)} L ${xS(currentMonth + s.points.length - 1)} ${cH} L ${xS(currentMonth)} ${cH} Z`}
                fill={`url(#zgrad_${s.id})`}
              />
              <path
                d={toPath(s.points, currentMonth)}
                fill="none"
                stroke={s.color}
                strokeWidth={s.strokeWidth + 0.5}
                strokeDasharray={s.dashed ? "6 4" : undefined}
                opacity={0.9}
              />
              {/* Label à droite */}
              {(() => {
                const endV = s.points[s.points.length - 1]
                const endM = currentMonth + s.points.length - 1
                return (
                  <text x={xS(endM) + 6} y={yS(endV) + 4} fontSize={11} fill={s.color} opacity={0.9} fontWeight="600">
                    {endV >= 1_000_000 ? `$${(endV/1_000_000).toFixed(2)}M` : `$${(endV/1000).toFixed(0)}K`}
                  </text>
                )
              })()}
            </g>
          ))}

          {/* Trajectoire réelle */}
          {realPoints.length > 0 && (
            <>
              <path d={realPath} fill="none" stroke="#fff" strokeWidth={3} opacity={0.95} />
              {realPoints.map((p, i) => (
                <circle key={i} cx={xS(p.m)} cy={yS(p.v)} r={4.5} fill="#fff" opacity={0.95} />
              ))}
              {/* Label dernier point */}
              <text
                x={xS(realPoints[realPoints.length - 1].m) + 6}
                y={yS(realPoints[realPoints.length - 1].v) - 9}
                fontSize={12}
                fill="#fff"
                fontWeight="700"
              >
                {realPoints[realPoints.length - 1].v >= 1000
                  ? `$${(realPoints[realPoints.length - 1].v / 1000).toFixed(0)}K réel`
                  : `$${realPoints[realPoints.length - 1].v} réel`}
              </text>
            </>
          )}

          {/* X axis */}
          <line x1={0} y1={cH} x2={cW} y2={cH} stroke="#1e293b" strokeWidth={0.5} />
          {xLabels.map(({ i, label }) => (
            <text key={i} x={xS(startM + i)} y={cH + 20} textAnchor="middle" fontSize={11} fill="#64748b">
              {label}
            </text>
          ))}
        </g>
      </svg>
    </div>
  )
}

// ── Milestone Table ───────────────────────────────────────────────────────────

function MilestoneTable({
  currentValue,
  activeScenarios,
}: {
  currentValue: number
  activeScenarios: Set<string>
}) {
  const currentMonth = monthsSinceStart(new Date())
  const remaining = 168 - currentMonth
  const targets = [100_000, 250_000, 500_000, 1_000_000]

  const projMap = useMemo(
    () =>
      Object.fromEntries(
        SCENARIOS.map((s) => [
          s.id,
          computeProjection(currentValue, s.annualRate, remaining, currentMonth),
        ])
      ),
    [currentValue, currentMonth, remaining]
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left text-slate-500 pb-2 pr-3 font-medium">Milestone</th>
            {SCENARIOS.filter((s) => activeScenarios.has(s.id)).map((s) => (
              <th key={s.id} className="text-center pb-2 px-2 font-medium" style={{ color: s.color }}>
                {s.label.split(" ").slice(1).join(" ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {targets.map((t) => (
            <tr key={t} className="border-b border-white/5">
              <td className="py-2 pr-3 text-amber-400 font-semibold">
                {t >= 1_000_000 ? `$${t / 1_000_000}M` : `$${t / 1_000}K`}
              </td>
              {SCENARIOS.filter((s) => activeScenarios.has(s.id)).map((s) => {
                const proj = projMap[s.id]
                if (!proj) return <td key={s.id} className="text-center py-2 px-2 text-slate-600">—</td>
                if (currentValue >= t)
                  return <td key={s.id} className="text-center py-2 px-2 text-emerald-400">✓ atteint</td>
                const idx = findMilestoneMonth(proj, t)
                if (idx === null)
                  return <td key={s.id} className="text-center py-2 px-2 text-slate-600">+14 ans</td>
                const absMonth = currentMonth + idx
                const yr = PORTFOLIO_START_DATE.getFullYear() + Math.floor(absMonth / 12)
                const mo = (PORTFOLIO_START_DATE.getMonth() + (absMonth % 12)) % 12
                const moLabel = ["jan","fév","mar","avr","mai","jun","jul","aoû","sep","oct","nov","déc"][mo]
                return (
                  <td key={s.id} className="text-center py-2 px-2" style={{ color: s.color }}>
                    {moLabel} {yr}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── CORTEX Speech ─────────────────────────────────────────────────────────────

function CortexSpeech({
  positions, totalValue, totalPnl, totalPnlPct, stocksValue, cryptoValue,
}: {
  positions: EnrichedPosition[]
  totalValue: number; totalPnl: number; totalPnlPct: number
  stocksValue: number; cryptoValue: number
}) {
  const best  = [...positions].sort((a, b) => b.pnlPct - a.pnlPct)[0]
  const worst = [...positions].sort((a, b) => a.pnlPct - b.pnlPct)[0]
  const proj_base_5y = computeProjection(totalValue, 0.12, 60, monthsSinceStart(new Date()))[60]
  const proj_ia_5y   = computeProjection(totalValue, 0.30, 60, monthsSinceStart(new Date()))[60]

  return (
    <div className="glass border border-white/10 rounded-xl p-5 space-y-3 text-sm leading-relaxed">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-glow" />
        <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-semibold">
          Analyse CORTEX — {new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}
        </span>
      </div>
      <p className="text-slate-300">
        Portefeuille à <span className="text-white font-semibold">{fmt$(totalValue)}</span> —
        performance globale{" "}
        <span className={`font-semibold ${pnlColor(totalPnl)}`}>{fmtPct(totalPnlPct)}</span>{" "}
        ({fmtSmall$(totalPnl)} de P&L). Tech{" "}
        <span className="text-blue-300">{((stocksValue / totalValue) * 100).toFixed(0)}%</span>,
        Crypto <span className="text-amber-300">{((cryptoValue / totalValue) * 100).toFixed(0)}%</span>.
      </p>
      <p className="text-slate-400">
        Leader : <span className="text-emerald-300 font-medium">{best?.name} ({fmtPct(best?.pnlPct ?? 0)})</span>.
        Point de vigilance :{" "}
        <span className="text-red-300 font-medium">{worst?.name} ({fmtPct(worst?.pnlPct ?? 0)})</span>.
        Long terme — ne rien vendre sauf signal CORTEX (VIX +20% ou BTC -10%).
      </p>
      <p className="text-slate-400">
        DCA $500/mois en cours. Dans 5 ans — scénario base (12%/an) :{" "}
        <span className="text-amber-300 font-semibold">{fmt$(proj_base_5y)}</span> ·
        scénario IA Bull (30%/an) :{" "}
        <span className="text-emerald-300 font-semibold">{fmt$(proj_ia_5y)}</span>.
        À partir d'avril 2029 : +€830/mois — accélération significative.
      </p>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function PortfolioSection() {
  const [prices, setPrices]               = useState<Record<string, number>>({})
  const [snapshots, setSnapshots]         = useState<Snapshot[]>([])
  const [loading, setLoading]             = useState(true)
  const [lastUpdate, setLastUpdate]       = useState("")
  const [activeScenarios, setActiveScenarios] = useState<Set<string>>(
    new Set(["recession", "base", "ia_bull", "supercycle"])
  )

  // Fetch prix live + historique en parallèle
  useEffect(() => {
    Promise.all([
      fetch("/api/portfolio").then((r) => r.json()),
      fetch("/api/portfolio/snapshot").then((r) => r.json()),
    ]).then(([priceData, histData]) => {
      setPrices(priceData.prices ?? {})
      setSnapshots(histData.snapshots ?? [])
      setLastUpdate(
        new Date(priceData.timestamp).toLocaleTimeString("fr-FR", {
          hour: "2-digit",
          minute: "2-digit",
        })
      )
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  // Enrichir les positions
  const enriched = useMemo<EnrichedPosition[]>(() => {
    const list = POSITIONS.map((p) => {
      const currentPrice = prices[p.ticker] ?? p.avgCost
      const invested = p.qty * p.avgCost
      const currentValue = p.qty * currentPrice
      const pnl = currentValue - invested
      const pnlPct = (pnl / invested) * 100
      return { ...p, currentPrice, invested, currentValue, pnl, pnlPct, weight: 0 }
    })
    const total = list.reduce((s, p) => s + p.currentValue, 0)
    return list.map((p) => ({ ...p, weight: total > 0 ? (p.currentValue / total) * 100 : 0 }))
  }, [prices])

  // Sauvegarder snapshot du jour (une fois les prix chargés)
  const saveSnapshot = useCallback(async (val: number, stocks: number, crypto: number, invested: number) => {
    try {
      await fetch("/api/portfolio/snapshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          total_value: Math.round(val * 100) / 100,
          stocks_value: Math.round(stocks * 100) / 100,
          crypto_value: Math.round(crypto * 100) / 100,
          total_invested: Math.round(invested * 100) / 100,
        }),
      })
    } catch {}
  }, [])

  const totalInvested = enriched.reduce((s, p) => s + p.invested, 0)
  const totalValue    = enriched.reduce((s, p) => s + p.currentValue, 0)
  const totalPnl      = totalValue - totalInvested
  const totalPnlPct   = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0
  const stocksValue   = enriched.filter((p) => p.type === "stock").reduce((s, p) => s + p.currentValue, 0)
  const cryptoValue   = enriched.filter((p) => p.type === "crypto").reduce((s, p) => s + p.currentValue, 0)

  // Sauvegarde snapshot une fois les données chargées
  useEffect(() => {
    if (!loading && totalValue > 0) {
      saveSnapshot(totalValue, stocksValue, cryptoValue, totalInvested)
    }
  }, [loading, totalValue])

  const stocks  = enriched.filter((p) => p.type === "stock")
  const cryptos = enriched.filter((p) => p.type === "crypto")

  const toggleScenario = (id: string) => {
    setActiveScenarios((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        if (next.size > 1) next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="space-y-6 animate-slide-up">

      {/* ── Header valeur totale ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-glow" />
              <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">
                Portefeuille Revolut · Suivi CORTEX
              </span>
            </div>
            <div className="flex items-baseline gap-3 mt-3">
              {loading ? (
                <div className="h-8 w-40 bg-white/10 rounded animate-pulse" />
              ) : (
                <span className="text-3xl font-bold text-white tracking-tight">{fmt$(totalValue)}</span>
              )}
              {!loading && (
                <span className={`text-lg font-semibold ${pnlColor(totalPnl)}`}>{fmtPct(totalPnlPct)}</span>
              )}
            </div>
            {!loading && (
              <div className={`text-sm mt-1 ${pnlColor(totalPnl)}`}>
                {totalPnl >= 0 ? "+" : ""}{fmtSmall$(totalPnl)} vs investi ({fmt$(totalInvested)})
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2 items-end text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Tech</span>
              <div className="bg-blue-500/20 border border-blue-500/30 text-blue-300 rounded-full px-3 py-1 font-semibold">
                {loading ? "…" : `${fmt$(stocksValue)} · ${((stocksValue / totalValue) * 100).toFixed(0)}%`}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Crypto</span>
              <div className="bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-full px-3 py-1 font-semibold">
                {loading ? "…" : `${fmt$(cryptoValue)} · ${((cryptoValue / totalValue) * 100).toFixed(0)}%`}
              </div>
            </div>
            {lastUpdate && (
              <span className="text-slate-600 font-mono text-[10px]">Prix live · {lastUpdate}</span>
            )}
          </div>
        </div>
        <div className="mt-4 h-2 rounded-full overflow-hidden bg-white/5 flex">
          {!loading && (
            <>
              <div className="bg-blue-500/60 h-full transition-all" style={{ width: `${(stocksValue / totalValue) * 100}%` }} />
              <div className="bg-amber-500/60 h-full transition-all" style={{ width: `${(cryptoValue / totalValue) * 100}%` }} />
            </>
          )}
        </div>
      </div>

      {/* ── CORTEX Speech ── */}
      {!loading && (
        <CortexSpeech
          positions={enriched}
          totalValue={totalValue} totalPnl={totalPnl} totalPnlPct={totalPnlPct}
          stocksValue={stocksValue} cryptoValue={cryptoValue}
        />
      )}

      {/* ── Positions ── */}
      {[
        { label: "📈 Actions", items: stocks, accent: "border-blue-500/30" },
        { label: "₿ Cryptos", items: cryptos, accent: "border-amber-500/30" },
      ].map(({ label, items, accent }) => (
        <div key={label} className={`glass border ${accent} rounded-xl overflow-hidden`}>
          <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-300">{label}</span>
            <span className="text-xs text-slate-500 font-mono">
              {loading ? "…" : fmt$(items.reduce((s, p) => s + p.currentValue, 0))}
            </span>
          </div>
          <div className="divide-y divide-white/5">
            {loading
              ? [1, 2, 3].map((i) => (
                  <div key={i} className="px-5 py-4 flex items-center gap-3">
                    <div className="h-4 w-16 bg-white/10 rounded animate-pulse" />
                    <div className="flex-1 h-4 bg-white/5 rounded animate-pulse" />
                  </div>
                ))
              : items.map((p) => (
                  <div key={p.ticker} className="px-5 py-3.5 flex items-center gap-3 hover:bg-white/[0.02] transition-colors">
                    <span className="text-base leading-none w-5">{TICKER_EMOJI[p.ticker] ?? "●"}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2">
                        <span className="text-white font-semibold text-sm">{p.ticker}</span>
                        <span className="text-slate-500 text-xs truncate">{p.name}</span>
                      </div>
                      <div className="text-slate-500 text-xs mt-0.5">
                        {p.qty} × {fmtSmall$(p.currentPrice)} · investi {fmt$(p.invested)}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-white font-semibold text-sm">{fmt$(p.currentValue)}</div>
                      <div className={`text-xs font-mono ${pnlColor(p.pnl)}`}>
                        {fmtPct(p.pnlPct)} ({p.pnl >= 0 ? "+" : ""}{fmtSmall$(p.pnl)})
                      </div>
                    </div>
                    <div className="hidden sm:flex flex-col items-end gap-1 w-14 shrink-0">
                      <span className="text-[10px] text-slate-600 font-mono">{p.weight.toFixed(1)}%</span>
                      <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${p.type === "stock" ? "bg-blue-400/60" : "bg-amber-400/60"}`}
                          style={{ width: `${Math.min(p.weight * 3, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </div>
      ))}

      {/* ── DCA Schedule ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span className="text-[10px] text-cyan-400 uppercase tracking-widest font-semibold">
            Plan DCA — Le 5 de chaque mois
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
          {DCA_PHASE1.map((d) => (
            <div key={d.ticker} className="bg-white/5 border border-white/10 rounded-lg p-3 text-center">
              <div className="text-white font-semibold">{d.ticker}</div>
              <div className="text-cyan-300 font-mono text-sm mt-0.5">${d.amountUsd}/mois</div>
            </div>
          ))}
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs">
          <div className="text-blue-300 font-semibold mb-1">Dès avril 2029 — Phase 2</div>
          <div className="text-slate-400">
            +€{DCA_PHASE2_BONUS_EUR}/mois ≈{" "}
            <span className="text-white font-medium">${(DCA_PHASE2_BONUS_EUR * EUR_TO_USD).toFixed(0)}</span>,
            même clé : NVDA 30% · GOOGL 30% · META 20% · BTC 20%
          </div>
          <div className="text-slate-500 mt-1">
            Total Phase 2 :{" "}
            <span className="text-white font-medium">
              ${(500 + DCA_PHASE2_BONUS_EUR * EUR_TO_USD).toFixed(0)}/mois
            </span>
          </div>
        </div>
      </div>

      {/* ── Chart Projection ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
            <span className="text-[10px] text-violet-400 uppercase tracking-widest font-semibold">
              Trajectoire · 14 ans
            </span>
          </div>
          {/* Legend réelle */}
          <div className="flex items-center gap-1.5 text-xs">
            <span className="w-5 h-0.5 bg-white rounded inline-block" />
            <span className="text-slate-400">Trajectoire réelle</span>
          </div>
        </div>

        {/* Scenario toggles */}
        <div className="flex flex-wrap gap-2 mb-5">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              onClick={() => toggleScenario(s.id)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-all font-medium ${
                activeScenarios.has(s.id)
                  ? "opacity-100"
                  : "opacity-30 grayscale"
              }`}
              style={{
                borderColor: s.color + "60",
                backgroundColor: s.color + "18",
                color: s.color,
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Scenario descriptions */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-5">
          {SCENARIOS.filter((s) => activeScenarios.has(s.id)).map((s) => (
            <div
              key={s.id}
              className="rounded-lg p-3 text-xs border"
              style={{ borderColor: s.color + "30", backgroundColor: s.color + "0c" }}
            >
              <div className="font-semibold mb-1" style={{ color: s.color }}>{s.label}</div>
              <div className="text-slate-500 text-[11px] leading-snug">{s.sublabel}</div>
              <div className="text-slate-600 text-[10px] mt-1 leading-snug">{s.description}</div>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="h-48 bg-white/5 rounded-lg animate-pulse" />
        ) : (
          <ProjectionChart
            currentValue={totalValue}
            snapshots={snapshots}
            activeScenarios={activeScenarios}
          />
        )}

        {/* Milestone table */}
        {!loading && (
          <div className="mt-5 border-t border-white/10 pt-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-3 font-medium">
              Quand atteins-tu ces milestones ?
            </div>
            <MilestoneTable currentValue={totalValue} activeScenarios={activeScenarios} />
          </div>
        )}
      </div>

      {/* ── Chart Zoom −12 / +12 mois ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span className="text-[10px] text-cyan-400 uppercase tracking-widest font-semibold">
            Zoom · −12 mois / +12 mois
          </span>
        </div>
        {loading ? (
          <div className="h-36 bg-white/5 rounded-lg animate-pulse" />
        ) : (
          <ZoomChart
            currentValue={totalValue}
            snapshots={snapshots}
            activeScenarios={activeScenarios}
          />
        )}
      </div>

    </div>
  )
}
