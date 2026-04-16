"use client"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useRef } from "react"

const DAYS_FR  = ["Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi"]
const MONTHS_FR= ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

function formatDate() {
  const d = new Date()
  return `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} ${d.getFullYear()}`
}

function formatTime() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
}

// Tiny click sound via Web Audio API
function playClick() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.setValueAtTime(880, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.08)
    gain.gain.setValueAtTime(0.06, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.08)
  } catch (_) {}
}

function playHover() {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.setValueAtTime(660, ctx.currentTime)
    gain.gain.setValueAtTime(0.02, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.04)
  } catch (_) {}
}

export default function NavBar() {
  const pathname = usePathname()
  const timeRef = useRef<HTMLSpanElement>(null)

  // Live clock
  useEffect(() => {
    const tick = () => {
      if (timeRef.current) timeRef.current.textContent = formatTime()
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const links = [
    { href: "/",        label: "Dashboard", icon: "⬡" },
    { href: "/debrief", label: "Débrief",   icon: "◈" },
    { href: "/archive", label: "Archive",   icon: "◇" },
  ]

  return (
    <header className="sticky top-0 z-50 glass-strong border-b border-indigo-500/10 scan-line-container">
      {/* Top accent line */}
      <div className="h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />

      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="flex items-center gap-2 group"
            onClick={playClick}
          >
            <div className="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg group-hover:shadow-indigo-500/40 transition-shadow">
              <span className="text-white text-xs font-bold font-mono">C</span>
            </div>
            <span className="font-bold tracking-[0.2em] text-white text-sm gradient-text">
              CORTEX
            </span>
          </Link>

          <nav className="hidden sm:flex items-center gap-1">
            {links.map((l) => {
              const isActive = pathname === l.href
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={playClick}
                  onMouseEnter={playHover}
                  className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                    isActive
                      ? "bg-indigo-500/15 text-white border border-indigo-500/30"
                      : "text-slate-400 hover:text-white hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <span className={`text-[10px] font-mono ${isActive ? "text-cyan-400" : "text-slate-600"}`}>
                    {l.icon}
                  </span>
                  {l.label}
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]" />
                  )}
                </Link>
              )
            })}
          </nav>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 font-mono">
            <span className="status-live text-green-400">LIVE</span>
          </div>
          <div className="hidden md:block text-xs text-slate-600 font-mono">
            {formatDate()} &nbsp;·&nbsp;
            <span ref={timeRef} className="text-indigo-400">{formatTime()}</span>
          </div>
        </div>
      </div>
    </header>
  )
}
