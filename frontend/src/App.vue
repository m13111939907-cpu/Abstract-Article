<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { RouterView } from 'vue-router'

import { checkConnection, connection, ensureReady } from './api/client'
import AppSidebar from './components/AppSidebar.vue'
import AppTopbar from './components/AppTopbar.vue'
import MascotPet from './components/MascotPet.vue'
import ToastStack from './components/ToastStack.vue'
import { toast } from './store'

async function reconnect() {
  const mode = await checkConnection()
  if (mode === 'live') {
    toast('已连接后端', '正在加载实时数据…')
    window.setTimeout(() => window.location.reload(), 500)
  } else {
    toast('仍未连接后端', '请确认后端已启动，且 8001 端口可访问。', 'warning')
  }
}

// 从后台切回浏览器时，自动尝试重连
function onFocus() {
  if (connection.mode === 'offline') reconnect()
}

onMounted(() => {
  ensureReady()
  window.addEventListener('focus', onFocus)
})

onBeforeUnmount(() => window.removeEventListener('focus', onFocus))
</script>

<template>
  <div class="sky" aria-hidden="true">
    <div class="stars stars-a" />
    <div class="stars stars-b" />
    <div class="sky-moon" />
    <div class="sky-shoot" />
  </div>

  <div class="app-shell">
    <AppSidebar />
    <div class="app-main">
      <AppTopbar />

      <div v-if="connection.mode === 'offline'" class="offline-banner">
        <span class="offline-dot" />
        <span class="offline-text">
          <strong>后端未连接</strong>
          当前无法加载真实数据，请启动后端后点击「重新连接」。
        </span>
        <button class="offline-retry" type="button" @click="reconnect">重新连接</button>
      </div>

      <main class="app-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </main>
      <footer class="app-foot">
        <span>文献提取器 · Python 程序设计作品 · 第五组</span>
        <span>Python 程序设计作品 · 第五组 · 2026</span>
      </footer>
    </div>
  </div>
  <MascotPet />
  <ToastStack />
</template>

<style scoped>
.offline-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 38px 0;
  padding: 10px 14px;
  border: 1px solid #f0c9c9;
  border-radius: 10px;
  background: var(--red-soft);
  color: #a83232;
  font-size: 12px;
  line-height: 1.5;
}

.offline-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 3px rgba(209, 67, 67, 0.14);
}

.offline-text {
  flex: 1;
  min-width: 0;
}

.offline-text strong {
  margin-right: 8px;
  font-weight: 650;
}

.offline-retry {
  flex: none;
  height: 28px;
  padding: 0 12px;
  border: 1px solid #e8b4b4;
  border-radius: 7px;
  background: var(--surface);
  color: #a83232;
  font-size: 11.5px;
  font-weight: 550;
}

.offline-retry:hover {
  border-color: var(--red);
}

@media (max-width: 1024px) {
  .offline-banner {
    margin: 12px 24px 0;
  }
}

@media (max-width: 640px) {
  .offline-banner {
    margin: 10px 16px 0;
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .offline-text {
    flex-basis: calc(100% - 20px);
  }
}
</style>
