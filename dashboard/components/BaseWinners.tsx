import type { BaseWinner } from "@/lib/types"

const STATUT_BADGE: Record<string, string> = {
  "BANGER":       "bg-red-500/15 border-red-500/40 text-red-300",
  "EXPLOSE":      "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
  "SANS TRAFIC":  "bg-violet-500/15 border-violet-500/40 text-violet-300",
  "A SURVEILLER": "bg-blue-500/15 border-blue-500/40 text-blue-300",
  "STABLE":       "bg-slate-500/15 border-slate-500/40 text-slate-300",
}

const VERDICT_BADGE: Record<string, string> = {
  "GO TEST":      "text-emerald-300",
  "A SURVEILLER": "text-amber-300",
}

const MARCHE_COLOR: Record<string, string> = {
  LIBRE: "text-emerald-400", PARTIEL: "text-amber-400", PRIS: "text-red-400", "A VERIFIER": "text-slate-500",
}

type Props = { items?: BaseWinner[] }

/** La base de winners : tout ce que le radar a trouvé et qui reste testable, par date de découverte. */
export default function BaseWinners({ items }: Props) {
  const rows = [...(items ?? [])].sort((a, b) => (b.trouve_le || "").localeCompare(a.trouve_le || ""))

  return (
    <div className="space-y-5">
      <div className="glass rounded-xl p-5 border border-amber-500/10">
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_6px_#f59e0b] animate-pulse-glow" />
            <div className="text-[10px] text-amber-400 uppercase tracking-widest font-semibold">🏆 Base de winners</div>
          </div>
          <span className="text-[10px] font-mono text-slate-500">{rows.length} produit{rows.length > 1 ? "s" : ""} testable{rows.length > 1 ? "s" : ""}</span>
        </div>
        <p className="text-slate-500 text-xs leading-relaxed">
          Tout ce que le radar a proposé et qui reste testable : vivant, un de tes marchés ouvert, stade ≤ 3, prix ≥ 30 €.
          Le lundi, chaque produit est rafraîchi (pubs, courbe) et le fichier Excel est déposé sur ton Drive — c&apos;est là que tu mets ton verdict.
        </p>
      </div>

      {rows.length === 0 && (
        <div className="text-slate-500 text-sm text-center py-12 glass rounded-xl border border-white/5">
          La base se remplit avec les pépites de chaque matin.
        </div>
      )}

      <div className="space-y-3">
        {rows.map((w) => (
          <div key={w.boutique} className="glass rounded-xl p-4 card-hover border border-white/5 space-y-2.5">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-white leading-snug">{w.produit}</div>
                <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                  {w.boutique}{w.niche ? ` · ${w.niche}` : ""}{w.prix ? ` · ${w.prix}` : ""}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 text-[10px] font-mono">
                <span className="text-slate-500">trouvé le {w.trouve_le}</span>
                {w.statut && (
                  <span className={`px-2 py-0.5 rounded border font-semibold ${STATUT_BADGE[w.statut] ?? STATUT_BADGE.STABLE}`}>{w.statut}</span>
                )}
                {w.verdict_cortex && (
                  <span className={`font-bold ${VERDICT_BADGE[w.verdict_cortex] ?? "text-slate-300"}`}>{w.verdict_cortex}</span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-slate-400">
              <span>Pubs : <span className="text-white">{w.chiffres?.ads_actives ?? "?"}</span></span>
              <span>×4 sem. : <span className="text-white">{w.chiffres?.acceleration != null ? `×${w.chiffres.acceleration}` : "?"}</span></span>
              <span>Courbe : <span className="text-slate-300">{w.chiffres?.courbe_ads ?? "?"}</span></span>
              {w.chiffres?.age_jours != null && <span>Âge : <span className="text-white">{w.chiffres.age_jours} j</span></span>}
              {w.stade_sophistication && <span>Stade : <span className="text-white">{w.stade_sophistication}/5</span></span>}
              {w.marches && (
                <span>
                  {Object.entries(w.marches).map(([k, v]) => (
                    <span key={k} className="mr-2">{k} <span className={MARCHE_COLOR[v] ?? "text-slate-400"}>{v}</span></span>
                  ))}
                </span>
              )}
            </div>

            {w.ou_lancer && <p className="text-xs text-slate-300 leading-relaxed"><span className="text-amber-400/80">🌍 </span>{w.ou_lancer}</p>}

            <div className="flex items-center gap-4 text-[11px]">
              {w.verdict_badr ? (
                <span className="px-2 py-0.5 rounded border border-amber-500/40 text-amber-200 bg-amber-500/10 font-mono">Mon verdict : {w.verdict_badr}</span>
              ) : (
                <span className="text-slate-600 font-mono">Mon verdict : à remplir dans l&apos;Excel</span>
              )}
              {w.lien_boutique && (
                <a href={w.lien_boutique} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300">↗ Boutique</a>
              )}
              {w.lien_adlibrary && (
                <a href={w.lien_adlibrary} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300">↗ Leurs pubs</a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
