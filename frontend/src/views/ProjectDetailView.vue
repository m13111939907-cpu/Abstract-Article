<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  annotatePaper,
  batchAnnotate,
  deleteProject,
  downloadProject,
  ensureReady,
  fetchProject,
  getProject,
  getProjectStats,
  listProjectPapers,
  listScreenings,
  screenProject,
  screenProject2,
  updateProject,
} from '../api/client'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import ScoreRing from '../components/ScoreRing.vue'
import { toast } from '../store'
import { displayKeywords, formatDate, formatDateTime } from '../utils/format'

const route = useRoute()
const router = useRouter()

const project = ref(null)
const stats = ref({
  total_papers: 0,
  first_selected: 0,
  second_screened: 0,
  second_passed: 0,
})
const firstPapers = ref([])
const screenings = ref([])
const loading = ref(true)
const notFound = ref(false)
const tab = ref('first')
const reviewFilter = ref('all')
const busy = ref('')
const busyPaper = ref(null)

const editOpen = ref(false)
const editForm = reactive({ name: '', keywords: '' })
const editErrors = reactive({ name: '', keywords: '' })

const deleteOpen = ref(false)
const deleting = ref(false)
const exportOpen = ref(false)

const projectId = computed(() => route.params.id)

const keywords = computed(() =>
  project.value ? displayKeywords(project.value.keywords) : [],
)

const filteredScreenings = computed(() => {
  if (reviewFilter.value === 'passed') return screenings.value.filter((item) => item.passed)
  if (reviewFilter.value === 'rejected') return screenings.value.filter((item) => !item.passed)
  return screenings.value
})

const steps = computed(() => [
  {
    key: 'fetch',
    index: '01',
    title: '抓取 RSS',
    desc: '从启用的订阅源拉取新论文，按 DOI / 链接去重。',
    value: stats.value.total_papers,
    unit: '篇候选',
    action: { key: 'fetch', label: '抓取文献', icon: 'refresh' },
  },
  {
    key: 'screen',
    index: '02',
    title: '字符初筛',
    desc: '标题命中 2 分，摘要与关键词命中 1 分。',
    value: stats.value.first_selected,
    unit: '篇入选',
    action: { key: 'screen', label: '运行筛选', icon: 'filter' },
  },
  {
    key: 'annotate',
    index: '03',
    title: '图谱 + LLM',
    desc: '实体关系写入 Neo4j，再由大模型结合图谱审阅。',
    value: stats.value.second_screened,
    unit: '篇已审阅',
    actions: [
      { key: 'annotate', label: '批量标注', icon: 'graph' },
      { key: 'screen2', label: '二轮审阅', icon: 'sparkles', primary: true },
    ],
  },
  {
    key: 'read',
    index: '04',
    title: '精读导出',
    desc: '人工确认后阅读原文，导出 CSV 或 BibTeX。',
    value: stats.value.second_passed,
    unit: '篇建议精读',
    action: { key: 'export', label: '导出结果', icon: 'download' },
    final: true,
  },
])

