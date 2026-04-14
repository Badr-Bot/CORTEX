import { NextRequest, NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
)

export async function POST(request: NextRequest) {
  try {
    const { question, response: userResponse, reportDate } = await request.json()

    if (!question || !userResponse) {
      return NextResponse.json({ error: "question et response requis" }, { status: 400 })
    }

    const today = reportDate || new Date().toISOString().split("T")[0]

    // Vérifier si déjà répondu aujourd'hui
    const { data: existing } = await supabase
      .from("journal")
      .select("id")
      .eq("date", today)
      .single()

    if (existing) {
      // Mettre à jour
      await supabase
        .from("journal")
        .update({
          your_response: userResponse,
          response_received_at: new Date().toISOString(),
        })
        .eq("id", existing.id)
    } else {
      // Créer
      await supabase.from("journal").insert({
        date: today,
        question_asked: question,
        your_response: userResponse,
        response_received_at: new Date().toISOString(),
      })
    }

    return NextResponse.json({ ok: true })
  } catch (e) {
    return NextResponse.json({ error: String(e) }, { status: 500 })
  }
}
