import { NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

function getClient() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY
  if (!url || !key) return null
  return createClient(url, key)
}

export async function GET() {
  const sb = getClient()
  if (!sb) return NextResponse.json({ active: [], closed: [] })

  try {
    const [activeRes, closedRes] = await Promise.all([
      sb
        .from("paper_portfolios")
        .select(`
          id, code, portfolio_type, horizon_days, initial_value, current_value,
          start_date, end_date, benchmark_start, pnl_pct, benchmark_pnl_pct, beat_sp500,
          status, rationale, created_at,
          paper_positions (
            id, ticker, asset_type, allocation_pct, allocation_usd,
            entry_price, current_price, pnl_usd, pnl_pct,
            conviction, reasoning, status
          ),
          paper_snapshots (
            snapshot_date, portfolio_value, pnl_pct, sp500_pnl_pct
          )
        `)
        .eq("status", "active")
        .order("created_at", { ascending: true }),
      sb
        .from("paper_portfolios")
        .select(
          "code, portfolio_type, start_date, end_date, initial_value, current_value, pnl_pct, benchmark_pnl_pct, beat_sp500, closed_at"
        )
        .eq("status", "closed")
        .order("closed_at", { ascending: false })
        .limit(12),
    ])

    return NextResponse.json({
      active: activeRes.data ?? [],
      closed: closedRes.data ?? [],
    })
  } catch {
    return NextResponse.json({ active: [], closed: [] })
  }
}
