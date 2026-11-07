<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import {
  checkConnection,
  connection,
  ensureReady,
  getLLMSettings,
  saveLLMSettings,
} from '../api/client'
import Icon from '../components/Icon.vue'
import { applyTheme, setPetEnabled, toast, ui } from '../store'
import { formatDateTime } from '../utils/format'

const retrying = ref(false)
const saving = ref(false)
const showKey = ref(false)
const hasKey = ref(false)

const isOffline = computed(() => connection.mode === 'offline')
const isChecking = computed(() => connection.mode === 'checking')

const themes = [
  { value: 'light', label: '浅色', icon: 'sun' },
  { value: 'dark', label: '深色', icon: 'moon' },
  { value: 'system', label: '跟随系统', icon: 'settings' },
]

const providers = [
  { value: 'mock', label: 'Mock（本地推理）', base: '', model: '' },
  {
    value: 'deepseek',
    label: 'DeepSeek',
    base: 'https://api.deepseek.com',
    model: 'deepseek-chat',
  },
  {
    value: 'huggingface',
    label: 'Hugging Face',
    base: 'https://api-inference.huggingface.co/v1',
    model: 'meta-llama/Llama-3.1-8B-Instruct',
  },
  { value: 'custom', label: '自定义 OpenAI 兼容', base: '', model: '' },
]

const form = reactive({
  provider: 'mock',
  model: 'deepseek-chat',
  base_url: 'https://api.deepseek.com',
  api_key: '',
})

const headline = computed(() => {
  if (isChecking.value) return '正在检测数据服务'
  if (isOffline.value) return '后端未连接'
  return '数据服务已连接'
})

const description = computed(() => {
  if (isChecking.value) return '正在请求 /api/health，确认 MySQL 与 Neo4j 的连通性。'
  if (isOffline.value) {
    return '无法访问后端服务，页面不会显示任何示例数据。启动 Docker Compose 后点击「重新检测」即可加载实时数据。'
  }
  return '前端正在通过 /api 代理读取 FastAPI，数据实时写入 MySQL 与 Neo4j。'
})

function healthTone(value) {
  if (isChecking.value) return 'wait'
  if (isOffline.value) return 'offline'
  return value === 'ok' ? 'ok' : 'bad'
}

function healthLabel(value) {
  if (isChecking.value) return '检测中'
  if (isOffline.value) return '不可用'
  return value === 'ok' ? '正常' : '异常'
}

function chooseTheme(value) {
  applyTheme(value)
}

function chooseProvider(value) {
  form.provider = value
  const preset = providers.find((item) => item.value === value)
  if (preset?.base) form.base_url = preset.base
  if (preset?.model) form.model = preset.model
  if (value === 'mock') {
    form.api_key = ''
    hasKey.value = false
  }
}

async function loadLLM() {
  try {
    const data = await getLLMSettings()
    form.provider = data.provider || 'mock'
    form.model = data.model || ''
    form.base_url = data.base_url || ''
    hasKey.value = Boolean(data.has_key)
  } catch (error) {
    toast('模型配置读取失败', error.message, 'error')
  }
}

async function saveLLM() {
  if (saving.value) return
  saving.value = true
  try {
    const data = await saveLLMSettings({ ...form })
    hasKey.value = Boolean(data.has_key)
    toast(
      '模型配置已保存',
      form.provider === 'mock' ? '当前使用 Mock 本地推理。' : `${data.model} 已就绪。`,
    )
  } catch (error) {
    toast('保存失败', error.message, 'error')
  } finally {
    saving.value = false
  }
}

async function retry() {
  retrying.value = true
  const mode = await checkConnection()
  retrying.value = false
  if (mode === 'live') {
    toast('后端连接成功', '已切换到实时数据，页面会自动刷新。')
    window.setTimeout(() => window.location.reload(), 900)
  } else {
    toast('仍未连接后端', '请确认 docker compose 已启动，且 8001 端口可访问。', 'warning')
  }
}

