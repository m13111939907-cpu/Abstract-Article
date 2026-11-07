<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  annotatePaper,
  ensureReady,
  getGraph,
  getGraphStats,
  listPapers,
} from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import GraphView from '../components/GraphView.vue'
import Icon from '../components/Icon.vue'
import { toast } from '../store'
import { formatDate } from '../utils/format'
import { graphType } from '../utils/graph'

const route = useRoute()
const router = useRouter()

const papers = ref([])
const graphStats = ref({ nodes: 0, relations: 0, papers: 0 })
const selectedPaperId = ref(null)
const graph = ref({ exists: false, nodes: [], edges: [] })
const selectedNode = ref(null)
const loading = ref(true)
const graphLoading = ref(false)
const annotating = ref(false)
const search = ref('')
const graphRef = ref(null)
const railList = ref(null)
const isMobile = ref(false)
let mediaQuery = null

const graphHeight = computed(() => (isMobile.value ? 340 : 520))

const filteredPapers = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return papers.value
  return papers.value.filter((paper) =>
    `${paper.title} ${paper.authors}`.toLowerCase().includes(keyword),
  )
})

const selectedPaper = computed(
  () => papers.value.find((paper) => paper.id === selectedPaperId.value) || null,
)

const legend = computed(() => {
  const types = [...new Set(graph.value.nodes.map((node) => node.type))]
  return types.map((type) => ({ type, ...graphType(type) }))
})

const selectedType = computed(() =>
  selectedNode.value ? graphType(selectedNode.value.type) : null,
)

const connections = computed(() => {
  if (!selectedNode.value) return []
  const nodesById = new Map(graph.value.nodes.map((node) => [node.id, node]))
  return graph.value.edges
    .filter(
      (edge) =>
        edge.source === selectedNode.value.id || edge.target === selectedNode.value.id,
    )
    .map((edge) => {
      const outgoing = edge.source === selectedNode.value.id
      const otherId = outgoing ? edge.target : edge.source
      const other = nodesById.get(otherId)
      return {
        id: otherId,
        label: other?.label || otherId,
        type: other?.type || 'CONCEPT',
        relation: edge.type.replaceAll('_', ' '),
        outgoing,
      }
    })
    .slice(0, 8)
})

async function scrollActiveIntoView() {
  await nextTick()
  railList.value
    ?.querySelector('.rail-item.is-active')
    ?.scrollIntoView({ block: 'nearest' })
}

async function pickPaper(paper, updateQuery = true) {
  if (selectedPaperId.value === paper.id && graph.value.paper_id === paper.id) return
  selectedPaperId.value = paper.id
  selectedNode.value = null
  graphLoading.value = true
  try {
    graph.value = await getGraph(paper.id)
    if (updateQuery) {
      router.replace({ path: '/graph', query: { paper: String(paper.id) } })
    }
    scrollActiveIntoView()
  } catch (error) {
    toast('图谱加载失败', error.message, 'error')
  } finally {
    graphLoading.value = false
  }
}

async function load() {
  loading.value = true
  try {
    await ensureReady()
    const [paperList, stats] = await Promise.all([listPapers({ limit: 500 }), getGraphStats()])
    papers.value = paperList
    graphStats.value = stats

    if (!paperList.length) return

    const preferredId = route.query.paper
    const preferred =
      paperList.find((paper) => String(paper.id) === String(preferredId)) ||
      paperList.find((paper) => paper.id === 1)
    const ordered = preferred
      ? [preferred, ...paperList.filter((paper) => paper.id !== preferred.id)]
      : paperList

    for (const paper of ordered.slice(0, 7)) {
      const candidate = await getGraph(paper.id)
      if (candidate.exists && candidate.nodes.length) {
        selectedPaperId.value = paper.id
        graph.value = candidate
        if (String(preferredId) !== String(paper.id)) {
          router.replace({ path: '/graph', query: { paper: String(paper.id) } })
        }
        scrollActiveIntoView()
        return
      }
    }

    selectedPaperId.value = ordered[0].id
    graph.value = await getGraph(ordered[0].id)
    scrollActiveIntoView()
  } catch (error) {
    toast('图谱加载失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

async function runAnnotate() {
  if (!selectedPaperId.value || annotating.value) return
  annotating.value = true
  try {
    const result = await annotatePaper(selectedPaperId.value)
    toast(
      '图谱已生成',
      `${result.entities} 个实体、${result.relations} 条关系已写入 Neo4j。`,
    )
    graph.value = await getGraph(selectedPaperId.value)
    graphStats.value = await getGraphStats()
    selectedNode.value = null
  } catch (error) {
    toast('标注失败', error.message, 'error')
  } finally {
    annotating.value = false
  }
}

function onSelectNode(node) {
  selectedNode.value = node
}

function focusNeighbor(id) {
  graphRef.value?.focusNode(id)
}

function pickFromSelect(event) {
  const paper = papers.value.find((item) => item.id === Number(event.target.value))
  if (paper) pickPaper(paper)
}

function zoom(factor) {
  graphRef.value?.zoomBy(factor)
}

function resetView() {
  graphRef.value?.resetView()
}

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 760px)')
  isMobile.value = mediaQuery.matches
  mediaQuery.addEventListener('change', (event) => {
    isMobile.value = event.matches
  })
  load()
})

