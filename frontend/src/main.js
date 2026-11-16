import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import 'leaflet/dist/leaflet.css'
import App from './App.vue'
import router from './router'
import { authApi } from './api'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(Antd)

async function bootstrap() {
  if (localStorage.getItem('token')) {
    try {
      await authApi.getMe()
    } catch {
      // 路由和响应拦截器会处理失效会话。
    }
  }
  app.mount('#app')
}

bootstrap()
