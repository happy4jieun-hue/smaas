<script setup lang="ts">
import type { ValidationResult } from "../types";
defineProps<{ data: ValidationResult }>();
</script>

<template>
  <div :class="['section', data.valid ? 'valid' : 'invalid']">
    <h3 class="section-title">검증 결과 (Validator)</h3>
    <div class="result-row">
      <span :class="['badge', data.valid ? 'pass' : 'fail']">
        {{ data.valid ? "✓ 통과" : "✗ 실패" }}
      </span>
      <span v-if="data.retryFromAgent" class="retry-info">
        재시도: {{ data.retryFromAgent }} 부터
      </span>
    </div>
    <ul v-if="data.issues.length > 0" class="issues">
      <li v-for="(issue, i) in data.issues" :key="i" class="issue">{{ issue }}</li>
    </ul>
    <p v-else class="no-issues">이슈 없음</p>
  </div>
</template>

<style scoped>
.section { border-radius: 10px; padding: 16px 20px; border: 1px solid; }
.section.valid { background: #f0fdf4; border-color: #bbf7d0; }
.section.invalid { background: #fff5f5; border-color: #fecaca; }
.section-title { font-size: 14px; font-weight: 700; color: #1e40af; margin: 0 0 12px; }
.result-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.badge { padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 700; }
.badge.pass { background: #dcfce7; color: #166534; }
.badge.fail { background: #fee2e2; color: #991b1b; }
.retry-info { font-size: 12px; color: #6b7280; }
.issues { margin: 0; padding-left: 18px; }
.issue { font-size: 13px; color: #7f1d1d; margin-bottom: 4px; line-height: 1.5; }
.no-issues { font-size: 13px; color: #16a34a; margin: 0; }
</style>
