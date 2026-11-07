import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { initPreferences } from './store'
import './style.css'

initPreferences()

createApp(App).use(router).mount('#app')
