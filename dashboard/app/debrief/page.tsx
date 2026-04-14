import { getLatestDebrief, getWeekJournal } from "@/lib/supabase"
import NavBar from "@/components/NavBar"

export const revalidate = 3600

const MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

function formatWeek(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00")
  const end = new Date(d)
  end.setDate(d.getDate() + 6)
  return `${d.getDate()} ${MONTHS_FR[d.getMonth()]} → ${end.getDate()} ${MONTHS_FR[end.getMonth()]} ${end.getFullYear()}`
}

function verdictStyle(verdict: string) {
  return {
    correct:   "bg-green-900/20 border-green-700 text-green-400",
    partiel:   "bg-yellow-900/20 border-yellow-700 text-yellow-400",
    incorrect: "bg-red-900/20 border-red-700 text-red-400",
  }[verdict] || "bg-slate-800 border-slate-600 text-slate-400"
}

function verdictIcon(v: string) {
  return { correct: "✅", partiel: "🟡", incorrect: "❌" }[v] || "❓"
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 70 ? "stroke-green-500" : score >= 45 ? "stroke-yellow-500" : "stroke-red-500"
  const circumference = 2 * Math.PI * 36
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="relative w-24 h-24">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="36" fill="none" stroke="#1e1e2e" strokeWidth="6" />
        <circle
          cx="40" cy="40" r="36" fill="none"
          className={color} strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-2xl font-bold text-white">{score}%</span>
      </div>
    </div>
  )
}

export default async function DebriefPage() {
  const [debrief, weekJournal] = await Promise.all([
    getLatestDebrief(),
    getWeekJournal(),
  ])

  const isSunday = new Date().getDay() === 0

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-6 space-y-6">

        <div>
          <h1 className="text-white font-bold text-lg">Débrief hebdomadaire</h1>
          <p className="text-slate-500 text-sm">Généré chaque dimanche à 20h00 par CORTEX</p>
        </div>

        {!debrief ? (
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-8 text-center space-y-3">
            <div className="text-3xl">🔍</div>
            <div className="text-white font-semibold">Pas encore de débrief</div>
            <div className="text-slate-500 text-sm max-w-sm mx-auto">
              CORTEX analyse tes réponses chaque dimanche à 20h00.
              {isSunday
                ? " Le débrief sera prêt ce soir."
                : " Continue à répondre aux questions chaque matin pour nourrir l'analyse."}
            </div>

            {/* Aperçu de la semaine en cours */}
            {weekJournal.length > 0 && (
              <div className="mt-6 text-left">
                <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">
                  Ta semaine en cours ({weekJournal.length} réponse{weekJournal.length > 1 ? "s" : ""})
                </div>
                <div className="space-y-2">
                  {weekJournal.map((entry) => (
                    <div key={entry.id} className="bg-[#0a0a0f] rounded-lg p-3">
                      <div className="text-xs text-slate-500 mb-1">
                        {new Date(entry.created_at).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "short" })}
                      </div>
                      <div className="text-xs text-slate-400 italic mb-1">{entry.question_asked}</div>
                      {entry.your_response ? (
                        <div className="text-sm text-slate-300">{entry.your_response}</div>
                      ) : (
                        <div className="text-xs text-slate-600">Pas de réponse</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Score global */}
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6">
              <div className="text-xs text-slate-400 uppercase tracking-wider mb-4">
                Semaine du {formatWeek(debrief.week_of)}
              </div>
              <div className="flex items-center gap-8">
                <ScoreRing score={debrief.taux_reussite} />
                <div className="space-y-2">
                  <div className="flex gap-4">
                    <div className="text-center">
                      <div className="text-green-400 text-xl font-bold">{debrief.evaluation_json.score.correct}</div>
                      <div className="text-xs text-slate-500">Correct</div>
                    </div>
                    <div className="text-center">
                      <div className="text-yellow-400 text-xl font-bold">{debrief.evaluation_json.score.partiel}</div>
                      <div className="text-xs text-slate-500">Partiel</div>
                    </div>
                    <div className="text-center">
                      <div className="text-red-400 text-xl font-bold">{debrief.evaluation_json.score.incorrect}</div>
                      <div className="text-xs text-slate-500">Incorrect</div>
                    </div>
                  </div>
                  <div className="text-xs text-slate-500">{debrief.evaluation_json.score.total} questions analysées</div>
                </div>
              </div>
            </div>

            {/* Évaluations jour par jour */}
            {debrief.evaluation_json.evaluations.length > 0 && (
              <div className="space-y-3">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Analyse jour par jour</div>
                {debrief.evaluation_json.evaluations.map((ev, i) => (
                  <div key={i} className={`border rounded-xl p-5 space-y-3 ${verdictStyle(ev.verdict)}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{verdictIcon(ev.verdict)} {ev.date}</span>
                      <span className="text-xs capitalize opacity-70">{ev.verdict}</span>
                    </div>
                    <div className="text-xs text-slate-400 italic">{ev.question}</div>
                    <div className="text-sm text-slate-300">
                      <span className="text-slate-500">Ta réponse : </span>{ev.reponse_badr}
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 space-y-2">
                      <div className="text-xs font-medium text-white">La bonne réponse :</div>
                      <p className="text-sm text-slate-300 leading-relaxed">{ev.reponse_correcte}</p>
                      <p className="text-xs text-slate-400 italic">Pourquoi : {ev.pourquoi}</p>
                    </div>
                    <div className="text-xs text-slate-300">
                      <span className="text-slate-500">→ Retenir : </span>{ev.learning}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Patterns */}
            {debrief.evaluation_json.patterns.length > 0 && (
              <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
                <div className="text-xs text-orange-400 uppercase tracking-wider font-medium mb-3">
                  Tes angles morts détectés
                </div>
                <ul className="space-y-2">
                  {debrief.evaluation_json.patterns.map((p, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-300">
                      <span className="text-orange-500 shrink-0">⚠</span>{p}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Meilleur/Pire + Learnings */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {debrief.evaluation_json.meilleur_coup && (
                <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4">
                  <div className="text-xs text-green-400 font-medium mb-2">🏆 Ta meilleure analyse</div>
                  <p className="text-sm text-slate-300 leading-relaxed italic">{debrief.evaluation_json.meilleur_coup}</p>
                </div>
              )}
              {debrief.evaluation_json.signal_manque && (
                <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4">
                  <div className="text-xs text-red-400 font-medium mb-2">📉 Ce que tu as manqué</div>
                  <p className="text-sm text-slate-300 leading-relaxed italic">{debrief.evaluation_json.signal_manque}</p>
                </div>
              )}
            </div>

            {/* Learnings */}
            {debrief.evaluation_json.learnings_cles.length > 0 && (
              <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
                <div className="text-xs text-blue-400 uppercase tracking-wider font-medium mb-3">
                  À retenir pour la semaine prochaine
                </div>
                <ol className="space-y-2">
                  {debrief.evaluation_json.learnings_cles.map((l, i) => (
                    <li key={i} className="flex gap-3 text-sm text-slate-300">
                      <span className="text-slate-600 shrink-0 font-mono">{i + 1}.</span>{l}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Focus */}
            {debrief.focus_semaine && (
              <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-blue-800/30 rounded-xl p-6 text-center">
                <div className="text-xs text-blue-400 uppercase tracking-wider font-medium mb-3">
                  🎯 Ton focus de la semaine prochaine
                </div>
                <p className="text-white font-semibold text-lg leading-relaxed">{debrief.focus_semaine}</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
