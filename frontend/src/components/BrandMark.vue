<script setup>
defineProps({
  size: { type: Number, default: 30 },
})
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 32 32"
    fill="none"
    aria-hidden="true"
    class="brand"
  >
    <rect width="32" height="32" rx="9" fill="#2F6BFF" />
    <rect x="0.5" y="0.5" width="31" height="31" rx="8.5" stroke="white" stroke-opacity=".16" />
    <path d="M9 11.5h14" stroke="white" stroke-width="1.8" stroke-linecap="round" />
    <path d="M9 16h9" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-opacity=".82" />
    <path d="M9 20.5h5" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-opacity=".6" />
    <circle cx="22.6" cy="20.5" r="2.1" fill="#BFD5FF" />
    <circle cx="22.6" cy="20.5" r="2.1" stroke="white" stroke-opacity=".5" stroke-width=".8" />
  </svg>
</template>

<style scoped>
.brand {
  display: block;
  filter: drop-shadow(0 4px 8px rgba(31, 87, 230, 0.2));
}
</style>
