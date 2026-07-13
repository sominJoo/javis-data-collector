<script setup lang="ts">
import type { AnalysisResult, RawDataDetail } from "~/types";

const route = useRoute();
const api = useApi();
const crumb = useCrumb();
const confirm = useConfirm();
const toast = useToast();
crumb.value = "원본 데이터 · 상세";

const id = route.params.id as string;
const detail = ref<RawDataDetail | null>(null);
const loading = ref(true);
const reanalyzing = ref(false);

const viewOpen = ref(false);
const viewItem = ref<AnalysisResult | null>(null);

async function load() {
  loading.value = true;
  try {
    detail.value = await api.getRawData(id);
  } catch {
    detail.value = null;
  } finally {
    loading.value = false;
  }
}

async function reanalyze() {
  const ok = await confirm({
    title: "데이터 재분석",
    message: "현재 데이터를 다시 분석하시겠습니까? 원본은 유지되고 AI 분석 결과만 재생성됩니다.",
    okText: "재분석",
    danger: false,
  });
  if (!ok) return;
  reanalyzing.value = true;
  try {
    await api.reanalyze(id);
    await load();
    toast("데이터 재분석이 완료되었습니다.");
  } finally {
    reanalyzing.value = false;
  }
}

function viewFull(item: AnalysisResult) {
  viewItem.value = item;
  viewOpen.value = true;
}

function fmtDate(iso: string): string {
  return iso.slice(0, 10);
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div v-if="loading" class="state">불러오는 중...</div>
    <div v-else-if="!detail" class="state">데이터를 찾을 수 없습니다.</div>

    <template v-else>
      <!-- 헤더 카드 -->
      <div class="head-card">
        <div class="head-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" />
          </svg>
        </div>
        <div class="head-body">
          <div class="head-tags">
            <span class="type-tag">{{ detail.reportTypeName }}</span>
            <StatusBadge :status="detail.status" />
          </div>
          <h3 class="head-title">{{ detail.title }}</h3>
          <div class="head-file">{{ detail.fileName }}</div>
        </div>
        <div class="head-meta">
          <div><div class="meta-label">등록일</div><div class="meta-val">{{ fmtDate(detail.createdAt) }}</div></div>
          <div><div class="meta-label">Chunk</div><div class="meta-val">{{ detail.chunkCount }}</div></div>
        </div>
        <div class="head-actions">
          <button class="gx-btn btn-ghost" :disabled="reanalyzing" @click="reanalyze">
            <span class="spin" :class="{ spinning: reanalyzing }">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 4v6h-6M1 20v-6h6" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
            </span>
            재분석
          </button>
          <button class="gx-btn btn-ghost" @click="navigateTo('/')">목록</button>
        </div>
      </div>

      <!-- 재분석 배너 -->
      <div v-if="reanalyzing" class="rebanner">
        <span class="spin spinning">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--pri)" stroke-width="2.4">
            <path d="M21 12a9 9 0 1 1-6.2-8.5" />
          </svg>
        </span>
        <span class="reb-text">재분석 중 · AI 분석 결과를 재생성하고 있습니다</span>
      </div>

      <!-- Summary + Chunk -->
      <div class="grid">
        <div class="card">
          <div class="card-title">Summary</div>
          <p class="summary">{{ detail.summary || "요약이 아직 생성되지 않았습니다." }}</p>
        </div>
        <div class="card">
          <div class="card-title">Chunk <span class="chunk-count">{{ detail.chunks.length }}</span></div>
          <div v-if="detail.chunks.length" class="chunk-list">
            <div v-for="c in detail.chunks" :key="c.order" class="chunk-item">
              <span class="chunk-order">#{{ c.order }}</span>
              <span class="chunk-text">{{ c.text }}</span>
            </div>
          </div>
          <div v-else class="empty-inline">생성된 Chunk가 없습니다.</div>
        </div>
      </div>

      <!-- AI 분석 결과 -->
      <div class="card">
        <div class="card-head">
          <span class="card-title">AI 분석 결과</span>
          <span class="card-sub">Skill로 생성된 텍스트</span>
        </div>
        <div v-if="detail.results.length" class="result-list">
          <div v-for="a in detail.results" :key="a.type" class="result-item">
            <div class="ri-body">
              <div class="ri-title">{{ a.title }}</div>
              <div class="ri-preview">{{ a.preview }}</div>
            </div>
            <button class="gx-btn ri-view" @click="viewFull(a)">전문 보기</button>
          </div>
        </div>
        <div v-else class="empty-inline">분석 결과가 아직 없습니다.</div>
      </div>
    </template>

    <AppModal v-model:open="viewOpen" :title="viewItem?.title">
      <p class="full-text">{{ viewItem?.content }}</p>
    </AppModal>
  </div>
</template>

<style scoped lang="scss">
.page {
  padding: 24px 28px;
  animation: gxfade 0.3s ease;
}
.state {
  padding: 60px;
  text-align: center;
  color: var(--tx3);
  font-size: 14px;
}

.head-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 20px;
}
.head-icon {
  width: 50px;
  height: 50px;
  border-radius: 13px;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.head-body {
  min-width: 0;
  flex: 1;
}
.head-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}
.type-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--sel);
  color: var(--pri);
}
.head-title {
  font-size: 19px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.head-file {
  font-size: 12px;
  color: var(--tx3);
  font-family: ui-monospace, monospace;
  margin-top: 4px;
}
.head-meta {
  display: flex;
  gap: 26px;
  flex: 0 0 auto;
}
.meta-label {
  font-size: 11px;
  color: var(--tx3);
  margin-bottom: 3px;
}
.meta-val {
  font-size: 13px;
  font-weight: 700;
  font-family: ui-monospace, monospace;
}
.head-actions {
  display: flex;
  gap: 10px;
  flex: 0 0 auto;
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
  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}
.spin {
  display: inline-flex;
  &.spinning {
    animation: gxspin 0.8s linear infinite;
  }
}

.rebanner {
  background: var(--sel);
  border: 1px solid var(--pri);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.reb-text {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--pri);
}

.grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px 20px;
}
.card-head {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.card-title {
  font-size: 12.5px;
  font-weight: 800;
  margin-bottom: 12px;
  display: inline-block;
}
.card-sub {
  margin-left: auto;
  font-size: 11px;
  color: var(--tx3);
}
.chunk-count {
  font-size: 11px;
  color: var(--pri);
  background: var(--sel);
  padding: 1px 7px;
  border-radius: 999px;
  margin-left: 4px;
}
.summary {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--tx2);
  margin: 0;
}
.chunk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chunk-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 9px;
  background: var(--panel2);
  font-size: 12px;
}
.chunk-order {
  font-family: ui-monospace, monospace;
  font-weight: 700;
  color: var(--pri);
  flex: 0 0 auto;
}
.chunk-text {
  min-width: 0;
  color: var(--tx2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty-inline {
  font-size: 12.5px;
  color: var(--tx3);
  padding: 8px 0;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 13px;
  border-radius: 10px;
  border: 1px solid var(--line);
}
.ri-body {
  flex: 1;
  min-width: 0;
}
.ri-title {
  font-size: 12.5px;
  font-weight: 700;
  margin-bottom: 3px;
}
.ri-preview {
  font-size: 11.5px;
  color: var(--tx3);
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ri-view {
  flex: 0 0 auto;
  height: 28px;
  padding: 0 12px;
  border-radius: 7px;
  border: 1px solid var(--pri);
  background: var(--panel);
  color: var(--pri);
  font-size: 11.5px;
  font-weight: 700;
}
.full-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--tx2);
  margin: 0;
  white-space: pre-wrap;
}
</style>
