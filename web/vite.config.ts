import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'path';

// Polyfill plugin to fix webidl-conversions compatibility issue
const polyfillPlugin = () => ({
  name: 'polyfill-arraybuffer',
  configResolved() {
    // Apply polyfill before any modules load
    if (typeof ArrayBuffer !== 'undefined' && !Object.getOwnPropertyDescriptor(ArrayBuffer.prototype, 'resizable')) {
      Object.defineProperty(ArrayBuffer.prototype, 'resizable', {
        get: function() {
          return false;
        },
        configurable: true,
        enumerable: false,
      });
    }
    if (typeof SharedArrayBuffer !== 'undefined' && !Object.getOwnPropertyDescriptor(SharedArrayBuffer.prototype, 'growable')) {
      Object.defineProperty(SharedArrayBuffer.prototype, 'growable', {
        get: function() {
          return false;
        },
        configurable: true,
        enumerable: false,
      });
    }
  },
});

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    polyfillPlugin(),
    react(),
    tailwindcss({
      configPath: './tailwind.config.js',
    }),
  ],
  // Base URL for the app:
  // - Development: '/'
  // - Staging: '/' (trigpointing.me root)
  // - Production: '/' (preview.trigpointing.uk root)
  // Set VITE_BASE_URL env var to override
  base: process.env.VITE_BASE_URL || '/',
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/polyfills.ts', './tests/setup.ts'],
    css: true, // Parse CSS imports
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/dist/**',
      ],
      include: ['src/**/*.{ts,tsx}'],
    }
  }
})

