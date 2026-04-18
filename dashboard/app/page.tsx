import { getLatestReport, getTodayJournal } from "@/lib/supabase"
import NavBar from "@/components/NavBar"
import SignalCard from "@/components/SignalCard"
import CryptoSection from "@/components/CryptoSection"
import MarketSection from "@/components/MarketSection"
import QuestionPanel from "@/components/QuestionPanel"
import SectionQuestionsPanel from "@/components/SectionQuestionsPanel"
import type { ReportJSON } from "@/lib/types"

export const dynamic = 'force-dynamic'

const LEXIQUE = [
  {
    category: "📊 Marchés & Économie",
    color: "emerald",
    terms: [
      { term: "S&P 500", def: "Indice regroupant les 500 plus grandes entreprises américaines coté en bourse. Baromètre principal de la santé économique US." },
      { term: "Nasdaq", def: "Indice boursier américain à fort biais technologique et IA. Plus volatile que le S&P 500." },
      { term: "VIX", def: "\"Indice de la peur\". Mesure la volatilité implicite anticipée du S&P 500. Sous 20 = calme. Entre 20-30 = stress modéré. Au-dessus de 30 = panique." },
      { term: "DXY", def: "Indice de force du dollar américain face à un panier de 6 devises majeures. DXY en hausse = pression sur les actifs risqués (actions, crypto, or)." },
      { term: "US 10Y", def: "Taux d'intérêt des obligations d'État américaines à 10 ans. Taux de référence mondial. Hausse = coût du crédit plus élevé = pression sur les valuations." },
      { term: "Régime de marché", def: "Phase macro actuelle : Expansion (croissance), Transition (incertitude), Contraction (récession). Détermine le biais directionnel global." },
      { term: "Score de récession", def: "Note de 0 à 10 calculée par CORTEX. 0-2 = risque faible, 3-4 = modéré, 5-6 = élevé, 7+ = critique. Basé sur les indicateurs avancés (chômage, yield curve, PMI...)." },
    ],
  },
  {
    category: "₿ Crypto",
    color: "amber",
    terms: [
      { term: "Fear & Greed Index", def: "Indice de 0 à 100 mesurant le sentiment du marché crypto. 0-25 = peur extrême (souvent opportunité d'achat), 75-100 = greed extrême (prudence recommandée)." },
      { term: "BTC Dominance", def: "Part de Bitcoin dans la capitalisation totale du marché crypto. En hausse = fuite vers la qualité (Bitcoin). En baisse = capitaux vers les altcoins (\"alt season\")." },
      { term: "Funding Rate", def: "Taux de financement des positions à terme perpetuels. Positif = les longs paient les shorts (marché haussier spéculatif). Négatif = les shorts paient les longs (marché défensif)." },
      { term: "Phase du cycle", def: "Stade du cycle crypto : Accumulation (creux), Bull market (hausse), Distribution (sommet), Bear market (baisse). Chaque phase dure plusieurs mois." },
      { term: "Bear case", def: "Scénario pessimiste — les conditions qui invalideraient la thèse haussière. À surveiller pour gérer le risque et adapter sa position." },
    ],
  },
  {
    category: "🎯 Signaux & Trading",
    color: "blue",
    terms: [
      { term: "Conviction ★", def: "Note de 1 à 5 étoiles sur la solidité de l'analyse. 1★ = signal spéculatif à petit sizing. 5★ = signal fort avec sources multiples, fort consensus." },
      { term: "Sizing (Position)", def: "Taille recommandée : Fort = pleine exposition (5-10% portefeuille), Moyen = exposition partielle (2-5%), Faible = petit test ou couverture (<2%)." },
      { term: "Stop si", def: "Condition d'invalidation du signal. Si cet événement survient, le signal n'est plus valable et il faut sortir ou réduire la position." },
      { term: "Impact direct", def: "Conséquence immédiate et mesurable sur un actif ou secteur spécifique. L'effet le plus proche du signal." },
      { term: "Impact systémique", def: "Conséquence en chaîne sur d'autres secteurs, marchés ou actifs. Vision macro de la propagation du signal." },
      { term: "Thèse opposée", def: "Argument contraire à la thèse principale — pourquoi le signal pourrait être erroné. Essentiel pour la gestion du risque." },
    ],
  },
  {
    category: "⚡ DeepTech",
    color: "violet",
    terms: [
      { term: "Peer-reviewed", def: "Recherche validée par des pairs scientifiques et publiée dans une revue académique. Indicateur de solidité et reproductibilité." },
      { term: "Horizon", def: "Délai estimé avant impact concret sur les marchés : Court (1-2 ans), Moyen (3-5 ans), Long (5-10 ans), Très long (10+ ans)." },
      { term: "Score de crédibilité", def: "Note 0-10 évaluant la maturité technologique. Combine peer-review, financement, prototype existant et premiers cas d'adoption réels." },
      { term: "Prototype", def: "Démonstration physique ou logicielle existante de la technologie. Réduit significativement le risque de réalisation." },
      { term: "Adoption", def: "Premiers cas d'usage réels déployés en production commerciale. Validation par le marché, pas seulement par la recherche." },
    ],
  },
  {
    category: "🧠 Système CORTEX",
    color: "orange",
    terms: [
      { term: "Signal", def: "Opportunité ou risque identifié avec une thèse d'investissement structurée : fait → implications → action → sizing → stop loss." },
      { term: "Nexus", def: "Section qui identifie les connexions transversales entre secteurs (IA × Crypto × Marchés × DeepTech). Révèle les confluences de signaux." },
      { term: "Connexion du jour", def: "Insight synthétique reliant les signaux de différents secteurs en une narrative cohérente. La vue d'ensemble au-delà des silos." },
      { term: "Question du matin", def: "Interrogation quotidienne pour forcer une décision avant d'ouvrir les marchés. L'objectif : distinguer l'investisseur actif du spectateur passif." },
    ],
  },
]

