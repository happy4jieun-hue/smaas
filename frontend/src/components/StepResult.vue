<script setup lang="ts">
defineProps<{ label: string; data: unknown }>();
</script>

<template>
  <div class="card">
    <div class="label">{{ label }}</div>
    <div v-if="data === undefined || data === null" class="empty">— 미완료 —</div>
    <pre v-else class="pre">{{ JSON.stringify(data, null, 2) }}</pre>
  </div>
</template>

<style scoped>
.card {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.label {
  font-weight: 700;
  font-size: 13px;
  color: #374151;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.empty {
  color: #9ca3af;
  font-size: 13px;
}
.pre {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-x: auto;
}
</style>
