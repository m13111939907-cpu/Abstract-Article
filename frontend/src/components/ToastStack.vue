<script setup>
import { ui, dismissToast } from '../store'
import Icon from './Icon.vue'

const toneIcon = {
  success: 'check',
  warning: 'alert',
  error: 'alert',
  info: 'info',
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-stack" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <div
          v-for="item in ui.toasts"
          :key="item.id"
          class="toast"
          :class="`is-${item.type}`"
        >
          <span class="toast-icon">
            <Icon :name="toneIcon[item.type] || 'info'" :size="15" />
          </span>
          <div class="toast-body">
            <strong>{{ item.title }}</strong>
            <p v-if="item.detail">{{ item.detail }}</p>
          </div>
          <button
            class="toast-close"
            type="button"
            aria-label="关闭提示"
            @click="dismissToast(item.id)"
          >
            <Icon name="x" :size="13" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-stack {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: min(352px, calc(100vw - 32px));
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 12px 12px 13px;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 16px 38px -18px rgba(13, 27, 52, 0.35);
  pointer-events: auto;
  backdrop-filter: blur(12px);
}

.toast-icon {
  display: grid;
  place-items: center;
  width: 27px;
  height: 27px;
  flex: none;
  border-radius: 8px;
  background: var(--blue-soft);
  color: var(--blue-deep);
}

.toast.is-warning .toast-icon {
  background: var(--amber-soft);
  color: #a0680f;
}

.toast.is-error .toast-icon {
  background: var(--red-soft);
  color: var(--red);
}

.toast-body {
  flex: 1;
  min-width: 0;
  padding-top: 1px;
}

.toast-body strong {
  display: block;
  font-size: 12.5px;
  font-weight: 550;
  color: var(--ink);
  line-height: 1.45;
}

.toast-body p {
  margin-top: 3px;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--muted);
}

.toast-close {
  flex: none;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--faint);
}

.toast-close:hover {
  background: var(--surface-soft);
  color: var(--ink-soft);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (max-width: 640px) {
  .toast-stack {
    right: 16px;
    bottom: 16px;
  }
}
</style>
