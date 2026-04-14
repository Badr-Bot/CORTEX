import { getLatestReport, getTodayJournal } from "@/lib/supabase"
import NavBar from "@/components/NavBar"
import SignalCard from "@/components/SignalCard"
import CryptoSection from "@/components/CryptoSection"
import MarketSection from "@/components/MarketSection"
import QuestionPanel from "@/components/QuestionPanel"
import type { ReportJSON } from "@/lib/types"

export const dynamic = 'force-dynamic' // Données temps réel depuis Supabase

const DAYS_FR = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
const MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00")
  return `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} ${d.getFullYear()}`
}

const TABS = [
  { id: "ai",       label: "🧠 IA",       color: "text-blue-400 border-blue-500"     },
  { id: "crypto",   label: "💰 Crypto",   color: "text-yellow-400 border-yellow-500" },
  { id: "market",   label: "📈 Marchés",  color: "text-green-400 border-green-500"   },
  { id: "deeptech", label: "⚡ DeepTech", color: "text-purple-400 border-purple-500" },
  { id: "nexus",    label: "🔗 Nexus",    color: "text-orange-400 border-orange-500" },
] as const

type TabId = typeof TABS[number]["id"]

function EmptyState() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="text-4xl">⚡</div>
          <div className="text-white font-semibold">Pas encore de rapport aujourd'hui</div>
          <div className="text-slate-500 text-sm">CORTEX génère le rapport à 06h00 chaque matin</div>
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
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
            <div className="text-xs text-blue-400 uppercase tracking-wider font-medium mb-3">
              Signaux à surveiller
            </div>
            <ul className="space-y-2">
              {report.ai.watchlist.map((item, i) => (
                <li key={i} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-slate-600">◦</span>{item}
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
          <div className="text-slate-500 text-sm text-center py-8">Aucun signal deeptech aujourd'hui</div>
        )}
      </div>
    )
  }

  if (tab === "nexus") {
    const n = report.nexus
    return (
      <div className="space-y-4">
        <div className="bg-[#12121a] border border-[#1e1e2e] border-l-2 border-l-orange-500 rounded-xl p-5">
          <div className="text-xs text-orange-400 uppercase tracking-wider font-medium mb-3">
            Connexion du jour
          </div>
          {n.has_connexion && n.connexion ? (
            <>
              {n.secteurs_lies?.length > 0 && (
                <div className="text-xs text-slate-500 mb-2 italic">
                  {n.secteurs_lies.join(" × ")}
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
  const [report, journalEntry] = await Promise.all([
    getLatestReport(),
    getTodayJournal(),
  ])

  if (!report || !report.report_json || !Object.keys(report.report_json).length) {
    return <EmptyState />
  }

  const activeTab = (searchParams.tab as TabId) || "ai"
  const json = report.report_json

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-white font-bold text-lg">Rapport du matin</h1>
            <p className="text-slate-500 text-sm">{formatDate(report.report_date)}</p>
          </div>
          <div className="text-xs text-slate-600">
            {report.signals_count} signaux analysés
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
          {TABS.map((tab) => (
            <a
              key={tab.id}
              href={`/?tab=${tab.id}`}
              className={`flex-shrink-0 px-4 py-2 rounded-lg text-sm font-medium transition-colors border-b-2 ${
                activeTab === tab.id
                  ? `bg-white/5 ${tab.color}`
                  : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-white/5"
              }`}
            >
              {tab.label}
            </a>
          ))}
        </div>

        {/* Contenu du tab actif */}
        <SectorContent tab={activeTab} report={json} />

        {/* Question du matin */}
        {json.nexus?.question && (
          <QuestionPanel
            question={json.nexus.question}
            reportDate={report.report_date}
            existingResponse={journalEntry?.your_response}
          />
        )}
      </main>
    </div>
  )
}