async function loadAll(quiet = false) {
  if (!quiet) loading.value = true
  try {
    await ensureReady()
    const detail = await getProject(projectId.value)
    project.value = detail
    editForm.name = detail.name
    editForm.keywords = detail.keywords

    const [projectStats, papers, reviewRows] = await Promise.all([
      getProjectStats(detail.id),
      listProjectPapers(detail.id, { limit: 100 }),
      listScreenings(detail.id),
    ])

    stats.value = projectStats
    firstPapers.value = papers
    screenings.value = reviewRows
    notFound.value = false
  } catch (error) {
    if (!project.value) notFound.value = true
    else toast('刷新失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

async function runStep(key) {
  if (busy.value) return
  exportOpen.value = false

  if (key === 'export') {
    await exportAs('csv')
    return
  }

  if (busy.value) return
  busy.value = key
  try {
    if (key === 'fetch') {
      const result = await fetchProject(projectId.value)
      const parts = [
        `获取 ${result.fetched} 条`,
        `新增 ${result.inserted} 篇`,
        `去重 ${result.duplicated} 条`,
      ]
      if (result.topic_fetched) {
        parts.push(`主题检索 ${result.topic_fetched} 条（新增 ${result.topic_inserted}）`)
      }
      if (result.candidates !== undefined) {
        parts.push(
          `本次新增候选 ${result.candidates} 篇（当前共 ${result.project_candidates} 篇）`,
        )
      }
      toast('抓取完成', parts.join(' · '))
    }
    if (key === 'screen') {
      const result = await screenProject(projectId.value)
      toast(
        '首轮筛选完成',
        `扫描 ${result.candidates} 篇，新入选 ${result.selected} 篇，已关联 ${result.skipped} 篇。`,
      )
    }
    if (key === 'annotate') {
      const result = await batchAnnotate(projectId.value)
      toast(
        '批量标注完成',
        `处理 ${result.annotated} 篇，写入 ${result.entities} 个实体、${result.relations} 条关系。`,
      )
    }
    if (key === 'screen2') {
      const result = await screenProject2(projectId.value)
      toast(
        '二轮审阅完成',
        `审阅 ${result.screened} 篇，${result.passed} 篇建议精读，${result.skipped} 篇已处理。`,
      )
    }
    await loadAll(true)
  } catch (error) {
    toast('操作失败', error.message, 'error')
  } finally {
    busy.value = ''
  }
}

async function annotateOne(paperId) {
  if (busyPaper.value) return
  busyPaper.value = paperId
  try {
    const result = await annotatePaper(paperId)
    toast(
      '标注完成',
      `生成 ${result.entities} 个实体、${result.relations} 条关系。`,
    )
  } catch (error) {
    toast('标注失败', error.message, 'error')
  } finally {
    busyPaper.value = null
  }
}

async function exportAs(format, stage = 'second') {
  exportOpen.value = false
  try {
    await downloadProject(projectId.value, { format, stage })
    toast('导出已开始', `${format === 'csv' ? 'CSV' : 'BibTeX'} 文件正在下载。`)
  } catch (error) {
    toast('导出失败', error.message, 'error')
  }
}

function openEdit() {
  editForm.name = project.value?.name || ''
  editForm.keywords = project.value?.keywords || ''
  editErrors.name = ''
  editErrors.keywords = ''
  editOpen.value = true
}

async function saveEdit() {
  editErrors.name = editForm.name.trim() ? '' : '项目名称不能为空'
  editErrors.keywords = editForm.keywords.trim() ? '' : '关键词不能为空'
  if (editErrors.name || editErrors.keywords) return

  try {
    const updated = await updateProject(projectId.value, {
      name: editForm.name.trim(),
      keywords: editForm.keywords.trim(),
    })
    project.value = updated
    editOpen.value = false
    toast('项目已更新', '名称与关键词已保存。')
    await loadAll(true)
  } catch (error) {
    toast('保存失败', error.message, 'error')
  }
}

async function confirmDelete() {
  deleting.value = true
  try {
    await deleteProject(projectId.value)
    toast('项目已删除', '文献与图谱仍保留在文献库中。')
    deleteOpen.value = false
    router.push('/projects')
  } catch (error) {
    toast('删除失败', error.message, 'error')
  } finally {
    deleting.value = false
  }
}

watch(
  () => route.params.id,
  () => loadAll(),
)

onMounted(() => loadAll())
</script>

<template>
  <div v-if="notFound" class="page">
    <EmptyState
      icon="folder"
      title="项目不存在"
      text="它可能已经被删除，回到项目列表重新选择一个。"
    >
      <RouterLink class="btn btn-primary btn-sm" to="/projects">返回项目列表</RouterLink>
    </EmptyState>
  </div>

  <div v-else class="page project-page">
    <div v-if="loading && !project" class="loading-block">
      <div class="skeleton" style="width: 120px; height: 12px" />
      <div class="skeleton" style="width: 46%; height: 34px; margin-top: 14px" />
      <div class="skeleton" style="width: 100%; height: 180px; margin-top: 24px; border-radius: 18px" />
    </div>

    <template v-else-if="project">
      <header class="project-head">
        <div class="project-head-main">
          <RouterLink class="back-link" to="/projects">
            <Icon name="chevronLeft" :size="13" />
            所有项目
          </RouterLink>
          <div class="project-title-row">
            <h1 class="page-title">{{ project.name }}</h1>
            <span class="status is-blue">进行中</span>
          </div>
          <div class="chips project-keywords">
            <span v-for="keyword in keywords" :key="keyword" class="chip">{{ keyword }}</span>
          </div>
          <p class="project-meta">
            项目编号 P-{{ String(project.id).padStart(2, '0') }} · 创建于
            {{ formatDate(project.created_at) }} · {{ stats.total_papers }} 篇文献参与筛选
          </p>
        </div>

        <div class="page-actions project-actions">
          <div class="export-wrap">
            <button
              class="btn btn-primary"
              type="button"
              @click="exportOpen = !exportOpen"
            >
              <Icon name="download" :size="15" />
              导出
              <Icon name="chevronDown" :size="12" />
            </button>
            <div v-if="exportOpen" class="menu-scrim" @click="exportOpen = false" />
            <div v-if="exportOpen" class="export-menu">
              <button type="button" @click="exportAs('csv', 'second')">
                <span>CSV · 二轮结果</span>
                <small>Excel 可直接打开</small>
              </button>
              <button type="button" @click="exportAs('bibtex', 'second')">
                <span>BibTeX · 二轮结果</span>
                <small>导入 Zotero / LaTeX</small>
              </button>
              <button type="button" @click="exportAs('csv', 'first')">
                <span>CSV · 首轮结果</span>
                <small>含匹配分与命中词</small>
              </button>
            </div>
          </div>

          <button class="btn btn-danger" type="button" @click="deleteOpen = true">
            <Icon name="trash" :size="14" />
            删除项目
          </button>
        </div>
      </header>

      <section class="stats" aria-label="项目指标">
        <article class="stat">
          <p class="stat-label">候选文献</p>
          <p class="stat-value">{{ stats.total_papers }}<span class="stat-unit">篇</span></p>
          <p class="stat-foot">全局去重后的候选池</p>
        </article>
        <article class="stat">
          <p class="stat-label">首轮入选</p>
          <p class="stat-value">{{ stats.first_selected }}<span class="stat-unit">篇</span></p>
          <p class="stat-foot">关键词字符匹配</p>
        </article>
        <article class="stat">
          <p class="stat-label">二轮审阅</p>
          <p class="stat-value">{{ stats.second_screened }}<span class="stat-unit">篇</span></p>
          <p class="stat-foot">图谱 + LLM 判断</p>
        </article>
        <article class="stat">
          <span class="stat-mark"><Icon name="sparkles" :size="16" /></span>
          <p class="stat-label">建议精读</p>
          <p class="stat-value">{{ stats.second_passed }}<span class="stat-unit">篇</span></p>
          <p class="stat-foot">{{ stats.second_rejected }} 篇未通过审阅</p>
        </article>
      </section>

      <section class="pipeline card">
        <div class="pipeline-head">
          <div>
            <h2 class="section-title">筛选流水线</h2>
            <p class="section-sub">按顺序执行，每一步都会写回同一份项目数据。</p>
          </div>
          <span class="pipeline-tag">4 STEPS</span>
        </div>

        <div class="pipeline-track">
          <template v-for="(step, index) in steps" :key="step.key">
            <article class="pipe-step" :class="{ 'is-final': step.final }">
              <div class="pipe-top">
                <span class="pipe-index mono">{{ step.index }}</span>
                <span v-if="step.value > 0" class="pipe-done">
                  <Icon name="check" :size="11" />
                </span>
              </div>
              <h3>{{ step.title }}</h3>
              <p>{{ step.desc }}</p>
              <div class="pipe-value">
                <strong>{{ step.value }}</strong>
                <span>{{ step.unit }}</span>
              </div>
              <div class="pipe-actions">
                <template v-if="step.actions">
                  <button
                    v-for="action in step.actions"
                    :key="action.key"
                    class="btn btn-sm"
                    :class="action.primary ? 'btn-primary' : 'btn-secondary'"
                    type="button"
                    :disabled="!!busy"
                    @click="runStep(action.key)"
                  >
                    <span v-if="busy === action.key" class="mini-spinner" />
                    <Icon v-else :name="action.icon" :size="13" />
                    {{ busy === action.key ? '处理中' : action.label }}
                  </button>
                </template>
                <button
                  v-else
                  class="btn btn-sm"
                  :class="step.final ? 'btn-primary' : 'btn-secondary'"
                  type="button"
                  :disabled="!!busy"
                  @click="runStep(step.action.key)"
                >
                  <span v-if="busy === step.action.key" class="mini-spinner" />
                  <Icon v-else :name="step.action.icon" :size="13" />
                  {{ busy === step.action.key ? '处理中' : step.action.label }}
                </button>
              </div>
            </article>
            <span v-if="index < steps.length - 1" class="pipe-arrow" aria-hidden="true">
              <Icon name="chevronRight" :size="14" />
            </span>
          </template>
        </div>
      </section>

      <section class="results">
        <div class="tabs">
          <button
            type="button"
            class="tab"
            :class="{ 'is-active': tab === 'first' }"
            @click="tab = 'first'"
          >
            首轮结果
            <span>{{ firstPapers.length }}</span>
          </button>
          <button
            type="button"
            class="tab"
            :class="{ 'is-active': tab === 'second' }"
            @click="tab = 'second'"
          >
            二轮审阅
            <span>{{ screenings.length }}</span>
          </button>
          <button
            type="button"
            class="tab"
            :class="{ 'is-active': tab === 'info' }"
            @click="tab = 'info'"
          >
            项目设置
          </button>
        </div>

        <div v-if="tab === 'first'" class="card results-card">
          <div class="results-head">
            <div>
              <h2 class="section-title">首轮入选文献</h2>
              <p class="section-sub">按匹配分从高到低排序，点击标题进入阅读页。</p>
            </div>
            <span class="result-hint">标题命中 +2 · 摘要命中 +1</span>
          </div>

          <div v-if="firstPapers.length" class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th style="width: 42%">文献</th>
                  <th>匹配分</th>
                  <th>命中关键词</th>
                  <th style="width: 150px">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in firstPapers" :key="row.id">
                  <td>
                    <div class="paper-cell">
                      <RouterLink
                        class="paper-title"
                        :to="{ path: `/papers/${row.paper.id}`, query: { project: project.id } }"
                      >
                        {{ row.paper.title }}
                      </RouterLink>
                      <span class="paper-authors">{{ row.paper.authors }}</span>
                    </div>
                  </td>
                  <td>
                    <span class="match-score" :class="{ 'is-high': row.match_score >= 6 }">
                      {{ row.match_score }}
                    </span>
                  </td>
                  <td>
                    <div class="chips">
                      <span
                        v-for="keyword in row.matched_keywords.slice(0, 3)"
                        :key="keyword"
                        class="chip is-plain"
                      >
                        {{ keyword }}
                      </span>
                      <span v-if="!row.matched_keywords.length" class="faint">—</span>
                    </div>
                  </td>
                  <td>
                    <div class="row-actions">
                      <button
                        class="btn btn-sm btn-secondary"
                        type="button"
                        :disabled="busyPaper === row.paper.id"
                        @click="annotateOne(row.paper.id)"
                      >
                        <Icon name="graph" :size="12" />
                        {{ busyPaper === row.paper.id ? '…' : '标注' }}
                      </button>
                      <RouterLink
                        class="icon-btn"
                        :to="{ path: `/papers/${row.paper.id}`, query: { project: project.id } }"
                        aria-label="阅读文献"
                      >
                        <Icon name="arrowUpRight" :size="14" />
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <EmptyState
            v-else
            icon="filter"
            title="还没有入选文献"
            text="先抓取订阅源，再运行一次字符初筛；命中的文献会出现在这里。"
          >
            <button class="btn btn-primary btn-sm" type="button" @click="runStep('fetch')">
              先抓取文献
            </button>
          </EmptyState>
        </div>

        <div v-else-if="tab === 'second'" class="card results-card">
          <div class="results-head">
            <div>
              <h2 class="section-title">大模型审阅</h2>
              <p class="section-sub">结论结合摘要与图谱实体，分数与理由均由模型给出。</p>
            </div>
            <div class="filter-tabs">
              <button
                v-for="option in [
                  { key: 'all', label: '全部' },
                  { key: 'passed', label: '建议精读' },
                  { key: 'rejected', label: '未通过' },
                ]"
                :key="option.key"
                type="button"
                class="filter-tab"
                :class="{ 'is-active': reviewFilter === option.key }"
                @click="reviewFilter = option.key"
              >
                {{ option.label }}
              </button>
            </div>
          </div>

          <div v-if="filteredScreenings.length" class="review-list">
            <article v-for="row in filteredScreenings" :key="row.id" class="review-row">
              <ScoreRing
                :score="row.score"
                :size="50"
                :tone="row.passed ? 'blue' : 'red'"
                :stroke="4"
              />
              <div class="review-main">
                <RouterLink
                  class="review-title"
                  :to="{ path: `/papers/${row.paper.id}`, query: { project: project.id } }"
                >
                  {{ row.paper.title }}
                </RouterLink>
                <p class="review-reason">{{ row.reason }}</p>
                <div class="review-meta">
                  <span>{{ row.model }}</span>
                  <span>{{ formatDateTime(row.created_at) }}</span>
                  <span>{{ row.paper.authors }}</span>
                </div>
              </div>
              <div class="review-side">
                <span class="status" :class="row.passed ? 'is-green' : 'is-red'">
                  {{ row.passed ? '建议精读' : '未通过' }}
                </span>
                <RouterLink
                  class="section-link"
                  :to="{ path: `/papers/${row.paper.id}`, query: { project: project.id } }"
                >
                  阅读 <Icon name="arrowRight" :size="12" />
                </RouterLink>
              </div>
            </article>
          </div>

          <EmptyState
            v-else
            icon="sparkles"
            title="还没有二轮审阅结果"
            text="先完成图谱标注，再点击「二轮审阅」，模型会逐篇给出分数与理由。"
          >
            <button class="btn btn-primary btn-sm" type="button" @click="runStep('screen2')">
              开始二轮审阅
            </button>
          </EmptyState>
        </div>

        <div v-else class="card results-card info-card">
          <div class="info-grid">
            <section>
              <h2 class="section-title">项目信息</h2>
              <p class="section-sub">名称与关键词会影响后续首轮与二轮筛选。</p>
              <div class="field" style="margin-top: 18px">
                <label class="field-label" for="edit-name">项目名称</label>
                <input
                  id="edit-name"
                  v-model="editForm.name"
                  class="input"
                  :class="{ 'is-error': editErrors.name }"
                />
                <p v-if="editErrors.name" class="field-error">{{ editErrors.name }}</p>
              </div>
              <div class="field">
                <label class="field-label" for="edit-keywords">检索关键词</label>
                <textarea
                  id="edit-keywords"
                  v-model="editForm.keywords"
                  class="textarea"
                  :class="{ 'is-error': editErrors.keywords }"
                />
                <p v-if="editErrors.keywords" class="field-error">{{ editErrors.keywords }}</p>
              </div>
              <button class="btn btn-primary" type="button" style="margin-top: 16px" @click="saveEdit">
                保存修改
              </button>
            </section>

            <section class="info-side">
              <h2 class="section-title">项目数据</h2>
              <dl class="info-list">
                <div><dt>项目编号</dt><dd>P-{{ String(project.id).padStart(2, '0') }}</dd></div>
                <div><dt>创建时间</dt><dd>{{ formatDateTime(project.created_at) }}</dd></div>
                <div><dt>首轮入选</dt><dd>{{ stats.first_selected }} 篇</dd></div>
                <div><dt>二轮审阅</dt><dd>{{ stats.second_screened }} 篇</dd></div>
                <div><dt>建议精读</dt><dd>{{ stats.second_passed }} 篇</dd></div>
              </dl>

              <div class="danger-zone">
                <div>
                  <strong>删除项目</strong>
                  <p>仅移除项目与筛选记录，文献和图谱会保留。</p>
                </div>
                <button class="btn btn-danger btn-sm" type="button" @click="deleteOpen = true">
                  删除
                </button>
              </div>
            </section>
          </div>
        </div>
      </section>
    </template>

    <BaseModal
      :open="editOpen"
      title="编辑项目"
      subtitle="修改会立即影响下一次筛选，但不会改动已有结果。"
      width="500px"
      @close="editOpen = false"
    >
      <div class="field">
        <label class="field-label" for="modal-name">项目名称</label>
        <input
          id="modal-name"
          v-model="editForm.name"
          class="input"
          :class="{ 'is-error': editErrors.name }"
        />
        <p v-if="editErrors.name" class="field-error">{{ editErrors.name }}</p>
      </div>
      <div class="field">
        <label class="field-label" for="modal-keywords">检索关键词</label>
        <textarea
          id="modal-keywords"
          v-model="editForm.keywords"
          class="textarea"
          :class="{ 'is-error': editErrors.keywords }"
        />
        <p v-if="editErrors.keywords" class="field-error">{{ editErrors.keywords }}</p>
      </div>
      <template #footer>
        <button class="btn btn-ghost" type="button" @click="editOpen = false">取消</button>
        <button class="btn btn-primary" type="button" @click="saveEdit">保存</button>
      </template>
    </BaseModal>

    <BaseModal
      :open="deleteOpen"
      title="删除这个项目？"
      subtitle="项目下的筛选记录与二轮结论会一并删除，文献与 Neo4j 图谱保留。"
      width="440px"
      @close="deleteOpen = false"
    >
      <p class="delete-target">{{ project?.name }}</p>
      <template #footer>
        <button class="btn btn-ghost" type="button" @click="deleteOpen = false">取消</button>
        <button
          class="btn btn-danger"
          type="button"
          :disabled="deleting"
          @click="confirmDelete"
        >
          {{ deleting ? '删除中…' : '确认删除' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.project-page {
  gap: 20px;
}

.loading-block {
  padding: 10px 0;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--faint);
  margin-bottom: 12px;
}

.back-link:hover {
  color: var(--blue-deep);
}

.project-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
  padding-top: 2px;
}

.project-head-main {
  min-width: 0;
}

.project-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.project-title-row .page-title {
  margin-top: 0;
}

.project-keywords {
  margin-top: 13px;
}

.project-meta {
  margin-top: 11px;
  color: var(--faint);
  font-size: 11px;
}

.project-actions {
  align-items: flex-start;
  padding-top: 18px;
}

.project-actions .btn-danger {
  background: #d14343;
  border-color: #c43a3a;
  color: #fff;
}

.project-actions .btn-danger:hover {
  background: #bb3636;
  border-color: #ab3030;
  color: #fff;
}

.export-wrap {
  position: relative;
}

.menu-scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
}

.export-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 41;
  width: 218px;
  padding: 5px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 11px;
  box-shadow: var(--shadow-md);
}

