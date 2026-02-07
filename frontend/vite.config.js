import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    https: (() => {
      try {
        const certDir = path.resolve(__dirname, '..', 'certs');
        const keyPath = path.join(certDir, 'dev-key.pem');
        const certPath = path.join(certDir, 'dev-cert.pem');

        if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
          return {
            key: fs.readFileSync(keyPath),
            cert: fs.readFileSync(certPath),
          };
        }
      } catch {
        // Ignore and fall back to HTTP
      }

      return undefined;
    })(),
    proxy: {
      '/api': {
        target: 'https://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
