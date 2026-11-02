<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'

const health = ref({ mysql: '检查中…', neo4j: '检查中…' })
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/health')
    health.value = data
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <main class="page">
    <h1>文献提取器</h1>
    <p class="subtitle">Step 1 · 环境连通性检查</p>

    <section class="card">
      <div class="row">
        <span>MySQL</span>
        <code :class="health.mysql === 'ok' ? 'ok' : 'bad'">{{ health.mysql }}</code>
      </div>
      <div class="row">
        <span>Neo4j</span>
        <code :class="health.neo4j === 'ok' ? 'ok' : 'bad'">{{ health.neo4j }}</code>
      </div>
      <p v-if="error" class="bad">{{ error }}</p>
    </section>

    <p class="hint">
      接口文档：<a href="http://localhost:8001/docs" target="_blank">/docs</a>
    </p>
  </main>
</template>

<style scoped>
.page {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px;
  text-align: left;
}

h1 {
  font-size: 32px;
  margin: 0 0 8px;
}

.subtitle {
  margin: 0 0 24px;
  color: var(--muted);
}

.card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  background: var(--card);
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.row + .row {
  border-top: 1px solid var(--border);
}

code {
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 14px;
}

code.ok {
  color: #15803d;
  background: #dcfce7;
}

code.bad {
  color: #b91c1c;
  background: #fee2e2;
}

.hint {
  margin-top: 20px;
  color: var(--muted);
  font-size: 14px;
}

.hint a {
  color: inherit;
}
</style>
