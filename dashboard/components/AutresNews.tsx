import type { AutreNews } from "@/lib/types"

type Sector = "ai" | "crypto" | "market" | "deeptech" | "ecommerce"

const SECTOR_STYLE: Record<Sector, { dot: string; label: string; arrow: string }> = {
  ai:        { dot: "bg-blue-400",    label: "text-blue-400",    arrow: "text-blue-500/60"    },
  crypto:    { dot: "bg-amber-400",   label: "text-amber-400",   arrow: "text-amber-500/60"   },
  market:    { dot: "bg-emerald-400", label: "text-emerald-400", arrow: "text-emerald-500/60" },
  deeptech:  { dot: "bg-violet-400",  label: "text-violet-400",  arrow: "text-violet-500/60"  },
  ecommerce: { dot: "bg-pink-400",    label: "text-pink-400",    arrow: "text-pink-500/60"    },
}

type Props = {
  items?: AutreNews[]
  sector: Sector
}

/** Le tour d'horizon : les autres news du jour, chacune expliquée en une phrase. */
export default function AutresNews({ items, sector }: Props) {
  if (!items || items.length === 0) return null
  const style = SECTOR_STYLE[sector]

  return (
    <div className="glass rounded-xl p-5 card-hover border border-white/5 animate-slide-up">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
          <div className={`text-[10px] uppercase tracking-widest font-semibold ${style.label}`}>
            📰 Les autres news du jour, en une phrase
          </div>
        </div>
        <span className="text-[10px] font-mono text-slate-600">{items.length} news</span>
      </div>
      <ul className="divide-y divide-white/5">
        {items.map((n, i) => (
          <li key={`${n.source_url}-${i}`} className="py-3 first:pt-0 last:pb-0 flex gap-3 items-start">
            <span className={`${style.arrow} mt-0.5 shrink-0`}>→</span>
            <div className="min-w-0 space-y-1">
              <div className="text-sm font-medium text-white leading-snug">{n.titre}</div>
              <p className="text-xs text-slate-400 leading-relaxed">{n.en_clair}</p>
              {n.source_url && (
                <a
                  href={n.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  <span className="opacity-60">↗</span>
                  {n.source_name || "Source"}
                </a>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