onBeforeUnmount(() => {
  mediaQuery = null
})
</script>

<template>
  <div class="page graph-page">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">KNOWLEDGE GRAPH</p>
        <h1 class="page-title">知识图谱</h1>
        <p class="page-sub">
          每篇文献一张图。实体与关系由大模型抽取，写入 Neo4j 后在这里可视化、追溯与复核。
        </p>
      </div>
      <div class="page-actions">
        <button
          class="btn btn-primary"
          type="button"
          :disabled="!selectedPaperId || annotating"
          @click="runAnnotate"
        >
          <Icon name="sparkles" :size="15" />
          {{ annotating ? '标注中…' : '重新标注本篇' }}
        </button>
      </div>
    </header>

    <section class="stats graph-stats">
      <article class="stat">
        <span class="stat-mark"><Icon name="graph" :size="16" /></span>
        <p class="stat-label">实体节点</p>
        <p class="stat-value">{{ graphStats.nodes }}<span class="stat-unit">个</span></p>
        <p class="stat-foot">去重后的概念、方法、数据集</p>
      </article>
      <article class="stat">
        <span class="stat-mark"><Icon name="link" :size="16" /></span>
        <p class="stat-label">关系边</p>
        <p class="stat-value">{{ graphStats.relations }}<span class="stat-unit">条</span></p>
        <p class="stat-foot">带置信度的有向关系</p>
      </article>
      <article class="stat">
        <span class="stat-mark"><Icon name="layers" :size="16" /></span>
        <p class="stat-label">已建图文献</p>
        <p class="stat-value">{{ graphStats.papers }}<span class="stat-unit">篇</span></p>
        <p class="stat-foot">按 paper_id 隔离存储</p>
      </article>
    </section>

    <div v-if="loading" class="explorer card">
      <div class="rail-skeleton">
        <div class="skeleton" style="height: 34px; width: 100%" />
        <div v-for="i in 6" :key="i" class="skeleton" style="height: 54px; width: 100%; margin-top: 8px" />
      </div>
      <div class="canvas-skeleton">
        <div class="skeleton" style="width: 100%; height: 100%; border-radius: 0" />
      </div>
    </div>

    <section v-else class="explorer card">
      <div class="mobile-picker">
        <span>当前文献</span>
        <select class="select" :value="selectedPaperId ?? ''" @change="pickFromSelect">
          <option v-for="paper in papers" :key="paper.id" :value="paper.id">
            {{ paper.title }}
          </option>
        </select>
      </div>

      <aside class="paper-rail">
        <div class="rail-head">
          <h2>文献列表</h2>
          <span>{{ papers.length }}</span>
        </div>
        <div class="search-field rail-search">
          <Icon name="search" :size="14" />
          <input
            v-model="search"
            class="input"
            type="search"
            placeholder="搜索标题或作者"
            aria-label="搜索图谱文献"
          />
        </div>

        <div ref="railList" class="rail-list">
          <button
            v-for="paper in filteredPapers"
            :key="paper.id"
            type="button"
            class="rail-item"
            :class="{ 'is-active': paper.id === selectedPaperId }"
            @click="pickPaper(paper)"
          >
            <span class="rail-index mono">{{ String(paper.id).padStart(2, '0') }}</span>
            <span class="rail-body">
              <strong>{{ paper.title }}</strong>
              <small>{{ paper.authors }}</small>
            </span>
          </button>
          <p v-if="!filteredPapers.length" class="rail-empty">没有匹配的文献。</p>
        </div>
      </aside>

      <div class="canvas">
        <div class="canvas-head">
          <div class="canvas-title">
            <span class="canvas-kicker">CURRENT PAPER</span>
            <strong>{{ selectedPaper?.title || '未选择文献' }}</strong>
          </div>
          <div class="canvas-tools">
            <button class="icon-btn" type="button" aria-label="放大" @click="zoom(1.2)">
              <Icon name="zoomIn" :size="16" />
            </button>
            <button class="icon-btn" type="button" aria-label="缩小" @click="zoom(0.8)">
              <Icon name="zoomOut" :size="16" />
            </button>
            <button class="icon-btn" type="button" aria-label="重置视图" @click="resetView">
              <Icon name="maximize" :size="15" />
            </button>
          </div>
        </div>

        <div class="canvas-body">
          <GraphView
            v-if="graph.exists && graph.nodes.length"
            ref="graphRef"
            :key="graph.paper_id"
            :graph="graph"
            :height="graphHeight"
            @select="onSelectNode"
          />

          <div v-else class="canvas-empty">
            <EmptyState
              icon="graph"
              title="这篇文献还没有知识图谱"
              text="运行一次标注，模型会从摘要中抽取实体与关系，并写入 Neo4j。"
            >
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="annotating"
                @click="runAnnotate"
              >
                {{ annotating ? '标注中…' : '运行标注' }}
              </button>
            </EmptyState>
          </div>

          <div v-if="graphLoading" class="canvas-loading">
            <span class="loading-ring" />
            <p>正在读取 Neo4j…</p>
          </div>

          <div v-if="legend.length" class="legend">
            <span v-for="item in legend" :key="item.type">
              <i :style="{ background: item.color }" />
              {{ item.label }}
            </span>
          </div>

          <aside v-if="selectedNode" class="inspector">
            <button
              class="inspector-close"
              type="button"
              aria-label="关闭节点详情"
              @click="selectedNode = null"
            >
              <Icon name="x" :size="13" />
            </button>
            <span
              class="inspector-type"
              :style="{ color: selectedType.color, borderColor: `${selectedType.color}33` }"
            >
              {{ selectedType.label }} · {{ selectedNode.type }}
            </span>
            <h3>{{ selectedNode.label }}</h3>
            <p class="inspector-meta">{{ connections.length }} 条直接关联</p>

            <div v-if="connections.length" class="connections">
              <button
                v-for="item in connections"
                :key="`${item.id}-${item.relation}`"
                type="button"
                @click="focusNeighbor(item.id)"
              >
                <span class="conn-dot" :style="{ background: graphType(item.type).color }" />
                <span class="conn-name">{{ item.label }}</span>
                <small>{{ item.relation }}</small>
              </button>
            </div>
            <p v-else class="inspector-meta">这是一个孤立节点。</p>
          </aside>
        </div>

        <div class="canvas-foot">
          <span>拖拽节点 · 滚轮缩放 · 点击节点查看关联</span>
          <span v-if="selectedPaper">发表于 {{ formatDate(selectedPaper.published_at) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.graph-page {
  gap: 20px;
}

.graph-stats .stat {
  padding: 15px 18px 13px;
}

.graph-stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.mobile-picker {
  display: none;
}

.graph-stats .stat-value {
  font-size: 26px;
}

.explorer {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  height: 632px;
  overflow: hidden;
}

/* ---------- 左侧列表 ---------- */

.paper-rail {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--line);
  background: #fcfdff;
}

.rail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 17px 17px 10px;
}

