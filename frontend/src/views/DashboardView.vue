<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import {
  ensureReady,
  getGraph,
  getGraphStats,
  getProjectStats,
  listProjectPapers,
  listProjects,
  listSources,
} from '../api/client'
import GraphView from '../components/GraphView.vue'
import Icon from '../components/Icon.vue'
import { toast } from '../store'
import { formatNumber, greeting, weekdayLabel } from '../utils/format'

const projects = ref([])
const sources = ref([])
const stats = ref({
  total_papers: 0,
  first_selected: 0,
  second_screened: 0,
  second_passed: 0,
})
const graphStats = ref({ nodes: 0, relations: 0, papers: 0 })
const heroGraph = ref({ nodes: [], edges: [] })

const todayLabel = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
}).format(new Date())

const passRate = computed(() => {
  if (!stats.value.second_screened) return 0
  return Math.round((stats.value.second_passed / stats.value.second_screened) * 100)
})

const entries = computed(() => [
  {
    to: '/projects',
    icon: 'folder',
    tone: 'blue',
    en: 'PROJECTS',
    title: '研究项目',
    desc: '为每个研究方向建立独立工作区',
    value: projects.value.length,
    unit: '个项目',
    meta: `首轮入选 ${stats.value.first_selected} 篇`,
  },
  {
    to: '/papers',
    icon: 'files',
    tone: 'cyan',
    en: 'LIBRARY',
    title: '文献库',
    desc: '浏览去重后的全部文献与关键词',
    value: stats.value.total_papers,
    unit: '篇文献',
    meta: `${sources.value.length} 个订阅源`,
  },
  {
    to: '/graph',
    icon: 'graph',
    tone: 'violet',
    en: 'KNOWLEDGE GRAPH',
    title: '知识图谱',
    desc: '沿着实体关系探索二轮判断依据',
    value: graphStats.value.nodes,
    unit: '个实体',
    meta: `${graphStats.value.relations} 条关系`,
  },
])

const flow = [
  { step: '01', label: 'RSS 聚合', icon: 'rss' },
  { step: '02', label: '字符初筛', icon: 'filter' },
  { step: '03', label: '图谱 + LLM', icon: 'graph' },
  { step: '04', label: '精读导出', icon: 'book' },
]

async function load() {
  try {
    await ensureReady()
    const [projectList, sourceList, gs] = await Promise.all([
      listProjects(),
      listSources(),
      getGraphStats(),
    ])

    projects.value = projectList
    sources.value = sourceList
    graphStats.value = gs

    if (projectList[0]) {
      const [projectStats, links] = await Promise.all([
        getProjectStats(projectList[0].id),
        listProjectPapers(projectList[0].id, { limit: 6 }),
      ])
      stats.value = projectStats

      for (const link of links) {
        const graph = await getGraph(link.paper.id)
        if (graph.exists && graph.nodes.length) {
          heroGraph.value = graph
          break
        }
      }
    }
  } catch (error) {
    toast('概览加载失败', error.message, 'error')
  }
}

onMounted(load)
</script>

