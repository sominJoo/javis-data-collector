<script setup lang="ts">
import type { RawData, ReportType } from "~/types";

const api = useApi();
const crumb = useCrumb();
const confirm = useConfirm();
const toast = useToast();
crumb.value = "원본 데이터";

const rows = ref<RawData[]>([]);
const total = ref(0); // 현재 필터·검색 조건의 전체 건수(API 제공)
const reportTypes = ref<ReportType[]>([]);
const query = ref("");
const typeCode = ref(""); // 보고서 유형 필터("" = 전체)
const loading = ref(false);
const refreshing = ref(false);

async function load() {
  loading.value = true;
  try {
    const res = await api.listRawData(query.value, typeCode.value);
    rows.value = res.items;
    total.value = res.total;
  } finally {
    loading.value = false;
  }
}

// 유형 필터 목록은 최초 1회만 조회한다(자주 변하지 않음).
async function loadReportTypes() {
  try {
    reportTypes.value = await api.listReportTypes();
  } catch {
    reportTypes.value = [];
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    await load();
  } finally {
    refreshing.value = false;
  }
}

let searchTimer: ReturnType<typeof setTimeout>;
watch(query, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 250);
});
watch(typeCode, load); // 유형 선택 즉시 재조회

async function removeRow(id: string) {
  const ok = await confirm({
    title: "데이터 삭제",
    message: "선택한 데이터를 삭제하시겠습니까? 원본과 AI 분석 결과가 함께 삭제됩니다.",
    okText: "삭제",
  });
  if (!ok) return;
  await api.deleteRawData(id);
  await load();
  toast("데이터가 삭제되었습니다.");
}

function open(id: string) {
  navigateTo(`/data/${id}`);
}

const empty = computed(() => !loading.value && rows.value.length === 0);

function fmtDate(iso: string): string {
  return iso.slice(0, 10);
}

onMounted(() => {
  loadReportTypes();
  load();
});
</script>

<template>
  <div class="page">
    <!-- 헤더 -->
    <div class="head">
      <h3>원본 데이터</h3>
      <span class="count">{{ total }}건</span>
      <div class="actions">
        <div class="filter">
          <select v-model="typeCode" aria-label="보고서 유형 필터">
            <option value="">전체 유형</option>
            <option v-for="t in reportTypes" :key="t.code" :value="t.code">{{ t.name }}</option>
          </select>
          <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9c99ab" stroke-width="2">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
        <div class="search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9c99ab" stroke-width="2">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input v-model="query" placeholder="제목·파일명 검색" />
        </div>
        <button class="gx-btn btn-ghost" @click="refresh">
          <span class="spin" :class="{ spinning: refreshing }">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </span>
          새로고침
        </button>
        <button class="gx-btn btn-primary" @click="navigateTo('/data/add')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
            <path d="M12 5v14M5 12h14" />
          </svg>
          데이터 추가
        </button>
      </div>
    </div>

    <!-- 테이블 -->
    <div class="table">
      <div class="thead">
        <div>상태</div>
        <div>제목 · 파일명</div>
        <div>보고서 유형</div>
        <div class="r">Chunk</div>
        <div class="pl">등록일</div>
        <div></div>
      </div>

      <div v-for="r in rows" :key="r.id" class="gx-row trow" @click="open(r.id)">
        <div><StatusBadge :status="r.status" /></div>
        <div class="title-cell">
          <div class="title">{{ r.title }}</div>
          <div class="file">{{ r.fileName }}</div>
        </div>
        <div><span class="type-tag">{{ r.reportTypeName }}</span></div>
        <div class="r mono">{{ r.chunkCount }}</div>
        <div class="pl mono date">{{ fmtDate(r.createdAt) }}</div>
        <div class="del" title="삭제" @click.stop="removeRow(r.id)">✕</div>
      </div>

      <div v-if="loading" class="state">불러오는 중...</div>
      <div v-else-if="empty" class="state">검색 결과가 없습니다.</div>
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
  margin-bottom: 16px;
}
h3 {
  font-size: 22px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.02em;
  white-space: nowrap;
  flex-shrink: 0;
}
.count {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 3px 10px;
  border-radius: 999px;
}
.actions {
  margin-left: auto;
  display: flex;
  gap: 10px;
}
.filter {
  position: relative;
  display: flex;
  align-items: center;
  select {
    appearance: none;
    height: 40px;
    padding: 0 34px 0 14px;
    border-radius: 10px;
    background: var(--panel);
    border: 1px solid var(--line2);
    color: var(--tx);
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    outline: none;
    max-width: 200px;
  }
  .chev {
    position: absolute;
    right: 12px;
    pointer-events: none;
  }
}
.search {
  display: flex;
  align-items: center;
  gap: 9px;
  height: 40px;
  padding: 0 14px;
  border-radius: 10px;
  background: var(--panel);
  border: 1px solid var(--line2);
  width: 220px;
  input {
    border: none;
    outline: none;
    background: transparent;
    font-size: 12.5px;
    color: var(--tx);
    flex: 1;
    width: 100%;
  }
}
.btn-ghost {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 40px;
  padding: 0 15px;
  border-radius: 10px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 13.5px;
  font-weight: 600;
}
.btn-primary {
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
.spin {
  display: inline-flex;
  &.spinning {
    animation: gxspin 0.8s linear infinite;
  }
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
  grid-template-columns: 110px 1fr 140px 90px 130px 48px;
  align-items: center;
  padding: 0 18px;
}
.thead {
  height: 42px;
  background: var(--panel2);
  border-bottom: 1px solid var(--line);
  font-size: 12px;
  font-weight: 700;
  color: var(--tx3);
}
.trow {
  height: 56px;
  border-bottom: 1px solid var(--line);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.12s;
}
.r {
  text-align: right;
}
.pl {
  padding-left: 14px;
}
.title-cell {
  min-width: 0;
  padding-right: 14px;
}
.title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file {
  font-size: 11.5px;
  color: var(--tx3);
  font-family: ui-monospace, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.type-tag {
  font-size: 11.5px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 6px;
  background: var(--sel);
  color: var(--pri);
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12.5px;
  color: var(--tx2);
}
.date {
  font-size: 12px;
}
.del {
  text-align: center;
  color: var(--tx3);
  cursor: pointer;
  font-size: 15px;
}
.state {
  padding: 60px;
  text-align: center;
  color: var(--tx3);
  font-size: 14px;
}
</style>