.rail-head h2 {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}

.rail-head span {
  font-size: 9.5px;
  color: var(--faint);
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 99px;
  padding: 1px 7px;
}

.rail-search {
  margin: 0 14px 10px;
}

.rail-search .input {
  height: 33px;
  padding-left: 31px;
  border-color: var(--line);
  background: #fff;
  font-size: 11px;
}

.rail-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 9px 12px;
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 12px,
    #000 calc(100% - 8px),
    transparent 100%
  );
  mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 12px,
    #000 calc(100% - 8px),
    transparent 100%
  );
}

.rail-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  width: 100%;
  padding: 10px 9px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  text-align: left;
  transition: 0.14s ease;
}

.rail-item + .rail-item {
  margin-top: 2px;
}

.rail-item:hover {
  background: var(--blue-softer);
}

.rail-item.is-active {
  background: #fff;
  border-color: #dbe8fa;
  box-shadow: 0 4px 12px -10px rgba(13, 27, 52, 0.3);
}

.rail-index {
  padding-top: 2px;
  font-size: 8.5px;
  color: #b1bfd1;
  flex: none;
}

.rail-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 3px;
}

.rail-body strong {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.5;
  color: var(--ink-soft);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rail-item.is-active .rail-body strong {
  color: var(--blue-deep);
}

.rail-body small {
  font-size: 9px;
  color: #a9b7c9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail-empty {
  padding: 20px 10px;
  font-size: 10.5px;
  color: var(--faint);
  text-align: center;
}

/* ---------- 画布 ---------- */

.canvas {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}

.canvas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  height: 61px;
  padding: 0 18px 0 22px;
  border-bottom: 1px solid var(--line);
}

