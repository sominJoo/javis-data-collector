<script setup lang="ts">
import type { AnalysisResult, FileReview, ReportType, UploadedFile } from "~/types";
import { PIPELINE_STAGES } from "~/types";

const api = useApi();
const crumb = useCrumb();
crumb.value = "원본 데이터 · 데이터 추가";

type Step = 1 | 2 | 3;
const step = ref<Step>(1);

// --- Step 1 상태 ---
const reportTypes = ref<ReportType[]>([]);
const selectedType = ref<string>("");
const files = ref<UploadedFile[]>([]);
const chunkCount = ref(700);
const fileInput = ref<HTMLInputElement | null>(null);

const canStart = computed(() => selectedType.value !== "" && files.value.length > 0);

function pickFiles() {
  fileInput.value?.click();
}
function onFilesChosen(e: Event) {
  const input = e.target as HTMLInputElement;
  for (const f of Array.from(input.files ?? [])) {
    files.value.push({
      id: `f-${Date.now()}-${files.value.length}`,
      name: f.name,
      size: `${(f.size / 1024).toFixed(1)} KB`,
    });
  }
  input.value = "";
}
function addDemoFile() {
  const n = files.value.length + 1;
  files.value.push({ id: `f-demo-${n}`, name: `sample_document_${n}.pdf`, size: "248.0 KB" });
}
function removeFile(id: string) {
  files.value = files.value.filter((f) => f.id !== id);
}
function chunkMinus() {
  if (chunkCount.value > 1) chunkCount.value--;
}
function chunkPlus() {
  chunkCount.value++;
}
// 키보드 입력 처리: 숫자만 허용하고 1 미만은 1로 보정
function onChunkInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.replace(/[^\d]/g, "");
  const n = Number.parseInt(raw, 10);
  chunkCount.value = Number.isNaN(n) || n < 1 ? 1 : n;
}

// --- Step 2 (파이프라인) ---
// 파일 1개 = 원본 데이터 1건이므로, 업로드된 파일을 순차적으로 각각 분석한다.
const stages = PIPELINE_STAGES;
const currentFileIdx = ref(0); // 현재 분석 중인 파일 인덱스
const currentStage = ref(0); // 현재 파일의 진행 중 단계 인덱스
let jobId = "";
let timer: ReturnType<typeof setInterval> | undefined;

async function startPipeline() {
  if (!canStart.value) return;
  const res = await api.registerData({
    reportTypeCode: selectedType.value,
    files: files.value,
    chunkCount: chunkCount.value,
  });
  jobId = res.jobId;
  step.value = 2;
  currentFileIdx.value = 0;
  currentStage.value = 0;
  timer = setInterval(() => {
    currentStage.value++;
    if (currentStage.value >= stages.length) {
      // 현재 파일 완료 → 다음 파일로 이동, 마지막 파일이면 검토 단계로
      if (currentFileIdx.value >= files.value.length - 1) {
        clearInterval(timer);
        void goReview();
      } else {
        currentFileIdx.value++;
        currentStage.value = 0;
      }
    }
  }, 700);
}

// 파일별 상태: 이미 처리된 파일은 done, 현재 파일은 active, 나머지는 todo
function fileState(fi: number): "done" | "active" | "todo" {
  if (fi < currentFileIdx.value) return "done";
  if (fi === currentFileIdx.value) return "active";
  return "todo";
}

// 현재 처리 중인 파일 내부의 단계 상태
function stageState(i: number): "done" | "active" | "todo" {
  if (i < currentStage.value) return "done";
  if (i === currentStage.value) return "active";
  return "todo";
}

const pipeProgress = computed(
  () => `파일 ${Math.min(currentFileIdx.value + 1, files.value.length)} / ${files.value.length}`,
);

// --- Step 3 (검토·저장) ---
const fileReviews = ref<FileReview[]>([]);
const activeFileIdx = ref(0);
const saving = ref(false);
const viewOpen = ref(false);
const viewItem = ref<AnalysisResult | null>(null);

const activeReview = computed(() => fileReviews.value[activeFileIdx.value] ?? null);

async function goReview() {
  fileReviews.value = await api.getReview(jobId, files.value);
  activeFileIdx.value = 0;
  step.value = 3;
}
function viewFull(item: AnalysisResult) {
  viewItem.value = item;
  viewOpen.value = true;
}
async function save() {
  saving.value = true;
  try {
    await api.saveData(jobId, {
      reportTypeCode: selectedType.value,
      files: files.value,
      chunkCount: chunkCount.value,
    });
    await navigateTo("/");
  } finally {
    saving.value = false;
  }
}

