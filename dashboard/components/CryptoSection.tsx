import type { ReportJSON } from "@/lib/types"
import SignalCard from "./SignalCard"

interface Props { crypto: ReportJSON["crypto"] }

function directionConfig(d: string) {
  const u = d.toUpperCase()
  if (u.includes("BULLISH") && !u.includes("NEUTRE")) return { color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30", glow: "glow-green", icon: "↑" }
  if (u.includes("BEARISH") && !u.includes("NEUTRE")) return { color: "text-red-400",     bg: "bg-red-500/10",     border: "border-red-500/30",     glow: "",          icon: "↓" }
  return                                                      { color: "text-amber-400",   bg: "bg-amber-500/10",   border: "border-amber-500/30",   glow: "",          icon: "→" }
}

function fearGreedColor(score: number) {
  if (score >= 75) return { color: "text-emerald-400", label: "Greed extrême" }
  if (score >= 55) return { color: "text-yellow-400",  label: "Greed" }
  if (score >= 45) return { color: "text-slate-300",   label: "Neutre" }
  if (score >= 25) return { color: "text-orange-400",  label: "Fear" }
  return                  { color: "text-red-400",     label: "Fear extrême" }
}

function scoreColor(v: number) {
  if (v > 0) return "text-emerald-400"
  if (v < 0) return "text-red-400"
  return "text-slate-400"
}

export default function CryptoSection({ crypto }: Props) {
  const d = crypto.dashboard
  const btcChange = d.btc_change_24h || 0
  const isUp = btcChange >= 0
  const dir = directionConfig(crypto.direction)
  const fg = fearGreedColor(Number(d.fear_greed_score) || 50)

  return (
    <div className="space-y-5 animate-fade-in">
      {/* BTC Dashboard */}
      <div className="glass rounded-xl p-5 card-hover border border-amber-500/10">
        <div className="flex items-center gap-2 mb-5">
          <div className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b] animate-pulse-glow" />
          <div className="text-[10px] text-amber-400 uppercase tracking-widest font-semibold">
            Tableau de bord Bitcoin
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {/* BTC Price */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Prix BTC</div>
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="text-xl font-bold text-white font-mono counter-animate">
                {d.btc_price ? `$${d.btc_price.toLocaleString()}` : "N/A"}
              </span>
              {btcChange !== 0 && (
                <span className={`text-sm font-mono font-semibold px-1.5 py-0.5 rounded ${
                  isUp ? "text-emerald-400 bg-emerald-500/10" : "text-red-400 bg-red-500/10"
                }`}>
                  {isUp ? "+" : ""}{btcChange.toFixed(1)}%
                </span>
              )}
            </div>
          </div>

          {/* Fear & Greed */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Fear & Greed</div>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold font-mono ${fg.color}`}>{d.fear_greed_score}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${fg.color} bg-white/5 border-current/30`}>
                {d.fear_greed_label || fg.label}
              </span>
            </div>
          </div>

          {/* Dominance */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Dominance BTC</div>
            <div className="space-y-1">
              <span className="text-lg font-bold text-white font-mono">{d.btc_dominance}%</span>
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full"
                  style={{ width: `${d.btc_dominance || 0}%`, transition: "width 1s ease" }}
                />
              </div>
            </div>
          </div>

          {/* Phase */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Phase du cycle</div>
            <div className="text-sm text-white font-medium">{crypto.phase || "N/A"}</div>
          </div>

          {/* Funding */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Funding Rate</div>
            <div className="text-sm text-slate-300">{d.funding_description || "N/A"}</div>
          </div>

          {/* Direction */}
          <div className="space-y-1">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Direction</div>
            <div className={`flex items-center gap-1.5 text-sm font-semibold ${dir.color}`}>
              <span className={`text-base`}>{dir.icon}</span>
              {crypto.direction}
              <span className="text-xs opacity-60 font-normal">— {crypto.magnitude}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Score */}
      {crypto.score && Object.keys(crypto.score).length > 0 && (
        <div className="glass rounded-xl p-5 card-hover border border-amber-500/10">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-amber-400/60" />
            <div className="text-[10px] text-amber-400 uppercase tracking-widest font-semibold">Score de direction</div>
          </div>
          <div className="space-y-3">
            {Object.entries(crypto.score).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between gap-4">
                <span className="text-slate-400 capitalize text-sm">{key}</span>
                <div className="flex items-center gap-3 flex-1 justify-end">
                  <div className="flex-1 max-w-[120px] h-1 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${val.value > 0 ? "bg-emerald-500" : val.value < 0 ? "bg-red-500" : "bg-slate-500"}`}
                      style={{ width: `${Math.abs(val.value) * 10}%` }}
                    />
                  </div>
                  <span className={`font-mono text-sm font-bold w-8 text-right ${scoreColor(val.value)}`}>
                    {val.value > 0 ? "+" : ""}{val.value}
                  </span>
                  <span className="text-xs text-slate-500 italic max-w-[120px] truncate">{val.note}</span>
                </div>
              </div>
            ))}
          </div>
          {crypto.bear_case && (
            <div className="mt-4 pt-3 border-t border-white/5 flex items-start gap-2">
              <span className="text-orange-400 text-xs mt-0.5">⚠</span>
              <div className="text-xs text-slate-500 italic">
                <span className="text-slate-400 not-italic font-medium">Bear case : </span>{crypto.bear_case}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Signaux */}
      {crypto.signals?.map((sig, i) => (
        <SignalCard key={i} signal={sig} index={i} sector="crypto" />
      ))}
    </div>
  )
}
