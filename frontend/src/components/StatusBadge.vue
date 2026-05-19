<script setup lang="ts">
const props = defineProps<{ status: string }>();

const COLOR: Record<string, { bg: string; text: string }> = {
  pending:    { bg: "#f3f4f6", text: "#6b7280" },
  running:    { bg: "#dbeafe", text: "#1d4ed8" },
  analyzing:  { bg: "#dbeafe", text: "#1d4ed8" },
  planning:   { bg: "#dbeafe", text: "#1d4ed8" },
  matching:   { bg: "#dbeafe", text: "#1d4ed8" },
  validating: { bg: "#dbeafe", text: "#1d4ed8" },
  saving:     { bg: "#dbeafe", text: "#1d4ed8" },
  notifying:  { bg: "#dbeafe", text: "#1d4ed8" },
  completed:  { bg: "#d1fae5", text: "#065f46" },
  failed:     { bg: "#fee2e2", text: "#991b1b" },
};

const color = COLOR[props.status] ?? { bg: "#f3f4f6", text: "#6b7280" };
</script>

<template>
  <span
    :style="{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: '12px',
      fontSize: '13px',
      fontWeight: 600,
      background: color.bg,
      color: color.text,
    }"
  >
    {{ status }}
  </span>
</template>
