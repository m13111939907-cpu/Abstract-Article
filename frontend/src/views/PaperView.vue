<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { annotatePaper, ensureReady, getReading } from '../api/client'
import EmptyState from '../components/EmptyState.vue'
import GraphView from '../components/GraphView.vue'
import Icon from '../components/Icon.vue'
import ScoreRing from '../components/ScoreRing.vue'
import { toast } from '../store'
import { domainOf, formatDate, formatDateTime } from '../utils/format'

const route = useRoute()

const reading = ref(null)
const loading = ref(true)
const notFound = ref(false)
const annotating = ref(false)

const paper = computed(() => reading.value?.paper || null)
const graph = computed(
  () => reading.value?.graph || { exists: false, nodes: [], edges: [] },
)
const screening = computed(() => reading.value?.screening || null)
const projectId = computed(() => route.query.project || null)

const backTo = computed(() =>
  projectId.value ? `/projects/${projectId.value}` : '/papers',
)
const backLabel = computed(() =>
  projectId.value ? '返回项目' : '返回文献库',
)

const doiLink = computed(() =>
  paper.value?.doi ? `https://doi.org/${paper.value.doi}` : paper.value?.url,
)

const verdict = computed(() => {
  if (!screening.value) return null
  return screening.value.passed ? '建议精读' : '暂缓精读'
})

const topWords = computed(() => (paper.value?.top_words || []).slice(0, 8))

