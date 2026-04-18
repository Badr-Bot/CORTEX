import { NextRequest, NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

function getClient() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY
  if (!url || !key) return null
  return createClient(url, key)
}

// GET — récupère tout l'historique des snapshots
export async function GET() {
  const sb = getClient()
  if (!sb) return NextResponse.json({ snapshots: [] })
  try {
    const { data } = await sb
      .from("portfolio_snapshots")
      .select("snapshot_date, total_value, stocks_value, crypto_value, total_invested")
      .order("snapshot_date", { ascending: true })
    return NextResponse.json({ snapshots: data ?? [] })
  } catch {
    return NextResponse.json({ snapshots: [] })
  }
}

// POST — sauvegarde le snapshot du jour (idempotent via UNIQUE sur snapshot_date)
export async function POST(req: NextRequest) {
  const sb = getClient()
  if (!sb) return NextResponse.json({ ok: false, reason: "no_client" })
  try {
    const body = await req.json()
    const { total_value, stocks_value, crypto_value, total_invested } = body
    if (!total_value || total_value <= 0) {
      return NextResponse.json({ ok: false, reason: "invalid_value" })
    }
    const today = new Date().toISOString().slice(0, 10)
    const { error } = await sb.from("portfolio_snapshots").upsert(
      { snapshot_date: today, total_value, stocks_value, crypto_value, total_invested },
      { onConflict: "snapshot_date" }
    )
    if (error) throw error
    return NextResponse.json({ ok: true, date: today })
  } catch (e: any) {
    return NextResponse.json({ ok: false, reason: e?.message ?? "error" })
  }
}