const selectedTypeObj = computed(() =>
  reportTypes.value.find((t) => t.code === selectedType.value),
);

onMounted(async () => {
  reportTypes.value = await api.listReportTypes();
});
onBeforeUnmount(() => timer && clearInterval(timer));
</script>

<template>
  <div class="page">
    <!-- 스텝 인디케이터 -->
    <div class="stepper">
      <div class="step-item" :class="{ on: step >= 1 }">
        <span class="num">{{ step > 1 ? "✓" : "1" }}</span>
        <span class="lbl">보고서 유형</span>
      </div>
      <div class="bar" :class="{ on: step >= 2 }" />
      <div class="step-item" :class="{ on: step >= 2 }">
        <span class="num">{{ step > 2 ? "✓" : "2" }}</span>
        <span class="lbl">업로드 · 분석</span>
      </div>
      <div class="bar" :class="{ on: step >= 3 }" />
      <div class="step-item" :class="{ on: step >= 3 }">
        <span class="num">3</span>
        <span class="lbl">검토 · 저장</span>
      </div>
    </div>

    <!-- STEP 1 -->
    <div v-if="step === 1" class="step1">
      <div class="col-main">
        <div class="card">
          <div class="card-head">
            <span class="card-title">① 보고서 유형 선택</span>
            <NuxtLink to="/report-types" class="link">+ 신규 등록</NuxtLink>
          </div>
          <div class="type-list">
            <div
              v-for="t in reportTypes"
              :key="t.code"
              class="gx-btn type-item"
              :class="{ sel: selectedType === t.code }"
              @click="selectedType = t.code"
            >
              <span class="radio" :class="{ on: selectedType === t.code }" />
              <div>
                <div class="type-top">
                  <span class="type-code">{{ t.code }}</span>
                  <span class="type-name">{{ t.name }}</span>
                </div>
                <div class="type-desc">{{ t.description }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-side">
        <div class="card">
          <div class="card-title mb">② 파일 업로드</div>
          <input ref="fileInput" type="file" multiple hidden @change="onFilesChosen" />
          <div class="dropzone gx-btn" @click="pickFiles">
            <div class="dz-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a94fa0" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
            </div>
            <div class="dz-title">클릭하여 파일 추가</div>
            <div class="dz-sub">PDF · DOCX · HWP · XLSX · 여러 개 가능</div>
          </div>
          <button class="gx-btn demo-add" @click="addDemoFile">데모 파일 추가</button>
          <div class="file-list">
            <div v-for="f in files" :key="f.id" class="file-item">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#cf5151" stroke-width="1.8">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" />
              </svg>
              <div class="file-meta">
                <div class="file-name">{{ f.name }}</div>
                <div class="file-size">{{ f.size }}</div>
              </div>
              <span class="file-x" @click="removeFile(f.id)">×</span>
            </div>
            <div v-if="files.length === 0" class="no-files">아직 추가된 파일이 없습니다.</div>
          </div>
        </div>

        <div class="card chunk-card">
          <div>
            <div class="card-title">Chunk 수</div>
            <div class="chunk-hint">1 이상 입력</div>
          </div>
          <div class="chunk-stepper">
            <span class="cs-btn" @click="chunkMinus">−</span>
            <input
              class="cs-val"
              type="text"
              inputmode="numeric"
              :value="chunkCount"
              @input="onChunkInput"
            />
            <span class="cs-btn" @click="chunkPlus">+</span>
          </div>
        </div>

        <div class="actions">
          <button class="gx-btn btn-ghost" @click="navigateTo('/')">취소</button>
          <button class="gx-btn btn-primary" :disabled="!canStart" @click="startPipeline">
            등록 및 분석 시작
          </button>
        </div>
      </div>
    </div>

    <!-- STEP 2 : 파이프라인 -->
    <div v-else-if="step === 2" class="step2">
      <div class="card side-summary">
        <div class="type-top">
          <span class="type-code">{{ selectedTypeObj?.code }}</span>
          <span class="type-name">{{ selectedTypeObj?.name }}</span>
        </div>
        <div class="sub-label">선택한 보고서 유형</div>
        <div class="file-list">
          <div v-for="f in files" :key="f.id" class="file-item compact">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#cf5151" stroke-width="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" />
            </svg>
            <div class="file-name">{{ f.name }}</div>
          </div>
        </div>
        <div class="chunk-info">
          <span>Chunk 수</span>
          <span class="chunk-info-val">{{ chunkCount }}</span>
        </div>
      </div>

      <div class="card pipe">
        <div class="pipe-head">
          <span class="pipe-dot" />
          <span class="pipe-title">AI 분석 진행 중</span>
          <span class="pipe-progress">{{ pipeProgress }}</span>
        </div>
        <div class="pipe-sub">파일별로 순차 분석합니다. 파일 1개당 원본 데이터 1건으로 저장됩니다.</div>

        <!-- 파일별 분석 -->
        <div class="file-pipes">
          <div
            v-for="(f, fi) in files"
            :key="f.id"
            class="file-pipe"
            :class="fileState(fi)"
          >
            <div class="fp-head">
              <span class="fp-icon" :class="fileState(fi)">
                <template v-if="fileState(fi) === 'done'">✓</template>
                <template v-else>{{ fi + 1 }}</template>
              </span>
              <span class="fp-name">{{ f.name }}</span>
              <span class="fp-status" :class="fileState(fi)">
                {{ fileState(fi) === "done" ? "분석 완료" : fileState(fi) === "active" ? "분석 중" : "대기" }}
              </span>
            </div>

            <!-- 현재 분석 중인 파일만 단계를 펼쳐서 표시 -->
            <div v-if="fileState(fi) === 'active'" class="pipe-steps">
              <div
                v-for="(s, i) in stages"
                :key="s.key"
                class="pipe-step"
                :class="stageState(i)"
              >
                <span class="ps-icon">
                  <template v-if="stageState(i) === 'done'">✓</template>
                  <template v-else>{{ i + 1 }}</template>
                </span>
                <div class="ps-body">
                  <div class="ps-label">{{ s.label }}</div>
                  <div v-if="stageState(i) === 'active'" class="ps-bar"><div class="ps-fill" /></div>
                </div>
                <span class="ps-status">
                  {{ stageState(i) === "done" ? "완료" : stageState(i) === "active" ? "처리 중" : "대기" }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- STEP 3 : 검토·저장 -->
    <div v-else class="step3 card">
      <div class="review-head">
        <span class="check">✓</span>
        <span class="card-title">분석 완료 · 추출 결과 검토</span>
        <span class="review-hint">파일별 Skill 추출 결과를 확인하세요. 파일 1개당 원본 데이터 1건으로 저장됩니다.</span>
      </div>
      <div class="review-note">
        아직 저장되지 않았습니다. 검토 후 <b>저장</b>을 눌러야 데이터가 등록됩니다.
        <span class="review-count">총 {{ fileReviews.length }}개 파일</span>
      </div>

      <!-- 파일별 탭 -->
      <div class="file-tabs">
        <button
          v-for="(fr, i) in fileReviews"
          :key="fr.fileId"
          class="gx-btn file-tab"
          :class="{ active: i === activeFileIdx }"
          @click="activeFileIdx = i"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" />
          </svg>
          <span class="file-tab-name">{{ fr.fileName }}</span>
        </button>
      </div>

      <!-- 선택한 파일의 Skill 결과 -->
      <div v-if="activeReview" class="review-grid">
        <div v-for="a in activeReview.results" :key="a.type" class="review-item">
          <div class="ri-body">
            <div class="ri-top">
              <span class="ri-title">{{ a.title }}</span>
              <span class="ri-tag">{{ a.type }}</span>
            </div>
            <div class="ri-preview">{{ a.preview }}</div>
          </div>
          <button class="gx-btn ri-view" @click="viewFull(a)">전문 보기</button>
        </div>
      </div>

      <div class="review-actions">
        <button class="gx-btn btn-ghost" @click="navigateTo('/')">취소</button>
        <button class="gx-btn btn-primary" :disabled="saving" @click="save">
          {{ saving ? "저장 중..." : `저장 (${fileReviews.length}건)` }}
        </button>
      </div>
    </div>

    <AppModal v-model:open="viewOpen" :title="viewItem?.title">
      <p class="full-text">{{ viewItem?.content }}</p>
    </AppModal>
  </div>
</template>

<style scoped lang="scss">
.page {
  padding: 26px 40px;
  animation: gxfade 0.3s ease;
}

/* stepper */
.stepper {
  display: flex;
  align-items: center;
  margin: 0 auto 24px;
  max-width: 660px;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 9px;
  .num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--field);
    color: var(--tx3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
  }
  .lbl {
    font-size: 13.5px;
    font-weight: 700;
    color: var(--tx3);
  }
  &.on .num {
    background: linear-gradient(135deg, #7c4da0, #c05cab);
    color: #fff;
  }
  &.on .lbl {
    color: var(--tx);
  }
}
.bar {
  flex: 1;
  height: 2px;
  background: var(--line2);
  margin: 0 12px;
  &.on {
    background: var(--pri);
  }
}

/* card 공통 */
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px;
}
.card-head {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}
.card-title {
  font-size: 14px;
  font-weight: 800;
  &.mb {
    display: block;
    margin-bottom: 14px;
  }
}
.link {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  color: var(--pri);
  text-decoration: none;
  cursor: pointer;
}

/* step1 layout */
.step1 {
  display: flex;
  gap: 22px;
}
.col-main {
  flex: 1;
  min-width: 0;
}
.col-side {
  flex: 0 0 440px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.type-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.type-item {
  display: flex;
  gap: 12px;
  padding: 13px 14px;
  border-radius: 11px;
  border: 1px solid var(--line);
  background: var(--panel);
  &.sel {
    border-color: var(--pri);
    background: var(--sel);
  }
}
.radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--line2);
  flex: 0 0 auto;
  margin-top: 2px;
  &.on {
    border-color: var(--pri);
    background: radial-gradient(circle, var(--pri) 40%, transparent 45%);
  }
}
.type-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.type-code {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 2px 7px;
  border-radius: 5px;
}
.type-name {
  font-size: 13.5px;
  font-weight: 700;
}
.type-desc {
  font-size: 12px;
  color: var(--tx2);
  margin-top: 4px;
  line-height: 1.5;
}