.export-menu button {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  text-align: left;
}

.export-menu button:hover {
  background: var(--blue-softer);
}

.export-menu span {
  font-size: 12px;
  font-weight: 500;
  color: var(--ink-soft);
}

.export-menu small {
  font-size: 10px;
  color: var(--faint);
}

/* ---------- 流水线 ---------- */

.pipeline {
  padding: 20px 22px 18px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
}

.pipeline-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.pipeline-head .section-sub {
  margin-top: 3px;
}

.pipeline-tag {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 9px;
  letter-spacing: 0.12em;
  color: #9fb0c7;
  border: 1px solid var(--line);
  border-radius: 99px;
  padding: 3px 8px;
}

.pipeline-track {
  display: flex;
  align-items: stretch;
  gap: 6px;
}

.pipe-step {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 14px 15px 13px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.pipe-step:hover {
  border-color: #d4e3f7;
}

.pipe-step.is-final {
  background: linear-gradient(180deg, #f4f8ff, #eef5ff);
  border-color: #d8e6fb;
}

.pipe-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pipe-index {
  font-size: 9px;
  color: #a4b2c7;
  letter-spacing: 0.06em;
}

.pipe-done {
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 99px;
  background: var(--green-soft);
  color: var(--green);
}

.pipe-step h3 {
  margin-top: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.pipe-step p {
  margin-top: 4px;
  min-height: 32px;
  font-size: 10.5px;
  line-height: 1.55;
  color: var(--faint);
}

.pipe-value {
  display: flex;
  align-items: baseline;
  gap: 5px;
  margin-top: 9px;
}

.pipe-value strong {
  font-size: 25px;
  font-weight: 600;
  letter-spacing: -0.04em;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}

.pipe-value span {
  font-size: 9.5px;
  color: var(--faint);
}

.pipe-actions {
  display: flex;
  gap: 6px;
  margin-top: auto;
  padding-top: 11px;
}

.pipe-actions .btn {
  flex: 1;
}

.pipe-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 12px;
  flex: none;
  color: #c6d4e8;
}

.mini-spinner {
  width: 11px;
  height: 11px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.btn-secondary .mini-spinner {
  border-color: rgba(47, 107, 255, 0.25);
  border-top-color: var(--blue);
}

/* ---------- 结果 ---------- */

.results {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  width: fit-content;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.7);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 31px;
  padding: 0 13px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.tab:hover {
  color: var(--ink-soft);
}

.tab.is-active {
  background: #fff;
  color: var(--blue-deep);
  box-shadow: 0 1px 2px rgba(13, 27, 52, 0.06);
}

.tab span {
  display: inline-grid;
  place-items: center;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 99px;
  background: var(--surface-soft);
  color: var(--faint);
  font-size: 9.5px;
  font-variant-numeric: tabular-nums;
}

.tab.is-active span {
  background: var(--blue-soft);
  color: var(--blue-deep);
}

.results-card {
  padding: 22px 24px 10px;
}

.results-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.results-head .section-sub {
  margin-top: 3px;
}

.result-hint {
  font-size: 10px;
  color: var(--faint);
  white-space: nowrap;
}

.paper-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.paper-title {
  font-size: 12.5px;
  font-weight: 500;
  line-height: 1.5;
  color: var(--ink);
}

.paper-title:hover {
  color: var(--blue-deep);
}

.paper-authors {
  font-size: 10px;
  color: var(--faint);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.match-score {
  display: inline-grid;
  place-items: center;
  min-width: 26px;
  height: 24px;
  padding: 0 5px;
  border-radius: 7px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.match-score.is-high {
  background: var(--blue-soft);
  border-color: #d3e4ff;
  color: var(--blue-deep);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.review-list {
  display: flex;
  flex-direction: column;
}

.review-row {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  padding: 16px 0;
  border-top: 1px solid #eef4fc;
}

.review-row:first-child {
  border-top: 0;
}

.review-main {
  flex: 1;
  min-width: 0;
}

.review-title {
  font-size: 13px;
  font-weight: 550;
  line-height: 1.5;
  color: var(--ink);
}

.review-title:hover {
  color: var(--blue-deep);
}

.review-reason {
  margin-top: 4px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--muted);
}

.review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 7px;
  font-size: 9.5px;
  color: var(--faint);
}

.review-meta span {
  position: relative;
}

.review-meta span + span::before {
  content: '·';
  position: absolute;
  left: -7px;
  color: #cbd6e6;
}

.review-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 9px;
  flex: none;
  padding-top: 2px;
}

.filter-tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 9px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
}

.filter-tab {
  height: 25px;
  padding: 0 9px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--faint);
  font-size: 10.5px;
}

.filter-tab.is-active {
  background: #fff;
  color: var(--blue-deep);
  box-shadow: var(--shadow-xs);
}

/* ---------- 设置 ---------- */

.info-card {
  padding: 24px;
}

.info-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 44px;
}

