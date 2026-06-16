import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        ws: false,
        timeout: 120000,
        proxyTimeout: 120000
      },
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
        changeOrigin: true,
        secure: false,
        followRedirects: true,
        timeout: 300000,
        proxyTimeout: 300000,
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
      }
    },
    hmr: {
      overlay: false,
      clientPort: 5174
    },
    watch: {
      usePolling: true,
      interval: 1000
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          supabase: ['@supabase/supabase-js'],
          charts: ['recharts', 'reactflow']
        }
      }
    }
  }
})