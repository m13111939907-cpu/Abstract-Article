<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ensureReady, listPapers, listProjects } from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import { toast } from '../store'
import { domainOf, formatDate } from '../utils/format'

const route = useRoute()

const papers = ref([])
const projects = ref([])
const projectId = ref(null)
const loading = ref(true)
const query = ref(String(route.query.q || ''))
const sourceFilter = ref('all')
const sortBy = ref('newest')
const visibleCount = ref(10)

const domains = computed(() => {
  const counts = new Map()
  for (const paper of papers.value) {
    const domain = domainOf(paper.url)
    counts.set(domain, (counts.get(domain) || 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1])
})

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  let list = papers.value

  if (sourceFilter.value !== 'all') {
    list = list.filter((paper) => domainOf(paper.url) === sourceFilter.value)
  }

  if (keyword) {
    list = list.filter((paper) =>
      [paper.title, paper.authors, paper.abstract, ...(paper.keywords || [])]
        .join(' ')
        .toLowerCase()
        .includes(keyword),
    )
  }

  return [...list].sort((a, b) => {
    if (sortBy.value === 'title') return a.title.localeCompare(b.title)
    return new Date(b.published_at || 0) - new Date(a.published_at || 0)
  })
})

const visiblePapers = computed(() => filtered.value.slice(0, visibleCount.value))

const grouped = computed(() => {
  const groups = []
  for (const paper of visiblePapers.value) {
    const date = new Date(paper.published_at || Date.now())
    const key = `${date.getFullYear()} 年 ${date.getMonth() + 1} 月`
    let group = groups.find((item) => item.key === key)
    if (!group) {
      group = { key, papers: [] }
      groups.push(group)
    }
    group.papers.push(paper)
  }
  return groups
})

watch([query, sourceFilter, sortBy], () => {
  visibleCount.value = 10
})

watch(
  () => route.query.q,
  (value) => {
    query.value = String(value || '')
  },
)

async function loadPapers() {
  if (!projectId.value) {
    papers.value = []
    return
  }
  papers.value = await listPapers({ projectId: projectId.value, limit: 500 })
}

