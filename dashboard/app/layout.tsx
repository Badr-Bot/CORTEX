import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "CORTEX — Intelligence Dashboard",
  description: "Système de veille quotidienne par intelligence artificielle",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-[#040408] antialiased grid-bg">
        {/* Ambient light top */}
        <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px] bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent pointer-events-none" />
        <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[200px] bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.06)_0%,transparent_70%)] pointer-events-none" />
        {children}
      </body>
    </html>
  )
}
