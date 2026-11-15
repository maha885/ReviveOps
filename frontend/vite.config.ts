import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config — proxies /health and /api to the FastAPI dev server so the
// frontend can call relative URLs without CORS issues during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
})
