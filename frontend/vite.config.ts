import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // M4: proxy all /api requests to the FastAPI backend — no CORS needed
      '/api': 'http://localhost:8000',
    },
  },
})
