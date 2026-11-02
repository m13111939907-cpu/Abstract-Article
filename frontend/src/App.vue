<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header class="nav">
    <RouterLink to="/" class="brand">文献提取器</RouterLink>
    <nav>
      <RouterLink to="/">首页</RouterLink>
    </nav>
  </header>
  <RouterView />
</template>

<style scoped>
.nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
}

.brand {
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
}

nav a {
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
}

nav a.router-link-active {
  color: var(--text);
}
</style>