.canvas-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.canvas-kicker {
  font-size: 7.5px;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: #b0bdd0;
}

.canvas-title strong {
  font-size: 11.5px;
  font-weight: 550;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-tools {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: none;
  padding: 2px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}

.canvas-tools .icon-btn {
  width: 28px;
  height: 27px;
  border-radius: 6px;
}

.canvas-body {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.canvas-empty {
  display: grid;
  place-items: center;
  height: 100%;
}

.legend {
  position: absolute;
  left: 16px;
  bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  padding: 7px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(8px);
  pointer-events: none;
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 9px;
  color: var(--muted);
}

.legend i {
  width: 6px;
  height: 6px;
  border-radius: 99px;
}

.inspector {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 224px;
  padding: 13px 14px 10px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 16px 40px -24px rgba(13, 27, 52, 0.38);
  backdrop-filter: blur(10px);
}

.inspector-close {
  position: absolute;
  right: 9px;
  top: 9px;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--faint);
}

.inspector-close:hover {
  background: var(--surface-soft);
  color: var(--ink-soft);
}

.inspector-type {
  display: inline-block;
  font-size: 8px;
  font-weight: 550;
  letter-spacing: 0.04em;
  border: 1px solid;
  border-radius: 99px;
  padding: 1px 6px;
}

.inspector h3 {
  margin-top: 7px;
  padding-right: 16px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--ink);
}

.inspector-meta {
  margin-top: 3px;
  font-size: 9px;
  color: var(--faint);
}

.connections {
  margin-top: 9px;
  padding-top: 7px;
  border-top: 1px dashed #e9f1fb;
  display: flex;
  flex-direction: column;
}

.connections button {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 6px 4px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  text-align: left;
}

.connections button:hover {
  background: var(--blue-softer);
}

.conn-dot {
  width: 5px;
  height: 5px;
  border-radius: 99px;
  flex: none;
}

.conn-name {
  flex: 1;
  min-width: 0;
  font-size: 10px;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.connections small {
  font-size: 7.5px;
  color: #a6b4c7;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(3px);
  color: var(--faint);
  font-size: 10.5px;
}

.loading-ring {
  width: 22px;
  height: 22px;
  border: 2px solid #dfeafa;
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.canvas-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 35px;
  padding: 0 18px;
  border-top: 1px solid var(--line);
  background: var(--surface-soft);
  color: #a7b5c9;
  font-size: 9px;
}

/* ---------- 骨架 ---------- */

.explorer:has(.rail-skeleton) {
  grid-template-columns: 270px 1fr;
}

.rail-skeleton {
  padding: 16px 14px;
  border-right: 1px solid var(--line);
}

.canvas-skeleton {
  overflow: hidden;
}

@media (max-width: 980px) {
  .explorer {
    grid-template-columns: 224px minmax(0, 1fr);
    height: 580px;
  }

  .inspector {
    width: 200px;
  }
}

@media (max-width: 760px) {
  .graph-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .graph-stats .stat:last-child {
    grid-column: 1 / -1;
  }

  .explorer {
    grid-template-columns: minmax(0, 1fr);
    height: auto;
  }

  .mobile-picker {
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 12px 14px;
    border-bottom: 1px solid var(--line);
    background: var(--surface-soft);
  }

  .mobile-picker span {
    font-size: 8.5px;
    font-weight: 600;
    letter-spacing: 0.12em;
    color: #a4b3c7;
  }

  .mobile-picker .select {
    height: 36px;
    font-size: 11px;
    color: var(--ink-soft);
  }

  .paper-rail {
    display: none;
  }

  .canvas {
    height: auto;
  }

  .canvas-head {
    height: 54px;
  }

  .canvas-body {
    height: 360px;
    flex: none;
  }

  .canvas-foot {
    display: none;
  }

  .canvas-empty {
    min-height: 340px;
  }

  .inspector {
    left: 12px;
    right: 12px;
    width: auto;
    top: auto;
    bottom: 12px;
  }

  .legend {
    display: none;
  }
}
</style>
