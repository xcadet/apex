import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // host: true so the dev server / preview is reachable when running inside Docker.
  server: { host: true, port: 5173 },
  preview: { host: true, port: 5173 },
})
