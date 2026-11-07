import axios from 'axios'
import { reactive } from 'vue'

import { toast } from '../store'

/**
 * 统一数据入口：只请求真实后端，不再回退到内置演示数据。
 * 后端不可达时保留连接状态，由页面提示错误。
 */
export const connection = reactive({
  mode: 'checking', // checking | live | offline
  mysql: '—',
  neo4j: '—',
  lastChecked: null,
  error: '',
})

const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

let readyPromise = null

export function ensureReady() {
  if (!readyPromise) readyPromise = checkConnection()
  return readyPromise
}

export async function checkConnection() {
  const previous = connection.mode
  connection.mode = 'checking'

  try {
    const { data } = await http.get('/health', { timeout: 3000 })
    connection.mysql = data?.mysql ?? 'unknown'
    connection.neo4j = data?.neo4j ?? 'unknown'
    connection.mode = 'live'
    connection.error = ''
    connection.lastChecked = new Date()
    if (previous === 'offline') {
      toast('已连接后端', '实时数据已接管当前界面。', 'success')
    }
  } catch (error) {
    connection.mode = 'offline'
    connection.mysql = '—'
    connection.neo4j = '—'
    connection.lastChecked = new Date()
    connection.error =
      error?.code === 'ECONNABORTED' ? '连接超时' : '无法连接后端服务'
  }

  return connection.mode
}

function normalizeError(error) {
  const detail = error?.response?.data?.detail
  let message = '请求失败，请稍后重试'

  if (typeof detail === 'string') {
    message = detail
  } else if (Array.isArray(detail) && detail.length) {
    message = detail.map((item) => item.msg).filter(Boolean).join('；') || message
  } else if (error?.message && !error?.response) {
    message = '无法连接后端服务'
  }

  if (error?.code === 'ECONNABORTED') {
    message = '请求超时：后端可能仍在处理，请稍后刷新查看结果'
  }

  const normalized = new Error(message)
  normalized.status = error?.response?.status
  return normalized
}

async function request(path, { method = 'get', params, data, timeout } = {}) {
  await ensureReady()

  // 离线状态下先自动重连一次，避免一次断连后所有操作都失败
  if (connection.mode === 'offline') {
    const mode = await checkConnection()
    if (mode !== 'live') {
      throw new Error('后端未连接：请确认后端已启动，再点击顶部「重新连接」')
    }
  }

  try {
    const response = await http.request({ url: path, method, params, data, timeout })
    return response.data
  } catch (error) {
    // 超时不代表后端掉线，避免误判为离线
    if (!error?.response && error?.code !== 'ECONNABORTED') {
      connection.mode = 'offline'
      connection.error = '后端连接中断'
    }
    throw normalizeError(error)
  }
}

/* ----------------------------- 项目 ----------------------------- */

export async function listProjects() {
  return request('/projects', { params: { limit: 100 } })
}

export async function getProject(id) {
  const projects = await listProjects()
  const project = projects.find((item) => String(item.id) === String(id))
  if (!project) throw new Error('项目不存在')
  return project
}

export async function createProject(payload) {
  return request('/projects', { method: 'post', data: payload })
}

export async function updateProject(id, payload) {
  return request(`/projects/${id}`, { method: 'patch', data: payload })
}

export async function deleteProject(id) {
  return request(`/projects/${id}`, { method: 'delete' })
}

export async function getProjectStats(id) {
  return request(`/projects/${id}/stats`)
}

export async function fetchProject(id, sourceId = null) {
  return request(`/projects/${id}/fetch`, {
    method: 'post',
    params: sourceId ? { source_id: sourceId } : undefined,
    timeout: 300000,
  })
}

export async function screenProject(id) {
  return request(`/projects/${id}/screen`, { method: 'post', timeout: 60000 })
}

export async function screenProject2(id, limit = 20) {
  return request(`/projects/${id}/screen2`, {
    method: 'post',
    params: { limit },
    timeout: 300000,
  })
}

export async function listProjectPapers(
  id,
  { status, limit = 100, offset = 0 } = {},
) {
  return request(`/projects/${id}/papers`, {
    params: { status, limit, offset },
  })
}

export async function listScreenings(id, passed = null) {
  return request(`/projects/${id}/screen2`, {
    params: {
      ...(passed === null || passed === undefined ? {} : { passed }),
      limit: 100,
    },
  })
}

export async function batchAnnotate(id, limit = 50) {
  return request(`/projects/${id}/annotate`, {
    method: 'post',
    params: { limit },
    timeout: 300000,
  })
}

/* ----------------------------- 文献 ----------------------------- */

export async function listPapers({ projectId = null, limit = 500, offset = 0 } = {}) {
  return request('/papers', {
    params: {
      ...(projectId === null || projectId === undefined ? {} : { project_id: projectId }),
      limit,
      offset,
    },
  })
}

export async function getPaper(id) {
  return request(`/papers/${id}`)
}

export async function getReading(id, projectId = null) {
  return request(`/papers/${id}/reading`, {
    params: projectId ? { project_id: projectId } : undefined,
  })
}

export async function getGraph(id) {
  return request(`/papers/${id}/graph`)
}

export async function annotatePaper(id) {
  return request(`/papers/${id}/annotate`, { method: 'post', timeout: 180000 })
}

export async function getGraphStats() {
  return request('/graph/stats')
}

/* ----------------------------- 订阅源 ----------------------------- */

export async function listSources() {
  return request('/sources')
}

export async function createSource(payload) {
  return request('/sources', { method: 'post', data: payload })
}

export async function updateSource(id, enabled) {
  return request(`/sources/${id}`, { method: 'patch', data: { enabled } })
}

export async function deleteSource(id) {
  return request(`/sources/${id}`, { method: 'delete' })
}

export async function previewSource(id, limit = 10) {
  return request(`/sources/${id}/preview`, { params: { limit } })
}

/* ----------------------------- 设置 ----------------------------- */

export async function getLLMSettings() {
  return request('/settings/llm')
}

export async function saveLLMSettings(payload) {
  return request('/settings/llm', { method: 'put', data: payload })
}

/* ----------------------------- 导出 ----------------------------- */

export async function downloadProject(projectId, options = {}) {
  await ensureReady()
  const { format = 'csv', stage = 'second', passed = null } = options

  const query = new URLSearchParams({ format, stage })
  if (passed !== null && passed !== undefined) query.set('passed', String(passed))
  const anchor = document.createElement('a')
  anchor.href = `/api/projects/${projectId}/export?${query.toString()}`
  anchor.download = ''
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}
