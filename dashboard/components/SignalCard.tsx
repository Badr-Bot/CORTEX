import type { Signal, DeeptechSignal } from "@/lib/types"

function stars(n: number) {
  const v = Math.max(1, Math.min(5, n))
  return "★".repeat(v) + "☆".repeat(5 - v)
}

function sizingConfig(s: string) {
  return {
    Fort:   { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30", dot: "bg-emerald-400" },
    Moyen:  { color: "text-amber-400",   bg: "bg-amber-500/10 border-amber-500/30",     dot: "bg-amber-400"  },
    Faible: { color: "text-red-400",     bg: "bg-red-500/10 border-red-500/30",         dot: "bg-red-400"    },
  }[s] || { color: "text-slate-400", bg: "bg-slate-500/10 border-slate-500/30", dot: "bg-slate-400" }
}

function horizonLabel(h: string) {
  return { "1-2": "Court terme", "3-5": "Moyen terme", "5-10": "Long terme", "10+": "Très long" }[h] || h
}

interface Props {
  signal: Signal
  index: number
  sector?: "ai" | "crypto" | "market" | "deeptech"
}

const SECTOR_CONFIG: Record<string, { accent: string; glow: string; label: string; icon: string }> = {
  ai:       { accent: "accent-ai",       glow: "hover:shadow-indigo-500/10",  label: "IA",       icon: "🧠" },
  crypto:   { accent: "accent-crypto",   glow: "hover:shadow-amber-500/10",   label: "Crypto",   icon: "₿" },
  market:   { accent: "accent-market",   glow: "hover:shadow-emerald-500/10", label: "Marchés",  icon: "📈" },
  deeptech: { accent: "accent-deeptech", glow: "hover:shadow-violet-500/10",  label: "DeepTech", icon: "⚡" },
}

export default function SignalCard({ signal, index, sector = "ai" }: Props) {
  const isDeeptech = sector === "deeptech"
  const dt = signal as DeeptechSignal
  const cfg = SECTOR_CONFIG[sector]
  const sizing = sizingConfig(signal.sizing)

  return (
    <div
      className={`glass card-hover border-l-2 rounded-xl p-5 space-y-4 animate-slide-up ${cfg.accent} stagger-${Math.min(index + 1, 5) as 1|2|3|4|5}`}
      style={{ animationDelay: `${index * 0.06}s` }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 w-7 h-7 rounded-md bg-white/5 border border-white/10 flex items-center justify-center">
            <span className="text-xs font-mono text-slate-400">#{index + 1}</span>
          </div>
          <h3 className="font-semibold text-white text-sm uppercase tracking-wide leading-snug">
            {signal.title}
          </h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="stars text-sm">{stars(signal.conviction)}</span>
          {isDeeptech && (
            <span className="text-xs text-violet-400 bg-violet-500/10 border border-violet-500/30 rounded-md px-2 py-0.5 font-mono">
              {horizonLabel(dt.horizon)}
            </span>
          )}
        </div>
      </div>

      {/* Ce qui se passe */}
      <div className="space-y-1">
        <div className="text-[10px] text-slate-500 uppercase tracking-widest font-medium flex items-center gap-2">
          <span className="w-3 h-px bg-slate-600" />
          🔍 Ce qui se passe
          <span className="w-3 h-px bg-slate-600" />
        </div>
        <p className="text-slate-300 text-sm leading-relaxed">{signal.fait}</p>
      </div>

      {/* Implications */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-black/30 rounded-lg p-3 border border-white/5 space-y-1">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-400/60" />
            <div className="text-[10px] text-cyan-400/60 uppercase tracking-wider">⚡ Impact direct</div>
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">{signal.implication_2}</p>
        </div>
        <div className="bg-black/30 rounded-lg p-3 border border-white/5 space-y-1">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-violet-400/60" />
            <div className="text-[10px] text-violet-400/60 uppercase tracking-wider">🌊 Impact systémique</div>
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">{signal.implication_3}</p>
        </div>
      </div>

      {/* Action bar */}
      <div className="bg-black/40 rounded-lg px-4 py-3 border border-white/5 flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">🎯 Action</span>
          <span className="text-xs text-white font-medium">{signal.action}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">💼 Position</span>
          <span className={`text-xs font-semibold font-mono px-2 py-0.5 rounded border ${sizing.bg} ${sizing.color}`}>
            {signal.sizing}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">🛑 Stop si</span>
          <span className="text-xs text-orange-400">{signal.invalide_si}</span>
        </div>
      </div>

      {/* Deeptech credibility badges */}
      {isDeeptech && (
        <div className="flex gap-2 flex-wrap">
          {(["peer_reviewed", "financement", "prototype", "adoption"] as const).map((key) => {
            const labels: Record<string, string> = {
              peer_reviewed: "Peer-reviewed", financement: "Financement",
              prototype: "Prototype", adoption: "Adoption",
            }
            const active = !!dt[key]
            return (
              <span
                key={key}
                className={`text-xs px-2.5 py-0.5 rounded-full border transition-all ${
                  active
                    ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10 shadow-[0_0_8px_rgba(16,185,129,0.2)]"
                    : "border-white/5 text-slate-600 bg-black/20"
                }`}
              >
                {active ? "✓" : "✗"} {labels[key]}
              </span>
            )
          })}
        </div>
      )}

      {/* Contre-argument */}
      {signal.these_opposee && signal.these_opposee !== "N/A" && (
        <div className="text-xs text-slate-500 italic border-t border-white/5 pt-3">
          <span className="not-italic text-slate-400 font-medium">⚠ Contre-argument : </span>
          {signal.these_opposee}
        </div>
      )}

      {/* Source */}
      <div className="flex items-center justify-between">
        {signal.source_url ? (
          <a
            href={signal.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors group"
          >
            <span className="opacity-60 group-hover:opacity-100">↗</span>
            {signal.source_name}
          </a>
        ) : (
          <span className="text-xs text-slate-600">{signal.source_name}</span>
        )}
      </div>
    </div>
  )
}
