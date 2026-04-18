import { NextResponse } from "next/server"

const STOCK_TICKERS = ["NVDA", "GOOGL", "MSFT", "META", "PDD"]
const CRYPTO_IDS = "bitcoin,ethereum,solana"

async function fetchStockPrices(): Promise<Record<string, number>> {
  const prices: Record<string, number> = {}
  await Promise.all(
    STOCK_TICKERS.map(async (ticker) => {
      try {
        const url = `https://query1.finance.yahoo.com/v8/finance/chart/${ticker}?interval=1d&range=1d`
        const r = await fetch(url, {
          headers: { "User-Agent": "Mozilla/5.0" },
          next: { revalidate: 300 },
        })
        const data = await r.json()
        const price = data.chart?.result?.[0]?.meta?.regularMarketPrice
        if (price) prices[ticker] = price
      } catch {}
    })
  )
  return prices
}

async function fetchCryptoPrices(): Promise<Record<string, number>> {
  try {
    const url = `https://api.coingecko.com/api/v3/simple/price?ids=${CRYPTO_IDS}&vs_currencies=usd`
    const r = await fetch(url, {
      headers: { "User-Agent": "CORTEX/1.0" },
      next: { revalidate: 300 },
    })
    const data = await r.json()
    return {
      BTC: data.bitcoin?.usd ?? 0,
      ETH: data.ethereum?.usd ?? 0,
      SOL: data.solana?.usd ?? 0,
    }
  } catch {
    return { BTC: 0, ETH: 0, SOL: 0 }
  }
}

export async function GET() {
  const [stockPrices, cryptoPrices] = await Promise.all([
    fetchStockPrices(),
    fetchCryptoPrices(),
  ])
  return NextResponse.json({
    prices: { ...stockPrices, ...cryptoPrices },
    timestamp: new Date().toISOString(),
  })
}
