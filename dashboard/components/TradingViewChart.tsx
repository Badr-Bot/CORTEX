"use client"
import { useEffect, useRef } from "react"

interface Props {
  symbol: string       // e.g. "BTCUSD" or "SP:SPX"
  label: string        // e.g. "Bitcoin" or "S&P 500"
  height?: number      // default 220
  colorTheme?: "dark"  // always dark
}

export default function TradingViewChart({ symbol, label, height = 220 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return
    containerRef.current.innerHTML = ""

    const script = document.createElement("script")
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js"
    script.async = true
    script.innerHTML = JSON.stringify({
      symbol: symbol,
      width: "100%",
      height: height,
      locale: "fr",
      dateRange: "1M",
      colorTheme: "dark",
      isTransparent: true,
      autosize: true,
      largeChartUrl: "",
      noTimeScale: false,
    })

    containerRef.current.appendChild(script)
    return () => { if (containerRef.current) containerRef.current.innerHTML = "" }
  }, [symbol, height])

  return (
    <div className="rounded-lg overflow-hidden">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</div>
      <div ref={containerRef} style={{ height: `${height}px` }} />
    </div>
  )
}
