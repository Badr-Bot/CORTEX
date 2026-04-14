/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Note: 'standalone' output n'est pas compatible avec Vercel
  // Vercel détecte automatiquement Next.js et gère le déploiement
}

module.exports = nextConfig
