import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const names = ['tunari.geojson', 'distritos_cochabamba.geojson'];
const readGeo = (name) => readFileSync(fileURLToPath(new URL(`../data/geo/${name}`, import.meta.url)));
export default defineConfig({
  base: process.env.VITE_BASE || '/',
  plugins: [react(), {
    name: 'shared-geometries',
    configureServer(server) {
      server.middlewares.use('/geo', (req, res, next) => {
        const name = req.url.split('?')[0].slice(1);
        if (!names.includes(name)) return next();
        res.setHeader('Content-Type', 'application/geo+json');
        res.end(readGeo(name));
      });
    },
    generateBundle() {
      for (const name of names) this.emitFile({ type: 'asset', fileName: `geo/${name}`, source: readGeo(name) });
    },
  }],
  server: { port: 5173, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } } },
  preview: { port: 4173, strictPort: true },
});
