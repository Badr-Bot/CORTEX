import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        surface: "#12121a",
        border: "#1e1e2e",
        ai: "#3b82f6",
        crypto: "#f59e0b",
        market: "#22c55e",
        deeptech: "#a855f7",
        nexus: "#f97316",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
}
export default config
