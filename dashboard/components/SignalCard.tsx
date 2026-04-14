import type { Signal, DeeptechSignal } from "@/lib/types"

function stars(n: number) {
  const v = Math.max(1, Math.min(5, n))
  return "★".repeat(v) + "☆".repeat(5 - v)
}

function sizingColor(s: string) {
  return { Fort: "text-green-400", Moyen: "text-yellow-400", Faible: "text-red-400" }[s] || "text-slate-400"
}

function horizonLabel(h: string) {
  return { "1-2": "Court terme", "3-5": "Moyen terme", "5-10": "Long terme", "10+": "Très long" }[h] || h
}

interface Props {
  signal: Signal
  index: number
  sector?: "ai" | "crypto" | "market" | "deeptech"
}

const SECTOR_ACCENT: Record<string, string> = {
  ai: "border-l-blue-500",
  crypto: "border-l-yellow-500",
  market: "border-l-green-500",
  deeptech: "border-l-purple-500",
}

export default function SignalCard({ signal, index, sector = "ai" }: Props) {
  const isDeeptech = sector === "deeptech"
  const dt = signal as DeeptechSignal

  return (
    <div className={`bg-[#12121a] border border-[#1e1e2e] border-l-2 ${SECTOR_ACCENT[sector]} rounded-xl p-5 space-y-4`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-slate-500 text-sm font-mono shrink-0">#{index + 1}</span>
          <h3 className="font-semibold text-white text-sm uppercase tracking-wide truncate">
            {signal.title}
          </h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="stars text-sm">{stars(signal.conviction)}</span>
          {isDeeptech && (
            <span className="text-xs text-slate-500 border border-[#1e1e2e] rounded px-2 py-0.5">
              {horizonLabel(dt.horizon)}
            </span>
          )}
        </div>
      </div>

      {/* Ce qui se passe */}
      <div>
        <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Ce qui se passe</div>
        <p className="text-slate-300 text-sm leading-relaxed">{signal.fait}</p>
      </div>

      {/* Implications */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-[#0a0a0f] rounded-lg p-3">
          <div className="text-xs text-slate-500 mb-1">Impact direct</div>
          <p className="text-slate-300 text-xs leading-relaxed">{signal.implication_2}</p>
        </div>
        <div className="bg-[#0a0a0f] rounded-lg p-3">
          <div className="text-xs text-slate-500 mb-1">Impact systémique</div>
          <p className="text-slate-300 text-xs leading-relaxed">{signal.implication_3}</p>
        </div>
      </div>

      {/* Action */}
      <div className="bg-[#0a0a0f] rounded-lg p-3 flex flex-wrap items-center gap-x-4 gap-y-1">
        <div>
          <span className="text-xs text-slate-500">Action : </span>
          <span className="text-xs text-white">{signal.action}</span>
        </div>
        <div>
          <span className="text-xs text-slate-500">Position : </span>
          <span className={`text-xs font-medium ${sizingColor(signal.sizing)}`}>{signal.sizing}</span>
        </div>
        <div>
          <span className="text-xs text-slate-500">Invalide si : </span>
          <span className="text-xs text-orange-400">{signal.invalide_si}</span>
        </div>
      </div>

      {/* Crédibilité Deeptech */}
      {isDeeptech && (
        <div className="flex gap-3 flex-wrap">
          {(["peer_reviewed", "financement", "prototype", "adoption"] as const).map((key) => {
            const labels: Record<string, string> = {
              peer_reviewed: "Peer-reviewed", financement: "Financement",
              prototype: "Prototype", adoption: "Adoption",
            }
            return (
              <span key={key} className={`text-xs px-2 py-0.5 rounded border ${
                dt[key]
                  ? "border-green-800 text-green-400 bg-green-900/20"
                  : "border-[#1e1e2e] text-slate-600"
              }`}>
                {dt[key] ? "✓" : "✗"} {labels[key]}
              </span>
            )
          })}
        </div>
      )}

      {/* Contre-argument */}
      {signal.these_opposee && signal.these_opposee !== "N/A" && (
        <div className="text-xs text-slate-500 italic border-t border-[#1e1e2e] pt-3">
          <span className="not-italic text-slate-400">Contre-argument : </span>
          {signal.these_opposee}
        </div>
      )}

      {/* Source */}
      {signal.source_url ? (
        <a
          href={signal.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          {signal.source_name} ↗
        </a>
      ) : (
        <span className="text-xs text-slate-600">{signal.source_name}</span>
      )}
    </div>
  )
}