<template>
  <div class="page dashboard">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">{{ todayLabel }} · {{ weekdayLabel() }}</p>
        <h1 class="page-title">{{ greeting() }}，欢迎回来</h1>
        <p class="page-sub">今天从哪个入口开始？</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn btn-primary" :to="{ path: '/projects', query: { new: '1' } }">
          <Icon name="plus" :size="15" />
          新建检索项目
        </RouterLink>
      </div>
    </header>

    <section class="hero card">
      <div class="scenery" aria-hidden="true">
        <span class="hill h1" />
        <span class="hill h2" />
        <span class="hill h3" />
      </div>

      <div class="hero-copy">
        <p class="eyebrow">THREE-ROUND SCREENING</p>
        <h2 class="hero-title">三轮筛选，只读该读的文献。</h2>
        <p class="hero-desc">Three rounds of screening. Read only what truly matters.</p>

        <div class="hero-stats">
          <div>
            <span>二轮通过率</span>
            <strong>{{ passRate }}<small>%</small></strong>
          </div>
          <div>
            <span>已建图文献</span>
            <strong>{{ formatNumber(graphStats.papers) }}<small>篇</small></strong>
          </div>
          <div>
            <span>实体关系</span>
            <strong>{{ formatNumber(graphStats.relations) }}<small>条</small></strong>
          </div>
        </div>
      </div>

      <div class="hero-visual">
        <div class="hero-badge">
          <span class="live-dot" />
          知识图谱预览
        </div>
        <GraphView
          v-if="heroGraph.nodes.length"
          :graph="heroGraph"
          compact
          :interactive="false"
          :height="300"
        />
        <div v-else class="hero-placeholder">
          <Icon name="graph" :size="24" />
          <p>完成一次标注后，<br />这里会出现实体关系图。</p>
        </div>
      </div>
    </section>

    <section class="entries" aria-label="快捷入口">
      <RouterLink
        v-for="(entry, index) in entries"
        :key="entry.to"
        :to="entry.to"
        class="entry card"
        :class="`tone-${entry.tone}`"
        :style="{ '--i': index }"
      >
        <span class="entry-icon"><Icon :name="entry.icon" :size="22" /></span>
        <p class="eyebrow">{{ entry.en }}</p>
        <h3>{{ entry.title }}</h3>
        <p class="entry-desc">{{ entry.desc }}</p>
        <div class="entry-foot">
          <p class="entry-value">
            {{ formatNumber(entry.value) }}<small>{{ entry.unit }}</small>
          </p>
          <span class="entry-arrow"><Icon name="arrowUpRight" :size="16" /></span>
        </div>
        <span class="entry-meta">{{ entry.meta }}</span>
      </RouterLink>
    </section>

    <section class="flow card" aria-label="处理流程">
      <div v-for="(step, index) in flow" :key="step.step" class="flow-step">
        <span class="flow-icon"><Icon :name="step.icon" :size="16" /></span>
        <div>
          <span class="flow-num">{{ step.step }}</span>
          <strong>{{ step.label }}</strong>
        </div>
        <Icon v-if="index < flow.length - 1" name="chevronRight" :size="14" class="flow-arrow" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  gap: 20px;
}

/* ---------- Hero ---------- */

.hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  min-height: 330px;
  overflow: hidden;
  background:
    radial-gradient(120% 150% at 100% 0%, #e6f1ff 0%, rgba(230, 241, 255, 0) 60%),
    linear-gradient(180deg, #f3f9ff 0%, #fbfdff 62%, #eef6ff 100%);
  border-color: #dbe8f9;
}

.scenery {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

/* 首页卡片里的星空 */
.scenery::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1.6px 1.6px at 8% 22%, var(--star), transparent 60%),
    radial-gradient(1.2px 1.2px at 18% 12%, var(--star), transparent 60%),
    radial-gradient(1.8px 1.8px at 27% 28%, var(--star-strong), transparent 60%),
    radial-gradient(1px 1px at 36% 14%, var(--star), transparent 60%),
    radial-gradient(1.4px 1.4px at 44% 34%, var(--star), transparent 60%),
    radial-gradient(1.2px 1.2px at 56% 18%, var(--star-strong), transparent 60%),
    radial-gradient(1.6px 1.6px at 64% 30%, var(--star), transparent 60%),
    radial-gradient(1px 1px at 73% 12%, var(--star), transparent 60%),
    radial-gradient(1.4px 1.4px at 84% 26%, var(--star-strong), transparent 60%),
    radial-gradient(1.2px 1.2px at 92% 16%, var(--star), transparent 60%);
  opacity: 0.85;
}


.hill {
  position: absolute;
  left: -6%;
  right: -6%;
  bottom: -12%;
  height: 62%;
  background: linear-gradient(180deg, var(--hill-1), var(--hill-2));
  opacity: 0.72;
}

.hill.h1 {
  clip-path: polygon(0 62%, 18% 34%, 34% 52%, 52% 22%, 70% 46%, 86% 28%, 100% 44%, 100% 100%, 0 100%);
  opacity: 0.45;
}

.hill.h2 {
  clip-path: polygon(0 74%, 16% 50%, 32% 66%, 48% 40%, 66% 62%, 82% 44%, 100% 58%, 100% 100%, 0 100%);
  opacity: 0.6;
}

.hill.h3 {
  clip-path: polygon(0 86%, 20% 70%, 38% 80%, 56% 60%, 74% 78%, 90% 64%, 100% 72%, 100% 100%, 0 100%);
  opacity: 0.85;
}

.hero-copy {
  position: relative;
  z-index: 1;
  padding: 34px 18px 28px 34px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.hero-title {
  margin-top: 14px;
  font-size: clamp(26px, 3.1vw, 40px);
  line-height: 1.2;
  letter-spacing: -0.04em;
  color: var(--ink);
  white-space: nowrap;
}

.hero-desc {
  margin-top: 12px;
  max-width: 460px;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.01em;
}


.hero-stats {
  display: flex;
  gap: 28px;
  margin-top: auto;
  padding-top: 28px;
}

.hero-stats div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.hero-stats span {
  font-size: 10.5px;
  color: var(--faint);
}

.hero-stats strong {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.hero-stats small {
  margin-left: 2px;
  font-size: 10px;
  font-weight: 450;
  color: var(--faint);
}

.hero-visual {
  position: relative;
  min-height: 260px;
}

.hero-visual::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(90deg, #f5faff 0%, transparent 18%);
}

.hero-badge {
  position: absolute;
  top: 18px;
  right: 20px;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 9px;
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--muted);
  font-size: 10px;
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow-xs);
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 99px;
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(14, 159, 110, 0.1);
}

