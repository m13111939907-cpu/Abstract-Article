<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createProject,
  ensureReady,
  getProjectStats,
  listProjects,
} from '../api/client'
import BaseModal from '../components/BaseModal.vue'
import Icon from '../components/Icon.vue'
import { toast } from '../store'
import { displayKeywords, formatDate, percent } from '../utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const projects = ref([])
const statsMap = ref({})
const query = ref('')

const showCreate = ref(false)
const submitting = ref(false)
const nameInput = ref(null)
const form = reactive({ name: '', keywords: '' })
const errors = reactive({ name: '', keywords: '' })

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return projects.value
  return projects.value.filter(
    (project) =>
      project.name.toLowerCase().includes(keyword) ||
      project.keywords.toLowerCase().includes(keyword),
  )
})

function statsOf(id) {
  return (
    statsMap.value[id] || {
      first_selected: 0,
      second_screened: 0,
      second_passed: 0,
      total_papers: 0,
    }
  )
}

function keywordsOf(project) {
  return displayKeywords(project.keywords)
}

function rateOf(project) {
  return percent(statsOf(project.id).second_passed, statsOf(project.id).first_selected)
}

async function load() {
  loading.value = true
  try {
    await ensureReady()
    const list = await listProjects()
    projects.value = list
    const stats = await Promise.all(list.map((project) => getProjectStats(project.id)))
    statsMap.value = Object.fromEntries(
      stats.map((item, index) => [list[index].id, item]),
    )
  } catch (error) {
    toast('项目加载失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.name = ''
  form.keywords = ''
  errors.name = ''
  errors.keywords = ''
  showCreate.value = true
  nextTick(() => nameInput.value?.focus())
}

function closeCreate() {
  showCreate.value = false
  if (route.query.new) router.replace({ path: '/projects' })
}

function validate() {
  errors.name = form.name.trim() ? '' : '请给项目起一个名字'
  errors.keywords = form.keywords.trim() ? '' : '至少写一个检索关键词'
  return !errors.name && !errors.keywords
}

async function submit() {
  if (!validate() || submitting.value) return
  submitting.value = true
  try {
    const project = await createProject({
      name: form.name.trim(),
      keywords: form.keywords.trim(),
    })
    toast('项目已创建', `「${project.name}」已进入工作台，可以开始抓取文献。`)
    showCreate.value = false
    router.push(`/projects/${project.id}`)
  } catch (error) {
    toast('创建失败', error.message, 'error')
  } finally {
    submitting.value = false
  }
}

watch(
  () => route.query.new,
  (value) => {
    if (value === '1') openCreate()
  },
  { immediate: true },
)

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">RESEARCH PROJECTS</p>
        <h1 class="page-title">研究项目</h1>
        <p class="page-sub">
          每次检索都是一个独立项目。关键词、筛选结果与知识图谱都归档在这里。
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn btn-secondary" to="/sources">
          <Icon name="rss" :size="15" />
          订阅源
        </RouterLink>
        <button class="btn btn-primary" type="button" @click="openCreate">
          <Icon name="plus" :size="15" />
          新建项目
        </button>
      </div>
    </header>

    <div class="toolbar">
      <div class="search-field">
        <Icon name="search" :size="15" />
        <input
          v-model="query"
          class="input"
          type="search"
          placeholder="按项目名或关键词筛选"
          aria-label="筛选项目"
        />
      </div>
      <p class="toolbar-meta">
        <span class="num">{{ filtered.length }}</span> 个项目
        <span v-if="query" class="faint">· 已筛选</span>
      </p>
    </div>

    <div v-if="loading" class="project-grid">
      <div v-for="index in 3" :key="index" class="project-card is-skeleton">
        <div class="skeleton" style="width: 38px; height: 38px; border-radius: 10px" />
        <div class="skeleton" style="width: 58%; height: 20px; margin-top: 18px" />
        <div class="skeleton" style="width: 86%; height: 12px; margin-top: 12px" />
        <div class="skeleton" style="width: 100%; height: 58px; margin-top: 22px" />
      </div>
    </div>

    <div v-else class="project-grid">
      <RouterLink
        v-for="(project, index) in filtered"
        :key="project.id"
        class="project-card card"
        :to="`/projects/${project.id}`"
      >
        <div class="project-top">
          <span class="project-folder">
            <Icon name="folder" :size="17" />
          </span>
          <span class="project-code mono">P-{{ String(index + 1).padStart(2, '0') }}</span>
          <span class="status is-blue">进行中</span>
        </div>

        <h2 class="project-name">{{ project.name }}</h2>
        <p class="project-keywords">
          {{ keywordsOf(project).join(' · ') || '未设置关键词' }}
        </p>

        <div class="project-stats">
          <div>
            <strong>{{ statsOf(project.id).first_selected }}</strong>
            <span>首轮入选</span>
          </div>
          <div>
            <strong>{{ statsOf(project.id).second_passed }}</strong>
            <span>建议精读</span>
          </div>
          <div>
            <strong>{{ rateOf(project) }}<small>%</small></strong>
            <span>通过率</span>
          </div>
        </div>

        <div class="progress" aria-hidden="true">
          <i :style="{ width: `${Math.max(rateOf(project), 2)}%` }" />
        </div>

        <div class="project-foot">
          <span>创建于 {{ formatDate(project.created_at) }}</span>
          <span class="open-link">打开项目 <Icon name="arrowRight" :size="13" /></span>
        </div>
      </RouterLink>

      <button class="new-card" type="button" @click="openCreate">
        <span class="new-icon"><Icon name="plus" :size="20" /></span>
        <strong>新建检索项目</strong>
        <p>为一组研究关键词建立独立工作区</p>
      </button>
    </div>

    <p v-if="!loading && !filtered.length && projects.length" class="no-result">
      没有匹配「{{ query }}」的项目，换个关键词试试。
    </p>

    <BaseModal
      :open="showCreate"
      title="新建检索项目"
      subtitle="项目名用于区分研究方向，关键词会参与首轮字符匹配与二轮 LLM 审阅。"
      width="500px"
      @close="closeCreate"
    >
      <div class="field">
        <label class="field-label" for="project-name">项目名称</label>
        <input
          id="project-name"
          ref="nameInput"
          v-model="form.name"
          class="input"
          :class="{ 'is-error': errors.name }"
          placeholder="例如：LLM × 知识图谱"
          maxlength="128"
          @keyup.enter="submit"
        />
        <p v-if="errors.name" class="field-error">{{ errors.name }}</p>
      </div>

      <div class="field">
        <label class="field-label" for="project-keywords">
          检索关键词
          <span class="field-hint">用逗号分隔，支持中英文</span>
        </label>
        <textarea
          id="project-keywords"
          v-model="form.keywords"
          class="textarea"
          :class="{ 'is-error': errors.keywords }"
          placeholder="large language model, knowledge graph, retrieval augmented generation"
        />
        <p v-if="errors.keywords" class="field-error">{{ errors.keywords }}</p>
        <p class="field-hint">
          标题命中记 2 分，摘要 / 关键词 / 高频词命中记 1 分，总分大于 0 进入首轮。
        </p>
      </div>

      <template #footer>
        <button class="btn btn-ghost" type="button" @click="closeCreate">取消</button>
        <button
          class="btn btn-primary"
          type="button"
          :class="{ 'is-busy': submitting }"
          :disabled="submitting"
          @click="submit"
        >
          <span v-if="submitting" class="mini-spinner" />
          {{ submitting ? '创建中…' : '创建项目' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 2px;
}

.toolbar .search-field {
  width: 280px;
}

.toolbar-meta {
  font-size: 11.5px;
  color: var(--faint);
}

.toolbar-meta .num {
  color: var(--ink-soft);
  font-weight: 600;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.project-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 20px 21px 16px;
  color: var(--ink);
  transition: transform 0.18s ease, border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  border-color: #cadcf6;
  box-shadow: 0 2px 4px rgba(13, 27, 52, 0.03),
    0 22px 44px -30px rgba(13, 27, 52, 0.35);
}

.project-card.is-skeleton {
  pointer-events: none;
}

.project-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.project-folder {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  background: var(--blue-soft);
  color: var(--blue);
}

.project-code {
  font-size: 9px;
  color: #a7b4c7;
  letter-spacing: 0.06em;
}

.project-top .status {
  margin-left: auto;
}

.project-name {
  margin-top: 15px;
  font-size: 18px;
  line-height: 1.4;
  letter-spacing: -0.02em;
  color: var(--ink);
}

.project-keywords {
  min-width: 0;
  margin-top: 5px;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid var(--line);
}

.project-stats > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.project-stats strong {
  font-size: 21px;
  font-weight: 600;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.project-stats strong small {
  font-size: 9px;
  color: var(--faint);
  margin-left: 1px;
}

.project-stats span {
  font-size: 10px;
  color: var(--faint);
  white-space: nowrap;
}

.progress {
  height: 4px;
  margin-top: 14px;
  border-radius: 99px;
  background: #eef3fb;
  overflow: hidden;
}

.progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #9dbdff, #2f6bff);
}

.project-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #eaf1fb;
  color: var(--faint);
  font-size: 10px;
}

.open-link {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #8fa5c4;
  transition: color 0.16s ease;
}

.project-card:hover .open-link {
  color: var(--blue-deep);
}

.new-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  padding: 24px;
  border: 1px dashed #c9dcf7;
  border-radius: var(--r-lg);
  background: rgba(255, 255, 255, 0.5);
  color: var(--muted);
  transition: 0.18s ease;
}

.new-card:hover {
  border-color: #9fbdf0;
  background: var(--blue-softer);
  color: var(--blue-deep);
}

.new-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--blue);
  box-shadow: var(--shadow-xs);
}

.new-card strong {
  margin-top: 13px;
  font-size: 13px;
  font-weight: 550;
  color: var(--ink-soft);
}

.new-card p {
  margin-top: 5px;
  max-width: 190px;
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--faint);
}

.no-result {
  padding: 30px 0;
  text-align: center;
  color: var(--faint);
  font-size: 12.5px;
}

.field-error {
  margin-top: 1px;
  font-size: 11px;
  color: var(--red);
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@media (max-width: 1240px) {
  .project-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .toolbar .search-field {
    width: 100%;
  }

  .project-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .new-card {
    min-height: 160px;
  }
}
</style>
