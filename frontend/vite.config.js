import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 5174,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        timeout: 120000,
        proxyTimeout: 120000,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8080',
        ws: true,
        changeOrigin: true,
        secure: false,
        timeout: 300000,
        proxyTimeout: 300000,
        followRedirects: true,
        rewrite: (path) => path.replace(/^\/ws/, '/ws'),
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('🔌 WebSocket proxy error:', err.message);
          });
          proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
            socket.on('error', (err) => {
              console.log('🔌 WebSocket socket error:', err.message);
            });
            proxyReq.setHeader('Connection', 'Upgrade');
          });
        }
      },

      // X-Ray WebSocket: FastAPI endpoint is /api/v1/xray/ws
      '/api/v1/xray/ws': {
        target: 'ws://127.0.0.1:8080',
        ws: true,
        changeOrigin: true,
        secure: false,
        timeout: 300000,
        proxyTimeout: 300000,
        followRedirects: true,
        // Без явного rewrite: пусть прокси использует тот же путь (/api/v1/xray/ws)
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('🔌 X-Ray WS proxy error:', err.message);
          });
          proxy.on('proxyReqWs', (proxyReq, req, socket, options, head) => {
            socket.on('error', (err) => {
              console.log('🔌 X-Ray WS socket error:', err.message);
            });
            proxyReq.setHeader('Connection', 'Upgrade');
          });
        }
      }

    },
    hmr: {
      overlay: false,
      clientPort: 5174
    }
  }
})