async function load() {
  loading.value = true
  try {
    await ensureReady()
    reading.value = await getReading(route.params.id, projectId.value)
    notFound.value = false
  } catch (error) {
    if (!reading.value) notFound.value = true
    else toast('刷新失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

async function runAnnotate() {
  if (annotating.value) return
  annotating.value = true
  try {
    const result = await annotatePaper(paper.value.id)
    toast(
      '图谱已更新',
      `生成 ${result.entities} 个实体、${result.relations} 条关系。`,
    )
    reading.value = await getReading(route.params.id, projectId.value)
  } catch (error) {
    toast('标注失败', error.message, 'error')
  } finally {
    annotating.value = false
  }
}

async function copyText(text, message) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const area = document.createElement('textarea')
    area.value = text
    document.body.appendChild(area)
    area.select()
    document.execCommand('copy')
    area.remove()
  }
  toast(message, '', 'success')
}

function citationText() {
  if (!paper.value) return ''
  const year = paper.value.published_at
    ? new Date(paper.value.published_at).getFullYear()
    : ''
  return `${paper.value.authors}. ${paper.value.title}[J]. ${year}. DOI: ${paper.value.doi}.`
}

watch(
  () => route.params.id,
  () => load(),
)

onMounted(load)
</script>

<template>
  <div v-if="notFound" class="page">
    <EmptyState
      icon="file"
      title="文献不存在"
      text="它可能已被删除，或者链接已经失效。"
    >
      <RouterLink class="btn btn-primary btn-sm" to="/papers">返回文献库</RouterLink>
    </EmptyState>
  </div>

  <div v-else class="page reading-page">
    <div v-if="loading && !paper" class="reading-loading">
      <div class="skeleton" style="width: 100px; height: 11px" />
      <div class="skeleton" style="width: 74%; height: 34px; margin-top: 16px" />
      <div class="skeleton" style="width: 42%; height: 13px; margin-top: 12px" />
      <div class="skeleton" style="width: 100%; height: 340px; margin-top: 28px; border-radius: 18px" />
    </div>

    <template v-else-if="paper">
      <header class="reading-head">
        <RouterLink class="back-link" :to="backTo">
          <Icon name="chevronLeft" :size="13" />
          {{ backLabel }}
        </RouterLink>

        <div class="reading-title-row">
          <div class="reading-title-main">
            <p class="eyebrow">READING · PAPER {{ String(paper.id).padStart(2, '0') }}</p>
            <h1 class="reading-title">{{ paper.title }}</h1>
            <p class="reading-authors">{{ paper.authors }}</p>

            <div class="reading-meta">
              <span><Icon name="calendar" :size="13" />{{ formatDate(paper.published_at) }}</span>
              <span>
                <Icon name="link" :size="13" />
                <a :href="doiLink" target="_blank" rel="noreferrer">{{ paper.doi || '外部链接' }}</a>
              </span>
              <span><Icon name="globe" :size="13" />{{ domainOf(paper.url) }}</span>
              <span v-if="screening" class="status" :class="screening.passed ? 'is-green' : 'is-red'">
                {{ verdict }}
              </span>
            </div>
          </div>

          <div class="reading-actions">
            <button
              class="btn btn-secondary"
              type="button"
              :disabled="annotating"
              @click="runAnnotate"
            >
              <Icon name="sparkles" :size="14" />
              {{ annotating ? '标注中…' : '重新标注' }}
            </button>
            <a class="btn btn-primary" :href="paper.url" target="_blank" rel="noreferrer">
              打开原文
              <Icon name="external" :size="14" />
            </a>
          </div>
        </div>
      </header>

      <div class="reading-grid">
        <article class="article card">
          <section class="article-section">
            <div class="article-label">
              <h2>摘要</h2>
              <span>ABSTRACT</span>
            </div>
            <p class="abstract-text">{{ paper.abstract || '该文献暂未抓取到摘要。' }}</p>
          </section>

          <section class="article-section">
            <div class="article-label">
              <h2>关键词</h2>
              <span>KEYWORDS</span>
            </div>
            <div class="chips">
              <span v-for="keyword in paper.keywords" :key="keyword" class="chip">
                {{ keyword }}
              </span>
              <span v-if="!paper.keywords.length" class="faint">未提取到关键词</span>
            </div>
          </section>

          <section class="article-section">
            <div class="article-label">
              <h2>全文高频词</h2>
              <span>TOP WORDS</span>
            </div>
            <ul class="word-grid">
              <li v-for="(word, index) in topWords" :key="word" class="word-row">
                <span class="word-rank mono">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="word-text">{{ word }}</span>
                <span class="word-track">
                  <i :style="{ width: `${Math.max(24, 100 - index * 9)}%` }" />
                </span>
              </li>
            </ul>
          </section>

          <footer class="article-foot">
            <div>
              <span>收录来源</span>
              <strong>{{ domainOf(paper.url) }}</strong>
            </div>
            <div>
              <span>DOI</span>
              <strong class="mono">{{ paper.doi || '—' }}</strong>
            </div>
            <button
              class="btn btn-secondary btn-sm"
              type="button"
              @click="copyText(citationText(), '引用已复制到剪贴板')"
            >
              <Icon name="copy" :size="13" />
              复制引用
            </button>
          </footer>
        </article>

        <aside class="reading-aside">
          <section class="card ai-card">
            <div class="aside-head">
              <h2>AI 审阅</h2>
              <span class="model-tag">{{ screening?.model || 'deepseek-chat' }}</span>
            </div>

            <template v-if="screening">
              <div class="ai-score">
                <ScoreRing
                  :score="screening.score"
                  :size="68"
                  :tone="screening.passed ? 'blue' : 'red'"
                  :stroke="5.5"
                />
                <div class="ai-verdict">
                  <span class="status" :class="screening.passed ? 'is-green' : 'is-red'">
                    {{ verdict }}
                  </span>
                  <p>图谱 + 摘要联合判断</p>
                </div>
              </div>
              <p class="ai-reason">{{ screening.reason }}</p>
              <p class="ai-time">
                <Icon name="clock" :size="12" />
                {{ formatDateTime(screening.created_at) }}
              </p>
            </template>

            <template v-else>
              <div class="ai-empty">
                <span class="ai-empty-icon"><Icon name="sparkles" :size="19" /></span>
                <p>这篇文献还没有进入二轮审阅。</p>
                <RouterLink
                  v-if="projectId"
                  class="btn btn-secondary btn-sm"
                  :to="`/projects/${projectId}`"
                >
                  回到项目运行审阅
                </RouterLink>
              </div>
            </template>
          </section>

          <section class="card graph-card">
            <div class="aside-head">
              <h2>知识图谱</h2>
              <span v-if="graph.exists" class="model-tag">
                {{ graph.nodes.length }} 实体 · {{ graph.edges.length }} 关系
              </span>
            </div>

            <template v-if="graph.exists && graph.nodes.length">
              <div class="graph-mini">
                <GraphView :graph="graph" compact :interactive="false" :height="218" />
              </div>
              <div class="aside-foot">
                <span>LLM 抽取 · Neo4j 存储</span>
                <RouterLink class="section-link" :to="{ path: '/graph', query: { paper: paper.id } }">
                  展开图谱 <Icon name="arrowRight" :size="12" />
                </RouterLink>
              </div>
            </template>

            <div v-else class="graph-empty">
              <span class="ai-empty-icon"><Icon name="graph" :size="19" /></span>
              <p>尚未构建实体关系图</p>
              <button
                class="btn btn-secondary btn-sm"
                type="button"
                :disabled="annotating"
                @click="runAnnotate"
              >
                {{ annotating ? '标注中…' : '运行标注' }}
              </button>
            </div>
          </section>

          <section class="card tools-card">
            <button type="button" class="tool-row" @click="copyText(paper.doi, 'DOI 已复制')">
              <span><Icon name="copy" :size="14" /> 复制 DOI</span>
              <Icon name="chevronRight" :size="13" />
            </button>
            <button
              type="button"
              class="tool-row"
              @click="copyText(paper.url, '原文链接已复制')"
            >
              <span><Icon name="link" :size="14" /> 复制原文链接</span>
              <Icon name="chevronRight" :size="13" />
            </button>
            <a class="tool-row" :href="doiLink" target="_blank" rel="noreferrer">
              <span><Icon name="external" :size="14" /> 在 DOI 页面打开</span>
              <Icon name="chevronRight" :size="13" />
            </a>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.reading-page {
  gap: 22px;
}

.reading-loading {
  padding-top: 8px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--faint);
  margin-bottom: 13px;
}

