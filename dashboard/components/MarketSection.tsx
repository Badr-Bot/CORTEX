import type { ReportJSON, HotStock } from "@/lib/types"
import SignalCard from "./SignalCard"
import TradingViewChart from "./TradingViewChart"

interface Props { market: ReportJSON["market"] }

function recScoreConfig(score: number) {
  if (score <= 2) return { color: "text-emerald-400", bg: "bg-emerald-500", label: "Faible" }
  if (score <= 4) return { color: "text-yellow-400",  bg: "bg-yellow-500",  label: "Modéré" }
  if (score <= 6) return { color: "text-orange-400",  bg: "bg-orange-500",  label: "Élevé"  }
  return               { color: "text-red-400",     bg: "bg-red-500",     label: "Critique" }
}

function statusConfig(s: string) {
  return {
    green:  { dot: "bg-emerald-400 shadow-[0_0_6px_#10b981]", text: "text-emerald-400" },
    yellow: { dot: "bg-amber-400 shadow-[0_0_6px_#f59e0b]",   text: "text-amber-400"   },
    red:    { dot: "bg-red-400 shadow-[0_0_6px_#ef4444]",     text: "text-red-400"     },
  }[s] || { dot: "bg-slate-500", text: "text-slate-400" }
}

function StockRow({ stock, index }: { stock: HotStock; index: number }) {
  const isUp1d = stock.change_1d >= 0
  const isUp5d = stock.change_5d >= 0
  return (
    <div
      className="flex items-center justify-between py-3 border-b border-white/5 last:border-0 group"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-white font-bold text-sm font-mono">{stock.ticker}</span>
          <span className="text-slate-500 text-xs truncate">{stock.name}</span>
        </div>
        {stock.reason && (
          <div className="text-[10px] text-slate-600 italic mt-0.5 truncate">{stock.reason}</div>
        )}
      </div>
      <div className="text-right shrink-0 ml-4 space-y-0.5">
        <div className={`text-sm font-bold font-mono px-2 py-0.5 rounded ${
          isUp1d ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"
        }`}>
          {stock.change_1d > 0 ? "+" : ""}{stock.change_1d.toFixed(1)}%
        </div>
        <div className={`text-[10px] font-mono ${isUp5d ? "text-emerald-600" : "text-red-600"}`}>
          {stock.change_5d > 0 ? "+" : ""}{stock.change_5d.toFixed(1)}% 5j
        </div>
      </div>
    </div>
  )
}

export default function MarketSection({ market }: Props) {
  const d = market.dashboard
  const rec = recScoreConfig(market.recession_score)

  const dashItems = [
    { key: "sp500",  label: "S&P 500",  icon: "📊" },
    { key: "nasdaq", label: "Nasdaq",   icon: "💻" },
    { key: "gold",   label: "Or",       icon: "🥇" },
    { key: "oil",    label: "Pétrole",  icon: "🛢" },
    { key: "dxy",    label: "DXY",      icon: "💵" },
  ] as const

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Indices grid */}
      <div className="glass rounded-xl p-5 card-hover border border-emerald-500/10">
        <div className="flex items-center gap-2 mb-5">
          <div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981] animate-pulse-glow" />
          <div className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">
            🌍 Marchés mondiaux
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {dashItems.map(({ key, label, icon }) => {
            const item = d[key] as { price: string; change_pct: number } | undefined
            if (!item) return null
            const chg = item.change_pct || 0
            const isUp = chg >= 0
            return (
              <div key={key} className="space-y-1">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <span>{icon}</span>{label}
                </div>
                <div className="text-white font-mono font-bold">{item.price}</div>
                <div className={`text-xs font-mono font-semibold ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                  {isUp ? "▲" : "▼"} {Math.abs(chg).toFixed(1)}%
                </div>
              </div>
            )
          })}

          {d.vix && (
            <div className="space-y-1">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">⚡ VIX</div>
              <div className="text-white font-mono font-bold">{d.vix.price}</div>
              <div className="text-xs text-slate-400">{d.vix.interpretation}</div>
            </div>
          )}
          {d.us_10y && (
            <div className="space-y-1">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">🏦 US 10Y</div>
              <div className="text-white font-mono font-bold">{d.us_10y.price}</div>
              <div className="text-xs text-slate-400">{d.us_10y.change_bps}</div>
            </div>
          )}
        </div>
      </div>

      {/* Recession + Régime */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Recession Score */}
        <div className="glass rounded-xl p-5 card-hover border border-emerald-500/10">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">⚠️ Risque récession</div>
            <div className={`text-sm font-mono px-2 py-0.5 rounded-lg border ${rec.color} bg-white/5 border-current/30`}>
              {rec.label}
            </div>
          </div>
          <div className={`text-4xl font-bold font-mono mb-3 ${rec.color}`}>
            {market.recession_score}<span className="text-slate-600 text-lg">/10</span>
          </div>
          {/* Score bar */}
          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden mb-4">
            <div
              className={`h-full ${rec.bg} rounded-full transition-all duration-1000`}
              style={{ width: `${market.recession_score * 10}%` }}
            />
          </div>
          {/* Indicators */}
          <div className="space-y-2">
            {Object.entries(market.recession_indicators || {}).map(([key, val]) => {
              const sc = statusConfig(val.status)
              return (
                <div key={key} className="flex items-start gap-2 text-xs">
                  <div className={`shrink-0 w-1.5 h-1.5 rounded-full mt-1 ${sc.dot}`} />
                  <div>
                    <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}</span>
                    {val.note && <span className="text-slate-600 italic ml-1">· {val.note}</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Régime */}
        <div className="glass rounded-xl p-5 card-hover border border-emerald-500/10">
          <div className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold mb-3">🏛️ Régime de marché</div>
          <div className="text-white font-bold text-base mb-2">{market.regime}</div>
          <p className="text-slate-400 text-sm leading-relaxed">{market.regime_justification}</p>
          {market.crash && (
            <div className="mt-4 pt-3 border-t border-white/5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider">💥 Risque crash</span>
                <span className="font-mono font-bold text-orange-400">{market.crash.crash_score}/10</span>
              </div>
              <div className="text-xs text-slate-500 italic">{market.crash.interpretation}</div>
            </div>
          )}
        </div>
      </div>

      {/* Hot stocks */}
      {market.hot_stocks && market.hot_stocks.length > 0 && (
        <div className="glass rounded-xl p-5 card-hover border border-emerald-500/10">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-emerald-400/60" />
            <div className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">
              🔥 Actions en mouvement
            </div>
          </div>
          {market.hot_stocks.map((s, i) => <StockRow key={i} stock={s} index={i} />)}
        </div>
      )}

      {/* Charts */}
      <div className="glass rounded-xl p-5 card-hover border border-emerald-500/10">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400/60" />
          <div className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold">📊 Graphiques 30 jours</div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <TradingViewChart symbol="SP:SPX" label="📊 S&P 500" height={200} />
          <TradingViewChart symbol="TVC:GOLD" label="🥇 Or (XAU/USD)" height={200} />
        </div>
      </div>

      {/* Signaux */}
      {market.signals?.map((sig, i) => (
        <SignalCard key={i} signal={sig} index={i} sector="market" />
      ))}
    </div>
  )
}
