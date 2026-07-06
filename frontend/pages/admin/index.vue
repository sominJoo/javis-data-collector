<script setup lang="ts">
import type { ApiKey, DbConnection } from "~/types";

const api = useApi();
const crumb = useCrumb();
const toast = useToast();
crumb.value = "API Key 관리";

const rows = ref<ApiKey[]>([]);
const loading = ref(false);

// --- API Key 모달 ---
const keyModalOpen = ref(false);
const editingNew = ref(false);
const form = ref<ApiKey>(blankKey());
const savingKey = ref(false);

// --- DB 연결 모달 ---
const dbModalOpen = ref(false);
const dbForm = ref(blankDb());
const dbTesting = ref(false);
const dbTested = ref(false);
const dbError = ref("");

// 마이그레이션 승인 플로우 (정책 2.3)
type MigChoice = "none" | "yes" | "no";
const dbNeedMig = ref(false); // 연결 테스트 결과: 필수 스키마·테이블 존재 여부
const dbMigChoice = ref<MigChoice>("none"); // 사용자 승인 선택
const dbMigrated = ref(false); // 마이그레이션 완료 여부
const dbMigrating = ref(false);

// 안내 배너 상태 (테스트 완료 후 4갈래)
const migNone = computed(() => dbTested.value && !dbNeedMig.value);
const migNeed = computed(
  () => dbTested.value && dbNeedMig.value && !dbMigrated.value && dbMigChoice.value !== "no",
);
const migDone = computed(() => dbTested.value && dbNeedMig.value && dbMigrated.value);
const migBlocked = computed(
  () => dbTested.value && dbNeedMig.value && dbMigChoice.value === "no" && !dbMigrated.value,
);

function blankKey(): ApiKey {
  return {
    id: "",
    name: "",
    keyMasked: "sk-graphio-••••••••••(생성 시 자동 발급)",
    active: true,
    expireAt: "2026-12-31T23:59:59Z",
    lastUsedAt: null,
    llm: { provider: "openai", endpoint: "https://api.openai.com/v1", model: "gpt-4o-mini" },
    embedding: {
      provider: "openai",
      endpoint: "https://api.openai.com/v1",
      model: "text-embedding-3-small",
    },
    dbConnections: [],
  };
}
function blankDb() {
  return { name: "", host: "", port: 5432, database: "", username: "", password: "" };
}

