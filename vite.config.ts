import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Prevent clearing the screen
  clearScreen: false,
  
  // Tauri expects a fixed port
  server: {
    port: 5173,
    strictPort: true,
    host: 'localhost',
  },
  
  // Build configuration
  build: {
    // Tauri supports ES2021
    target: ['es2021', 'chrome100', 'safari14'],
    // Don't minify for easier debugging
    minify: !process.env.TAURI_DEBUG ? 'esbuild' : false,
    // Produce sourcemaps for debugging
    sourcemap: !!process.env.TAURI_DEBUG,
  },
  
  // Ensure proper base path
  base: './',
});
