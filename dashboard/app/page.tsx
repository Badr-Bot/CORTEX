import { getLatestReport, getTodayJournal } from "@/lib/supabase"
import NavBar from "@/components/NavBar"
import SignalCard from "@/components/SignalCard"
import CryptoSection from "@/components/CryptoSection"
import MarketSection from "@/components/MarketSection"
import QuestionPanel from "@/components/QuestionPanel"
import type { ReportJSON } from "@/lib/types"

export const dynamic = 'force-dynamic'

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
] as const

type TabId = typeof TABS[number]["id"]

const TAB_COLORS: Record<string, { active: string; dot: string; shadow: string }> = {
  blue:    { active: "bg-blue-500/15 text-blue-300 border-blue-500/40",    dot: "bg-blue-400",    shadow: "shadow-[0_0_12px_rgba(99,102,241,0.3)]"  },
  amber:   { active: "bg-amber-500/15 text-amber-300 border-amber-500/40", dot: "bg-amber-400",   shadow: "shadow-[0_0_12px_rgba(245,158,11,0.3)]"  },
  emerald: { active: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40", dot: "bg-emerald-400", shadow: "shadow-[0_0_12px_rgba(16,185,129,0.3)]" },
  violet:  { active: "bg-violet-500/15 text-violet-300 border-violet-500/40", dot: "bg-violet-400",  shadow: "shadow-[0_0_12px_rgba(168,85,247,0.3)]"  },
  orange:  { active: "bg-orange-500/15 text-orange-300 border-orange-500/40", dot: "bg-orange-400",  shadow: "shadow-[0_0_12px_rgba(249,115,22,0.3)]"   },
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
                Signaux à surveiller
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
              Connexion du jour
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

  return null
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

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-6">

        {/* Hero header */}
        <div className="animate-slide-up space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-mono text-indigo-400/60 uppercase tracking-widest">Rapport quotidien</span>
                <div className="h-px flex-1 max-w-[80px] bg-gradient-to-r from-indigo-500/30 to-transparent" />
              </div>
              <h1 className="text-2xl font-bold text-white leading-tight">
                Rapport du <span className="gradient-text">matin</span>
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

        {/* Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide animate-slide-up stagger-1">
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

        {/* Question du matin */}
        {json.nexus?.question && (
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
