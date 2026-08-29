import SignalCard from "@/components/SignalCard"
import EcomToolbox from "@/components/EcomToolbox"
import type { EcommerceData, EcomTheme } from "@/lib/types"

const THEMES: Record<EcomTheme, { icon: string; label: string; badge: string }> = {
  marketplace: { icon: "🛒", label: "Plateformes",   badge: "bg-blue-500/10 border-blue-500/30 text-blue-300"       },
  automation:  { icon: "🤖", label: "Automatisation", badge: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"       },
  emailing:    { icon: "📧", label: "Emailing",       badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" },
  creatives:   { icon: "🎨", label: "Créas & pub",    badge: "bg-pink-500/10 border-pink-500/30 text-pink-300"       },
  operations:  { icon: "📦", label: "Logistique",     badge: "bg-amber-500/10 border-amber-500/30 text-amber-300"    },
}

function themeConfig(theme?: string) {
  return THEMES[(theme as EcomTheme)] ?? { icon: "•", label: "E-commerce", badge: "bg-slate-500/10 border-slate-500/30 text-slate-300" }
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`
}

export default function EcommerceSection({ ecommerce }: { ecommerce?: EcommerceData }) {
  if (!ecommerce) {
    return (
      <div className="text-slate-500 text-sm text-center py-12 glass rounded-xl border border-white/5">
        Aucune donnée e-commerce aujourd&apos;hui
      </div>
    )
  }

  const stocks = ecommerce.dashboard?.stocks ?? []
  const secteur = ecommerce.dashboard?.secteur
  const nouveautes = ecommerce.nouveautes ?? []
  const signals = ecommerce.signals ?? []
  const actions = ecommerce.actions_semaine ?? []

  return (
    <div className="space-y-5">
      {/* Tendance globale */}
      {ecommerce.tendance_globale && (
        <div className="glass border-l-2 accent-ecommerce rounded-xl p-5 card-hover animate-slide-up">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-1.5 h-1.5 rounded-full bg-pink-400 shadow-[0_0_6px_#ec4899] animate-pulse-glow" />
            <div className="text-[10px] text-pink-400 uppercase tracking-widest font-semibold">
              🌡️ La tendance du moment
            </div>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">{ecommerce.tendance_globale}</p>
        </div>
      )}

      {/* Boîte à outils + radar produits : ce que Badr attend en premier */}
      <EcomToolbox outils={ecommerce.outils} radar={ecommerce.radar_produits} ecartes={ecommerce.radar_ecartes} />

      {/* Actions du secteur */}
      {stocks.length > 0 && (
        <div className="glass rounded-xl p-5 card-hover border border-white/5 animate-slide-up">
          <div className="flex items-center justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-pink-400" />
              <div className="text-[10px] text-pink-400 uppercase tracking-widest font-semibold">
                📊 Les actions du secteur
              </div>
            </div>
            {secteur && (
              <span className="text-[10px] font-mono text-slate-500">
                {secteur.pct_hausse}% en hausse — {secteur.sentiment}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {stocks.slice(0, 9).map((s) => (
              <div key={s.ticker} className="bg-black/30 rounded-lg p-3 border border-white/5">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-xs font-semibold text-white truncate">{s.nom}</span>
                  <span className="text-[9px] font-mono text-slate-600 shrink-0">{s.ticker}</span>
                </div>
                <div className="flex items-baseline justify-between gap-2 mt-1">
                  <span className="text-sm font-mono text-slate-300">{s.price}</span>
                  <span className={`text-xs font-mono font-semibold ${s.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {s.change_pct >= 0 ? "▴" : "▾"} {pct(s.change_pct)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nouveautés par thème */}
      {nouveautes.length > 0 && (
        <div className="glass rounded-xl p-5 card-hover border border-white/5 animate-slide-up space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-pink-400" />
            <div className="text-[10px] text-pink-400 uppercase tracking-widest font-semibold">
              🆕 Les nouveautés à connaître
            </div>
          </div>
          <div className="space-y-3">
            {nouveautes.slice(0, 5).map((n, i) => {
              const cfg = themeConfig(n.theme)
              return (
                <div key={i} className="bg-black/30 rounded-lg p-3.5 border border-white/5 space-y-1.5">
                  <div className="flex items-start gap-2 flex-wrap">
                    <span className={`shrink-0 text-[10px] font-semibold font-mono px-2 py-0.5 rounded border ${cfg.badge}`}>
                      {cfg.icon} {cfg.label}
                    </span>
                    <span className="text-sm font-semibold text-white leading-snug">{n.titre}</span>
                  </div>
                  <p className="text-slate-300 text-xs leading-relaxed">{n.quoi}</p>
                  {n.pourquoi && (
                    <p className="text-slate-500 text-xs leading-relaxed italic">
                      Pourquoi ça compte : {n.pourquoi}
                    </p>
                  )}
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
              )
            })}
          </div>
        </div>
      )}

      {/* Signaux approfondis */}
      {signals.map((sig, i) => {
        const cfg = themeConfig(sig.theme)
        return (
          <div key={i} className="space-y-1.5">
            <span className={`inline-block text-[10px] font-semibold font-mono px-2 py-0.5 rounded border ${cfg.badge}`}>
              {cfg.icon} {cfg.label}
            </span>
            <SignalCard signal={sig} index={i} sector="ecommerce" />
          </div>
        )
      })}

      {/* À tester cette semaine */}
      {actions.length > 0 && (
        <div className="glass border-l-2 accent-ecommerce rounded-xl p-5 card-hover animate-slide-up">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-pink-400 shadow-[0_0_6px_#ec4899] animate-pulse-glow" />
            <div className="text-[10px] text-pink-400 uppercase tracking-widest font-semibold">
              ✅ À tester cette semaine
            </div>
          </div>
          <ul className="space-y-2.5">
            {actions.slice(0, 2).map((a, i) => (
              <li key={i} className="text-sm text-slate-300 flex gap-3 items-start">
                <span className="text-pink-500/60 mt-0.5 shrink-0">→</span>
                {a}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!signals.length && !nouveautes.length && !ecommerce.outils?.length && (
        <div className="text-slate-500 text-sm text-center py-12 glass rounded-xl border border-white/5">
          Aucune nouveauté e-commerce aujourd&apos;hui
        </div>
      )}
    </div>
  )
}