async function load() {
  loading.value = true;
  try {
    rows.value = await api.listApiKeys();
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingNew.value = true;
  form.value = blankKey();
  keyModalOpen.value = true;
}
function openEdit(key: ApiKey) {
  editingNew.value = false;
  form.value = JSON.parse(JSON.stringify(key));
  keyModalOpen.value = true;
}
async function saveKey() {
  savingKey.value = true;
  try {
    await api.saveApiKey(form.value, editingNew.value);
    keyModalOpen.value = false;
    await load();
    toast(editingNew.value ? "API Key가 생성되었습니다." : "API Key 정보가 저장되었습니다.");
  } finally {
    savingKey.value = false;
  }
}
async function toggle(key: ApiKey) {
  await api.toggleApiKey(key.id);
  await load();
  toast(key.active ? "API Key를 비활성화했습니다." : "API Key를 활성화했습니다.");
}

// DB 연결
function resetDbTest() {
  dbTested.value = false;
  dbNeedMig.value = false;
  dbMigChoice.value = "none";
  dbMigrated.value = false;
  dbError.value = "";
}
function openDbModal() {
  dbForm.value = blankDb();
  resetDbTest();
  dbModalOpen.value = true;
}
async function testDb() {
  dbError.value = "";
  dbTesting.value = true;
  try {
    const res = await api.testDbConnection(dbForm.value);
    dbTested.value = res.ok;
    dbNeedMig.value = res.needsMigration;
    dbMigChoice.value = "none";
    dbMigrated.value = false;
    if (res.ok) {
      toast("연결 테스트가 완료되었습니다.");
    } else {
      dbError.value = "연결 테스트에 실패했습니다. 입력값을 확인하세요.";
    }
  } finally {
    dbTesting.value = false;
  }
}
// 마이그레이션 승인/거부
async function migrateYes() {
  dbMigrating.value = true;
  try {
    await api.migrateDb(dbForm.value);
    dbMigChoice.value = "yes";
    dbMigrated.value = true;
    toast("마이그레이션이 완료되었습니다.");
  } finally {
    dbMigrating.value = false;
  }
}
function migrateNo() {
  dbMigChoice.value = "no";
}
function migrateReset() {
  dbMigChoice.value = "none";
}
function saveDb() {
  // 정책 2.3: 연결 테스트 성공 + (마이그레이션 불필요 or 마이그레이션 승인 완료) 후에만 저장
  if (!dbTested.value) {
    toast("연결 테스트를 먼저 수행해주세요.", "err");
    return;
  }
  if (dbNeedMig.value && !dbMigrated.value) {
    toast("마이그레이션을 수행해야 연결정보를 등록할 수 있습니다.", "err");
    return;
  }
  const conn: DbConnection = {
    id: `db-${Date.now()}`,
    name: dbForm.value.name,
    host: dbForm.value.host,
    port: dbForm.value.port,
    database: dbForm.value.database,
    username: dbForm.value.username,
    isDefault: form.value.dbConnections.length === 0,
  };
  form.value.dbConnections.push(conn);
  dbModalOpen.value = false;
  toast("분석 DB 연결정보가 등록되었습니다.");
}
function removeDb(id: string) {
  form.value.dbConnections = form.value.dbConnections.filter((d) => d.id !== id);
}

function fmtDate(iso: string): string {
  return iso.slice(0, 10);
}
function fmtUsed(iso: string | null): string {
  return iso ? iso.slice(0, 10) : "미사용";
}

const canSaveKey = computed(() => form.value.name.trim() !== "");
const canSaveDb = computed(
  () =>
    dbTested.value &&
    dbForm.value.name.trim() !== "" &&
    (!dbNeedMig.value || dbMigrated.value),
);

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="head">
      <h3>API Key 관리</h3>
      <span class="count">{{ rows.length }}건</span>
      <button class="gx-btn btn-primary" @click="openCreate">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
          <path d="M12 5v14M5 12h14" />
        </svg>
        API Key 추가
      </button>
    </div>

    <div class="table">
      <div class="thead">
        <div>Key 이름</div>
        <div>API Key 토큰</div>
        <div>사용량</div>
        <div>DB</div>
        <div>만료일</div>
        <div>관리</div>
      </div>
      <div v-for="k in rows" :key="k.id" class="trow">
        <div class="kname">
          <span class="state-dot" :class="k.active ? 'on' : 'off'" />
          {{ k.name }}
        </div>
        <div class="mono token">{{ k.keyMasked }}</div>
        <div class="mono muted">{{ fmtUsed(k.lastUsedAt) }}</div>
        <div class="mono">{{ k.dbConnections.length }}개</div>
        <div class="mono muted">{{ fmtDate(k.expireAt) }}</div>
        <div class="actions">
          <button class="mini" @click="openEdit(k)">편집</button>
          <button class="mini" :class="{ danger: k.active }" @click="toggle(k)">
            {{ k.active ? "비활성" : "활성" }}
          </button>
        </div>
      </div>
      <div v-if="loading" class="state-row">불러오는 중...</div>
      <div v-else-if="rows.length === 0" class="state-row">등록된 API Key가 없습니다.</div>
    </div>

    <!-- API Key 추가/편집 모달 -->
    <AppModal v-model:open="keyModalOpen" :title="editingNew ? 'API Key 추가' : 'API Key 편집'">
      <div class="form">
        <div class="section-label">기본 정보</div>
        <div class="fg">
          <label>Key 이름 <span class="req">*</span></label>
          <input v-model="form.name" class="input" placeholder="예: 기본 서비스 키" />
        </div>
        <div class="fg">
          <label>만료일</label>
          <input v-model="form.expireAt" class="input mono" placeholder="2026-12-31T23:59:59Z" />
        </div>

        <div class="section-label">LLM 설정</div>
        <div class="fg2">
          <input v-model="form.llm.endpoint" class="input" placeholder="Endpoint" />
          <input v-model="form.llm.model" class="input" placeholder="Model" />
        </div>

        <div class="section-label">Embedding 설정</div>
        <div class="fg2">
          <input v-model="form.embedding.endpoint" class="input" placeholder="Endpoint" />
          <input v-model="form.embedding.model" class="input" placeholder="Model" />
        </div>

        <div class="section-label db-head">
          DB 연결정보
          <button class="add-db" @click="openDbModal">+ 연결 추가</button>
        </div>
        <div v-if="form.dbConnections.length" class="db-list">
          <div v-for="d in form.dbConnections" :key="d.id" class="db-item">
            <div>
              <div class="db-name">
                {{ d.name }}
                <span v-if="d.isDefault" class="db-default">기본</span>
              </div>
              <div class="db-detail">{{ d.username }}@{{ d.host }}:{{ d.port }}/{{ d.database }}</div>
            </div>
            <span class="db-x" @click="removeDb(d.id)">×</span>
          </div>
        </div>
        <div v-else class="db-empty">등록된 DB 연결정보가 없습니다. (선택 사항)</div>

        <div class="modal-actions">
          <button class="gx-btn btn-ghost" @click="keyModalOpen = false">취소</button>
          <button class="gx-btn btn-primary" :disabled="!canSaveKey || savingKey" @click="saveKey">
            {{ savingKey ? "저장 중..." : "저장" }}
          </button>
        </div>
      </div>
    </AppModal>

    <!-- DB 연결정보 모달 -->
    <AppModal v-model:open="dbModalOpen" title="분석 DB 연결정보 등록">
      <div class="form">
        <div class="hint-line">분석된 데이터를 저장할 PostgreSQL 연결정보를 등록합니다.</div>
        <div class="fg">
          <label>Connection Name <span class="req">*</span></label>
          <input v-model="dbForm.name" class="input" placeholder="분석 DB-03" @input="resetDbTest" />
        </div>
        <div class="fg2">
          <div class="fg">
            <label>Host <span class="req">*</span></label>
            <input v-model="dbForm.host" class="input" placeholder="db.internal" @input="resetDbTest" />
          </div>
          <div class="fg">
            <label>Port</label>
            <input v-model.number="dbForm.port" class="input mono" @input="resetDbTest" />
          </div>
        </div>
        <div class="fg2">
          <div class="fg">
            <label>Database <span class="req">*</span></label>
            <input v-model="dbForm.database" class="input" placeholder="collector" @input="resetDbTest" />
          </div>
          <div class="fg">
            <label>Username <span class="req">*</span></label>
            <input v-model="dbForm.username" class="input" placeholder="postgres" @input="resetDbTest" />
          </div>
        </div>
        <div class="fg">
          <label>Password</label>
          <input v-model="dbForm.password" type="password" class="input" placeholder="••••••••" @input="resetDbTest" />
        </div>

        <div v-if="dbTested" class="test-ok">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          연결 테스트 성공 — 연결 가능
        </div>
        <div v-if="dbError" class="err">{{ dbError }}</div>

        <!-- 마이그레이션 승인 안내 (정책 2.3) -->
        <div v-if="migNone" class="mig-banner ok">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          <div>필수 스키마·테이블이 <b>이미 존재</b>합니다. 마이그레이션 없이 등록할 수 있습니다.</div>
        </div>

        <div v-if="migNeed" class="mig-banner warn">
          <div class="mig-msg">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <path d="M12 9v4M12 17h.01" />
            </svg>
            <div>
              데이터 수집기에 필요한 <b>스키마·테이블이 존재하지 않습니다.</b>
              마이그레이션을 진행하시겠습니까? 진행하지 않으면 연결정보를 등록할 수 없습니다.
            </div>
          </div>
          <div class="mig-actions">
            <button class="mig-yes" :disabled="dbMigrating" @click="migrateYes">
              {{ dbMigrating ? "진행 중..." : "마이그레이션 진행" }}
            </button>
            <button class="mig-no" :disabled="dbMigrating" @click="migrateNo">진행 안 함</button>
          </div>
        </div>

        <div v-if="migDone" class="mig-banner ok">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M20 6 9 17l-5-5" />
          </svg>
          <div><b>마이그레이션 완료.</b> 스키마·테이블이 생성되었습니다. 이제 등록할 수 있습니다.</div>
        </div>

        <div v-if="migBlocked" class="mig-banner danger">
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
          </svg>
          <div>
            마이그레이션을 진행하지 않아 <b class="danger-tx">연결정보를 등록할 수 없습니다.</b>
            <span class="mig-reset" @click="migrateReset">다시 선택</span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="gx-btn btn-ghost" :disabled="dbTesting" @click="testDb">
            {{ dbTesting ? "테스트 중..." : "연결 테스트" }}
          </button>
          <button class="gx-btn btn-primary" :disabled="!canSaveDb" @click="saveDb">저장</button>
        </div>
      </div>
    </AppModal>
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
  &:disabled {
    opacity: 0.5;
    cursor: default;
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
  grid-template-columns: 1fr 260px 100px 70px 120px 140px;
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
}
.kname {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  &.on {
    background: var(--grn);
  }
  &.off {
    background: var(--tx3);
  }
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}
.token {
  color: var(--tx2);
}
.muted {
  color: var(--tx3);
}
.actions {
  display: flex;
  gap: 8px;
}
.mini {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  &.danger {
    color: var(--red);
    border-color: var(--red-bg);
  }
}
.state-row {
  padding: 50px;
  text-align: center;
  color: var(--tx3);
}

/* form (modal) */
.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.section-label {
  font-size: 12px;
  font-weight: 800;
  color: var(--pri);
  letter-spacing: 0.04em;
  margin-top: 4px;
}
.db-head {
  display: flex;
  align-items: center;
}
.add-db {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--pri);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.hint-line {
  font-size: 12.5px;
  color: var(--tx3);
  margin-bottom: 2px;
}
.fg {
  display: flex;
  flex-direction: column;
  gap: 7px;
  flex: 1;
  label {
    font-size: 12.5px;
    font-weight: 700;
  }
}
.fg2 {
  display: flex;
  gap: 12px;
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
}
.mono {
  font-family: ui-monospace, monospace;
}
.db-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.db-item {
  display: flex;
  align-items: center;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--line);
}
.db-name {
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}
.db-default {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--pri);
  background: var(--sel);
  padding: 1px 7px;
  border-radius: 5px;
}
.db-detail {
  font-size: 11.5px;
  color: var(--tx3);
  font-family: ui-monospace, monospace;
  margin-top: 3px;
}
.db-x {
  margin-left: auto;
  color: var(--tx3);
  cursor: pointer;
  font-size: 16px;
}
.db-empty {
  font-size: 12.5px;
  color: var(--tx3);
  padding: 10px 0;
}
.test-ok {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--grn);
  background: var(--grn-bg);
  padding: 10px 12px;
  border-radius: 8px;
}