onMounted(async () => {
  const mode = await ensureReady()
  if (mode === 'live') loadLLM()
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div class="page-head-main">
        <p class="eyebrow">SETTINGS</p>
        <h1 class="page-title">设置</h1>
        <p class="page-sub">外观、模型接口与数据服务。</p>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary" type="button" :disabled="retrying" @click="retry">
          <Icon name="refresh" :size="15" :class="{ spin: retrying }" />
          {{ retrying ? '检测中…' : '重新检测' }}
        </button>
      </div>
    </header>

    <div class="settings-grid">
      <div class="settings-main">
        <section class="card connection-card">
          <div class="status-hero">
            <span class="status-orb" :class="{ 'is-offline': isOffline, 'is-live': !isOffline && !isChecking }">
              <Icon name="database" :size="22" />
            </span>
            <div class="status-copy">
              <p class="eyebrow">BACKEND CONNECTION</p>
              <h2>{{ headline }}</h2>
              <p>{{ description }}</p>
            </div>
            <span class="status" :class="isOffline ? 'is-amber' : isChecking ? 'is-blue' : 'is-green'">
              {{ isOffline ? 'OFFLINE' : isChecking ? 'CHECKING' : 'LIVE' }}
            </span>
          </div>

          <div class="health-grid">
            <div class="health-row">
              <span class="health-icon"><Icon name="database" :size="16" /></span>
              <div class="health-copy">
                <strong>MySQL</strong>
                <small>projects · papers · screenings</small>
              </div>
              <code>{{ isOffline ? 'offline' : connection.mysql }}</code>
              <span class="health-badge" :class="`is-${healthTone(connection.mysql)}`">
                {{ healthLabel(connection.mysql) }}
              </span>
            </div>

            <div class="health-row">
              <span class="health-icon"><Icon name="graph" :size="16" /></span>
              <div class="health-copy">
                <strong>Neo4j</strong>
                <small>Entity · RELATED 图数据</small>
              </div>
              <code>{{ isOffline ? 'offline' : connection.neo4j }}</code>
              <span class="health-badge" :class="`is-${healthTone(connection.neo4j)}`">
                {{ healthLabel(connection.neo4j) }}
              </span>
            </div>
          </div>

          <div class="connection-foot">
            <span>
              最后检测 {{ connection.lastChecked ? formatDateTime(connection.lastChecked) : '—' }}
              <template v-if="isOffline"> · {{ connection.error }}</template>
            </span>
            <a href="http://localhost:8001/docs" target="_blank" rel="noreferrer" class="section-link">
              打开接口文档 <Icon name="external" :size="12" />
            </a>
          </div>
        </section>

        <section class="card appearance-card">
          <div class="section-head">
            <div>
              <h2 class="section-title">外观</h2>
              <p class="section-sub">主题会保存在本地，下次打开自动恢复。</p>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-copy">
              <strong>主题模式</strong>
              <small>深色模式适合夜间和答辩投影</small>
            </div>
            <div class="segmented">
              <button
                v-for="theme in themes"
                :key="theme.value"
                type="button"
                class="segment"
                :class="{ 'is-active': ui.theme === theme.value }"
                @click="chooseTheme(theme.value)"
              >
                <Icon :name="theme.icon" :size="14" />
                {{ theme.label }}
              </button>
            </div>
          </div>

          <div class="setting-row">
            <div class="setting-copy">
              <strong>Aha 桌宠</strong>
              <small>右下角的小助手，点击可以换一句提醒</small>
            </div>
            <button
              class="switch"
              type="button"
              role="switch"
              :aria-checked="ui.petEnabled"
              :class="{ 'is-on': ui.petEnabled }"
              @click="setPetEnabled(!ui.petEnabled)"
            >
              <span />
            </button>
          </div>
        </section>

        <section class="card model-card">
          <div class="section-head">
            <div>
              <h2 class="section-title">模型与接口</h2>
              <p class="section-sub">配置后立即用于实体标注和二轮审阅；留空则使用 Mock。</p>
            </div>
            <span class="model-pill">{{ form.provider }}</span>
          </div>

          <div class="model-form">
            <div class="field">
              <label class="field-label">服务商</label>
              <div class="provider-grid">
                <button
                  v-for="provider in providers"
                  :key="provider.value"
                  type="button"
                  class="provider"
                  :class="{ 'is-active': form.provider === provider.value }"
                  @click="chooseProvider(provider.value)"
                >
                  {{ provider.label }}
                </button>
              </div>
            </div>

            <div class="field-row">
              <div class="field">
                <label class="field-label" for="model-name">模型名称</label>
                <input
                  id="model-name"
                  v-model="form.model"
                  class="input"
                  placeholder="deepseek-chat / llama-3.1-8b-instruct"
                />
              </div>
              <div class="field">
                <label class="field-label" for="model-base">接口地址</label>
                <input
                  id="model-base"
                  v-model="form.base_url"
                  class="input"
                  placeholder="https://api.deepseek.com"
                />
              </div>
            </div>

            <div class="field">
              <label class="field-label" for="model-key">
                API Key
                <span v-if="hasKey" class="key-state">已配置</span>
              </label>
              <div class="key-field">
                <input
                  id="model-key"
                  v-model="form.api_key"
                  class="input"
                  :type="showKey ? 'text' : 'password'"
                  :placeholder="hasKey ? '已保存，重新填写可覆盖' : 'sk-...'"
                  autocomplete="off"
                />
                <button class="icon-btn key-toggle" type="button" @click="showKey = !showKey">
                  <Icon :name="showKey ? 'eyeOff' : 'eye'" :size="15" />
                </button>
              </div>
              <p class="field-hint">
                DeepSeek 填 https://api.deepseek.com；Hugging Face 使用 OpenAI 兼容地址。
                配置保存在后端内存，重启后回退到 .env。
              </p>
            </div>

            <div class="model-actions">
              <button class="btn btn-primary" type="button" :disabled="saving" @click="saveLLM">
                {{ saving ? '保存中…' : '保存配置' }}
              </button>
              <span class="model-tip">
                <Icon name="info" :size="13" />
                当前状态：{{ form.provider === 'mock' ? 'Mock 本地推理' : hasKey ? '已配置 Key' : '缺少 Key，自动回退 Mock' }}
              </span>
            </div>
          </div>
        </section>
      </div>

      <aside class="settings-side">
        <section class="card links-card">
          <h2 class="section-title">快捷入口</h2>
          <a href="http://localhost:8001/docs" target="_blank" rel="noreferrer" class="link-row">
            <span><Icon name="book" :size="14" /> FastAPI 接口文档</span>
            <Icon name="external" :size="12" />
          </a>
          <a href="http://localhost:7474" target="_blank" rel="noreferrer" class="link-row">
            <span><Icon name="graph" :size="14" /> Neo4j Browser</span>
            <Icon name="external" :size="12" />
          </a>
          <a href="http://localhost:5173" target="_blank" rel="noreferrer" class="link-row">
            <span><Icon name="globe" :size="14" /> 前端开发地址</span>
            <Icon name="external" :size="12" />
          </a>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
  gap: 16px;
  align-items: start;
}

.settings-main,
.settings-side {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* ---------- 连接 ---------- */

.connection-card {
  padding: 24px;
}

.status-hero {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.status-orb {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  flex: none;
  border-radius: 13px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  color: var(--faint);
}

.status-orb.is-live {
  background: var(--green-soft);
  border-color: #d1efe3;
  color: #0b7a56;
}

.status-orb.is-offline {
  background: var(--amber-soft);
  border-color: #f1e1c1;
  color: #a0680f;
}

.status-copy {
  flex: 1;
  min-width: 0;
}

.status-copy h2 {
  margin-top: 7px;
  font-size: 20px;
  letter-spacing: -0.025em;
}

.status-copy p:last-child {
  margin-top: 5px;
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--muted);
  max-width: 560px;
}

.health-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 20px;
}

.health-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-soft);
}

