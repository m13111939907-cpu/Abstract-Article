<script setup>
import { onBeforeUnmount, watch } from 'vue'

import Icon from './Icon.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  width: { type: String, default: '480px' },
})

const emit = defineEmits(['close'])

function close() {
  emit('close')
}

function onKeydown(event) {
  if (event.key === 'Escape' && props.open) close()
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      document.body.style.overflow = 'hidden'
      window.addEventListener('keydown', onKeydown)
    } else {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKeydown)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-scrim" @mousedown.self="close">
        <section
          class="modal-card"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          :style="{ maxWidth: width }"
        >
          <header class="modal-head">
            <div>
              <h2>{{ title }}</h2>
              <p v-if="subtitle">{{ subtitle }}</p>
            </div>
            <button
              class="modal-close"
              type="button"
              aria-label="关闭"
              @click="close"
            >
              <Icon name="x" :size="16" />
            </button>
          </header>

          <div class="modal-body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-scrim {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(13, 27, 52, 0.32);
  backdrop-filter: blur(5px);
}

.modal-card {
  width: 100%;
  max-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 18px;
  box-shadow: 0 30px 80px -28px rgba(13, 27, 52, 0.45);
  overflow: hidden;
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 24px 16px;
}

.modal-head h2 {
  font-size: 18px;
  line-height: 1.35;
  color: var(--ink);
}

.modal-head p {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--muted);
  max-width: 420px;
}

.modal-close {
  display: grid;
  place-items: center;
  width: 29px;
  height: 29px;
  flex: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--muted);
}

.modal-close:hover {
  background: var(--surface-soft);
  color: var(--ink);
}

.modal-body {
  padding: 4px 24px 22px;
  overflow-y: auto;
}

.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
  padding: 15px 24px;
  background: var(--surface-soft);
  border-top: 1px solid var(--line);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
  transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-card,
.modal-leave-to .modal-card {
  transform: translateY(10px) scale(0.985);
}

@media (max-width: 560px) {
  .modal-scrim {
    padding: 12px;
  }

  .modal-head {
    padding: 20px 18px 14px;
  }

  .modal-body {
    padding: 4px 18px 20px;
  }

  .modal-foot {
    padding: 14px 18px;
  }
}
</style>
