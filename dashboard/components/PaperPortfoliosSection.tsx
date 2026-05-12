"use client"

import { useState, useEffect, useMemo } from "react"

// ── Types ─────────────────────────────────────────────────────────────────────

interface PaperPosition {
  id: string
  ticker: string
  asset_type: string
  allocation_pct: number
  allocation_usd: number
  entry_price: number | null
  current_price: number | null
  pnl_usd: number
  pnl_pct: number
  conviction: string | null
  reasoning: string | null
  status: string
}

interface PaperSnapshot {
  snapshot_date: string
  portfolio_value: number
  pnl_pct: number
  sp500_pnl_pct: number
}

interface PaperPortfolio {
  id: string
  code: string
  portfolio_type: string
  horizon_days: number
  initial_value: number
  current_value: number
  start_date: string
  end_date: string
  benchmark_start: number | null
  pnl_pct: number | null
  benchmark_pnl_pct: number | null
  beat_sp500: boolean | null
  status: string
  rationale: string | null
  paper_positions: PaperPosition[]
  paper_snapshots: PaperSnapshot[]
}

interface ClosedPortfolio {
  code: string
  portfolio_type: string
  start_date: string
  end_date: string
  initial_value: number
  current_value: number
  pnl_pct: number | null
  benchmark_pnl_pct: number | null
  beat_sp500: boolean | null
  closed_at: string | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_META: Record<string, { label: string; prefix: string; color: string; border: string; dot: string; badge: string; glow: string }> = {
  weekly:  { label: "Semaine",  prefix: "PW", color: "text-cyan-300",   border: "border-cyan-500/25",   dot: "bg-cyan-400",   badge: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300",   glow: "shadow-[0_0_12px_rgba(34,211,238,0.2)]"   },
  monthly: { label: "Mois",     prefix: "PM", color: "text-blue-300",   border: "border-blue-500/25",   dot: "bg-blue-400",   badge: "bg-blue-500/10 border-blue-500/30 text-blue-300",   glow: "shadow-[0_0_12px_rgba(99,102,241,0.2)]"   },
  annual:  { label: "Année",    prefix: "PA", color: "text-violet-300", border: "border-violet-500/25", dot: "bg-violet-400", badge: "bg-violet-500/10 border-violet-500/30 text-violet-300", glow: "shadow-[0_0_12px_rgba(168,85,247,0.2)]" },
}

const CONVICTION_STARS: Record<string, string> = {
  forte: "★★★★★",
  moyenne: "★★★☆☆",
  faible: "★★☆☆☆",
}

const fmtPct  = (v: number | null) => v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`
const fmtUsd  = (v: number)        => `$${Math.abs(v).toFixed(2)}`
const fmtDate = (s: string)        => {
  const d = new Date(s + "T00:00:00")
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" })
}
const pnlColor = (v: number | null) =>
  v == null ? "text-slate-500" : v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400"

// ── Mini spark chart portfolio vs S&P ─────────────────────────────────────────

function SparkChart({ snapshots, color }: { snapshots: PaperSnapshot[]; color: string }) {
  if (snapshots.length < 2) return null

  const sorted = [...snapshots].sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))
  const pVals = sorted.map((s) => s.pnl_pct)
  const sVals = sorted.map((s) => s.sp500_pnl_pct)
  const allVals = [...pVals, ...sVals]
  const minV = Math.min(...allVals)
  const maxV = Math.max(...allVals)
  const range = maxV - minV || 1

  const W = 200, H = 48, PAD = 4
  const cW = W - PAD * 2
  const cH = H - PAD * 2

  const x = (i: number) => PAD + (i / (sorted.length - 1)) * cW
  const y = (v: number) => PAD + (1 - (v - minV) / range) * cH

  const toPath = (vals: number[]) =>
    vals.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ")

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-10" preserveAspectRatio="none">
      {/* Baseline 0% */}
      <line
        x1={PAD} y1={y(0)} x2={W - PAD} y2={y(0)}
        stroke="rgba(255,255,255,0.06)" strokeWidth={0.8}
      />
      {/* S&P 500 */}
      <path d={toPath(sVals)} fill="none" stroke="#64748b" strokeWidth={1} opacity={0.5} />
      {/* Portfolio */}
      <path d={toPath(pVals)} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  )
}

// ── Carte d'un portfolio actif ─────────────────────────────────────────────────

function PortfolioCard({ portfolio }: { portfolio: PaperPortfolio }) {
  const [expanded, setExpanded] = useState(false)
  const meta = TYPE_META[portfolio.portfolio_type] ?? TYPE_META.weekly
  const positions = [...portfolio.paper_positions].sort((a, b) => b.allocation_pct - a.allocation_pct)

  // Calcul PnL live depuis les positions si pnl_pct null
  const totalValue = portfolio.current_value
  const pnl = totalValue - portfolio.initial_value
  const pnlPct = portfolio.pnl_pct ?? ((pnl / portfolio.initial_value) * 100)

  const daysLeft = Math.max(
    0,
    Math.ceil((new Date(portfolio.end_date).getTime() - Date.now()) / 86_400_000)
  )
  const daysTotal = portfolio.horizon_days
  const progress = Math.min(1, (daysTotal - daysLeft) / daysTotal)

  const sparkColor = portfolio.portfolio_type === "weekly"
    ? "#22d3ee" : portfolio.portfolio_type === "monthly"
    ? "#6366f1" : "#a855f7"

  return (
    <div className={`glass rounded-xl overflow-hidden border ${meta.border} ${meta.glow}`}>

      {/* ── Header ── */}
      <div className="px-5 py-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`w-1.5 h-1.5 rounded-full ${meta.dot} animate-pulse-glow`} />
            <span className={`text-[10px] uppercase tracking-widest font-semibold ${meta.color}`}>
              {portfolio.code} · {meta.label}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">
              ${totalValue.toFixed(0)}
            </span>
            <span className={`text-base font-semibold ${pnlColor(pnlPct)}`}>
              {fmtPct(pnlPct)}
            </span>
          </div>
          <div className={`text-xs mt-0.5 ${pnlColor(pnl)}`}>
            {pnl >= 0 ? "+" : ""}{fmtUsd(pnl)} sur ${portfolio.initial_value.toFixed(0)} investis
          </div>
        </div>

        {/* Dates + vs S&P */}
        <div className="text-right shrink-0 text-xs text-slate-500 font-mono space-y-1">
          <div>{fmtDate(portfolio.start_date)} → {fmtDate(portfolio.end_date)}</div>
          <div className="text-[10px]">{daysLeft}j restants</div>
          {portfolio.benchmark_pnl_pct != null && (
            <div className={portfolio.beat_sp500 ? "text-emerald-400" : "text-red-400"}>
              vs S&P {fmtPct(portfolio.benchmark_pnl_pct)}
              {portfolio.beat_sp500 ? " 🏆" : " 📉"}
            </div>
          )}
        </div>
      </div>

      {/* Barre de progression durée */}
      <div className="mx-5 mb-3 h-1 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            portfolio.portfolio_type === "weekly" ? "bg-cyan-500/60"
            : portfolio.portfolio_type === "monthly" ? "bg-blue-500/60"
            : "bg-violet-500/60"
          }`}
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      {/* Mini spark chart */}
      {portfolio.paper_snapshots.length >= 2 && (
        <div className="px-5 mb-3">
          <div className="flex items-center justify-between text-[10px] text-slate-600 mb-1 font-mono">
            <span>Évolution</span>
            <span className="flex items-center gap-2">
              <span className="text-slate-500">— S&P 500</span>
              <span style={{ color: sparkColor }}>— {portfolio.code}</span>
            </span>
          </div>
          <SparkChart snapshots={portfolio.paper_snapshots} color={sparkColor} />
        </div>
      )}