/* upload */
.dropzone {
  border: 2px dashed var(--line2);
  border-radius: 12px;
  padding: 26px 20px;
  text-align: center;
  background: var(--panel2);
  margin-bottom: 12px;
}
.dz-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--sel);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
}
.dz-title {
  font-size: 13.5px;
  font-weight: 700;
  margin-bottom: 4px;
}
.dz-sub {
  font-size: 12px;
  color: var(--tx3);
}
.demo-add {
  width: 100%;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx2);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 14px;
}
.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  &.compact {
    padding: 8px 10px;
  }
}
.file-meta {
  flex: 1;
  min-width: 0;
}
.file-name {
  flex: 1;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-size {
  font-size: 11px;
  color: var(--tx3);
}
.file-x {
  color: var(--tx3);
  cursor: pointer;
  font-size: 15px;
}
.no-files {
  font-size: 12px;
  color: var(--tx3);
  text-align: center;
  padding: 6px;
}

/* chunk */
.chunk-card {
  display: flex;
  align-items: center;
  gap: 12px;
}
.chunk-hint {
  font-size: 11.5px;
  color: var(--tx3);
  margin-top: 2px;
}
.chunk-stepper {
  margin-left: auto;
  display: flex;
  align-items: center;
  height: 40px;
  border-radius: 10px;
  border: 1px solid var(--fieldline);
  background: var(--field);
  overflow: hidden;
}
.cs-btn {
  width: 36px;
  text-align: center;
  color: var(--tx2);
  cursor: pointer;
  line-height: 40px;
}
.cs-val {
  width: 64px;
  height: 40px;
  text-align: center;
  font-family: ui-monospace, monospace;
  font-size: 15px;
  font-weight: 700;
  color: var(--tx);
  background: transparent;
  border: none;
  border-left: 1px solid var(--fieldline);
  border-right: 1px solid var(--fieldline);
  outline: none;
  -moz-appearance: textfield;
  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
}

/* actions */
.actions {
  display: flex;
  gap: 10px;
}
.btn-ghost {
  flex: 0 0 120px;
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 14px;
  font-weight: 600;
}
.btn-primary {
  flex: 1;
  height: 48px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 12px 24px -10px rgba(160, 60, 150, 0.6);
  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
}

/* step2 */
.step2 {
  display: flex;
  gap: 22px;
}
.side-summary {
  flex: 0 0 380px;
}
.sub-label {
  font-size: 12px;
  color: var(--tx2);
  margin: 6px 0 18px;
}
.chunk-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--field);
  margin-top: 16px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--tx2);
}
.chunk-info-val {
  font-family: ui-monospace, monospace;
  font-size: 15px;
  font-weight: 800;
  color: var(--tx);
}
.pipe {
  flex: 1;
  min-width: 0;
}
.pipe-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.pipe-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pri);
  box-shadow: 0 0 0 4px var(--sel);
}
.pipe-title {
  font-size: 15px;
  font-weight: 800;
}
.pipe-progress {
  margin-left: auto;
  font-family: ui-monospace, monospace;
  font-size: 13px;
  font-weight: 700;
  color: var(--pri);
}
.pipe-sub {
  font-size: 12.5px;
  color: var(--tx3);
  margin-bottom: 22px;
}

