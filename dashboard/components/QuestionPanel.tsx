"use client"
import { useState, useRef } from "react"

interface Props {
  question: string
  reportDate: string
  existingResponse?: string | null
}

function playSuccess() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const notes = [523, 659, 784]
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = "sine"
      osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.12)
      gain.gain.setValueAtTime(0.08, ctx.currentTime + i * 0.12)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.2)
      osc.start(ctx.currentTime + i * 0.12)
      osc.stop(ctx.currentTime + i * 0.12 + 0.2)
    })
  } catch (_) {}
}

function playTyping() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.setValueAtTime(200 + Math.random() * 100, ctx.currentTime)
    gain.gain.setValueAtTime(0.01, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.03)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.03)
  } catch (_) {}
}

export default function QuestionPanel({ question, reportDate, existingResponse }: Props) {
  const [response, setResponse] = useState(existingResponse || "")
  const [saved, setSaved] = useState(!!existingResponse)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(!existingResponse)
  const [charCount, setCharCount] = useState(existingResponse?.length || 0)
  const typingRef = useRef<number>(0)

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setResponse(e.target.value)
    setCharCount(e.target.value.length)
    // Throttled typing sound
    const now = Date.now()
    if (now - typingRef.current > 80) {
      playTyping()
      typingRef.current = now
    }
  }

  async function handleSubmit() {
    if (!response.trim()) return
    setSaving(true)
    const res = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, response, reportDate }),
    })
    if (res.ok) {
      setSaved(true)
      setEditing(false)
      playSuccess()
    }
    setSaving(false)
  }

  return (
    <div className="glass border-l-2 accent-nexus rounded-xl p-5 space-y-4 card-hover animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-orange-500/20 border border-orange-500/40 flex items-center justify-center">
            <span className="text-[9px] text-orange-400">✦</span>
          </div>
          <div className="text-[10px] text-orange-400 uppercase tracking-widest font-semibold">
            Question du matin
          </div>
        </div>
        {saved && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-1"
          >
            <span className="text-[9px]">✎</span> Modifier
          </button>
        )}
      </div>

      {/* Question */}
      <p className="text-white font-medium leading-relaxed text-sm">{question}</p>

      {/* Response area */}
      {!editing && saved ? (
        <div className="bg-black/30 rounded-lg p-4 border border-white/5 space-y-2 animate-fade-in">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
            <div className="text-[10px] text-emerald-400/70 uppercase tracking-wider">Ta réponse — enregistrée</div>
          </div>
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{response}</p>
        </div>
      ) : (
        <div className="space-y-3 animate-fade-in">
          <div className="relative">
            <textarea
              value={response}
              onChange={handleChange}
              placeholder="Force-toi à décider, pas juste observer... C'est la différence entre l'investisseur et le spectateur."
              rows={4}
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 text-sm focus:outline-none focus:border-orange-500/50 focus:shadow-[0_0_16px_rgba(249,115,22,0.1)] transition-all duration-200 resize-none font-[family-name:var(--font-sans)]"
            />
            <div className="absolute bottom-2 right-3 text-[10px] font-mono text-slate-600">
              {charCount}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSubmit}
              disabled={saving || !response.trim()}
              className="relative btn-neon px-5 py-2 rounded-xl bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-500 hover:to-orange-400 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all duration-200 shadow-lg hover:shadow-orange-500/30"
            >
              {saving ? (
                <span className="flex items-center gap-2">
                  <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />
                  Sauvegarde...
                </span>
              ) : (
                "Sauvegarder ↗"
              )}
            </button>
            <span className="text-xs text-slate-600 italic">
              Dimanche, tu sauras si tu avais raison.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
