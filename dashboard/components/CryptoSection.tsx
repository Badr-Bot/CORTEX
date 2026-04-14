import type { ReportJSON } from "@/lib/types"
import SignalCard from "./SignalCard"

interface Props { crypto: ReportJSON["crypto"] }

function directionColor(d: string) {
  const u = d.toUpperCase()
  if (u.includes("BULLISH") && !u.includes("NEUTRE")) return "text-green-400"
  if (u.includes("BEARISH") && !u.includes("NEUTRE")) return "text-red-400"
  return "text-yellow-400"
}

function scoreColor(v: number) {
  if (v > 0) return "text-green-400"
  if (v < 0) return "text-red-400"
  return "text-slate-400"
}

export default function CryptoSection({ crypto }: Props) {
  const d = crypto.dashboard
  const btcChange = d.btc_change_24h || 0

  return (
    <div className="space-y-5">
      {/* Dashboard BTC */}
      <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
        <div className="text-xs text-yellow-400 uppercase tracking-wider font-medium mb-4">
          Tableau de bord Bitcoin
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-slate-500 mb-1">Prix BTC</div>
            <div className="text-white font-semibold">
              {d.btc_price ? `$${d.btc_price.toLocaleString()}` : "N/A"}
              {btcChange !== 0 && (
                <span className={`ml-2 text-sm ${btcChange >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {btcChange > 0 ? "+" : ""}{btcChange.toFixed(1)}%
                </span>
              )}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Fear & Greed</div>
            <div className="text-white">{d.fear_greed_score} — <span className="text-slate-400 text-sm">{d.fear_greed_label}</span></div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Dominance BTC</div>
            <div className="text-white">{d.btc_dominance}%</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Phase du cycle</div>
            <div className="text-white text-sm">{crypto.phase || "N/A"}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Funding Rate</div>
            <div className="text-slate-300 text-sm">{d.funding_description || "N/A"}</div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">Direction</div>
            <div className={`font-medium text-sm ${directionColor(crypto.direction)}`}>
              {crypto.direction} — {crypto.magnitude}
            </div>
          </div>
        </div>
      </div>

      {/* Score */}
      {crypto.score && Object.keys(crypto.score).length > 0 && (
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
          <div className="text-xs text-yellow-400 uppercase tracking-wider font-medium mb-3">Score de direction</div>
          <div className="space-y-2">
            {Object.entries(crypto.score).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-slate-400 capitalize">{key}</span>
                <div className="flex items-center gap-3">
                  <span className={`font-mono font-medium ${scoreColor(val.value)}`}>
                    {val.value > 0 ? "+" : ""}{val.value}
                  </span>
                  <span className="text-xs text-slate-500 italic">{val.note}</span>
                </div>
              </div>
            ))}
          </div>
          {crypto.bear_case && (
            <div className="mt-3 pt-3 border-t border-[#1e1e2e] text-xs text-slate-500 italic">
              <span className="text-slate-400 not-italic">Bear case : </span>{crypto.bear_case}
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