      {/* ── Positions ── */}
      <div className="border-t border-white/5">
        <div className="px-5 py-2.5 flex items-center justify-between">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-medium">
            {positions.length} position{positions.length > 1 ? "s" : ""}
          </span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors font-mono"
          >
            {expanded ? "▲ Masquer" : "▼ Détail"}
          </button>
        </div>

        {/* Résumé compact — toujours visible */}
        <div className="px-5 pb-3 flex flex-wrap gap-1.5">
          {positions.map((p) => (
            <span
              key={p.id}
              className={`text-xs px-2 py-0.5 rounded border font-mono ${meta.badge}`}
            >
              {p.ticker} {p.allocation_pct.toFixed(0)}%
              <span className={`ml-1 ${pnlColor(p.pnl_pct)}`}>{fmtPct(p.pnl_pct)}</span>
            </span>
          ))}
        </div>

        {/* Détail expandable */}
        {expanded && (
          <div className="divide-y divide-white/5">
            {positions.map((p) => (
              <div key={p.id} className="px-5 py-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-white font-semibold text-sm">{p.ticker}</span>
                    <span className="text-[10px] text-slate-600 uppercase">{p.asset_type}</span>
                    {p.conviction && (
                      <span className="text-amber-400 text-[10px] tracking-wider">
                        {CONVICTION_STARS[p.conviction] ?? ""}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-semibold font-mono ${pnlColor(p.pnl_pct)}`}>
                      {fmtPct(p.pnl_pct)}
                    </div>
                    <div className={`text-xs ${pnlColor(p.pnl_usd)}`}>
                      {p.pnl_usd >= 0 ? "+" : ""}{fmtUsd(p.pnl_usd)}
                    </div>
                  </div>
                </div>

                {/* Allocation + prix */}
                <div className="flex items-center gap-3 text-xs text-slate-500 font-mono flex-wrap">
                  <span className={`font-medium ${meta.color}`}>${p.allocation_usd.toFixed(0)} ({p.allocation_pct.toFixed(0)}%)</span>
                  {p.entry_price && (
                    <span>Entrée : <span className="text-slate-400">${p.entry_price.toFixed(p.entry_price < 10 ? 4 : 2)}</span></span>
                  )}
                  {p.current_price && (
                    <span>Actuel : <span className="text-slate-300">${p.current_price.toFixed(p.current_price < 10 ? 4 : 2)}</span></span>
                  )}
                </div>

                {/* Barre de poids dans le portefeuille */}
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        portfolio.portfolio_type === "weekly" ? "bg-cyan-500/50"
                        : portfolio.portfolio_type === "monthly" ? "bg-blue-500/50"
                        : "bg-violet-500/50"
                      }`}
                      style={{ width: `${p.allocation_pct}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-slate-600 font-mono w-8 text-right">{p.allocation_pct.toFixed(0)}%</span>
                </div>

                {p.reasoning && (
                  <p className="text-[11px] text-slate-500 leading-relaxed italic">
                    "{p.reasoning}"
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Raisonnement global CORTEX */}
      {portfolio.rationale && (
        <div className="px-5 py-3 border-t border-white/5">
          <div className="text-[10px] text-slate-600 uppercase tracking-widest mb-1.5 font-medium">
            Raisonnement CORTEX
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">{portfolio.rationale}</p>
        </div>
      )}
    </div>
  )
}

// ── Historique clos ────────────────────────────────────────────────────────────

function ClosedHistory({ portfolios }: { portfolios: ClosedPortfolio[] }) {
  if (!portfolios.length) return null

  const wins  = portfolios.filter((p) => p.beat_sp500 === true).length
  const total = portfolios.filter((p) => p.beat_sp500 != null).length

  return (
    <div className="glass border border-white/10 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
          <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">
            Historique clôturé
          </span>
        </div>
        {total > 0 && (
          <span className={`text-xs font-mono font-semibold ${wins / total >= 0.5 ? "text-emerald-400" : "text-red-400"}`}>
            {wins}/{total} battu S&P 500
          </span>
        )}
      </div>

      <div className="divide-y divide-white/5">
        {portfolios.map((p) => {
          const meta = TYPE_META[p.portfolio_type] ?? TYPE_META.weekly
          return (
            <div key={p.code} className="px-5 py-3 flex items-center gap-3">
              <span className={`text-xs font-mono font-semibold w-8 ${meta.color}`}>{p.code}</span>
              <div className="flex-1 text-xs text-slate-500 font-mono">
                {fmtDate(p.start_date)} → {fmtDate(p.end_date)}
              </div>
              <div className="text-right">
                <div className={`text-sm font-semibold font-mono ${pnlColor(p.pnl_pct)}`}>
                  {fmtPct(p.pnl_pct)}
                </div>
                {p.benchmark_pnl_pct != null && (
                  <div className="text-[10px] text-slate-600 font-mono">
                    S&P {fmtPct(p.benchmark_pnl_pct)}
                  </div>
                )}
              </div>
              <span className="text-base">
                {p.beat_sp500 === true ? "🏆" : p.beat_sp500 === false ? "❌" : "—"}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── État vide ─────────────────────────────────────────────────────────────────

function EmptyPaper() {
  return (
    <div className="glass border border-white/10 rounded-xl p-8 text-center space-y-3">
      <div className="text-3xl">🤖</div>
      <div className="text-white font-semibold">Aucun portefeuille paper actif</div>
      <p className="text-slate-500 text-sm max-w-sm mx-auto">
        Lance le workflow <span className="font-mono text-indigo-400">portfolio_init</span> sur GitHub Actions
        pour créer PW1, PM1 et PA1 — CORTEX allouera $1 000 fictifs avec son intelligence complète.
      </p>
      <div className="text-[10px] text-slate-600 font-mono">
        GitHub → Actions → CORTEX Portfolio Init → Run workflow
      </div>
    </div>
  )
}

// ── Composant principal ────────────────────────────────────────────────────────

export default function PaperPortfoliosSection() {
  const [active, setActive]   = useState<PaperPortfolio[]>([])
  const [closed, setClosed]   = useState<ClosedPortfolio[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/paper-portfolios")
      .then((r) => r.json())
      .then(({ active: a, closed: c }) => {
        setActive(a ?? [])
        setClosed(c ?? [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  // Stats globales sur les portefeuilles actifs
  const totalPnl = useMemo(
    () => active.reduce((s, p) => s + (p.current_value - p.initial_value), 0),
    [active]
  )

  return (
    <div className="space-y-4 animate-fade-in">

      {/* ── Header section ── */}
      <div className="glass rounded-xl p-5 border border-indigo-500/15">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-glow" />
              <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-semibold">
                Paper Trading CORTEX
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Portefeuilles fictifs $1 000 alloués par l'intelligence CORTEX — sans risque réel.
            </p>
          </div>
          {active.length > 0 && (
            <div className="text-right">
              <div className={`text-lg font-bold font-mono ${pnlColor(totalPnl)}`}>
                {totalPnl >= 0 ? "+" : ""}{fmtUsd(totalPnl)}
              </div>
              <div className="text-[10px] text-slate-500">P&L combiné</div>
            </div>
          )}
        </div>

        {/* Légende types */}
        <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-white/5">
          {Object.entries(TYPE_META).map(([type, m]) => (
            <div key={type} className="flex items-center gap-1.5 text-[11px]">
              <span className={`w-1.5 h-1.5 rounded-full ${m.dot}`} />
              <span className={`font-mono font-semibold ${m.color}`}>{m.prefix}x</span>
              <span className="text-slate-500">{m.label} · {type === "weekly" ? "7j" : type === "monthly" ? "30j" : "365j"}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Portfolios actifs ── */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 glass rounded-xl border border-white/5 animate-pulse" />
          ))}
        </div>
      ) : active.length === 0 ? (
        <EmptyPaper />
      ) : (
        <div className="space-y-4">
          {active.map((p) => (
            <PortfolioCard key={p.id} portfolio={p} />
          ))}
        </div>
      )}

      {/* ── Historique ── */}
      {!loading && <ClosedHistory portfolios={closed} />}

    </div>
  )
}