/* 파일별 분석 */
.file-pipes {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.file-pipe {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px 16px;
  background: var(--panel2);
  &.active {
    border-color: var(--pri);
    background: var(--sel);
  }
}
.fp-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fp-icon {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--field);
  color: var(--tx3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex: 0 0 auto;
  &.done {
    background: var(--grn);
    color: #fff;
  }
  &.active {
    background: linear-gradient(135deg, #7c4da0, #c05cab);
    color: #fff;
  }
}
.fp-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fp-status {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--tx3);
  &.done {
    color: var(--grn);
  }
  &.active {
    color: var(--pri);
  }
}
.file-pipe.active .pipe-steps {
  margin-top: 14px;
}
.pipe-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pipe-step {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--panel2);
  border: 1px solid var(--line);
  .ps-icon {
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: var(--field);
    color: var(--tx3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 13px;
  }
  .ps-label {
    font-size: 13.5px;
    font-weight: 600;
    color: var(--tx2);
  }
  .ps-status {
    font-size: 11.5px;
    font-weight: 700;
    color: var(--tx3);
  }
  &.done .ps-icon {
    background: var(--grn);
    color: #fff;
  }
  &.done .ps-status {
    color: var(--grn);
  }
  &.active {
    border-color: var(--pri);
    background: var(--sel);
    .ps-icon {
      background: linear-gradient(135deg, #7c4da0, #c05cab);
      color: #fff;
    }
    .ps-label {
      color: var(--tx);
      font-weight: 700;
    }
    .ps-status {
      color: var(--pri);
    }
  }
}
.ps-body {
  flex: 1;
  min-width: 0;
}
.ps-bar {
  height: 4px;
  border-radius: 999px;
  background: var(--panel);
  margin-top: 8px;
  overflow: hidden;
}
.ps-fill {
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, #7c4da0, #c05cab);
}

/* step3 */
.step3 {
  padding: 24px;
}
.review-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.check {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: var(--grn);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.review-hint {
  margin-left: auto;
  font-size: 12px;
  color: var(--tx3);
}
.review-note {
  font-size: 12.5px;
  color: var(--tx3);
  margin: 0 0 16px 36px;
  b {
    color: var(--tx2);
  }
}
.review-count {
  margin-left: 8px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 2px 9px;
  border-radius: 999px;
}
.file-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 12px;
}
.file-tab {
  display: flex;
  align-items: center;
  gap: 7px;
  max-width: 260px;
  height: 36px;
  padding: 0 14px;
  border-radius: 9px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx2);
  font-size: 12.5px;
  font-weight: 600;
  &.active {
    border-color: var(--pri);
    background: var(--sel);
    color: var(--pri);
  }
}
.file-tab-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.review-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 22px;
}
.review-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 11px;
  border: 1px solid var(--line);
}
.ri-body {
  flex: 1;
  min-width: 0;
}
.ri-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.ri-title {
  font-size: 13px;
  font-weight: 700;
}
.ri-tag {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 2px 7px;
  border-radius: 5px;
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
  height: 30px;
  padding: 0 13px;
  border-radius: 8px;
  border: 1px solid var(--pri);
  background: var(--panel);
  color: var(--pri);
  font-size: 11.5px;
  font-weight: 700;
}
.review-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  border-top: 1px solid var(--line);
  padding-top: 18px;
  .btn-ghost {
    flex: 0 0 auto;
    padding: 0 20px;
    height: 44px;
  }
  .btn-primary {
    flex: 0 0 auto;
    padding: 0 28px;
    height: 44px;
  }
}
.full-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--tx2);
  margin: 0;
  white-space: pre-wrap;
}
</style>
