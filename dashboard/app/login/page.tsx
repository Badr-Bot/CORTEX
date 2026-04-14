"use client"
import { useState, FormEvent } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Suspense } from "react"

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")

    const res = await fetch("/api/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    })

    if (res.ok) {
      const from = params.get("from") || "/"
      router.push(from)
    } else {
      setError("Mot de passe incorrect")
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f]">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-3xl font-bold tracking-widest text-white mb-1">CORTEX</div>
          <div className="text-slate-500 text-sm">Système d&apos;intelligence active</div>
        </div>

        <form onSubmit={handleSubmit} className="bg-[#12121a] border border-[#1e1e2e] rounded-2xl p-8 space-y-5">
          <div>
            <label className="block text-xs text-slate-400 mb-2 uppercase tracking-wider">
              Accès sécurisé
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition-colors"
              autoFocus
            />
          </div>

          {error && (
            <div className="text-red-400 text-sm text-center">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            {loading ? "..." : "Entrer"}
          </button>
        </form>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0a0a0f]" />}>
      <LoginForm />
    </Suspense>
  )
}
