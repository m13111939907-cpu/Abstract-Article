<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'

import {
  createSource,
  deleteSource,
  ensureReady,
  listSources,
  previewSource,
  updateSource,
} from '../api/client'
import BaseModal from '../components/BaseModal.vue'
import EmptyState from '../components/EmptyState.vue'
import Icon from '../components/Icon.vue'
import { toast } from '../store'
import { domainOf, formatDate } from '../utils/format'

const sources = ref([])
const loading = ref(true)
const toggling = ref(null)

const showAdd = ref(false)
const saving = ref(false)
const nameInput = ref(null)
const form = reactive({ name: '', rss_url: '' })
const errors = reactive({ name: '', rss_url: '' })

const deleteTarget = ref(null)
const deleting = ref(false)

const previewTarget = ref(null)
const previewData = ref(null)
const previewLoading = ref(false)
const previewError = ref('')

const enabledCount = computed(() => sources.value.filter((item) => item.enabled).length)

async function load() {
  loading.value = true
  try {
    await ensureReady()
    sources.value = await listSources()
  } catch (error) {
    toast('订阅源加载失败', error.message, 'error')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  form.name = ''
  form.rss_url = ''
  errors.name = ''
  errors.rss_url = ''
  showAdd.value = true
  nextTick(() => nameInput.value?.focus())
}

async function submit() {
  errors.name = form.name.trim() ? '' : '请填写订阅源名称'
  let validUrl = false
  try {
    const url = new URL(form.rss_url.trim())
    validUrl = url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    validUrl = false
  }
  errors.rss_url = validUrl ? '' : '请输入以 http(s):// 开头的 RSS 地址'
  if (errors.name || errors.rss_url || saving.value) return

  saving.value = true
  try {
    const source = await createSource({
      name: form.name.trim(),
      rss_url: form.rss_url.trim(),
    })
    sources.value.push(source)
    showAdd.value = false
    toast('订阅源已添加', `「${source.name}」已启用，下次抓取会一并拉取。`)
  } catch (error) {
    toast('添加失败', error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function toggle(source) {
  if (toggling.value) return
  toggling.value = source.id
  const previous = source.enabled
  source.enabled = !previous
  try {
    await updateSource(source.id, source.enabled)
    toast(source.enabled ? '已启用订阅源' : '已停用订阅源', source.name)
  } catch (error) {
    source.enabled = previous
    toast('操作失败', error.message, 'error')
  } finally {
    toggling.value = null
  }
}

async function openPreview(source) {
  previewTarget.value = source
  previewData.value = null
  previewError.value = ''
  previewLoading.value = true
  try {
    previewData.value = await previewSource(source.id, 10)
  } catch (error) {
    previewError.value = error.message
  } finally {
    previewLoading.value = false
  }
}

function closePreview() {
  previewTarget.value = null
  previewData.value = null
  previewError.value = ''
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteSource(deleteTarget.value.id)
    sources.value = sources.value.filter((item) => item.id !== deleteTarget.value.id)
    toast('订阅源已删除', deleteTarget.value.name)
    deleteTarget.value = null
  } catch (error) {
    toast('无法删除', error.message, 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">RSS SOURCES</p>
        <h1 class="page-title">订阅源</h1>
        <p class="page-sub">
          聚合期刊与预印本平台的 RSS。抓取时统一清洗文本、抽取关键词，并按 DOI / 链接做一次去重。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" type="button" @click="openAdd">
          <Icon name="plus" :size="15" />
          添加订阅源
        </button>
      </div>
    </header>

    <div class="sources-grid">
      <section class="card source-card">
        <div class="source-card-head">
          <div>
            <h2 class="section-title">RSS 订阅源</h2>
            <p class="section-sub">
              {{ sources.length }} 个来源 · {{ enabledCount }} 个启用 · 抓取时只读取启用的源
            </p>
          </div>
          <span class="source-count">{{ sources.length }}</span>
        </div>

        <div v-if="loading" class="source-loading">
          <div v-for="index in 4" :key="index" class="skeleton" style="height: 56px" />
        </div>

        <div v-else-if="sources.length" class="source-rows">
          <div class="source-row" :class="{ 'is-disabled': !source.enabled }" v-for="source in sources" :key="source.id">
            <span class="source-logo">{{ source.name.slice(0, 1).toUpperCase() }}</span>

            <div class="source-main">
              <div class="source-name">
                <strong>{{ source.name }}</strong>
                <span v-if="source.enabled" class="source-live">LIVE</span>
              </div>
              <a :href="source.rss_url" target="_blank" rel="noreferrer" class="source-url">
                {{ source.rss_url }}
              </a>
              <span class="source-created">添加于 {{ formatDate(source.created_at) }} · {{ domainOf(source.rss_url) }}</span>
            </div>

            <button
              class="icon-btn preview-btn"
              type="button"
              title="预览 RSS 最新条目"
              aria-label="预览 RSS 最新条目"
              @click="openPreview(source)"
            >
              <Icon name="eye" :size="15" />
            </button>

            <button
              class="switch"
              type="button"
              role="switch"
              :aria-checked="source.enabled"
              :aria-label="`${source.enabled ? '停用' : '启用'} ${source.name}`"
              :disabled="toggling === source.id"
              :class="{ 'is-on': source.enabled }"
              @click="toggle(source)"
            >
              <span />
            </button>

            <button
              class="icon-btn delete-btn"
              type="button"
              aria-label="删除订阅源"
              @click="deleteTarget = source"
            >
              <Icon name="trash" :size="15" />
            </button>
          </div>
        </div>

        <EmptyState
          v-else
          icon="rss"
          title="还没有订阅源"
          text="添加 Nature、Science 或 arXiv 的 RSS 地址，就可以开始抓取文献。"
        >
          <button class="btn btn-primary btn-sm" type="button" @click="openAdd">
            添加第一个订阅源
          </button>
        </EmptyState>
      </section>

      <aside class="side-note">
        <section class="card note-card">
          <p class="eyebrow">HOW IT WORKS</p>
          <h2>从 RSS 到文献库</h2>
          <ol class="note-steps">
            <li>
              <span>01</span>
              <div><strong>下载与解析</strong><p>httpx 获取 XML，feedparser 解析每一条 entry。</p></div>
            </li>
            <li>
              <span>02</span>
              <div><strong>清洗与抽取</strong><p>去 HTML 与出版前缀，jieba / 英文词频提取关键词。</p></div>
            </li>
            <li>
              <span>03</span>
              <div><strong>哈希去重</strong><p>按 DOI、链接或标题计算 SHA-256，跨项目只保留一份。</p></div>
            </li>
            <li>
              <span>04</span>
              <div><strong>写入 MySQL</strong><p>标题、作者、摘要、关键词、高频词一并入库。</p></div>
            </li>
          </ol>
        </section>

        <section class="card tip-card">
          <span class="tip-icon"><Icon name="info" :size="16" /></span>
          <div>
            <strong>删除只解除来源关联</strong>
            <p>已入库的文献会保留，来源标记会被清空；需要继续抓取时重新添加同一地址即可。</p>
          </div>
        </section>
      </aside>
    </div>

    <BaseModal
      :open="showAdd"
      title="添加 RSS 订阅源"
      subtitle="支持 RSS 2.0 与 Atom。添加后可随时启用或停用。"
      width="500px"
      @close="showAdd = false"
    >
      <div class="field">
        <label class="field-label" for="source-name">名称</label>
        <input
          id="source-name"
          ref="nameInput"
          v-model="form.name"
          class="input"
          :class="{ 'is-error': errors.name }"
          placeholder="例如：Nature"
          maxlength="128"
        />
        <p v-if="errors.name" class="field-error">{{ errors.name }}</p>
      </div>

      <div class="field">
        <label class="field-label" for="source-url">RSS 地址</label>
        <input
          id="source-url"
          v-model="form.rss_url"
          class="input"
          :class="{ 'is-error': errors.rss_url }"
          placeholder="https://www.nature.com/nature.rss"
          @keyup.enter="submit"
        />
        <p v-if="errors.rss_url" class="field-error">{{ errors.rss_url }}</p>
        <p class="field-hint">
          常用示例：nature.com/nature.rss · science.org/rss/news_current.xml · rss.arxiv.org/rss/cs.CL
        </p>
      </div>

      <template #footer>
        <button class="btn btn-ghost" type="button" @click="showAdd = false">取消</button>
        <button
          class="btn btn-primary"
          type="button"
          :disabled="saving"
          @click="submit"
        >
          {{ saving ? '添加中…' : '添加并启用' }}
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :open="!!previewTarget"
      :title="previewTarget ? `RSS 预览 · ${previewTarget.name}` : 'RSS 预览'"
      :subtitle="previewData ? `${previewData.feed_title} · 共 ${previewData.total} 条` : '正在读取 RSS…'"
      width="640px"
      @close="closePreview"
    >
      <div v-if="previewLoading" class="preview-loading">
        <span class="spinner" />
        正在请求原始 RSS…
      </div>
      <p v-else-if="previewError" class="preview-error">{{ previewError }}</p>
      <ol v-else-if="previewData" class="preview-list">
        <li v-for="(item, index) in previewData.items" :key="index">
          <span class="preview-num">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="preview-copy">
            <a :href="item.link" target="_blank" rel="noreferrer">{{ item.title }}</a>
            <p v-if="item.summary">{{ item.summary }}</p>
            <span class="preview-date">{{ formatDate(item.published_at) }}</span>
          </div>
        </li>
      </ol>
      <p class="preview-note">仅预览原始 RSS，不会写入数据库。</p>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="closePreview">关闭</button>
      </template>
    </BaseModal>

    <BaseModal
      :open="!!deleteTarget"
      title="删除订阅源？"
      subtitle="删除后不会再从该地址抓取。已经入库的文献不会被删除。"
      width="430px"
      @close="deleteTarget = null"
    >
      <div class="delete-preview">
        <span class="source-logo">{{ deleteTarget?.name.slice(0, 1).toUpperCase() }}</span>
        <div>
          <strong>{{ deleteTarget?.name }}</strong>
          <p>{{ deleteTarget?.rss_url }}</p>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-ghost" type="button" @click="deleteTarget = null">取消</button>
        <button class="btn btn-danger" type="button" :disabled="deleting" @click="confirmDelete">
          {{ deleting ? '删除中…' : '确认删除' }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.sources-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.75fr);
  gap: 16px;
  align-items: start;
}

.source-card {
  padding: 22px 24px 10px;
}

.source-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.source-card-head .section-sub {
  margin-top: 3px;
}

.source-count {
  display: grid;
  place-items: center;
  min-width: 30px;
  height: 24px;
  padding: 0 8px;
  border-radius: 99px;
  background: var(--blue-soft);
  color: var(--blue-deep);
  font-size: 10.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.source-loading {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 12px;
}

.source-rows {
  display: flex;
  flex-direction: column;
}

.source-row {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 15px 4px;
  border-top: 1px solid #eef4fc;
  transition: opacity 0.16s ease;
}

.source-row.is-disabled {
  opacity: 0.62;
}

.source-logo {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  border-radius: 10px;
  background: linear-gradient(150deg, #f2f7ff, #e3eeff);
  border: 1px solid #d9e6fa;
  color: var(--blue-deep);
  font-size: 13px;
  font-weight: 600;
}

.source-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.source-name {
  display: flex;
  align-items: center;
  gap: 7px;
}

.source-name strong {
  font-size: 12.5px;
  font-weight: 550;
  color: var(--ink);
}

.source-live {
  font-size: 7px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: #0b7a56;
  background: var(--green-soft);
  border-radius: 4px;
  padding: 1px 4px;
}

.source-url {
  font-size: 10px;
  color: #8ea1bb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-url:hover {
  color: var(--blue-deep);
}

.source-created {
  font-size: 9px;
  color: #b0bccc;
}

.switch {
  position: relative;
  width: 34px;
  height: 19px;
  flex: none;
  padding: 0;
  border: 0;
  border-radius: 99px;
  background: #dfe7f2;
  transition: background 0.18s ease;
}

.switch span {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(13, 27, 52, 0.18);
  transition: transform 0.18s ease;
}

.switch.is-on {
  background: var(--blue);
}

.switch.is-on span {
  transform: translateX(15px);
}

.switch:disabled {
  opacity: 0.5;
}

.delete-btn {
  width: 30px;
  height: 30px;
  color: #aebbcb;
}

.delete-btn:hover {
  color: var(--red);
  background: var(--red-soft);
}

/* ---------- RSS 预览 ---------- */

.preview-btn {
  width: 30px;
  height: 30px;
  color: #aebbcb;
}

.preview-btn:hover {
  color: var(--blue-deep);
  background: var(--blue-soft);
}

.preview-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 26px 4px;
  color: var(--muted);
  font-size: 12px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--line-2);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.preview-error {
  padding: 16px;
  border-radius: 10px;
  background: var(--red-soft);
  color: var(--red);
  font-size: 12px;
}

.preview-list {
  display: flex;
  flex-direction: column;
  max-height: 430px;
  overflow-y: auto;
}

.preview-list li {
  display: flex;
  gap: 12px;
  padding: 12px 2px;
  border-bottom: 1px dashed var(--line);
}

.preview-list li:last-child {
  border-bottom: 0;
}

.preview-num {
  flex: none;
  padding-top: 2px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 9px;
  color: var(--faint);
}

.preview-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.preview-copy a {
  font-size: 12.5px;
  font-weight: 550;
  line-height: 1.5;
  color: var(--ink);
}

.preview-copy a:hover {
  color: var(--blue-deep);
}

.preview-copy p {
  font-size: 10.5px;
  line-height: 1.6;
  color: var(--muted);
}

.preview-date {
  font-size: 9.5px;
  color: var(--faint);
}

.preview-note {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
  font-size: 9.5px;
  color: var(--faint);
}

/* ---------- 右侧说明 ---------- */

.side-note {
  display: flex;
  flex-direction: column;
  gap: 13px;
  position: sticky;
  top: 78px;
}

.note-card {
  padding: 22px 22px 18px;
  background: linear-gradient(180deg, #fff 0%, #fbfdff 100%);
}

.note-card h2 {
  margin-top: 9px;
  font-size: 17px;
  letter-spacing: -0.02em;
}

.note-steps {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
}

.note-steps li {
  display: flex;
  gap: 11px;
  padding: 11px 0;
  border-top: 1px dashed #eaf1fb;
}

.note-steps li > span {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 8.5px;
  color: #9fb3cf;
  padding-top: 2px;
}

.note-steps strong {
  font-size: 11.5px;
  font-weight: 550;
  color: var(--ink-soft);
}

.note-steps p {
  margin-top: 3px;
  font-size: 10px;
  line-height: 1.65;
  color: var(--faint);
}

.tip-card {
  display: flex;
  gap: 10px;
  padding: 14px 15px;
  background: var(--surface-soft);
}

.tip-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: none;
  border-radius: 7px;
  background: var(--blue-soft);
  color: var(--blue-deep);
}

.tip-card strong {
  font-size: 10.5px;
  font-weight: 550;
  color: var(--ink-soft);
}

.tip-card p {
  margin-top: 3px;
  font-size: 9.5px;
  line-height: 1.6;
  color: var(--faint);
}

.field-error {
  font-size: 11px;
  color: var(--red);
}

.delete-preview {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-soft);
}

.delete-preview strong {
  font-size: 12px;
  font-weight: 550;
  color: var(--ink-soft);
}

.delete-preview p {
  margin-top: 2px;
  font-size: 9.5px;
  color: var(--faint);
  word-break: break-all;
}

@media (max-width: 940px) {
  .sources-grid {
    grid-template-columns: 1fr;
  }

  .side-note {
    position: static;
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
}

@media (max-width: 640px) {
  .source-card {
    padding: 18px 16px 6px;
  }

  .source-row {
    gap: 10px;
  }

  .source-created {
    display: none;
  }

  .side-note {
    grid-template-columns: 1fr;
  }
}
</style>