.health-icon {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: 7px;
  background: var(--surface);
  border: 1px solid var(--line);
  color: var(--blue);
}

.health-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.health-copy strong {
  font-size: 11px;
  font-weight: 550;
  color: var(--ink-soft);
}

.health-copy small {
  font-size: 8.5px;
  color: var(--faint);
}

.health-row code {
  max-width: 88px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 9px;
  color: var(--faint);
}

.health-badge {
  flex: none;
  font-size: 8.5px;
  font-weight: 500;
  border-radius: 99px;
  padding: 1px 6px;
}

.health-badge.is-ok {
  color: #0b7a56;
  background: var(--green-soft);
}

.health-badge.is-offline {
  color: #946112;
  background: var(--amber-soft);
}

.health-badge.is-bad {
  color: #b33636;
  background: var(--red-soft);
}

.health-badge.is-wait {
  color: var(--blue-deep);
  background: var(--blue-soft);
}

.connection-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding-top: 13px;
  border-top: 1px solid var(--line);
  font-size: 9.5px;
  color: var(--faint);
}

/* ---------- 外观 ---------- */

.appearance-card {
  padding: 22px 24px 10px;
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 15px 0;
  border-top: 1px solid var(--line);
}

.setting-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setting-copy strong {
  font-size: 12.5px;
  font-weight: 550;
  color: var(--ink-soft);
}