.hero-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #9db4d6;
  font-size: 11.5px;
  line-height: 1.7;
  text-align: center;
}

/* ---------- 三个入口 ---------- */

.entries {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.entry {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 208px;
  padding: 22px 22px 18px;
  overflow: hidden;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  animation: rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--i) * 60ms);
}

.entry::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  background: radial-gradient(120% 90% at 100% 0%, var(--entry-glow), transparent 62%);
  transition: opacity 0.2s ease;
}

.entry:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
  border-color: var(--entry-line);
}

.entry:hover::before {
  opacity: 1;
}

.entry-icon {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 13px;
  background: var(--entry-soft);
  color: var(--entry-color);
}

.entry .eyebrow {
  position: relative;
  z-index: 1;
  margin-top: 16px;
  color: var(--entry-color);
}

.entry .eyebrow::before {
  background: var(--entry-color);
}

.entry h3 {
  position: relative;
  z-index: 1;
  margin-top: 6px;
  font-size: 20px;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.entry-desc {
  position: relative;
  z-index: 1;
  margin-top: 5px;
  font-size: 11.5px;
  color: var(--muted);
}

.entry-foot {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 18px;
}

.entry-value {
  font-size: 32px;
  line-height: 1;
  font-weight: 600;
  letter-spacing: -0.04em;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.entry-value small {
  margin-left: 5px;
  font-size: 10.5px;
  font-weight: 450;
  letter-spacing: 0;
  color: var(--faint);
}

.entry-arrow {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid var(--line);
  color: var(--muted);
  transition: 0.18s ease;
}

.entry:hover .entry-arrow {
  background: var(--entry-color);
  border-color: var(--entry-color);
  color: #fff;
  transform: translate(2px, -2px);
}

.entry-meta {
  position: relative;
  z-index: 1;
  margin-top: 8px;
  font-size: 10px;
  color: var(--faint);
}

.tone-blue {
  --entry-color: #2f6bff;
  --entry-soft: #eaf2ff;
  --entry-glow: rgba(47, 107, 255, 0.14);
  --entry-line: #b9cff5;
}

.tone-cyan {
  --entry-color: #0f8a9e;
  --entry-soft: #e4f7fa;
  --entry-glow: rgba(15, 138, 158, 0.14);
  --entry-line: #b6e3ea;
}

.tone-violet {
  --entry-color: #6557d8;
  --entry-soft: #f0eeff;
  --entry-glow: rgba(101, 87, 216, 0.15);
  --entry-line: #ccc4f4;
}

/* ---------- 流程 ---------- */

.flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 20px;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.flow-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 9px;
  background: var(--blue-soft);
  color: var(--blue-deep);
}

.flow-step > div {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.flow-num {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 8.5px;
  color: var(--faint);
}

.flow-step strong {
  font-size: 11.5px;
  font-weight: 550;
  color: var(--ink-soft);
  white-space: nowrap;
}

.flow-arrow {
  margin-left: auto;
  color: var(--line-3);
  flex: none;
}

/* ---------- 响应式 ---------- */

@media (max-width: 1180px) {
  .hero {
    grid-template-columns: minmax(0, 1fr) minmax(280px, 0.72fr);
  }

  .hero-title {
    white-space: normal;
  }

  .entries {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .entry:last-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .hero {
    grid-template-columns: 1fr;
  }

  .hero-copy {
    padding: 28px 24px 8px;
  }

  .hero-visual {
    min-height: 230px;
  }

  .hero-visual::after {
    display: none;
  }

  .flow {
    flex-wrap: wrap;
    gap: 12px 18px;
  }

  .flow-arrow {
    display: none;
  }
}

@media (max-width: 640px) {
  .hero-copy {
    padding: 24px 18px 6px;
  }

  .hero-title {
    font-size: 25px;
  }

  .hero-stats {
    gap: 18px;
  }

  .entries {
    grid-template-columns: 1fr;
  }

  .entry:last-child {
    grid-column: auto;
  }

  .flow-step {
    flex: 1 1 44%;
  }
}
</style>
