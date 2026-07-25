import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies API and health calls to the local backend (uvicorn on
// port 8000), so the origin looks the same in dev as in production. In prod the
// built app is served by the same FastAPI process, so there is no proxy there.
// Do not point this at the live VPS; dev talks to the local backend only.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