.setting-copy small {
  font-size: 10.5px;
  color: var(--faint);
}

.segmented {
  display: flex;
  gap: 3px;
  padding: 3px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface-soft);
}

.segment {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 11px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font-size: 11.5px;
  transition: 0.16s ease;
}

.segment:hover {
  color: var(--ink-soft);
}

.segment.is-active {
  background: var(--surface);
  color: var(--blue-deep);
  box-shadow: var(--shadow-xs);
}

.switch {
  position: relative;
  width: 38px;
  height: 21px;
  flex: none;
  padding: 0;
  border: 0;
  border-radius: 99px;
  background: var(--line-2);
  transition: background 0.18s ease;
}

.switch span {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 2px rgba(13, 27, 52, 0.18);
  transition: transform 0.18s ease;
}

.switch.is-on {
  background: var(--blue);
}

.switch.is-on span {
  transform: translateX(17px);
}

/* ---------- 模型 ---------- */

.model-card {
  padding: 22px 24px;
}

.model-pill {
  flex: none;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 9px;
  color: var(--blue-deep);
  background: var(--blue-soft);
  border: 1px solid var(--line-2);
  border-radius: 99px;
  padding: 3px 8px;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 7px;
}

.provider {
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 11px;
  transition: 0.16s ease;
}

.provider:hover {
  border-color: var(--line-3);
  color: var(--ink-soft);
}

.provider.is-active {
  border-color: #9dbbf5;
  background: var(--blue-soft);
  color: var(--blue-deep);
  font-weight: 550;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.key-field {
  position: relative;
}

.key-field .input {
  padding-right: 42px;
}

.key-toggle {
  position: absolute;
  right: 4px;
  top: 4px;
  width: 32px;
  height: 32px;
}

.key-state {
  font-size: 9px;
  font-weight: 550;
  color: #0b7a56;
  background: var(--green-soft);
  border-radius: 99px;
  padding: 1px 7px;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
  padding-top: 15px;
  border-top: 1px solid var(--line);
}

.model-tip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: var(--faint);
}

/* ---------- 侧栏 ---------- */

.links-card {
  padding: 18px 18px 8px;
}

.links-card .section-title {
  margin-bottom: 6px;
  font-size: 12.5px;
}

.link-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 9px 0;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  font-size: 10.5px;
}

.link-row:hover {
  color: var(--blue-deep);
}

.link-row > span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
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

@media (max-width: 1080px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-side {
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    align-items: start;
  }
}

@media (max-width: 760px) {
  .health-grid,
  .field-row,
  .provider-grid {
    grid-template-columns: 1fr;
  }

  .settings-side {
    grid-template-columns: 1fr;
  }

  .setting-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .model-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .connection-foot {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
}
</style>
