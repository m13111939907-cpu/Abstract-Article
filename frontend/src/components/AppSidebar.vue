<script setup>
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { connection } from '../api/client'
import { ui } from '../store'
import BrandMark from './BrandMark.vue'
import Icon from './Icon.vue'

const route = useRoute()
const router = useRouter()

const navGroups = [
  {
    label: '工作区',
    items: [
      { to: '/', icon: 'grid', label: '概览', match: (path) => path === '/' },
      {
        to: '/projects',
        icon: 'folder',
        label: '研究项目',
        match: (path) => path.startsWith('/projects'),
      },
      {
        to: '/papers',
        icon: 'files',
        label: '文献库',
        match: (path) => path.startsWith('/papers'),
      },
      {
        to: '/graph',
        icon: 'graph',
        label: '知识图谱',
        match: (path) => path.startsWith('/graph'),
      },
      {
        to: '/sources',
        icon: 'rss',
        label: '订阅源',
        match: (path) => path.startsWith('/sources'),
      },
    ],
  },
  {
    label: '系统',
    items: [
      {
        to: '/settings',
        icon: 'settings',
        label: '设置',
        match: (path) => path.startsWith('/settings'),
      },
    ],
  },
]

const conn = computed(() => {
  if (connection.mode === 'checking') {
    return { label: '正在连接', sub: '检测数据服务…', tone: 'wait' }
  }
  if (connection.mode === 'offline') {
    return { label: '后端未连接', sub: '无法加载数据', tone: 'warn' }
  }
  const healthy = connection.mysql === 'ok' && connection.neo4j === 'ok'
  return healthy
    ? { label: '数据服务正常', sub: 'MySQL · Neo4j', tone: 'ok' }
    : { label: '服务部分异常', sub: '请到设置页检查', tone: 'warn' }
})

function startProject() {
  ui.sidebarOpen = false
  router.push({ path: '/projects', query: { new: '1' } })
}

watch(
  () => route.fullPath,
  () => {
    ui.sidebarOpen = false
  },
)
</script>

<template>
  <div
    v-if="ui.sidebarOpen"
    class="scrim"
    aria-hidden="true"
    @click="ui.sidebarOpen = false"
  />

  <aside class="sidebar" :class="{ 'is-open': ui.sidebarOpen }">
    <RouterLink to="/" class="brand-row" aria-label="返回概览">
      <BrandMark :size="31" />
      <div class="brand-copy">
        <strong>文献提取器</strong>
        <span>LITERATURE LAB</span>
      </div>
    </RouterLink>

    <button class="btn btn-primary btn-block new-btn" @click="startProject">
      <Icon name="plus" :size="16" />
      新建检索项目
    </button>

    <nav class="nav" aria-label="主导航">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <p class="nav-caption">{{ group.label }}</p>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ 'is-active': item.match(route.path) }"
        >
          <Icon :name="item.icon" :size="17" />
          <span>{{ item.label }}</span>
          <span v-if="item.to === '/graph'" class="nav-dot" aria-hidden="true" />
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-bottom">
      <RouterLink to="/settings" class="conn-card" :class="`is-${conn.tone}`">
        <span class="conn-dot" aria-hidden="true" />
        <span class="conn-copy">
          <strong>{{ conn.label }}</strong>
          <small>{{ conn.sub }}</small>
        </span>
        <Icon name="chevron-right" :size="13" class="conn-arrow" />
      </RouterLink>

      <div class="team-card">
        <span class="team-badge">第五组</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 40;
  width: var(--sidebar-w);
  display: flex;
  flex-direction: column;
  padding: 22px 16px 16px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  border-right: 1px solid var(--line);
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 6px;
  color: var(--ink);
}

.brand-copy {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-copy strong {
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.brand-copy span {
  margin-top: 4px;
  font-size: 8px;
  font-weight: 600;
  letter-spacing: 0.19em;
  color: var(--faint);
}

.new-btn {
  margin-top: 24px;
  height: 39px;
  font-size: 12.5px;
  border-radius: 10px;
}

.nav {
  flex: 1;
  margin-top: 26px;
  overflow-y: auto;
}

.nav-group + .nav-group {
  margin-top: 24px;
}

.nav-caption {
  padding: 0 10px;
  margin-bottom: 8px;
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: #a3b0c4;
  text-transform: uppercase;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 39px;
  padding: 0 10px;
  border-radius: 9px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 450;
  transition: background 0.16s ease, color 0.16s ease;
}

.nav-item + .nav-item {
  margin-top: 2px;
}

.nav-item:hover {
  background: var(--blue-softer);
  color: var(--ink-soft);
}

.nav-item.is-active {
  background: var(--blue-soft);
  color: var(--blue-deep);
  font-weight: 550;
}

.nav-item.is-active :deep(.icon) {
  color: var(--blue);
}

.nav-dot {
  margin-left: auto;
  width: 5px;
  height: 5px;
  border-radius: 99px;
  background: #b9cdf0;
}

.nav-item.is-active .nav-dot {
  background: var(--blue);
}

.sidebar-bottom {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 14px;
}

.conn-card {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 11px;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: var(--surface-soft);
  color: var(--ink-soft);
  transition: border-color 0.16s ease, background 0.16s ease;
}

.conn-card:hover {
  border-color: var(--line-2);
  background: #fff;
}

.conn-dot {
  width: 7px;
  height: 7px;
  border-radius: 99px;
  background: #aab8cc;
  box-shadow: 0 0 0 3px rgba(147, 162, 185, 0.12);
  flex: none;
}

.conn-card.is-ok .conn-dot {
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(14, 159, 110, 0.12);
}

.conn-card.is-warn .conn-dot {
  background: #d9a340;
  box-shadow: 0 0 0 3px rgba(217, 163, 64, 0.14);
}

.conn-card.is-wait .conn-dot {
  background: var(--blue);
  box-shadow: 0 0 0 3px rgba(47, 107, 255, 0.12);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.35;
  }
}

.conn-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.3;
}

.conn-copy strong {
  font-size: 11.5px;
  font-weight: 550;
}

.conn-copy small {
  margin-top: 2px;
  font-size: 10px;
  color: var(--faint);
}

.conn-arrow {
  margin-left: auto;
  color: #b6c3d6;
}

/* 组别标识 */
.team-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 6px 2px;
  border-top: 1px solid var(--line);
}

.team-badge {
  font-size: 9.5px;
  font-weight: 600;
  color: var(--blue-deep);
  background: var(--blue-soft);
  border-radius: 99px;
  padding: 2px 8px;
}


@media (max-width: 1024px) {
  .sidebar {
    width: 252px;
    transform: translateX(-100%);
    transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1);
    box-shadow: 24px 0 60px -40px rgba(13, 27, 52, 0.5);
  }

  .sidebar.is-open {
    transform: none;
  }

  .scrim {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 35;
    background: rgba(15, 31, 56, 0.28);
    backdrop-filter: blur(2px);
  }
}

@media (max-width: 640px) {
  .sidebar {
    width: 84%;
    max-width: 300px;
  }
}
</style>
