<script setup lang="ts">
import type { ReportType } from "~/types";
import { blankSkills } from "~/types";

const route = useRoute();
const api = useApi();
const crumb = useCrumb();
const toast = useToast();

const code = route.params.code as string;
const isNew = code === "new";
crumb.value = isNew ? "보고서 유형 관리 · 신규 등록" : "보고서 유형 관리 · 수정";

const form = ref<ReportType>({
  code: "",
  name: "",
  description: "",
  classificationTypes: [],
  skills: blankSkills(),
  updatedAt: "",
  active: true,
});
const loading = ref(!isNew);
const saving = ref(false);
const error = ref("");

// --- 입력값 설정: Classification Type (다중 선택, 옵션은 API 조회) ---
const classOptions = ref<string[]>([]);
const classLoading = ref(true);

// --- 필수 Skill ---
const selSkillIdx = ref<number | null>(null);
const genLoadingIdx = ref<number | null>(null);
const uploadFileInput = ref<HTMLInputElement | null>(null);
let uploadTargetIdx = -1;

const skillDone = computed(() => form.value.skills.filter((s) => s.status !== "none").length);
const skillTotal = computed(() => form.value.skills.length);
const allSkillsDone = computed(() => skillDone.value === skillTotal.value);
const selectedSkill = computed(() =>
  selSkillIdx.value != null ? form.value.skills[selSkillIdx.value] : null,
);
// 선택된 스킬 내용을 UI에서 직접 편집 가능하도록 하는 writable computed
const editContent = computed({
  get: () => selectedSkill.value?.content ?? "",
  set: (v: string) => {
    if (selSkillIdx.value != null) form.value.skills[selSkillIdx.value].content = v;
  },
});

function selectSkill(i: number) {
  if (form.value.skills[i].status !== "none") selSkillIdx.value = i;
}
async function generateSkill(i: number) {
  genLoadingIdx.value = i;
  try {
    const content = await api.generateSkill(form.value.skills[i].skillType, form.value);
    form.value.skills[i] = { ...form.value.skills[i], status: "gen", content };
    selSkillIdx.value = i;
  } finally {
    genLoadingIdx.value = null;
  }
}
function pickUploadFile(i: number) {
  uploadTargetIdx = i;
  uploadFileInput.value?.click();
}
async function onSkillFileChosen(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || uploadTargetIdx < 0) return;
  const content = await file.text();
  form.value.skills[uploadTargetIdx] = {
    ...form.value.skills[uploadTargetIdx],
    status: "uploaded",
    content,
  };
  selSkillIdx.value = uploadTargetIdx;
}

const canSave = computed(
  () => form.value.code.trim() !== "" && form.value.name.trim() !== "" && allSkillsDone.value,
);

async function save() {
  error.value = "";
  saving.value = true;
  try {
    await api.saveReportType(form.value, isNew);
    toast("보고서 유형이 저장되었습니다.");
    await navigateTo("/report-types");
  } catch (e) {
    error.value = e instanceof Error ? e.message : "저장에 실패했습니다.";
    toast(error.value, "err");
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  api
    .listClassificationTypes()
    .then((opts) => (classOptions.value = opts))
    .finally(() => (classLoading.value = false));

  if (!isNew) {
    try {
      form.value = JSON.parse(JSON.stringify(await api.getReportType(code)));
    } finally {
      loading.value = false;
    }
  }
});
</script>

