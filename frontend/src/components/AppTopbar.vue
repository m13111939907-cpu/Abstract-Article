<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { connection } from '../api/client'
import { ui } from '../store'
import Icon from './Icon.vue'

const route = useRoute()
const router = useRouter()

const query = ref('')
const searchInput = ref(null)

const section = computed(() => route.meta.section || '工作区')
const title = computed(() => route.meta.title || '概览')

const status = computed(() => {
  if (connection.mode === 'checking') {
    return { label: '连接中', tone: 'wait' }
  }
  if (connection.mode === 'offline') {
    return { label: '未连接', tone: 'offline' }
  }
  const healthy = connection.mysql === 'ok' && connection.neo4j === 'ok'
  return healthy
    ? { label: '已连接', tone: 'live' }
    : { label: '部分异常', tone: 'warn' }
})

function submit() {
  const value = query.value.trim()
  if (!value) return
  router.push({ path: '/papers', query: { q: value } })
  query.value = ''
}

function focusSearch(event) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    searchInput.value?.focus()
  }
  if (event.key === 'Escape' && document.activeElement === searchInput.value) {
    searchInput.value?.blur()
  }
}

onMounted(() => window.addEventListener('keydown', focusSearch))
onBeforeUnmount(() => window.removeEventListener('keydown', focusSearch))
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <button
        class="icon-btn menu-btn"
        aria-label="打开导航"
        @click="ui.sidebarOpen = true"
      >
        <Icon name="menu" :size="19" />
      </button>

      <nav class="crumbs" aria-label="面包屑">
        <span>{{ section }}</span>
        <Icon name="chevron-right" :size="11" />
        <strong>{{ title }}</strong>
      </nav>
    </div>

    <div class="topbar-right">
      <form class="global-search" role="search" @submit.prevent="submit">
        <Icon name="search" :size="15" />
        <input
          ref="searchInput"
          v-model="query"
          type="search"
          placeholder="搜索文献、作者或关键词"
          aria-label="全局搜索"
        />
        <kbd>Ctrl K</kbd>
      </form>

      <button
        class="conn-pill"
        :class="`is-${status.tone}`"
        type="button"
        title="查看连接状态"
        @click="router.push('/settings')"
      >
        <span class="pill-dot" />
        {{ status.label }}
      </button>

      <a
        class="icon-btn docs-btn"
        href="http://localhost:8001/docs"
        target="_blank"
        rel="noreferrer"
        title="FastAPI 接口文档"
        aria-label="打开接口文档"
      >
        <Icon name="external" :size="17" />
      </a>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 38px;
  background: rgba(244, 247, 252, 0.82);
  backdrop-filter: blur(16px) saturate(140%);
  border-bottom: 1px solid rgba(229, 237, 249, 0.92);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.menu-btn {
  display: none;
}

.crumbs {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--faint);
  white-space: nowrap;
}

.crumbs strong {
  font-weight: 550;
  color: var(--ink-soft);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.global-search {
  position: relative;
  display: flex;
  align-items: center;
  width: 268px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.9);
  transition: border-color 0.16s ease, box-shadow 0.16s ease,
    background 0.16s ease;
}

.global-search:focus-within {
  background: #fff;
  border-color: #b5cdf2;
  box-shadow: 0 0 0 3px rgba(47, 107, 255, 0.08);
}

.global-search :deep(.icon) {
  position: absolute;
  left: 11px;
  color: var(--faint);
}

.global-search input {
  width: 100%;
  height: 100%;
  padding: 0 56px 0 33px;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 12px;
  color: var(--ink);
}

.global-search input::placeholder {
  color: #9fadc2;
}

.global-search input::-webkit-search-cancel-button {
  display: none;
}

.global-search kbd {
  position: absolute;
  right: 8px;
  font-family: inherit;
  font-size: 9px;
  color: #a3b0c4;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 1px 4px;
  letter-spacing: 0.02em;
}

.conn-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--muted);
  font-size: 10.5px;
  font-weight: 500;
  white-space: nowrap;
}

.conn-pill:hover {
  background: #fff;
  border-color: var(--line-2);
}

.pill-dot {
  width: 5px;
  height: 5px;
  border-radius: 99px;
  background: currentColor;
}

.conn-pill.is-live {
  color: #0b7a56;
}

.conn-pill.is-live .pill-dot {
  background: var(--green);
}

.conn-pill.is-offline {
  color: #946112;
  background: var(--amber-soft);
  border-color: #f0dfba;
}

.conn-pill.is-offline .pill-dot {
  background: #d9a340;
}

.conn-pill.is-wait {
  color: var(--blue-deep);
}

.conn-pill.is-wait .pill-dot {
  background: var(--blue);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}

.docs-btn {
  width: 32px;
  height: 32px;
}


@media (max-width: 1080px) {
  .topbar {
    padding: 0 24px;
  }

  .global-search {
    width: 210px;
  }

  .docs-btn {
    display: none;
  }
}

@media (max-width: 1024px) {
  .menu-btn {
    display: inline-grid;
  }
}

@media (max-width: 760px) {
  .global-search {
    display: none;
  }

  .topbar {
    padding: 0 16px;
  }

  .conn-pill {
    display: none;
  }
}

@media (max-width: 520px) {
  .crumbs span,
  .crumbs :deep(.icon) {
    display: none;
  }
}
</style>
