import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "CORTEX",
  description: "Intelligence artificielle — Veille quotidienne",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen bg-[#0a0a0f] text-slate-200 antialiased">
        {children}
      </body>
    </html>
  )
}
