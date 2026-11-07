import { reactive } from 'vue'

const PET_KEY = 'le-pet'

export const ui = reactive({
  sidebarOpen: false,
  toasts: [],
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

/* ---------------- 桌面宠物 ---------------- */

export function setPetEnabled(enabled) {
  ui.petEnabled = Boolean(enabled)
  localStorage.setItem(PET_KEY, ui.petEnabled ? '1' : '0')
}

export function initPreferences() {
  ui.petEnabled = localStorage.getItem(PET_KEY) !== '0'
}
