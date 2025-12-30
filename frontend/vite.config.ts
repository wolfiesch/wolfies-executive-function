import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // Bundle analyzer - generates dist/stats.html on build
    // Run `npm run build:analyze` to generate and view
    visualizer({
      filename: 'dist/stats.html',
      open: false,
      gzipSize: true,
      brotliSize: true,
      template: 'treemap', // Options: treemap, sunburst, network
    }),
  ],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      // API proxy for backend requests
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // WebSocket proxy for real-time updates
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },

  build: {
    // ========================================================
    // MANUAL CHUNKS CONFIGURATION
    // ========================================================
    // Splits vendor libraries into separate chunks for better caching.
    // When your app code changes, only the app chunk is invalidated.
    // Vendor chunks stay cached in the browser.
    //
    // CS Concept: **HTTP Caching** - Browsers cache files by URL.
    // Separate chunks = separate cache entries = unchanged chunks
    // don't need to be re-downloaded when you deploy updates.
    //
    // Bundle Analysis:
    // - Run `npm run build:analyze` to visualize chunk sizes
    // - Target: main bundle < 200KB, vendor chunks cached
    // ========================================================
    rollupOptions: {
      output: {
        manualChunks: {
          // ────────────────────────────────────────────────
          // CORE REACT LIBRARIES (rarely change, cache forever)
          // ~140KB gzipped, loaded on every page
          // ────────────────────────────────────────────────
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],

          // ────────────────────────────────────────────────
          // DATA LAYER (changes occasionally)
          // ~30KB gzipped, needed for API calls
          // ────────────────────────────────────────────────
          'vendor-data': ['@tanstack/react-query', 'zustand', 'axios'],

          // ────────────────────────────────────────────────
          // UI COMPONENT LIBRARIES (Radix primitives)
          // ~60KB gzipped, core UI foundation
          // ────────────────────────────────────────────────
          'vendor-ui': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-popover',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-select',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-slot',
          ],

          // ────────────────────────────────────────────────
          // CHARTS (HEAVY - only load when needed)
          // ~180KB gzipped, used on Dashboard & Goals pages
          // Lazy-loaded with page components
          // ────────────────────────────────────────────────
          'vendor-charts': ['recharts'],

          // ────────────────────────────────────────────────
          // ANIMATION LIBRARY
          // ~80KB gzipped, used for smooth transitions
          // ────────────────────────────────────────────────
          'vendor-motion': ['framer-motion'],

          // ────────────────────────────────────────────────
          // UTILITIES (tree-shakeable but grouped)
          // ~20KB gzipped
          // ────────────────────────────────────────────────
          'vendor-utils': ['date-fns', 'clsx', 'tailwind-merge', 'zod'],

          // ────────────────────────────────────────────────
          // COMMAND PALETTE (lazy-loaded on Cmd+K)
          // ~15KB gzipped
          // ────────────────────────────────────────────────
          'vendor-cmdk': ['cmdk'],
        },
      },
    },

    // Warn on chunks > 250KB (after splitting, should all be smaller)
    chunkSizeWarningLimit: 250,
  },

  // ========================================================
  // OPTIMIZATION
  // ========================================================
  optimizeDeps: {
    // Pre-bundle these dependencies for faster dev server startup
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@tanstack/react-query',
      'zustand',
      'lucide-react',
    ],
  },
})