const LEXIQUE_COLORS: Record<string, { border: string; label: string; dot: string; badge: string }> = {
  emerald: { border: "border-emerald-500/20", label: "text-emerald-400", dot: "bg-emerald-400", badge: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" },
  amber:   { border: "border-amber-500/20",   label: "text-amber-400",   dot: "bg-amber-400",   badge: "bg-amber-500/10 border-amber-500/30 text-amber-300"   },
  blue:    { border: "border-blue-500/20",     label: "text-blue-400",    dot: "bg-blue-400",    badge: "bg-blue-500/10 border-blue-500/30 text-blue-300"     },
  violet:  { border: "border-violet-500/20",   label: "text-violet-400",  dot: "bg-violet-400",  badge: "bg-violet-500/10 border-violet-500/30 text-violet-300" },
  orange:  { border: "border-orange-500/20",   label: "text-orange-400",  dot: "bg-orange-400",  badge: "bg-orange-500/10 border-orange-500/30 text-orange-300" },
}

function LexiqueSection() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="glass rounded-xl p-5 border border-cyan-500/10">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#06b6d4] animate-pulse-glow" />
          <div className="text-[10px] text-cyan-400 uppercase tracking-widest font-semibold">📖 Lexique CORTEX</div>
        </div>
        <p className="text-slate-500 text-xs">Tous les termes techniques utilisés dans les analyses — pour lire les signaux sans ambiguïté.</p>
      </div>

      {LEXIQUE.map((section) => {
        const c = LEXIQUE_COLORS[section.color]
        return (
          <div key={section.category} className={`glass rounded-xl p-5 card-hover border ${c.border} space-y-4`}>
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
              <div className={`text-[10px] uppercase tracking-widest font-semibold ${c.label}`}>{section.category}</div>
            </div>
            <div className="space-y-3">
              {section.terms.map((t) => (
                <div key={t.term} className="flex gap-3 items-start">
                  <span className={`shrink-0 text-xs font-semibold font-mono px-2 py-0.5 rounded border ${c.badge} mt-0.5`}>
                    {t.term}
                  </span>
                  <p className="text-slate-400 text-xs leading-relaxed">{t.def}</p>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const DAYS_FR   = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
const MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00")
  return `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} ${d.getFullYear()}`
}

const TABS = [
  { id: "ai",       label: "IA",        icon: "🧠", color: "blue"    },
  { id: "crypto",   label: "Crypto",    icon: "₿",  color: "amber"   },
  { id: "market",   label: "Marchés",   icon: "📈", color: "emerald" },
  { id: "deeptech", label: "DeepTech",  icon: "⚡", color: "violet"  },
  { id: "nexus",    label: "Nexus",     icon: "◈",  color: "orange"  },
  { id: "lexique",  label: "Lexique",   icon: "📖", color: "cyan"    },
] as const

type TabId = typeof TABS[number]["id"]

const TAB_COLORS: Record<string, { active: string; dot: string; shadow: string }> = {
  blue:    { active: "bg-blue-500/15 text-blue-300 border-blue-500/40",    dot: "bg-blue-400",    shadow: "shadow-[0_0_12px_rgba(99,102,241,0.3)]"  },
  amber:   { active: "bg-amber-500/15 text-amber-300 border-amber-500/40", dot: "bg-amber-400",   shadow: "shadow-[0_0_12px_rgba(245,158,11,0.3)]"  },
  emerald: { active: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40", dot: "bg-emerald-400", shadow: "shadow-[0_0_12px_rgba(16,185,129,0.3)]" },
  violet:  { active: "bg-violet-500/15 text-violet-300 border-violet-500/40", dot: "bg-violet-400",  shadow: "shadow-[0_0_12px_rgba(168,85,247,0.3)]"  },
  orange:  { active: "bg-orange-500/15 text-orange-300 border-orange-500/40", dot: "bg-orange-400",  shadow: "shadow-[0_0_12px_rgba(249,115,22,0.3)]"   },
  cyan:    { active: "bg-cyan-500/15 text-cyan-300 border-cyan-500/40",    dot: "bg-cyan-400",    shadow: "shadow-[0_0_12px_rgba(6,182,212,0.3)]"    },
}

function EmptyState() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-6 animate-fade-in">
          <div className="relative inline-block">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500/20 to-violet-500/20 border border-indigo-500/20 flex items-center justify-center mx-auto animate-float">
              <span className="text-3xl">⚡</span>
            </div>
            <div className="absolute -inset-4 rounded-full border border-indigo-500/10 animate-ping opacity-30" />
          </div>
          <div>
            <h1 className="text-white font-bold text-xl mb-2 gradient-text">Pas encore de rapport aujourd'hui</h1>
            <p className="text-slate-500 text-sm font-mono">CORTEX génère le rapport à 06h00 chaque matin</p>
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-slate-600 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/50 animate-pulse-glow" />
            Système en veille
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500/50 animate-pulse-glow" />
          </div>
        </div>
      </main>
    </div>
  )
}

function SectorContent({ tab, report }: { tab: TabId; report: ReportJSON }) {
  if (tab === "ai") {
    return (
      <div className="space-y-5">
        {report.ai.signals?.map((sig, i) => (
          <SignalCard key={i} signal={sig} index={i} sector="ai" />
        ))}
        {report.ai.watchlist && report.ai.watchlist.length > 0 && (
          <div className="glass border-l-2 accent-ai rounded-xl p-5 card-hover animate-slide-up">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_6px_#6366f1] animate-pulse-glow" />
              <div className="text-[10px] text-blue-400 uppercase tracking-widest font-semibold">
                👁️ Signaux à surveiller
              </div>
            </div>
            <ul className="space-y-2.5">
              {report.ai.watchlist.map((item, i) => (
                <li key={i} className="text-sm text-slate-300 flex gap-3 items-start">
                  <span className="text-blue-500/60 mt-0.5 shrink-0">→</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  if (tab === "crypto") return <CryptoSection crypto={report.crypto} />
  if (tab === "market") return <MarketSection market={report.market} />

  if (tab === "deeptech") {
    return (
      <div className="space-y-5">
        {report.deeptech.signals?.map((sig, i) => (
          <SignalCard key={i} signal={sig} index={i} sector="deeptech" />
        ))}
        {!report.deeptech.signals?.length && (
          <div className="text-slate-500 text-sm text-center py-12 glass rounded-xl border border-white/5">
            Aucun signal deeptech aujourd'hui
          </div>
        )}
      </div>
    )
  }

  if (tab === "nexus") {
    const n = report.nexus
    return (
      <div className="space-y-4">
        <div className="glass border-l-2 accent-nexus rounded-xl p-5 card-hover animate-slide-up">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1.5 h-1.5 rounded-full bg-orange-400 shadow-[0_0_6px_#f97316] animate-pulse-glow" />
            <div className="text-[10px] text-orange-400 uppercase tracking-widest font-semibold">
              🔗 Connexion du jour
            </div>
          </div>
          {n.has_connexion && n.connexion ? (
            <>
              {n.secteurs_lies?.length > 0 && (
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  {n.secteurs_lies.map((s, i) => (
                    <span key={i} className="text-xs text-slate-500 bg-white/5 border border-white/10 rounded-full px-2 py-0.5">
                      {s}
                    </span>
                  ))}
                  <span className="text-slate-600">×</span>
                </div>
              )}
              <p className="text-slate-200 leading-relaxed">{n.connexion}</p>
            </>
          ) : (
            <p className="text-slate-500 italic">
              Pas de connexion significative aujourd'hui — les secteurs évoluent indépendamment.
            </p>
          )}
        </div>
      </div>
    )
  }

  if (tab === "lexique") return <LexiqueSection />

  return null
}

function getSectionQuestions(tab: TabId, report: ReportJSON): string[] {
  const map: Partial<Record<TabId, string[]>> = {
    ai:       (report.ai as any)?.questions,
    crypto:   (report.crypto as any)?.questions,
    market:   (report.market as any)?.questions,
    deeptech: (report.deeptech as any)?.questions,
    nexus:    (report.nexus as any)?.questions,
  }
  return map[tab] ?? []
}

interface PageProps {
  searchParams: { tab?: string }
}

export default async function DashboardPage({ searchParams }: PageProps) {
  let report = null
  let journalEntry = null
  try {
    ;[report, journalEntry] = await Promise.all([
      getLatestReport(),
      getTodayJournal(),
    ])
  } catch {
    return <EmptyState />
  }

  if (!report || !report.report_json || !Object.keys(report.report_json).length) {
    return <EmptyState />
  }

  const activeTab = (searchParams.tab as TabId) || "ai"
  const json = report.report_json

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-3 sm:px-4 py-3 sm:py-5 space-y-4 sm:space-y-6">

        {/* Hero header */}
        <div className="animate-slide-up space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono text-indigo-400/60 uppercase tracking-widest">📋 Rapport quotidien</span>
                <div className="h-px flex-1 max-w-[80px] bg-gradient-to-r from-indigo-500/30 to-transparent" />
              </div>
              <h1 className="text-2xl font-bold text-white leading-tight">
                ☀️ Rapport du <span className="gradient-text">matin</span>
              </h1>
              <p className="text-slate-500 text-sm mt-1 font-mono">{formatDate(report.report_date)}</p>
            </div>
            <div className="text-right shrink-0">
              <div className="glass rounded-xl px-4 py-2.5 border border-indigo-500/20">
                <div className="text-2xl font-bold font-mono gradient-text">{report.signals_count}</div>
                <div className="text-[10px] text-slate-500 uppercase tracking-wider">signaux</div>
              </div>
            </div>
          </div>

          {/* Decorative line */}
          <div className="h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />
        </div>

        {/* Tabs — sticky sous le header */}
        <div className="sticky top-14 z-40 bg-[#040408] -mx-3 sm:-mx-4 px-3 sm:px-4 py-2 border-b border-white/5 flex gap-2 overflow-x-auto scrollbar-hide animate-slide-up stagger-1">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            const colors = TAB_COLORS[tab.color]
            return (
              <a
                key={tab.id}
                href={`/?tab=${tab.id}`}
                className={`flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 border ${
                  isActive
                    ? `${colors.active} ${colors.shadow}`
                    : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"
                }`}
              >
                <span className="text-base leading-none">{tab.icon}</span>
                {tab.label}
                {isActive && (
                  <span className={`w-1.5 h-1.5 rounded-full ${colors.dot} shadow-lg`} />
                )}
              </a>
            )
          })}
        </div>

        {/* Tab content */}
        <div className="animate-fade-in">
          <SectorContent tab={activeTab} report={json} />
        </div>

        {/* Questions par section avec champs de réponse */}
        {activeTab !== "lexique" && (() => {
          const qs = getSectionQuestions(activeTab, json)
          return qs.length > 0 ? (
            <SectionQuestionsPanel tab={activeTab} questions={qs} reportDate={report.report_date} />
          ) : null
        })()}

        {/* Question du matin — uniquement sur l'onglet Nexus */}
        {json.nexus?.question && activeTab === "nexus" && (
          <QuestionPanel
            question={json.nexus.question}
            reportDate={report.report_date}
            existingResponse={journalEntry?.your_response}
          />
        )}

        {/* Footer */}
        <div className="pt-4 pb-8 flex items-center justify-center gap-3 text-[10px] text-slate-700 font-mono">
          <span className="w-8 h-px bg-slate-800" />
          CORTEX INTELLIGENCE SYSTEM
          <span className="w-8 h-px bg-slate-800" />
        </div>
      </main>
    </div>
  )
}
