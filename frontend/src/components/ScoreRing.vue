<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  size: { type: Number, default: 62 },
  tone: { type: String, default: 'auto' },
  stroke: { type: Number, default: 5 },
})

const normalized = computed(() => Math.min(1, Math.max(0, Number(props.score) || 0)))
const radius = computed(() => (props.size - props.stroke) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value * (1 - normalized.value))

const color = computed(() => {
  if (props.tone === 'red') return '#d14343'
  if (props.tone === 'green') return '#0e9f6e'
  if (props.tone === 'blue') return '#2f6bff'
  if (normalized.value >= 0.75) return '#2f6bff'
  if (normalized.value >= 0.55) return '#d99b32'
  return '#d14343'
})

const percent = computed(() => Math.round(normalized.value * 100))
</script>

<template>
  <span class="ring" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        stroke="#edf3fc"
        :stroke-width="stroke"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke="color"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
        class="ring-value"
      />
    </svg>
    <span class="ring-label">
      <strong>{{ percent }}</strong><small>%</small>
    </span>
  </span>
</template>

<style scoped>
.ring {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
}

.ring svg {
  position: absolute;
  inset: 0;
}

.ring-value {
  transition: stroke-dashoffset 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.ring-label {
  position: relative;
  display: flex;
  align-items: baseline;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
}

.ring-label strong {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.03em;
}

.ring-label small {
  margin-left: 1px;
  font-size: 8px;
  color: var(--faint);
}
</style>