.info-side {
  border-left: 1px solid var(--line);
  padding-left: 36px;
}

.info-list {
  margin-top: 12px;
}

.info-list > div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px dashed #eef4fc;
  font-size: 11.5px;
}

.info-list dt {
  color: var(--faint);
}

.info-list dd {
  margin: 0;
  color: var(--ink-soft);
  font-variant-numeric: tabular-nums;
}

.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 22px;
  padding: 13px 14px;
  border: 1px solid #f3dede;
  border-radius: 10px;
  background: #fffafa;
}

.danger-zone strong {
  font-size: 11.5px;
  font-weight: 550;
  color: #9c3838;
}

.danger-zone p {
  margin-top: 2px;
  font-size: 10px;
  color: #b98484;
}

.field-error {
  font-size: 11px;
  color: var(--red);
}

.delete-target {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-soft);
  font-size: 13px;
  font-weight: 550;
  color: var(--ink);
}

@media (max-width: 1280px) {
  .pipeline-track {
    flex-wrap: wrap;
  }

  .pipe-step {
    flex: 1 1 calc(50% - 20px);
    min-width: 220px;
  }

  .pipe-arrow {
    display: none;
  }
}

@media (max-width: 920px) {
  .info-grid {
    grid-template-columns: 1fr;
    gap: 26px;
  }

  .info-side {
    border-left: 0;
    padding-left: 0;
    padding-top: 22px;
    border-top: 1px solid var(--line);
  }
}

@media (max-width: 640px) {
  .project-actions {
    width: 100%;
    padding-top: 0;
  }

  .pipeline {
    padding: 18px 16px;
  }

  .pipe-step {
    flex: 1 1 100%;
  }

  .results-card {
    padding: 18px 16px 6px;
  }

  .results-head {
    flex-direction: column;
    gap: 10px;
  }

  .review-row {
    gap: 11px;
  }

  .review-side {
    display: none;
  }

  .review-meta span:nth-child(3) {
    display: none;
  }
}
</style>
