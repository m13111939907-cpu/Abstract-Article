import { reactive } from 'vue'

const THEME_KEY = 'le-theme'
const PET_KEY = 'le-pet'

export const ui = reactive({
  sidebarOpen: false,
  toasts: [],
  theme: 'light',
  petEnabled: true,
})

let seq = 0

export function toast(title, detail = '', type = 'success') {
  const id = ++seq
  ui.toasts.push({ id, title, detail, type })
  window.setTimeout(() => dismissToast(id), 3800)
  return id
}

export function dismissToast(id) {
  const index = ui.toasts.findIndex((item) => item.id === id)
  if (index !== -1) ui.toasts.splice(index, 1)
}

/* ---------------- 主题 ---------------- */

function resolveTheme(theme) {
  if (theme !== 'system') return theme
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function paintTheme(theme) {
  document.documentElement.dataset.theme = resolveTheme(theme)
}

export function applyTheme(theme) {
  ui.theme = ['light', 'dark', 'system'].includes(theme) ? theme : 'light'
  localStorage.setItem(THEME_KEY, ui.theme)
  paintTheme(ui.theme)
}

export function toggleTheme() {
  applyTheme(ui.theme === 'dark' ? 'light' : 'dark')
}

/* ---------------- 桌面宠物 ---------------- */

export function setPetEnabled(enabled) {
  ui.petEnabled = Boolean(enabled)
  localStorage.setItem(PET_KEY, ui.petEnabled ? '1' : '0')
}

export function initPreferences() {
  applyTheme(localStorage.getItem(THEME_KEY) || 'light')
  ui.petEnabled = localStorage.getItem(PET_KEY) !== '0'

  // 跟随系统时，系统主题变化同步刷新
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (ui.theme === 'system') paintTheme('system')
  })
}
