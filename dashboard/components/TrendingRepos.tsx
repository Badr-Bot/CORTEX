import type { TrendingRepo } from "@/lib/types"

const TYPE_BADGE: Record<TrendingRepo["type"], { icon: string; label: string; badge: string }> = {
  repo:   { icon: "🐙", label: "Repo GitHub", badge: "bg-slate-500/10 border-slate-500/30 text-slate-300"   },
  modele: { icon: "🤗", label: "Modèle IA",   badge: "bg-amber-500/10 border-amber-500/30 text-amber-300"   },
  space:  { icon: "🧪", label: "Démo",        badge: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"      },
}

function typeConfig(type?: string) {
  return TYPE_BADGE[(type as TrendingRepo["type"])] ?? TYPE_BADGE.repo
}

type Props = {
  items?: TrendingRepo[]
}

/** Les repos GitHub et modèles IA qui montent, avec ce que Badr peut en faire. */
export default function TrendingRepos({ items }: Props) {
  if (!items || items.length === 0) return null

  return (
    <div className="glass border-l-2 accent-ai rounded-xl p-5 card-hover animate-slide-up space-y-4">
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_6px_#6366f1] animate-pulse-glow" />
        <div className="text-[10px] text-blue-400 uppercase tracking-widest font-semibold">
          🔥 Repos et modèles qui montent
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {items.map((r, i) => {
          const cfg = typeConfig(r.type)
          return (
            <div key={`${r.source_url}-${i}`} className="bg-black/30 rounded-lg p-3.5 border border-white/5 space-y-2">
              <div className="flex items-start justify-between gap-2">
                <a
                  href={r.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold font-mono text-white hover:text-indigo-300 transition-colors break-all"
                >
                  {r.nom}
                </a>
                <span className={`shrink-0 text-[10px] font-semibold font-mono px-2 py-0.5 rounded border ${cfg.badge}`}>
                  {cfg.icon} {cfg.label}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{r.quoi}</p>
              <p className="text-xs text-slate-500 leading-relaxed">
                <span className="text-blue-400/80 font-medium">Pour toi : </span>
                {r.pour_toi}
              </p>
              {r.popularite && (
                <div className="text-[10px] font-mono text-slate-600">⭐ {r.popularite}</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
