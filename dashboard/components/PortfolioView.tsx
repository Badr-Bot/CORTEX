"use client"

import { useState } from "react"
import PortfolioSection from "@/components/PortfolioSection"
import PaperPortfoliosSection from "@/components/PaperPortfoliosSection"

export default function PortfolioView() {
  const [view, setView] = useState<"real" | "paper">("real")

  return (
    <div className="space-y-4">
      {/* Toggle */}
      <div className="flex gap-1 p-1 glass rounded-xl border border-white/10 w-fit">
        <button
          onClick={() => setView("real")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            view === "real"
              ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.15)]"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          💼 Mon portefeuille
        </button>
        <button
          onClick={() => setView("paper")}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all ${
            view === "paper"
              ? "bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.15)]"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          🤖 Paper Trading
        </button>
      </div>

      {view === "real" ? <PortfolioSection /> : <PaperPortfoliosSection />}
    </div>
  )
}
