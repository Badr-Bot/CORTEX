import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

export async function POST(request: NextRequest) {
  const { password } = await request.json()

  if (password !== process.env.DASHBOARD_PASSWORD) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const response = NextResponse.json({ ok: true })
  response.cookies.set("cortex_auth", "1", {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30, // 30 jours
    path: "/",
  })

  return response
}
