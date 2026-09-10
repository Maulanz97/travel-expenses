import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { validatePublicEnvironment } from './config/publicEnvironment.js'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  validatePublicEnvironment(loadEnv(mode, process.cwd(), 'VITE_'))
  return ({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${command === 'serve' && process.env.LOCAL_DEV_AUTH === '1' ? process.env.LOCAL_DEV_API_PORT || '8000' : '8000'}`,
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (request) => {
            request.removeHeader('x-local-dev-token')
            if (command === 'serve' && process.env.LOCAL_DEV_AUTH === '1' && process.env.APP_ENV === 'development' && process.env.LOCAL_DEV_TOKEN?.length >= 32) {
              request.setHeader('x-local-dev-token', process.env.LOCAL_DEV_TOKEN)
            }
          })
        },
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
})