async function load() {
  loading.value = true
  try {
    await ensureReady()
    projects.value = await listProjects()
    const requested = Number(route.query.project)
    const matched = projects.value.find((item) => item.id === requested)
    projectId.value = matched ? matched.id : projects.value[0]?.id ?? null
    await loadPapers()
  } catch (error) {
    toast('文献库加载失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

watch(projectId, () => {
  visibleCount.value = 10
  loadPapers().catch((error) => toast('文献库加载失败', error.message, 'error'))
})

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">LITERATURE LIBRARY</p>
        <h1 class="page-title">文献库</h1>
        <p class="page-sub">
          当前项目下的文献。切换项目只会显示属于该项目的论文。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn btn-secondary" to="/sources">
          <Icon name="rss" :size="15" />
          管理订阅源
        </RouterLink>
        <RouterLink class="btn btn-primary" to="/graph">
          <Icon name="graph" :size="15" />
          知识图谱
        </RouterLink>
      </div>
    </header>

    <section class="toolbar card">
      <div class="search-field">
        <Icon name="search" :size="15" />
        <input
          v-model="query"
          class="input"
          type="search"
          placeholder="搜索标题、作者、摘要或关键词"
          aria-label="搜索文献"
        />
      </div>

      <div class="toolbar-right">
        <label class="select-wrap">
          <Icon name="folder" :size="14" />
          <select v-model="projectId" class="select" aria-label="选择项目">
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </label>

        <label class="select-wrap">
          <Icon name="globe" :size="14" />
          <select v-model="sourceFilter" class="select" aria-label="按来源筛选">
            <option value="all">全部来源</option>
            <option v-for="[domain, count] in domains" :key="domain" :value="domain">
              {{ domain }}（{{ count }}）
            </option>
          </select>
        </label>

        <label class="select-wrap">
          <Icon name="sort" :size="14" />
          <select v-model="sortBy" class="select" aria-label="排序方式">
            <option value="newest">最新发布</option>
            <option value="title">标题 A-Z</option>
          </select>
        </label>
      </div>
    </section>

    <div class="list-meta">
      <p>
        共 <strong>{{ filtered.length }}</strong> 篇
        <span v-if="query" class="faint">· 搜索「{{ query }}」</span>
      </p>
      <span>已显示 {{ visiblePapers.length }} 篇</span>
    </div>

    <div v-if="loading" class="paper-list card">
      <div v-for="index in 5" :key="index" class="paper-skeleton">
        <div class="skeleton" style="width: 26px; height: 10px" />
        <div style="flex: 1">
          <div class="skeleton" style="width: 62%; height: 14px" />
          <div class="skeleton" style="width: 34%; height: 9px; margin-top: 9px" />
        </div>
      </div>
    </div>

    <div v-else-if="filtered.length" class="paper-list card">
      <section v-for="group in grouped" :key="group.key" class="month-group">
        <h2 class="month-label">
          <span>{{ group.key }}</span>
          <i />
          <small>{{ group.papers.length }} 篇</small>
        </h2>

        <RouterLink
          v-for="paper in group.papers"
          :key="paper.id"
          class="paper-row"
          :to="{ path: `/papers/${paper.id}`, query: { from: 'papers' } }"
        >
          <span class="paper-no mono">{{ String(paper.id).padStart(2, '0') }}</span>
          <div class="paper-main">
            <h3>{{ paper.title }}</h3>
            <p class="paper-authors">{{ paper.authors }}</p>
            <div class="chips paper-tags">
              <span v-for="keyword in paper.keywords.slice(0, 3)" :key="keyword" class="chip">
                {{ keyword }}
              </span>
              <span v-if="paper.keywords.length > 3" class="chip-more">
                +{{ paper.keywords.length - 3 }}
              </span>
            </div>
          </div>
          <div class="paper-side">
            <span class="paper-domain">{{ domainOf(paper.url) }}</span>
            <time class="num">{{ formatDate(paper.published_at) }}</time>
          </div>
          <span class="paper-arrow"><Icon name="arrowUpRight" :size="15" /></span>
        </RouterLink>
      </section>
    </div>

    <EmptyState
      v-else
      icon="files"
      title="没有找到匹配的文献"
      text="换一个关键词，或者到订阅源页面添加新的 RSS 源后重新抓取。"
    >
      <RouterLink class="btn btn-secondary btn-sm" to="/sources">前往订阅源</RouterLink>
    </EmptyState>

    <div v-if="!loading && visibleCount < filtered.length" class="load-more">
      <button class="btn btn-secondary" type="button" @click="visibleCount += 10">
        加载更多
        <Icon name="chevronDown" :size="14" />
      </button>
      <span>还有 {{ filtered.length - visibleCount }} 篇</span>
    </div>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
}

.toolbar .search-field {
  flex: 1;
  max-width: 440px;
}

.toolbar .search-field .input {
  height: 36px;
  border-color: transparent;
  background: var(--surface-soft);
}

.toolbar .search-field .input:focus {
  background: #fff;
  border-color: var(--line-2);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.select-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.select-wrap :deep(.icon) {
  position: absolute;
  left: 10px;
  color: var(--faint);
  pointer-events: none;
}

.select-wrap .select {
  height: 34px;
  padding: 0 26px 0 31px;
  border-color: var(--line);
  background: var(--surface-soft);
  font-size: 11.5px;
  color: var(--muted);
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, #9aa9be 50%),
    linear-gradient(135deg, #9aa9be 50%, transparent 50%);
  background-position: calc(100% - 13px) 14px, calc(100% - 9px) 14px;
  background-size: 4px 4px, 4px 4px;
  background-repeat: no-repeat;
}

.list-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
  color: var(--faint);
  font-size: 11px;
}

.list-meta strong {
  color: var(--ink-soft);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.paper-list {
  padding: 8px 26px 18px;
}

.month-group {
  padding-top: 12px;
}

.month-label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0 8px;
  font-size: 10px;
  font-weight: 550;
  letter-spacing: 0.08em;
  color: #9aa9be;
}

.month-label span {
  white-space: nowrap;
}

.month-label i {
  flex: 1;
  height: 1px;
  background: var(--line);
}

.month-label small {
  font-size: 9.5px;
  color: #b3bfd0;
  font-weight: 450;
  letter-spacing: 0;
}

.paper-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 4px;
  border-radius: 10px;
  color: var(--ink);
  border-bottom: 1px dashed #edf3fb;
  transition: background 0.16s ease;
}

.month-group .paper-row:last-child {
  border-bottom: 0;
}

.paper-row:hover {
  background: #f9fbff;
}

.paper-no {
  padding-top: 3px;
  font-size: 9.5px;
  color: #b3c0d2;
  flex: none;
}

.paper-main {
  flex: 1;
  min-width: 0;
}

.paper-main h3 {
  font-size: 14.5px;
  font-weight: 550;
  line-height: 1.5;
  letter-spacing: -0.01em;
  color: var(--ink);
  transition: color 0.16s ease;
}

.paper-row:hover h3 {
  color: var(--blue-deep);
}

.paper-authors {
  margin-top: 3px;
  font-size: 10.5px;
  color: var(--faint);
}

.paper-tags {
  margin-top: 9px;
}

.paper-tags .chip {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--muted);
  font-weight: 450;
}

.paper-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex: none;
  padding-top: 2px;
  width: 104px;
}

