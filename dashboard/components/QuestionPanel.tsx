"use client"
import { useState } from "react"

interface Props {
  question: string
  reportDate: string
  existingResponse?: string | null
}

export default function QuestionPanel({ question, reportDate, existingResponse }: Props) {
  const [response, setResponse] = useState(existingResponse || "")
  const [saved, setSaved] = useState(!!existingResponse)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState(!existingResponse)

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
    }
    setSaving(false)
  }

  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] border-l-2 border-l-orange-500 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-orange-400 uppercase tracking-wider font-medium">
          Question du matin
        </div>
        {saved && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Modifier
          </button>
        )}
      </div>

      <p className="text-white font-medium leading-relaxed">{question}</p>

      {!editing && saved ? (
        <div className="bg-[#0a0a0f] rounded-lg p-4">
          <div className="text-xs text-slate-500 mb-2">Ta réponse</div>
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{response}</p>
        </div>
      ) : (
        <div className="space-y-3">
          <textarea
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="Écris ta réponse ici — force-toi à décider, pas juste observer..."
            rows={4}
            className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3 text-white placeholder-slate-600 text-sm focus:outline-none focus:border-orange-500 transition-colors resize-none"
          />
          <div className="flex items-center gap-3">
            <button
              onClick={handleSubmit}
              disabled={saving || !response.trim()}
              className="px-4 py-2 rounded-lg bg-orange-600 hover:bg-orange-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
            >
              {saving ? "Sauvegarde..." : "Sauvegarder"}
            </button>
            <span className="text-xs text-slate-500">
              Ton journal CORTEX — dimanche tu verras si tu avais raison.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
