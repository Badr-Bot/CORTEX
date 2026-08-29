import type { EcomTool, RadarProduit, ToolCategory } from "@/lib/types"

const CATEGORIES: Record<ToolCategory, { icon: string; label: string; badge: string }> = {
  video:           { icon: "🎬", label: "Vidéo & créas",      badge: "bg-pink-500/10 border-pink-500/30 text-pink-300"         },
  produit_gagnant: { icon: "🏆", label: "Produit gagnant",    badge: "bg-amber-500/10 border-amber-500/30 text-amber-300"      },
  analyse_marche:  { icon: "📊", label: "Analyse de marché",  badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" },
  scraping:        { icon: "🕷️", label: "Scraping",           badge: "bg-slate-500/10 border-slate-500/30 text-slate-300"      },
  pub:             { icon: "📣", label: "Pubs Meta / TikTok", badge: "bg-blue-500/10 border-blue-500/30 text-blue-300"         },
  fiches_produit:  { icon: "🖼️", label: "Fiches produit",     badge: "bg-violet-500/10 border-violet-500/30 text-violet-300"   },
  service_client:  { icon: "💬", label: "Service client",     badge: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"         },
  skill_claude:    { icon: "🧠", label: "Skill Claude",       badge: "bg-orange-500/10 border-orange-500/30 text-orange-300"   },
  automatisation:  { icon: "⚙️", label: "Automatisation",     badge: "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"   },
}

function categoryConfig(cat?: string) {
  return CATEGORIES[(cat as ToolCategory)] ?? CATEGORIES.automatisation
}

const STATUT_BADGE: Record<string, string> = {
  "BANGER":       "bg-red-500/15 border-red-500/40 text-red-300",
  "EXPLOSE":      "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
  "SANS TRAFIC":  "bg-violet-500/15 border-violet-500/40 text-violet-300",
  "A SURVEILLER": "bg-blue-500/15 border-blue-500/40 text-blue-300",
}

const VERDICT_BADGE: Record<string, string> = {
  "GO TEST":      "bg-emerald-500/20 border-emerald-500/50 text-emerald-200",
  "A SURVEILLER": "bg-amber-500/15 border-amber-500/40 text-amber-200",
  "ECARTER":      "bg-slate-500/15 border-slate-500/40 text-slate-300",
}

const MARCHE_FR_BADGE: Record<string, string> = {
  "LIBRE":      "text-emerald-400",
  "PRIS":       "text-red-400",
  "PARTIEL":    "text-amber-400",
  "A VERIFIER": "text-slate-400",
}

const DIFFICULTE_LABEL: Record<string, string> = {
  facile: "🟢 facile", moyen: "🟡 moyen", difficile: "🔴 difficile",
}

function RadarCard({ p }: { p: RadarProduit }) {
  return (
    <div className="bg-black/30 rounded-lg p-4 border border-white/5 space-y-3">
      {/* En-tête : produit, boutique, statut, verdict */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white leading-snug">{p.produit}</div>
          <div className="text-[11px] font-mono text-slate-500 mt-0.5">
            {p.boutique}{p.niche ? ` · ${p.niche}` : ""}{p.prix ? ` · ${p.prix}` : ""}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] font-semibold font-mono px-2 py-0.5 rounded border ${STATUT_BADGE[p.statut] ?? STATUT_BADGE["A SURVEILLER"]}`}>
            {p.statut}
          </span>
          <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${VERDICT_BADGE[p.verdict] ?? VERDICT_BADGE["A SURVEILLER"]}`}>
            {p.verdict}
          </span>
        </div>
      </div>

      {/* Les 4 questions de Badr */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        <div className="bg-black/30 rounded-md p-3 border border-white/5 space-y-1">
          <div className="text-[10px] text-amber-400/80 uppercase tracking-wider">💶 Combien par jour ?</div>
          <p className="text-xs text-slate-300 leading-relaxed">{p.ca_jour_estime}</p>
        </div>
        <div className="bg-black/30 rounded-md p-3 border border-white/5 space-y-1">
          <div className="text-[10px] text-amber-400/80 uppercase tracking-wider">🧗 Dur ou pas ? {DIFFICULTE_LABEL[p.difficulte] ?? p.difficulte}</div>
          <p className="text-xs text-slate-300 leading-relaxed">{p.difficulte_pourquoi}</p>
        </div>
        <div className="bg-black/30 rounded-md p-3 border border-white/5 space-y-1">
          <div className="text-[10px] text-amber-400/80 uppercase tracking-wider">📍 Stade du marché</div>
          <p className="text-xs text-slate-300 leading-relaxed">{p.stade_marche}</p>
        </div>
        <div className="bg-black/30 rounded-md p-3 border border-white/5 space-y-1">
          <div className="text-[10px] text-amber-400/80 uppercase tracking-wider">
            👀 Les gens connaissent ? · France : <span className={MARCHE_FR_BADGE[p.marche_fr] ?? "text-slate-400"}>{p.marche_fr}</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">{p.notoriete}</p>
          {p.marche_fr_detail && <p className="text-[11px] text-slate-500 italic">{p.marche_fr_detail}</p>}
        </div>
      </div>

      {/* Le signal chiffré */}
      <p className="text-xs text-slate-400 leading-relaxed">
        <span className="text-slate-300 font-medium">Le signal : </span>{p.signal}
      </p>

      {/* Critères */}
      {(p.criteres_ok?.length || p.criteres_ko?.length) ? (
        <div className="flex flex-wrap gap-1.5">
          {p.criteres_ok?.map((c) => (
            <span key={`ok-${c}`} className="text-[10px] px-2 py-0.5 rounded-full border border-emerald-500/30 text-emerald-400 bg-emerald-500/10">✓ {c}</span>
          ))}
          {p.criteres_ko?.map((c) => (
            <span key={`ko-${c}`} className="text-[10px] px-2 py-0.5 rounded-full border border-white/5 text-slate-500 bg-black/20">✗ {c}</span>
          ))}
        </div>
      ) : null}

      {/* Verdict + budget */}
      <div className="bg-black/40 rounded-md px-4 py-3 border border-white/5 space-y-1">
        <p className="text-xs text-slate-200 leading-relaxed">
          <span className="text-emerald-400/80 font-medium">Verdict : </span>{p.verdict_pourquoi}
        </p>
        <p className="text-[11px] text-slate-500">💸 Budget pour savoir : {p.budget_test}</p>
      </div>

      <div className="flex items-center gap-4">
        <a href={p.lien_boutique} target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors">
          <span className="opacity-60">↗</span> Boutique
        </a>
        {p.lien_adlibrary && (
          <a href={p.lien_adlibrary} target="_blank" rel="noopener noreferrer"
             className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors">
            <span className="opacity-60">↗</span> Leurs pubs (Ad Library)
          </a>
        )}
      </div>
    </div>
  )
}

type Props = {
  outils?: EcomTool[]
  radar?: RadarProduit[]
}

/** La boîte à outils du jour + le radar produits : ce que Badr peut utiliser cette semaine. */
export default function EcomToolbox({ outils, radar }: Props) {
  const hasTools = !!outils && outils.length > 0
  const hasRadar = !!radar && radar.length > 0
  if (!hasTools && !hasRadar) return null

  return (
    <>
      {hasTools && (
        <div className="glass border-l-2 accent-ecommerce rounded-xl p-5 card-hover animate-slide-up space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-pink-400 shadow-[0_0_6px_#ec4899] animate-pulse-glow" />
              <div className="text-[10px] text-pink-400 uppercase tracking-widest font-semibold">
                🧰 Boîte à outils — à utiliser cette semaine
              </div>
            </div>
            <span className="text-[10px] font-mono text-slate-600">{outils!.length} outils</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {outils!.map((t, i) => {
              const cfg = categoryConfig(t.categorie)
              return (
                <div key={`${t.source_url}-${i}`} className="bg-black/30 rounded-lg p-4 border border-white/5 space-y-2 flex flex-col">
                  <div className="flex items-start justify-between gap-2">
                    <span className={`shrink-0 text-[10px] font-semibold font-mono px-2 py-0.5 rounded border ${cfg.badge}`}>
                      {cfg.icon} {cfg.label}
                    </span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${t.gratuit === false ? "text-amber-400 bg-amber-500/10" : "text-emerald-400 bg-emerald-500/10"}`}>
                      {t.gratuit === false ? "payant" : "gratuit"}
                    </span>
                  </div>
                  <a
                    href={t.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold text-white hover:text-indigo-300 transition-colors leading-snug break-words"
                  >
                    {t.nom}
                  </a>
                  <p className="text-xs text-slate-300 leading-relaxed">{t.quoi}</p>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    <span className="text-pink-400/80 font-medium">Pour toi : </span>
                    {t.pour_toi}
                  </p>
                  <div className="mt-auto pt-2 border-t border-white/5 text-xs text-slate-300 leading-relaxed">
                    <span className="text-emerald-400/80 font-medium">▶ Pour tester : </span>
                    {t.comment_tester}
                  </div>
                  <a
                    href={t.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    <span className="opacity-60">↗</span>
                    {t.source_name || "Ouvrir"}
                  </a>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {hasRadar && (
        <div className="glass rounded-xl p-5 card-hover border border-amber-500/10 animate-slide-up space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_#f59e0b] animate-pulse-glow" />
              <div className="text-[10px] text-amber-400 uppercase tracking-widest font-semibold">
                🎯 Radar produits — les 3 du jour, analysés
              </div>
            </div>
            <span className="text-[10px] font-mono text-slate-600">TrendTrack · méthode MASTER</span>
          </div>
          <div className="space-y-3">
            {radar!.map((p, i) => (
              <RadarCard key={`${p.boutique}-${i}`} p={p} />
            ))}
          </div>
        </div>
      )}
    </>
  )
}