.paper-domain {
  max-width: 100%;
  font-size: 9.5px;
  color: #8fa1ba;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.paper-side time {
  font-size: 9.5px;
  color: #b0bccc;
}

.paper-arrow {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  margin-top: -1px;
  border-radius: 7px;
  color: #b3c0d2;
  flex: none;
  transition: 0.16s ease;
}

.paper-row:hover .paper-arrow {
  background: var(--blue-soft);
  color: var(--blue-deep);
}

.paper-skeleton {
  display: flex;
  gap: 14px;
  padding: 20px 4px;
  border-bottom: 1px dashed #edf3fb;
  align-items: flex-start;
}

.load-more {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px 0 8px;
}

.load-more span {
  font-size: 10px;
  color: var(--faint);
}

/* ---------- 最近入库 ---------- */

.recent-card {
  padding: 20px 24px 6px;
}

.recent-card .section-head {
  margin-bottom: 12px;
}

.recent-count {
  font-size: 10.5px;
  color: var(--faint);
  white-space: nowrap;
}

.recent-paper {
  display: flex;
  align-items: center;
  gap: 11px;
  color: var(--ink);
  max-width: 100%;
}

.recent-index {
  flex: none;
  font-size: 9.5px;
  color: var(--faint);
}

.recent-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.4;
}

.recent-copy strong {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-copy small {
  margin-top: 2px;
  font-size: 10px;
  color: var(--faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-paper:hover strong {
  color: var(--blue-deep);
}

.row-arrow {
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  border-radius: 7px;
  color: var(--faint);
  transition: 0.16s ease;
}

.row-arrow:hover {
  color: var(--blue-deep);
  background: var(--blue-soft);
}

@media (max-width: 760px) {
  .recent-card {
    padding: 16px 14px 4px;
  }

  .recent-card .table th:nth-child(2),
  .recent-card .table td:nth-child(2),
  .recent-card .table th:nth-child(3),
  .recent-card .table td:nth-child(3),
  .recent-card .table th:nth-child(4),
  .recent-card .table td:nth-child(4) {
    display: none;
  }

  .recent-copy strong {
    white-space: normal;
  }
}

@media (max-width: 760px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .toolbar .search-field {
    max-width: none;
  }

  .toolbar-right {
    justify-content: space-between;
  }

  .paper-list {
    padding: 4px 16px 12px;
  }

  .paper-side {
    display: none;
  }

  .paper-main h3 {
    font-size: 13.5px;
  }

  .paper-tags .chip:nth-child(3) {
    display: none;
  }
}
</style>
