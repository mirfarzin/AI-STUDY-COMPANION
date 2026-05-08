import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/documents': 'http://localhost:8000',
      '/document': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/predict': 'http://localhost:8000',
    },
  },
})
