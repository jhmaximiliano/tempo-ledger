import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En desarrollo, /api/... se reenvía a la API de FastAPI. Si la API corre en otro puerto:
//   $env:TEMPO_API_URL = "http://127.0.0.1:8001"; npm run dev
const apiUrl = process.env.TEMPO_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: apiUrl, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})