<template>
  <div class="page">
    <div class="head">
      <h3>{{ isNew ? "보고서 유형 신규 등록" : "보고서 유형 수정" }}</h3>
      <div class="head-actions">
        <button class="gx-btn btn-ghost" @click="navigateTo('/report-types')">취소</button>
        <button class="gx-btn btn-primary" :disabled="!canSave || saving" @click="save">
          {{ saving ? "저장 중..." : "저장" }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="state-row">불러오는 중...</div>

    <div v-else class="cols">
      <div class="col-main">
        <!-- 기본 정보 -->
        <div class="card">
          <div class="card-title">기본 정보</div>
          <div class="field-grid">
            <label>Code <span class="req">*</span></label>
            <div>
              <input
                v-model="form.code"
                :disabled="!isNew"
                placeholder="예: FINANCE_REPORT"
                class="input mono"
              />
              <div v-if="!isNew" class="hint">Code는 등록 후 변경할 수 없습니다.</div>
            </div>
            <label>이름 <span class="req">*</span></label>
            <input v-model="form.name" placeholder="보고서 유형 이름" class="input" />
            <label>설명</label>
            <textarea v-model="form.description" placeholder="설명을 입력하세요" class="input area" />
          </div>
        </div>

        <!-- 입력값 설정 -->
        <div class="card">
          <div class="card-title">입력값 설정</div>
          <div class="sub">Classification Type (다중 선택 가능, 선택 사항)</div>
          <MultiSelect
            v-model="form.classificationTypes"
            :options="classOptions"
            :loading="classLoading"
            placeholder="Classification Type을 선택하세요"
          />
        </div>
      </div>

      <div class="col-side">
        <!-- 필수 Skill -->
        <div class="card skill-card">
          <div class="skill-head">
            <span class="card-title">필수 Skill</span>
            <span class="skill-count" :class="{ done: allSkillsDone }">
              {{ skillDone }} / {{ skillTotal }}
            </span>
          </div>
          <div class="sub">스킬별로 자동 생성하거나 업로드하세요. 모두 등록해야 저장할 수 있습니다.</div>

          <div class="skill-list">
            <div
              v-for="(sk, i) in form.skills"
              :key="sk.name"
              class="gx-btn skill-row"
              :class="{ sel: selSkillIdx === i, filled: sk.status !== 'none' }"
              @click="selectSkill(i)"
            >
              <div class="skill-row-top">
                <span class="skill-icon" :class="{ on: sk.status !== 'none' }">
                  <template v-if="sk.status !== 'none'">✓</template>
                  <template v-else>{{ i + 1 }}</template>
                </span>
                <span class="skill-name">{{ sk.name }}</span>
                <span class="skill-status" :class="sk.status">
                  {{ sk.status === "gen" ? "자동 생성됨" : sk.status === "uploaded" ? "업로드됨" : "미등록" }}
                </span>
              </div>
              <div class="skill-row-actions">
                <button
                  class="gx-btn skill-gen"
                  :disabled="genLoadingIdx === i"
                  @click.stop="generateSkill(i)"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1m0-12.8-2.1 2.1M7.7 16.3l-2.1 2.1" />
                  </svg>
                  {{ genLoadingIdx === i ? "생성 중..." : "자동 생성" }}
                </button>
                <button class="gx-btn skill-upload" @click.stop="pickUploadFile(i)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
                  </svg>
                  업로드
                </button>
              </div>
            </div>
          </div>
          <input
            ref="uploadFileInput"
            type="file"
            hidden
            accept=".txt,.md,.yaml,.yml,.json"
            @change="onSkillFileChosen"
          />
        </div>

        <!-- 상태는 수정 시에만 노출. 신규 등록은 무조건 활성으로 생성된다. -->
        <div v-if="!isNew" class="card">
          <div class="card-title">상태</div>
          <label class="switch">
            <input type="checkbox" v-model="form.active" />
            <span>{{ form.active ? "활성" : "비활성" }}</span>
          </label>
        </div>

        <div v-if="error" class="err">{{ error }}</div>
      </div>
    </div>

    <!-- 스킬 내용: 하단 전체 너비. 클릭한 스킬을 여기서 직접 편집한다. -->
    <div v-if="!loading" class="card skill-detail-card">
      <template v-if="selectedSkill?.content">
        <div class="sp-head">
          <span class="sp-name">{{ selectedSkill.name }}</span>
          <span class="sp-tag" :class="selectedSkill.status">
            {{ selectedSkill.status === "uploaded" ? "업로드" : "자동 생성" }}
          </span>
          <span class="sp-editable">내용을 직접 수정할 수 있습니다.</span>
        </div>
        <textarea v-model="editContent" class="sp-editor" spellcheck="false" />
      </template>
      <div v-else class="sp-empty">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M9 13h6M9 17h6" />
        </svg>
        <span>스킬을 자동 생성/업로드한 뒤<br />해당 스킬을 클릭하면 내용이 여기에 표시됩니다.</span>
      </div>
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
  margin-bottom: 20px;
}
h3 {
  font-size: 22px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.02em;
}
.head-actions {
  margin-left: auto;
  display: flex;
  gap: 10px;
}
.btn-ghost {
  height: 40px;
  padding: 0 18px;
  border-radius: 10px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 13.5px;
  font-weight: 600;
}
.btn-primary {
  height: 40px;
  padding: 0 20px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
}
.state-row {
  padding: 50px;
  text-align: center;
  color: var(--tx3);
}
.cols {
  display: flex;
  gap: 22px;
  margin-bottom: 16px;
}
.col-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.col-side {
  flex: 0 0 440px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 22px;
}
.card-title {
  font-size: 14px;
  font-weight: 800;
  margin-bottom: 16px;
}
.sub {
  font-size: 12px;
  color: var(--tx3);
  margin-bottom: 12px;
}
.field-grid {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 14px;
  align-items: start;
  label {
    font-size: 13px;
    font-weight: 700;
    padding-top: 12px;
  }
}
.req {
  color: var(--red);
}
.input {
  width: 100%;
  height: 44px;
  border-radius: 10px;
  background: var(--field);
  border: 1px solid var(--fieldline);
  padding: 0 14px;
  font-size: 13.5px;
  color: var(--tx);
  outline: none;
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}
.area {
  height: 90px;
  padding: 12px 14px;
  resize: vertical;
}
.mono {
  font-family: ui-monospace, monospace;
}
.hint {
  font-size: 11.5px;
  color: var(--tx3);
  margin-top: 6px;
}
.skill-card {
  display: flex;
  flex-direction: column;
}
.skill-head {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  .card-title {
    margin-bottom: 0;
  }
}
.skill-count {
  margin-left: auto;
  font-size: 11.5px;
  font-weight: 700;
  color: var(--amb);
  background: var(--amb-bg);
  padding: 3px 9px;
  border-radius: 999px;
  &.done {
    color: var(--grn);
    background: var(--grn-bg);
  }
}
.skill-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.skill-row {
  border: 1.5px dashed var(--line2);
  border-radius: 11px;
  padding: 12px 14px;
  cursor: pointer;
  background: transparent;
  &.filled {
    border: 1px solid var(--line);
  }
  &.sel {
    border: 1.5px solid var(--pri);
    background: var(--sel);
  }
}
.skill-row-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 11px;
}
.skill-icon {
  width: 20px;
  height: 20px;
  border-radius: 6px;
  background: var(--field);
  color: var(--tx3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex: 0 0 auto;
  &.on {
    background: var(--grn);
    color: #fff;
  }
}
.skill-name {
  font-size: 13px;
  font-weight: 700;
}
.skill-status {
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  color: var(--amb);
  &.gen {
    color: var(--grn);
  }
  &.uploaded {
    color: var(--blu);
  }
}
.skill-row-actions {
  display: flex;
  gap: 7px;
  padding-left: 28px;
}
.skill-gen {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 11px;
  border-radius: 8px;
  border: none;
  background: linear-gradient(135deg, #7c4da0, #c05cab);
  color: #fff;
  font-size: 11.5px;
  font-weight: 700;
  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}
.skill-upload {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 11px;
  border-radius: 8px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 11.5px;
  font-weight: 600;
}
.skill-detail-card {
  display: flex;
  flex-direction: column;
}
.sp-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
}
.sp-editable {
  margin-left: auto;
  font-size: 11.5px;
  color: var(--tx3);
}
.sp-name {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--tx2);
}
.sp-tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--grn);
  background: var(--grn-bg);
  padding: 2px 8px;
  border-radius: 6px;
  &.uploaded {
    color: var(--blu);
    background: var(--blu-bg);
  }
}
.sp-editor {
  width: 100%;
  min-height: 420px;
  resize: vertical;
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 11px;
  padding: 16px 18px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.7;
  color: var(--tx2);
  outline: none;
  white-space: pre;
  overflow: auto;
  &:focus {
    border-color: var(--pri);
  }
}
.sp-empty {
  height: 100%;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--tx3);
  gap: 9px;
  padding: 16px;
  span {
    font-size: 12px;
    line-height: 1.6;
  }
}
.switch {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  input {
    accent-color: var(--pri);
    width: 16px;
    height: 16px;
  }
}
.err {
  font-size: 12.5px;
  color: var(--red);
  padding: 10px 12px;
  background: var(--red-bg);
  border-radius: 8px;
}
</style>
