"use client"
import { useState, useEffect } from "react"

const COLORS: Record<string, { dot: string; badge: string }> = {
  ai:       { dot: "bg-blue-400",    badge: "bg-blue-500/15 text-blue-300 border border-blue-500/40" },
  crypto:   { dot: "bg-amber-400",   badge: "bg-amber-500/15 text-amber-300 border border-amber-500/40" },
  market:   { dot: "bg-emerald-400", badge: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/40" },
  deeptech: { dot: "bg-violet-400",  badge: "bg-violet-500/15 text-violet-300 border border-violet-500/40" },
  nexus:    { dot: "bg-orange-400",  badge: "bg-orange-500/15 text-orange-300 border border-orange-500/40" },
}

interface Props {
  tab: string
  questions: string[]
  reportDate: string
}

export default function SectionQuestionsPanel({ tab, questions, reportDate }: Props) {
  const storageKey = `cortex_sq_${reportDate}_${tab}`
  const c = COLORS[tab] ?? COLORS.ai

  const [answers, setAnswers] = useState<string[]>(questions.map(() => ""))
  const [saved, setSaved]     = useState<boolean[]>(questions.map(() => false))
  const [loaded, setLoaded]   = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) {
        const parsed = JSON.parse(raw)
        setAnswers(parsed.answers ?? questions.map(() => ""))
        setSaved(parsed.saved   ?? questions.map(() => false))
      }
    } catch {}
    setLoaded(true)
  }, [storageKey, questions.length])

  function persist(nextAnswers: string[], nextSaved: boolean[]) {
    try { localStorage.setItem(storageKey, JSON.stringify({ answers: nextAnswers, saved: nextSaved })) } catch {}
  }

  function handleChange(i: number, val: string) {
    const next = [...answers]; next[i] = val; setAnswers(next)
  }

  function handleSave(i: number) {
    if (!answers[i].trim()) return
    const nextSaved = [...saved]; nextSaved[i] = true
    setSaved(nextSaved)
    persist(answers, nextSaved)
  }

  function handleEdit(i: number) {
    const nextSaved = [...saved]; nextSaved[i] = false
    setSaved(nextSaved)
    persist(answers, nextSaved)
  }

  if (!loaded) return null

  return (
    <div className="glass rounded-xl p-5 border border-white/5 animate-slide-up space-y-5">
      <div className="flex items-center gap-2">
        <div className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
        <div className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">🧠 Questions pour toi</div>
      </div>

      {questions.map((q, i) => (
        <div key={i} className="space-y-3">
          <div className="flex gap-3 items-start">
            <span className={`shrink-0 text-xs font-bold font-mono px-2 py-0.5 rounded ${c.badge} mt-0.5`}>
              Q{i + 1}
            </span>
            <p className="text-slate-200 text-sm leading-relaxed">{q}</p>
          </div>

          {saved[i] ? (
            <div className="ml-10 bg-black/30 rounded-lg p-3 border border-white/5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
                  <span className="text-[10px] text-emerald-400/70 uppercase tracking-wider">Réponse enregistrée</span>
                </div>
                <button
                  onClick={() => handleEdit(i)}
                  className="text-xs text-slate-600 hover:text-slate-400 transition-colors"
                >✎ Modifier</button>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed whitespace-pre-wrap">{answers[i]}</p>
            </div>
          ) : (
            <div className="ml-10 space-y-2">
              <textarea
                value={answers[i]}
                onChange={e => handleChange(i, e.target.value)}
                placeholder="Force-toi à décider, pas juste observer..."
                rows={3}
                className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2.5 text-white placeholder-slate-600 text-xs focus:outline-none focus:border-orange-500/40 focus:shadow-[0_0_12px_rgba(249,115,22,0.08)] transition-all resize-none"
              />
              <button
                onClick={() => handleSave(i)}
                disabled={!answers[i].trim()}
                className="px-4 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold transition-all"
              >
                Sauvegarder ↗
              </button>
            </div>
          )}
        </div>
      ))}

      <p className="text-[10px] text-slate-600 italic">
        Tes réponses sont sauvegardées localement — CORTEX te score le dimanche.
      </p>
    </div>
  )
}
