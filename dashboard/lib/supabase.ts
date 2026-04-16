import { createClient, SupabaseClient } from "@supabase/supabase-js"
import type { DailyReport, JournalEntry, WeeklyDebrief } from "./types"

// Lazy singleton — instancié seulement à la première requête (pas au build)
// Ceci évite l'erreur "supabaseUrl is required" lors de la collecte de données
// statiques de Next.js, qui s'exécute sans les variables d'environnement.
let _client: SupabaseClient | null = null

function getClient(): SupabaseClient {
  if (!_client) {
    const url  = process.env.NEXT_PUBLIC_SUPABASE_URL!
    const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    if (!url || !anon) {
      throw new Error("Variables d'environnement Supabase manquantes : NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY requis.")
    }
    // IMPORTANT: fetch sans cache — sinon Next.js Data Cache retient les anciens
    // rapports et le dashboard affiche des données périmées après régénération.
    _client = createClient(url, anon, {
      global: {
        fetch: (input, init) => fetch(input, { ...init, cache: "no-store" }),
      },
    })
  }
  return _client
}

// Export du client pour usage direct si nécessaire
export { getClient as getSupabaseClient }

// ── Reports ──────────────────────────────────────────────────────────────────

export async function getLatestReport(): Promise<DailyReport | null> {
  const { data, error } = await getClient()
    .from("daily_reports")
    .select("*")
    .not("report_json", "is", null)
    .order("report_date", { ascending: false })
    .limit(1)
    .single()

  if (error || !data) return null
  return data as DailyReport
}

export async function getReportByDate(date: string): Promise<DailyReport | null> {
  const { data, error } = await getClient()
    .from("daily_reports")
    .select("*")
    .eq("report_date", date)
    .not("report_json", "is", null)
    .single()

  if (error || !data) return null
  return data as DailyReport
}

export async function getReportHistory(limit = 30): Promise<DailyReport[]> {
  const { data } = await getClient()
    .from("daily_reports")
    .select("id, report_date, signals_count, question, sent_at")
    .not("report_json", "is", null)
    .order("report_date", { ascending: false })
    .limit(limit)

  return (data || []) as DailyReport[]
}

// ── Journal ───────────────────────────────────────────────────────────────────

export async function getTodayJournal(): Promise<JournalEntry | null> {
  const today = new Date().toISOString().split("T")[0]
  const { data } = await getClient()
    .from("journal")
    .select("*")
    .eq("date", today)
    .order("created_at", { ascending: false })
    .limit(1)
    .single()

  return data as JournalEntry | null
}

export async function getWeekJournal(): Promise<JournalEntry[]> {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 7)
  const { data } = await getClient()
    .from("journal")
    .select("*")
    .gte("created_at", cutoff.toISOString())
    .order("created_at", { ascending: false })

  return (data || []) as JournalEntry[]
}

// ── Weekly Debrief ────────────────────────────────────────────────────────────

export async function getLatestDebrief(): Promise<WeeklyDebrief | null> {
  const { data } = await getClient()
    .from("weekly_debrief")
    .select("*")
    .order("week_of", { ascending: false })
    .limit(1)
    .single()

  return data as WeeklyDebrief | null
}