/* 마이그레이션 승인 배너 */
.mig-banner {
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--tx2);
  b {
    color: var(--tx);
  }
  &.ok {
    display: flex;
    align-items: flex-start;
    gap: 11px;
    border: 1px solid var(--grn);
    background: var(--grn-bg);
    color: var(--grn);
    div {
      color: var(--tx2);
    }
    svg {
      flex: 0 0 auto;
      margin-top: 1px;
    }
  }
  &.warn {
    border: 1px solid var(--amb);
    background: var(--amb-bg);
    padding: 16px 18px;
    svg {
      color: var(--amb);
    }
  }
  &.danger {
    display: flex;
    align-items: flex-start;
    gap: 11px;
    border: 1px solid var(--red);
    background: var(--red-bg);
    color: var(--red);
    div {
      color: var(--tx2);
    }
    svg {
      flex: 0 0 auto;
      margin-top: 1px;
    }
  }
}
.mig-msg {
  display: flex;
  align-items: flex-start;
  gap: 11px;
  margin-bottom: 13px;
  svg {
    flex: 0 0 auto;
    margin-top: 1px;
  }
}
.mig-actions {
  display: flex;
  gap: 9px;
  padding-left: 29px;
}
.mig-yes {
  height: 38px;
  padding: 0 16px;
  border-radius: 9px;
  border: none;
  background: var(--amb);
  color: #fff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}
.mig-no {
  height: 38px;
  padding: 0 16px;
  border-radius: 9px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx2);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}
.danger-tx {
  color: var(--red) !important;
}
.mig-reset {
  color: var(--pri);
  font-weight: 700;
  cursor: pointer;
}
.err {
  font-size: 12.5px;
  color: var(--red);
  background: var(--red-bg);
  padding: 10px 12px;
  border-radius: 8px;
}
.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  border-top: 1px solid var(--line);
  padding-top: 16px;
  margin-top: 4px;
}
.btn-ghost {
  height: 42px;
  padding: 0 18px;
  border-radius: 10px;
  border: 1px solid var(--line2);
  background: var(--panel);
  color: var(--tx);
  font-size: 13.5px;
  font-weight: 600;
  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
}
.modal-actions .btn-primary {
  margin-left: 0;
  box-shadow: none;
  height: 42px;
}
</style>
