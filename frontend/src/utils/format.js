const DATE_FMT = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

const pad = (value) => String(value).padStart(2, '0')

export function parseDate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** 2026.11.02 */
export function formatDate(value) {
  const date = parseDate(value)
  if (!date) return '—'
  return `${date.getFullYear()}.${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
}

/** 11.02 */
export function formatShort(value) {
  const date = parseDate(value)
  if (!date) return '—'
  return `${pad(date.getMonth() + 1)}.${pad(date.getDate())}`
}

/** 2026.11.02 14:30 */
export function formatDateTime(value) {
  const date = parseDate(value)
  if (!date) return '—'
  return `${formatDate(date)} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function relativeTime(value) {
  const date = parseDate(value)
  if (!date) return '—'
  const diff = Date.now() - date.getTime()
  if (diff < 0) return formatDate(date)
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return formatDate(date)
}

export function domainOf(url) {
  if (!url) return '未标注来源'
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return '外部链接'
  }
}

/** 支持中英文逗号、分号、空白 */
export function splitKeywords(raw) {
  return String(raw || '')
    .split(/[,，;；\s]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

/** 仅按逗号/分号切分，用于展示多词关键词短语 */
export function displayKeywords(raw) {
  return String(raw || '')
    .split(/[,，;；]+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function formatNumber(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '0'
  return number.toLocaleString('zh-CN')
}

export function percent(value, total) {
  if (!total) return 0
  return Math.round((Number(value) / Number(total)) * 100)
}

export function greeting(date = new Date()) {
  const hour = date.getHours()
  if (hour < 6) return '夜深了'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

export function weekdayLabel(date = new Date()) {
  return ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][
    date.getDay()
  ]
}

export function initials(name) {
  return String(name || '?')
    .trim()
    .slice(0, 1)
    .toUpperCase()
}
