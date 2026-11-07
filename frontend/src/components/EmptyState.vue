<script setup>
import Icon from './Icon.vue'

defineProps({
  icon: { type: String, default: 'file' },
  title: { type: String, default: '这里还没有内容' },
  text: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="empty" :class="{ 'is-compact': compact }">
    <span class="empty-icon">
      <Icon :name="icon" :size="compact ? 19 : 23" />
    </span>
    <h3>{{ title }}</h3>
    <p v-if="text">{{ text }}</p>
    <div v-if="$slots.default" class="empty-action">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty.is-compact {
  padding: 26px 18px;
}

.empty-icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: var(--blue-softer);
  border: 1px dashed #c9dcf8;
  color: #7ea6e8;
}

.is-compact .empty-icon {
  width: 37px;
  height: 37px;
  border-radius: 11px;
}

.empty h3 {
  margin-top: 13px;
  font-size: 13.5px;
  font-weight: 550;
  color: var(--ink-soft);
}

.is-compact h3 {
  margin-top: 10px;
  font-size: 12.5px;
}

.empty p {
  margin-top: 5px;
  max-width: 380px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--faint);
}

.empty-action {
  margin-top: 14px;
}
</style>