.back-link:hover {
  color: var(--blue-deep);
}

.reading-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 28px;
}

.reading-title-main {
  min-width: 0;
  max-width: 860px;
}

.reading-title {
  margin-top: 9px;
  font-size: 31px;
  line-height: 1.35;
  letter-spacing: -0.035em;
  color: var(--ink);
}

.reading-authors {
  margin-top: 9px;
  font-size: 12px;
  color: var(--muted);
}

.reading-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 13px;
  color: var(--faint);
  font-size: 10.5px;
}

.reading-meta > span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.reading-meta a {
  color: var(--muted);
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reading-meta a:hover {
  color: var(--blue-deep);
}

.reading-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  padding-top: 24px;
}

.reading-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 18px;
  align-items: start;
}

/* ---------- 正文 ---------- */

.article {
  padding: 30px 34px 0;
  overflow: hidden;
}

.article-section + .article-section {
  margin-top: 26px;
  padding-top: 24px;
  border-top: 1px dashed #eaf1fb;
}

.article-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 12px;
}

.article-label h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.article-label span {
  font-size: 8.5px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #adbacd;
}

.abstract-text {
  font-size: 14.5px;
  line-height: 1.95;
  color: #34435e;
  letter-spacing: 0.002em;
}

.word-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 30px;
}

.word-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 0;
}

.word-rank {
  font-size: 8.5px;
  color: #b2c0d2;
  width: 15px;
  flex: none;
}

.word-text {
  width: 104px;
  flex: none;
  font-size: 11.5px;
  color: var(--ink-soft);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.word-track {
  flex: 1;
  height: 4px;
  border-radius: 99px;
  background: #f0f5fc;
  overflow: hidden;
}

.word-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #b9d0f7, #5f8ee8);
}

.article-foot {
  display: flex;
  align-items: center;
  gap: 30px;
  margin: 28px -34px 0;
  padding: 15px 34px;
  border-top: 1px solid var(--line);
  background: var(--surface-soft);
}

.article-foot > div {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.article-foot span {
  font-size: 8.5px;
  color: #a4b3c8;
  letter-spacing: 0.04em;
}

.article-foot strong {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--muted);
}

.article-foot .btn {
  margin-left: auto;
}

/* ---------- 侧栏 ---------- */

.reading-aside {
  position: sticky;
  top: 80px;
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.ai-card,
.graph-card,
.tools-card {
  padding: 18px 18px 16px;
}

.aside-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.aside-head h2 {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.model-tag {
  font-size: 8.5px;
  color: #8ea0b8;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 99px;
  padding: 2px 7px;
  white-space: nowrap;
  max-width: 65%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ai-score {
  display: flex;
  align-items: center;
  gap: 14px;
}

.ai-verdict {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.ai-verdict .status {
  width: fit-content;
}

.ai-verdict p {
  font-size: 9.5px;
  color: var(--faint);
}

.ai-reason {
  margin-top: 13px;
  padding: 11px 12px;
  border-radius: 9px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  font-size: 11px;
  line-height: 1.75;
  color: var(--muted);
}

.ai-time {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 10px;
  font-size: 9px;
  color: #b0bccc;
}

.ai-empty,
.graph-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px 6px;
  gap: 7px;
  text-align: center;
}

.ai-empty-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--blue-softer);
  border: 1px dashed #cadcf7;
  color: #86a9e2;
}

.ai-empty p,
.graph-empty p {
  font-size: 10.5px;
  color: var(--faint);
  line-height: 1.6;
}

.graph-mini {
  margin: 0 -6px;
  border: 1px solid var(--line);
  border-radius: 10px;
  overflow: hidden;
}

.aside-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 11px;
}

.aside-foot > span {
  font-size: 8.5px;
  color: #adbacd;
}

.tools-card {
  padding: 5px;
}

.tool-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 9px 11px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 10.5px;
  text-align: left;
}

.tool-row + .tool-row {
  border-top: 1px dashed #eef4fc;
}

.tool-row:hover {
  background: var(--blue-softer);
  color: var(--blue-deep);
}

.tool-row > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

@media (max-width: 1040px) {
  .reading-grid {
    grid-template-columns: minmax(0, 1fr) 290px;
  }

  .reading-title {
    font-size: 26px;
  }
}

@media (max-width: 880px) {
  .reading-title-row {
    flex-direction: column;
    gap: 14px;
  }

  .reading-actions {
    padding-top: 0;
  }

  .reading-grid {
    grid-template-columns: 1fr;
  }

  .reading-aside {
    position: static;
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }

  .tools-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .reading-title {
    font-size: 23px;
  }

  .article {
    padding: 22px 18px 0;
  }

  .article-foot {
    margin: 24px -18px 0;
    padding: 14px 18px;
    flex-wrap: wrap;
    gap: 12px;
  }

  .article-foot .btn {
    margin-left: 0;
    width: 100%;
  }

  .word-grid {
    grid-template-columns: 1fr;
  }

  .reading-aside {
    grid-template-columns: 1fr;
  }
}
</style>
