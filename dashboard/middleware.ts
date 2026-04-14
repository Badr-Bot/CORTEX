import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Pages publiques
  if (pathname.startsWith("/login") || pathname.startsWith("/api/auth")) {
    return NextResponse.next()
  }

  // Vérifier le cookie d'auth
  const auth = request.cookies.get("cortex_auth")?.value
  if (!auth || auth !== "1") {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("from", pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
