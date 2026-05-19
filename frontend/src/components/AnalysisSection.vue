<script setup lang="ts">
import type { AnalysisResult } from "../types";
defineProps<{ data: AnalysisResult }>();
</script>

<template>
  <div class="section">
    <h3 class="section-title">분석 결과 (Analyzer)</h3>
    <div class="grid">
      <div class="field">
        <span class="label">카테고리</span>
        <span class="value">{{ data.category }}</span>
      </div>
      <div class="field">
        <span class="label">복잡도</span>
        <span class="stars">
          <span v-for="i in 5" :key="i" :class="['star', i <= data.complexity ? 'filled' : '']">★</span>
        </span>
      </div>
      <div class="field">
        <span class="label">예상 시간</span>
        <span class="value">{{ data.estimatedHours }}h</span>
      </div>
    </div>
    <div class="field" style="margin-top: 10px;">
      <span class="label">요약</span>
      <p class="summary">{{ data.summary }}</p>
    </div>
    <div class="field">
      <span class="label">필요 스킬</span>
      <div class="tags">
        <span v-for="s in data.requiredSkills" :key="s" class="tag skill">{{ s }}</span>
      </div>
    </div>
    <div class="field">
      <span class="label">키워드</span>
      <div class="tags">
        <span v-for="k in data.keywords" :key="k" class="tag keyword">{{ k }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; }
.section-title { font-size: 14px; font-weight: 700; color: #1e40af; margin: 0 0 14px; }
.grid { display: flex; gap: 24px; flex-wrap: wrap; }
.field { display: flex; flex-direction: column; gap: 4px; }
.label { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }
.value { font-size: 14px; color: #111827; font-weight: 500; }
.summary { font-size: 13px; color: #374151; margin: 4px 0 0; line-height: 1.6; }
.stars { display: flex; gap: 2px; margin-top: 2px; }
.star { font-size: 16px; color: #d1d5db; }
.star.filled { color: #f59e0b; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.tag { padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; }
.skill { background: #dbeafe; color: #1e40af; }
.keyword { background: #f3f4f6; color: #374151; }
</style>
