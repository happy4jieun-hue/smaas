<script setup lang="ts">
interface AgentError { agentName: string; message: string; timestamp: string; }
defineProps<{ errors: AgentError[] }>();
</script>

<template>
  <div class="section">
    <h3 class="section-title">에러 로그</h3>
    <div v-for="(e, i) in errors" :key="i" class="error-item">
      <div class="error-top">
        <span class="agent-name">{{ e.agentName }}</span>
        <span class="ts">{{ new Date(e.timestamp).toLocaleString("ko-KR") }}</span>
      </div>
      <p class="message">{{ e.message }}</p>
    </div>
  </div>
</template>

<style scoped>
.section { background: #fff5f5; border: 1px solid #fecaca; border-radius: 10px; padding: 16px 20px; }
.section-title { font-size: 14px; font-weight: 700; color: #991b1b; margin: 0 0 12px; }
.error-item { background: #fff; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
.error-item:last-child { margin-bottom: 0; }
.error-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.agent-name { font-size: 12px; font-weight: 700; color: #991b1b; background: #fee2e2; padding: 2px 8px; border-radius: 4px; }
.ts { font-size: 11px; color: #9ca3af; }
.message { font-size: 13px; color: #7f1d1d; margin: 0; line-height: 1.5; }
</style>
