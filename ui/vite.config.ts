import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Prevent browser caching of assets during development
    headers: {
      'Cache-Control': 'no-store',
    },
  },
})
