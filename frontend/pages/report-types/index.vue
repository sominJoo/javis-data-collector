<script setup lang="ts">
import type { ReportType } from "~/types";

const api = useApi();
const crumb = useCrumb();
crumb.value = "보고서 유형 관리";

const rows = ref<ReportType[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    rows.value = await api.listReportTypes();
  } finally {
    loading.value = false;
  }
}

function fmtDate(iso: string): string {
  return iso.slice(0, 10);
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="head">
      <h3>보고서 유형 관리</h3>
      <span class="count">{{ rows.length }}건</span>
      <button class="gx-btn btn-primary" @click="navigateTo('/report-types/new')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
          <path d="M12 5v14M5 12h14" />
        </svg>
        신규 등록
      </button>
    </div>

    <div class="table">
      <div class="thead">
        <div>Code</div>
        <div>이름</div>
        <div>설명</div>
        <div>수정일</div>
        <div>상태</div>
        <div></div>
      </div>
      <div
        v-for="t in rows"
        :key="t.code"
        class="gx-row trow"
        @click="navigateTo(`/report-types/${t.code}`)"
      >
        <div class="code-cell"><span class="code">{{ t.code }}</span></div>
        <div class="name">{{ t.name }}</div>
        <div class="desc">{{ t.description }}</div>
        <div class="mono">{{ fmtDate(t.updatedAt) }}</div>
        <div>
          <span class="state" :class="t.active ? 'on' : 'off'">
            {{ t.active ? "활성" : "비활성" }}
          </span>
        </div>
        <div class="chev">›</div>
      </div>
      <div v-if="loading" class="state-row">불러오는 중...</div>
      <div v-else-if="rows.length === 0" class="state-row">등록된 보고서 유형이 없습니다.</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.page {
  padding: 26px 28px;
  animation: gxfade 0.3s ease;
}
.head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
h3 {
  font-size: 22px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.02em;
  white-space: nowrap;
}
.count {
  font-size: 13px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 3px 10px;
  border-radius: 999px;
}
.btn-primary {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 7px;
  height: 40px;
  padding: 0 17px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  box-shadow: 0 10px 22px -10px rgba(160, 60, 150, 0.6);
}
.table {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
}
.thead,
.trow {
  display: grid;
  grid-template-columns: 120px 160px 1fr 118px 90px 40px;
  align-items: center;
  padding: 0 20px;
}
.thead {
  height: 44px;
  background: var(--panel2);
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  font-weight: 700;
  color: var(--tx3);
}
.trow {
  height: 58px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s;
}
.code-cell {
  min-width: 0;
  padding-right: 12px;
}
.code {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
  font-family: ui-monospace, monospace;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 3px 8px;
  border-radius: 6px;
}
.name {
  font-weight: 600;
}
.desc {
  color: var(--tx2);
  font-size: 12.5px;
  padding-right: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: var(--tx2);
}
.state {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 6px;
  &.on {
    background: var(--grn-bg);
    color: var(--grn);
  }
  &.off {
    background: var(--field);
    color: var(--tx3);
  }
}
.chev {
  color: var(--tx3);
  font-size: 18px;
  text-align: center;
}
.state-row {
  padding: 50px;
  text-align: center;
  color: var(--tx3);
  font-size: 14px;
}
</style>
