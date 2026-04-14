import type { ReportJSON, HotStock } from "@/lib/types"
import SignalCard from "./SignalCard"

interface Props { market: ReportJSON["market"] }

function recColor(score: number) {
  if (score <= 2) return "text-green-400"
  if (score <= 4) return "text-yellow-400"
  if (score <= 6) return "text-orange-400"
  return "text-red-400"
}

function statusIcon(s: string) {
  return { green: "🟢", yellow: "🟡", red: "🔴" }[s] || "🟡"
}

function StockRow({ stock }: { stock: HotStock }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1e1e2e] last:border-0">
      <div>
        <span className="text-white font-semibold text-sm">{stock.ticker}</span>
        <span className="text-slate-400 text-xs ml-2">{stock.name}</span>
        {stock.reason && <div className="text-xs text-slate-500 italic mt-0.5">{stock.reason}</div>}
      </div>
      <div className="text-right shrink-0 ml-4">
        <div className={`text-sm font-medium ${stock.change_1d >= 0 ? "text-green-400" : "text-red-400"}`}>
          {stock.change_1d > 0 ? "+" : ""}{stock.change_1d.toFixed(1)}%
        </div>
        <div className={`text-xs ${stock.change_5d >= 0 ? "text-green-500" : "text-red-500"}`}>
          {stock.change_5d > 0 ? "+" : ""}{stock.change_5d.toFixed(1)}% sem.
        </div>
      </div>
    </div>
  )
}

export default function MarketSection({ market }: Props) {
  const d = market.dashboard

  const dashItems = [
    { key: "sp500", label: "S&P 500" },
    { key: "nasdaq", label: "Nasdaq" },
    { key: "gold", label: "Or" },
    { key: "oil", label: "Pétrole" },
    { key: "dxy", label: "DXY" },
  ] as const

  return (
    <div className="space-y-5">
      {/* Tableau de bord */}
      <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
        <div className="text-xs text-green-400 uppercase tracking-wider font-medium mb-4">
          Tableau de bord marchés
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {dashItems.map(({ key, label }) => {
            const item = d[key] as { price: string; change_pct: number } | undefined
            if (!item) return null
            const chg = item.change_pct || 0
            return (
              <div key={key}>
                <div className="text-xs text-slate-500 mb-1">{label}</div>
                <div className="text-white font-medium">{item.price}</div>
                <div className={`text-xs ${chg >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {chg > 0 ? "+" : ""}{chg.toFixed(1)}%
                </div>
              </div>
            )
          })}
          {d.vix && (
            <div>
              <div className="text-xs text-slate-500 mb-1">VIX</div>
              <div className="text-white font-medium">{d.vix.price}</div>
              <div className="text-xs text-slate-400">{d.vix.interpretation}</div>
            </div>
          )}
          {d.us_10y && (
            <div>
              <div className="text-xs text-slate-500 mb-1">US 10Y</div>
              <div className="text-white font-medium">{d.us_10y.price}</div>
              <div className="text-xs text-slate-400">{d.us_10y.change_bps}</div>
            </div>
          )}
        </div>
      </div>

      {/* Récession + Régime */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs text-green-400 uppercase tracking-wider font-medium">Risque récession</div>
            <div className={`text-2xl font-bold font-mono ${recColor(market.recession_score)}`}>
              {market.recession_score}/10
            </div>
          </div>
          <div className="space-y-1.5">
            {Object.entries(market.recession_indicators || {}).map(([key, val]) => (
              <div key={key} className="flex items-center gap-2 text-xs">
                <span>{statusIcon(val.status)}</span>
                <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}</span>
                <span className="text-slate-500 italic truncate">{val.note}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
          <div className="text-xs text-green-400 uppercase tracking-wider font-medium mb-3">Régime de marché</div>
          <div className="text-white font-semibold mb-2">{market.regime}</div>
          <p className="text-slate-400 text-sm leading-relaxed">{market.regime_justification}</p>
          {market.crash && (
            <div className="mt-3 pt-3 border-t border-[#1e1e2e]">
              <div className="text-xs text-slate-500">Risque crash : <span className="font-semibold text-white">{market.crash.crash_score}/10</span></div>
              <div className="text-xs text-slate-400 italic mt-1">{market.crash.interpretation}</div>
            </div>
          )}
        </div>
      </div>

      {/* Actions chaudes */}
      {market.hot_stocks && market.hot_stocks.length > 0 && (
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-5">
          <div className="text-xs text-green-400 uppercase tracking-wider font-medium mb-3">
            Actions en mouvement
          </div>
          {market.hot_stocks.map((s, i) => <StockRow key={i} stock={s} />)}
        </div>
      )}

      {/* Signaux */}
      {market.signals?.map((sig, i) => (
        <SignalCard key={i} signal={sig} index={i} sector="market" />
      ))}
    </div>
  )
}
