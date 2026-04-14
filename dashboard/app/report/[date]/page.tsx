import { getReportByDate } from "@/lib/supabase"
import NavBar from "@/components/NavBar"
import SignalCard from "@/components/SignalCard"
import CryptoSection from "@/components/CryptoSection"
import MarketSection from "@/components/MarketSection"
import Link from "next/link"
import { notFound } from "next/navigation"

export const dynamic = 'force-dynamic' // Données temps réel depuis Supabase

const DAYS_FR = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
const MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00")
  return `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} ${d.getFullYear()}`
}

export default async function ReportPage({ params }: { params: { date: string } }) {
  const report = await getReportByDate(params.date)
  if (!report || !report.report_json) notFound()

  const json = report.report_json

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 space-y-8">
        <div className="flex items-center gap-4">
          <Link href="/archive" className="text-slate-500 hover:text-slate-300 transition-colors text-sm">
            ← Archive
          </Link>
          <div>
            <h1 className="text-white font-bold text-lg">{formatDate(report.report_date)}</h1>
            <p className="text-slate-500 text-sm">{report.signals_count} signaux analysés</p>
          </div>
        </div>

        {/* IA */}
        <section>
          <h2 className="text-blue-400 font-semibold mb-4">🧠 Intelligence Artificielle</h2>
          <div className="space-y-4">
            {json.ai.signals?.map((sig, i) => <SignalCard key={i} signal={sig} index={i} sector="ai" />)}
          </div>
        </section>

        {/* Crypto */}
        <section>
          <h2 className="text-yellow-400 font-semibold mb-4">💰 Crypto & Web3</h2>
          <CryptoSection crypto={json.crypto} />
        </section>

        {/* Marchés */}
        <section>
          <h2 className="text-green-400 font-semibold mb-4">📈 Marchés & Macro</h2>
          <MarketSection market={json.market} />
        </section>

        {/* DeepTech */}
        <section>
          <h2 className="text-purple-400 font-semibold mb-4">⚡ DeepTech & Ruptures</h2>
          <div className="space-y-4">
            {json.deeptech.signals?.map((sig, i) => <SignalCard key={i} signal={sig} index={i} sector="deeptech" />)}
          </div>
        </section>

        {/* Nexus */}
        {json.nexus?.has_connexion && (
          <section>
            <h2 className="text-orange-400 font-semibold mb-4">🔗 Nexus — Connexion du jour</h2>
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
              {json.nexus.secteurs_lies?.length > 0 && (
                <div className="text-xs text-slate-500 italic mb-2">{json.nexus.secteurs_lies.join(" × ")}</div>
              )}
              <p className="text-slate-200 leading-relaxed">{json.nexus.connexion}</p>
            </div>
          </section>
        )}

        {/* Question du jour */}
        {json.nexus?.question && (
          <section>
            <div className="bg-[#12121a] border border-orange-800/30 rounded-xl p-5">
              <div className="text-xs text-orange-400 font-medium mb-2">Question du matin</div>
              <p className="text-white font-medium">{json.nexus.question}</p>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
