"use client"

import { useState, useEffect, useMemo } from "react"
import {
  POSITIONS,
  DCA_PHASE1,
  DCA_PHASE2_START,
  DCA_PHASE2_BONUS_EUR,
  EUR_TO_USD,
  PORTFOLIO_START_DATE,
  computeProjection,
  findMilestoneMonth,
  type Position,
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

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt$ = (v: number) =>
  v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 })

const fmtSmall$ = (v: number) =>
  v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 })

const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`

const pnlColor = (v: number) => (v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400")

const TICKER_EMOJI: Record<string, string> = {
  NVDA: "🟢", GOOGL: "🔵", MSFT: "🔷", META: "🟣", PDD: "🟠",
  BTC: "🟡", ETH: "🔵", SOL: "🟣",
}

// ── Projection Chart (SVG) ────────────────────────────────────────────────────

function ProjectionChart({ startValue }: { startValue: number }) {
  const MONTHS = 168 // 14 ans
  const proj10 = useMemo(() => computeProjection(startValue, 0.10, MONTHS), [startValue])
  const proj20 = useMemo(() => computeProjection(startValue, 0.20, MONTHS), [startValue])

  const milestones = [100_000, 250_000, 500_000, 1_000_000]
  const W = 760, H = 300
  const PAD = { l: 70, r: 20, t: 20, b: 40 }
  const chartW = W - PAD.l - PAD.r
  const chartH = H - PAD.t - PAD.b

  const maxVal = Math.max(...proj20) * 1.05
  const xScale = (m: number) => (m / MONTHS) * chartW
  const yScale = (v: number) => chartH - (v / maxVal) * chartH

  const toPath = (data: number[]) =>
    data.map((v, i) => `${i === 0 ? "M" : "L"} ${xScale(i).toFixed(1)} ${yScale(v).toFixed(1)}`).join(" ")

  // Labels X : tous les 2 ans
  const xLabels: { m: number; label: string }[] = []
  for (let y = 0; y <= 14; y += 2) {
    xLabels.push({ m: y * 12, label: String(2026 + y) })
  }

  // Milestone 10%
  const m10_100k = findMilestoneMonth(proj10, 100_000)
  const m10_1M   = findMilestoneMonth(proj10, 1_000_000)
  const m20_1M   = findMilestoneMonth(proj20, 1_000_000)

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 flex-wrap text-xs">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-emerald-400 inline-block rounded" />
          <span className="text-slate-400">+10%/an</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-violet-400 inline-block rounded" />
          <span className="text-slate-400">+20%/an</span>
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-amber-400 border-dashed inline-block rounded" />
          <span className="text-slate-400">Milestones</span>
        </span>
        <span className="ml-auto text-slate-600 font-mono">DCA +€830 dès avr. 2029</span>
      </div>

      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: 320 }}>
          <defs>
            <linearGradient id="g10" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="g20" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#a78bfa" stopOpacity="0" />
            </linearGradient>
          </defs>

          <g transform={`translate(${PAD.l},${PAD.t})`}>
            {/* Grid lines */}
            {milestones.map((m) => (
              <g key={m}>
                <line
                  x1={0} y1={yScale(m)} x2={chartW} y2={yScale(m)}
                  stroke="#f59e0b" strokeOpacity="0.2" strokeDasharray="4 4" strokeWidth={0.8}
                />
                <text x={-6} y={yScale(m) + 4} textAnchor="end" fontSize={9} fill="#f59e0b" opacity={0.6}>
                  {m >= 1_000_000 ? `$${m/1_000_000}M` : `$${m/1_000}K`}
                </text>
              </g>
            ))}

            {/* Phase 2 start (April 2029 = month 36) */}
            <line
              x1={xScale(36)} y1={0} x2={xScale(36)} y2={chartH}
              stroke="#60a5fa" strokeOpacity="0.3" strokeDasharray="3 3" strokeWidth={1}
            />
            <text x={xScale(36) + 3} y={12} fontSize={9} fill="#60a5fa" opacity={0.6}>
              +€830 DCA
            </text>

            {/* Fill areas */}
            <path
              d={`${toPath(proj20)} L ${xScale(MONTHS)} ${chartH} L 0 ${chartH} Z`}
              fill="url(#g20)"
            />
            <path
              d={`${toPath(proj10)} L ${xScale(MONTHS)} ${chartH} L 0 ${chartH} Z`}
              fill="url(#g10)"
            />

            {/* Lines */}
            <path d={toPath(proj20)} fill="none" stroke="#a78bfa" strokeWidth={2} />
            <path d={toPath(proj10)} fill="none" stroke="#34d399" strokeWidth={2} />

            {/* Current value dot */}
            <circle cx={0} cy={yScale(startValue)} r={4} fill="#f59e0b" />
            <text x={6} y={yScale(startValue) - 6} fontSize={9} fill="#f59e0b">
              {fmt$(startValue)} aujourd'hui
            </text>

            {/* Milestone annotations */}
            {m10_100k && (
              <g>
                <circle cx={xScale(m10_100k)} cy={yScale(100_000)} r={3} fill="#34d399" />
                <text x={xScale(m10_100k) + 4} y={yScale(100_000) - 5} fontSize={8} fill="#34d399" opacity={0.8}>
                  $100K à {2026 + Math.floor(m10_100k / 12)}.{String(m10_100k % 12 || 12).padStart(2, "0")}
                </text>
              </g>
            )}
            {m20_1M && (
              <g>
                <circle cx={xScale(m20_1M)} cy={yScale(1_000_000)} r={3} fill="#a78bfa" />
                <text x={xScale(m20_1M) + 4} y={yScale(1_000_000) - 5} fontSize={8} fill="#a78bfa" opacity={0.8}>
                  $1M à {2026 + Math.floor(m20_1M / 12)}
                </text>
              </g>
            )}

            {/* X axis */}
            <line x1={0} y1={chartH} x2={chartW} y2={chartH} stroke="#334155" strokeWidth={0.5} />
            {xLabels.map(({ m, label }) => (
              <text key={m} x={xScale(m)} y={chartH + 16} textAnchor="middle" fontSize={9} fill="#475569">
                {label}
              </text>
            ))}
          </g>
        </svg>
      </div>

      {/* Summary milestones table */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        {[
          { label: "$100K", m10: findMilestoneMonth(proj10, 100_000), m20: findMilestoneMonth(proj20, 100_000) },
          { label: "$250K", m10: findMilestoneMonth(proj10, 250_000), m20: findMilestoneMonth(proj20, 250_000) },
          { label: "$500K", m10: findMilestoneMonth(proj10, 500_000), m20: findMilestoneMonth(proj20, 500_000) },
          { label: "$1M",   m10: findMilestoneMonth(proj10, 1_000_000), m20: findMilestoneMonth(proj20, 1_000_000) },
        ].map(({ label, m10, m20 }) => (
          <div key={label} className="bg-white/5 border border-white/10 rounded-lg p-3 text-center">
            <div className="text-slate-300 font-bold text-sm mb-1">{label}</div>
            <div className="text-emerald-400">
              {m10 ? `${2026 + Math.floor(m10 / 12)} (10%)` : "—"}
            </div>
            <div className="text-violet-400 mt-0.5">
              {m20 ? `${2026 + Math.floor(m20 / 12)} (20%)` : "—"}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── CORTEX Speech ─────────────────────────────────────────────────────────────

function CortexSpeech({
  positions,
  totalValue,
  totalPnl,
  totalPnlPct,
  stocksValue,
  cryptoValue,
}: {
  positions: EnrichedPosition[]
  totalValue: number
  totalPnl: number
  totalPnlPct: number
  stocksValue: number
  cryptoValue: number
}) {
  const best  = [...positions].sort((a, b) => b.pnlPct - a.pnlPct)[0]
  const worst = [...positions].sort((a, b) => a.pnlPct - b.pnlPct)[0]
  const stockPct = ((stocksValue / totalValue) * 100).toFixed(0)
  const cryptoPct = ((cryptoValue / totalValue) * 100).toFixed(0)

  const proj10at5y = computeProjection(totalValue, 0.10, 60)[60]
  const proj20at5y = computeProjection(totalValue, 0.20, 60)[60]

  return (
    <div className="glass border border-white/10 rounded-xl p-5 space-y-4 text-sm leading-relaxed">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-glow" />
        <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-semibold">
          Analyse CORTEX — Portefeuille Badr
        </span>
      </div>

      <p className="text-slate-300">
        Ton portefeuille pèse actuellement{" "}
        <span className="text-white font-semibold">{fmt$(totalValue)}</span>, avec une performance globale de{" "}
        <span className={`font-semibold ${pnlColor(totalPnl)}`}>{fmtPct(totalPnlPct)}</span>{" "}
        ({fmtSmall$(totalPnl)} de P&L). À ce stade, c'est de la friction normale — pas un signal d'alarme.
      </p>

      <p className="text-slate-400">
        <span className="text-blue-300 font-medium">Tech : {stockPct}%</span> du portefeuille,
        <span className="text-amber-300 font-medium"> Crypto : {cryptoPct}%</span>. Meilleur performer :{" "}
        <span className="text-emerald-300 font-medium">{best?.name} ({fmtPct(best?.pnlPct ?? 0)})</span>.
        Point de vigilance :{" "}
        <span className="text-red-300 font-medium">{worst?.name} ({fmtPct(worst?.pnlPct ?? 0)})</span>.
      </p>

      <p className="text-slate-400">
        Avec ton DCA de <span className="text-white font-medium">$500/mois</span> (NVDA + GOOGL + META + BTC),
        en maintenant cette cadence et en ajoutant{" "}
        <span className="text-blue-300 font-medium">€830/mois dès avril 2029</span>, à{" "}
        <span className="text-emerald-400 font-medium">10%/an</span> tu atteins{" "}
        <span className="text-white font-semibold">{fmt$(proj10at5y)}</span> dans 5 ans.
        À <span className="text-violet-400 font-medium">20%/an</span> (scénario tech bull) :{" "}
        <span className="text-white font-semibold">{fmt$(proj20at5y)}</span>.
      </p>

      <p className="text-slate-500 text-xs border-t border-white/5 pt-3">
        Stratégie validée — long terme, pas de vente prévue. CORTEX te préviendra si VIX spike +20%,
        BTC crash -10% ou S&P recule -3% en séance. En dehors de ces seuils : laisse tourner, continue le DCA.
      </p>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function PortfolioSection() {
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState("")

  useEffect(() => {
    fetch("/api/portfolio")
      .then((r) => r.json())
      .then((data) => {
        setPrices(data.prices ?? {})
        setLastUpdate(new Date(data.timestamp).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }))
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // Positions enrichies avec prix live
  const enriched = useMemo<EnrichedPosition[]>(() => {
    const positions = POSITIONS.map((p) => {
      const currentPrice = prices[p.ticker] ?? p.avgCost
      const invested = p.qty * p.avgCost
      const currentValue = p.qty * currentPrice
      const pnl = currentValue - invested
      const pnlPct = (pnl / invested) * 100
      return { ...p, currentPrice, invested, currentValue, pnl, pnlPct, weight: 0 }
    })
    const total = positions.reduce((s, p) => s + p.currentValue, 0)
    return positions.map((p) => ({ ...p, weight: total > 0 ? (p.currentValue / total) * 100 : 0 }))
  }, [prices])

  const totalInvested = enriched.reduce((s, p) => s + p.invested, 0)
  const totalValue    = enriched.reduce((s, p) => s + p.currentValue, 0)
  const totalPnl      = totalValue - totalInvested
  const totalPnlPct   = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0
  const stocksValue   = enriched.filter((p) => p.type === "stock").reduce((s, p) => s + p.currentValue, 0)
  const cryptoValue   = enriched.filter((p) => p.type === "crypto").reduce((s, p) => s + p.currentValue, 0)

  const monthlyDCA = 500
  const bonusUsd = DCA_PHASE2_BONUS_EUR * EUR_TO_USD

  const stocks = enriched.filter((p) => p.type === "stock")
  const cryptos = enriched.filter((p) => p.type === "crypto")

  return (
    <div className="space-y-6 animate-slide-up">

      {/* ── Header ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse-glow" />
              <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">
                Portefeuille Revolut — Suivi CORTEX
              </span>
            </div>
            <div className="flex items-baseline gap-3 mt-3">
              {loading ? (
                <div className="h-8 w-40 bg-white/10 rounded animate-pulse" />
              ) : (
                <span className="text-3xl font-bold text-white tracking-tight">{fmt$(totalValue)}</span>
              )}
              <span className={`text-lg font-semibold ${pnlColor(totalPnl)}`}>
                {fmtPct(totalPnlPct)}
              </span>
            </div>
            <div className={`text-sm mt-1 ${pnlColor(totalPnl)}`}>
              {totalPnl >= 0 ? "+" : ""}{fmtSmall$(totalPnl)} vs investi ({fmt$(totalInvested)})
            </div>
          </div>

          {/* Allocation pills */}
          <div className="flex flex-col gap-2 items-end text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Tech</span>
              <div className="bg-blue-500/20 border border-blue-500/30 text-blue-300 rounded-full px-3 py-1 font-semibold">
                {fmt$(stocksValue)} · {((stocksValue / totalValue) * 100).toFixed(0)}%
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-500">Crypto</span>
              <div className="bg-amber-500/20 border border-amber-500/30 text-amber-300 rounded-full px-3 py-1 font-semibold">
                {fmt$(cryptoValue)} · {((cryptoValue / totalValue) * 100).toFixed(0)}%
              </div>
            </div>
            {lastUpdate && (
              <span className="text-slate-600 font-mono text-[10px]">Prix live · {lastUpdate}</span>
            )}
          </div>
        </div>

        {/* Allocation bar */}
        <div className="mt-4 h-2 rounded-full overflow-hidden bg-white/5 flex">
          <div
            className="bg-blue-500/60 h-full transition-all"
            style={{ width: `${(stocksValue / totalValue) * 100}%` }}
          />
          <div
            className="bg-amber-500/60 h-full transition-all"
            style={{ width: `${(cryptoValue / totalValue) * 100}%` }}
          />
        </div>
      </div>

      {/* ── CORTEX Speech ── */}
      {!loading && (
        <CortexSpeech
          positions={enriched}
          totalValue={totalValue}
          totalPnl={totalPnl}
          totalPnlPct={totalPnlPct}
          stocksValue={stocksValue}
          cryptoValue={cryptoValue}
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
              {fmt$(items.reduce((s, p) => s + p.currentValue, 0))}
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
                    {/* Weight bar */}
                    <div className="hidden sm:flex flex-col items-end gap-1 w-14 shrink-0">
                      <span className="text-[10px] text-slate-600 font-mono">{p.weight.toFixed(1)}%</span>
                      <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={p.type === "stock" ? "bg-blue-400/60 h-full rounded-full" : "bg-amber-400/60 h-full rounded-full"}
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
        <div className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {DCA_PHASE1.map((d) => (
              <div key={d.ticker} className="bg-white/5 border border-white/10 rounded-lg p-3 text-center">
                <div className="text-white font-semibold">{d.ticker}</div>
                <div className="text-cyan-300 font-mono text-sm mt-0.5">${d.amountUsd}/mois</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-slate-500 flex items-center justify-between pt-1">
            <span>Phase 1 (maintenant → mars 2029) : <span className="text-white font-medium">${monthlyDCA}/mois</span></span>
            <span className="font-mono text-slate-600">${(monthlyDCA * 12).toLocaleString()}/an</span>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs">
            <div className="text-blue-300 font-semibold mb-1">Dès avril 2029 — Phase 2</div>
            <div className="text-slate-400">
              +€{DCA_PHASE2_BONUS_EUR}/mois ≈ <span className="text-white font-medium">${bonusUsd.toFixed(0)}</span>,
              réparti avec la même clé : NVDA 30% · GOOGL 30% · META 20% · BTC 20%
            </div>
            <div className="text-slate-500 mt-1">
              Total Phase 2 :{" "}
              <span className="text-white font-medium">
                ${(monthlyDCA + bonusUsd).toFixed(0)}/mois
              </span>{" "}
              · ${((monthlyDCA + bonusUsd) * 12).toFixed(0)}/an
            </div>
          </div>
        </div>
      </div>

      {/* ── Projection Chart ── */}
      <div className="glass border border-white/10 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-violet-400" />
          <span className="text-[10px] text-violet-400 uppercase tracking-widest font-semibold">
            Trajectoire de croissance — 14 ans
          </span>
        </div>
        {loading ? (
          <div className="h-48 bg-white/5 rounded-lg animate-pulse" />
        ) : (
          <ProjectionChart startValue={totalValue} />
        )}
      </div>

    </div>
  )
}
