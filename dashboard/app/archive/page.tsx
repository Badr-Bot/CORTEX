import { getReportHistory } from "@/lib/supabase"
import NavBar from "@/components/NavBar"
import Link from "next/link"

export const revalidate = 3600

const DAYS_FR = ["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"]
const MONTHS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00")
  return `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} ${d.getFullYear()}`
}

export default async function ArchivePage() {
  const reports = await getReportHistory(60)

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 space-y-6">
        <div>
          <h1 className="text-white font-bold text-lg">Archive des rapports</h1>
          <p className="text-slate-500 text-sm">{reports.length} rapport{reports.length !== 1 ? "s" : ""} disponible{reports.length !== 1 ? "s" : ""}</p>
        </div>

        {reports.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            Aucun rapport archivé pour l'instant.
          </div>
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <Link
                key={r.id}
                href={`/report/${r.report_date}`}
                className="flex items-center justify-between bg-[#12121a] border border-[#1e1e2e] hover:border-slate-600 rounded-xl px-5 py-4 transition-colors group"
              >
                <div>
                  <div className="text-white text-sm font-medium group-hover:text-blue-300 transition-colors">
                    {formatDate(r.report_date)}
                  </div>
                  {r.question && (
                    <div className="text-xs text-slate-500 mt-0.5 line-clamp-1 italic">
                      {r.question}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-xs text-slate-500">{r.signals_count} signaux</div>
                  <span className="text-slate-600 group-hover:text-slate-400 transition-colors">→</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
