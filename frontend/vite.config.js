import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: './',
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Ant Design Vue 单独打包（最大的包）
          if (id.includes('node_modules/ant-design-vue')) {
            return 'ant-design-vue'
          }
          // 地图库（Leaflet）—— 完全独立，不会循环
          if (id.includes('node_modules/leaflet')) {
            return 'leaflet'
          }
          // 图表库（ECharts / zrender）—— 完全独立
          if (id.includes('node_modules/echarts') ||
              id.includes('node_modules/vue-echarts') ||
              id.includes('node_modules/zrender') ||
              id.includes('node_modules/chart.js') ||
              id.includes('node_modules/apexcharts')) {
            return 'charts'
          }
          // 其他第三方依赖统一打包（避免 chunk 循环引用）
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        }
      }
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
})
