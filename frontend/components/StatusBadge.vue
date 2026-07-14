<script setup lang="ts">
import type { JobStatus } from "~/types";

const props = defineProps<{ status: JobStatus }>();

// 상태별 라벨/색상 매핑.
const meta = computed(() => {
  const map: Record<JobStatus, { label: string; dot: string; bg: string; tx: string }> = {
    SUCCESS: { label: "완료", dot: "var(--grn)", bg: "var(--grn-bg)", tx: "var(--grn)" },
    RUNNING: { label: "분석중", dot: "var(--amb)", bg: "var(--amb-bg)", tx: "var(--amb)" },
    WAITING: { label: "대기", dot: "var(--blu)", bg: "var(--blu-bg)", tx: "var(--blu)" },
    FAILED: { label: "실패", dot: "var(--red)", bg: "var(--red-bg)", tx: "var(--red)" },
  };
  return map[props.status];
});
</script>

<template>
  <span class="badge" :style="{ background: meta.bg, color: meta.tx }">
    <span class="dot" :style="{ background: meta.dot }" />
    {{ meta.label }}
  </span>
</template>

<style scoped lang="scss">
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
</style>
