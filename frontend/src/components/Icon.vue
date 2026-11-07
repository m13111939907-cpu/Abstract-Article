<script setup>
import { computed } from 'vue'
import paths from './icons'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  stroke: { type: [Number, String], default: 1.7 },
})

const shape = computed(() => paths[props.name] || paths.info)
</script>

<template>
  <svg
    class="icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, index) in shape" :key="index" :d="d" />
  </svg>
</template>

<style scoped>
.icon {
  flex: none;
}
</style>
