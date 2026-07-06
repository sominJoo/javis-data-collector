import type {
  AnalysisResult,
  ApiKey,
  ApiResponse,
  DataRegisterPayload,
  DataStats,
  DbConnection,
  DbTestResult,
  FileReview,
  RawData,
  RawDataDetail,
  ReportType,
  Session,
  UploadedFile,
} from "~/types";
import {
  mockApiKeys,
  mockClassificationTypes,
  mockRawData,
  mockReportTypes,
  skillBody,
} from "~/mocks/data";

// 데이터 수집기 API 인터페이스.
// Phase 1은 목 데이터로 동작하며, NUXT_PUBLIC_USE_MOCK=false 로 실제 백엔드에 연결한다.
export interface DataCollectorApi {
  login(apiKey: string): Promise<Session>;
  adminLogin(id: string, password: string): Promise<Session>;
  getStats(): Promise<DataStats>;
  listRawData(query?: string): Promise<RawData[]>;
  getRawData(id: string): Promise<RawDataDetail>;
  deleteRawData(id: string): Promise<void>;
  registerData(payload: DataRegisterPayload): Promise<{ jobId: string }>;
  getReview(jobId: string, files: UploadedFile[]): Promise<FileReview[]>;
  saveData(jobId: string, payload: DataRegisterPayload): Promise<RawData[]>;
  reanalyze(id: string): Promise<void>;
  listReportTypes(): Promise<ReportType[]>;
  getReportType(code: string): Promise<ReportType>;
  saveReportType(payload: ReportType, isNew: boolean): Promise<ReportType>;
  generateSkill(name: string): Promise<string>;
  listClassificationTypes(): Promise<string[]>;
  listApiKeys(): Promise<ApiKey[]>;
  saveApiKey(payload: ApiKey, isNew: boolean): Promise<ApiKey>;
  toggleApiKey(id: string): Promise<void>;
  testDbConnection(conn: Omit<DbConnection, "id" | "isDefault">): Promise<DbTestResult>;
  migrateDb(conn: Omit<DbConnection, "id" | "isDefault">): Promise<void>;
}

const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms));

// 파일별 Skill 추출 결과 (목). 파일명을 반영해 파일마다 다른 결과처럼 보이게 한다.
function resultsForFile(fileName: string): AnalysisResult[] {
  return [
    {
      type: "SUMMARY",
      title: "Summary",
      preview: `${fileName}의 핵심 내용을 요약했습니다.`,
      content: `${fileName} 문서 전반의 핵심 내용을 요약한 결과입니다. 주요 주제와 결론을 담고 있습니다.`,
    },
    {
      type: "WORKFLOW",
      title: "WORKFLOW",
      preview: "단계 A → B → C → D",
      content: `${fileName} 워크플로우: 단계 A → 단계 B → 단계 C → 단계 D`,
    },
    {
      type: "CONCEPT_EXTRACTION",
      title: "CONCEPT_EXTRACTION",
      preview: "핵심 개념 5건 추출",
      content: `${fileName} 핵심 개념: 개념1, 개념2, 개념3, 개념4, 개념5`,
    },
    {
      type: "EVALUATION_POLICY",
      title: "EVALUATION_POLICY",
      preview: "평가 기준 3개 항목",
      content: `${fileName} 평가 정책: 정확성, 완결성, 일관성 기준으로 평가합니다.`,
    },
  ];
}

function toStats(rows: RawDataDetail[]): DataStats {
  return {
    total: rows.length,
    done: rows.filter((r) => r.status === "SUCCESS").length,
    ing: rows.filter((r) => r.status === "RUNNING" || r.status === "WAITING").length,
    chunks: rows.reduce((sum, r) => sum + r.chunkCount, 0),
  };
}

function createMockApi(): DataCollectorApi {
  return {
    async login(apiKey) {
      await delay();
      if (!apiKey.trim()) throw new Error("API Key를 입력하세요.");
      return { token: "mock-token", role: "user", displayName: "사용자" };
    },
    async adminLogin(id, password) {
      await delay();
      if (!id.trim() || !password.trim()) throw new Error("ID와 비밀번호를 입력하세요.");
      return { token: "mock-admin-token", role: "admin", displayName: "관리자" };
    },
    async getStats() {
      await delay(150);
      return toStats(mockRawData);
    },
    async listRawData(query) {
      await delay();
      const q = (query ?? "").trim().toLowerCase();
      // 최신 등록일 기준 정렬 (정책 문서 6.1)
      const sorted = [...mockRawData].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      const rows: RawData[] = sorted.map(({ summary, chunks, results, ...row }) => row);
      if (!q) return rows;
      return rows.filter(
        (r) => r.title.toLowerCase().includes(q) || r.fileName.toLowerCase().includes(q),
      );
    },
    async getRawData(id) {
      await delay();
      const found = mockRawData.find((r) => r.id === id);
      if (!found) throw new Error("데이터를 찾을 수 없습니다.");
      return found;
    },
    async deleteRawData(id) {
      await delay();
      const idx = mockRawData.findIndex((r) => r.id === id);
      if (idx >= 0) mockRawData.splice(idx, 1);
    },
    async registerData(payload) {
      await delay();
      if (!payload.reportTypeCode) throw new Error("보고서 유형을 선택하세요.");
      if (payload.files.length === 0) throw new Error("파일을 추가하세요.");
      return { jobId: `job-${Date.now()}` };
    },
    async getReview(_jobId, files) {
      await delay(400);
      return files.map((f) => ({
        fileId: f.id,
        fileName: f.name,
        results: resultsForFile(f.name),
      }));
    },
    async saveData(_jobId, payload) {
      await delay();
      const type = mockReportTypes.find((t) => t.code === payload.reportTypeCode);
      // 파일 1개 = 원본 데이터 1건 (정책 3.1/3.3)
      const created: RawData[] = [];
      payload.files.forEach((f, i) => {
        const row: RawDataDetail = {
          id: `d-${Date.now()}-${i}`,
          title: f.name.replace(/\.[^.]+$/, ""),
          fileName: f.name,
          reportTypeCode: payload.reportTypeCode,
          reportTypeName: type?.name ?? payload.reportTypeCode,
          chunkCount: payload.chunkCount,
          createdAt: new Date().toISOString(),
          status: "SUCCESS",
          summary: `${f.name} 문서의 핵심 내용을 요약한 결과입니다.`,
          chunks: Array.from({ length: Math.min(payload.chunkCount, 5) }, (_, ci) => ({
            order: ci + 1,
            text: `Chunk ${ci + 1} 내용...`,
          })),
          results: resultsForFile(f.name),
        };
        mockRawData.unshift(row);
        const { summary, chunks, results, ...listRow } = row;
        created.push(listRow);
      });
      return created;
    },
    async reanalyze(id) {
      await delay(600);
      const found = mockRawData.find((r) => r.id === id);
      if (found) found.status = "SUCCESS";
    },
    async listReportTypes() {
      await delay(150);
      return mockReportTypes;
    },
    async getReportType(code) {
      await delay();
      const found = mockReportTypes.find((t) => t.code === code);
      if (!found) throw new Error("보고서 유형을 찾을 수 없습니다.");
      return found;
    },
    async saveReportType(payload, isNew) {
      await delay();
      const now = new Date().toISOString();
      if (isNew) {
        if (!payload.code.trim()) throw new Error("Code를 입력하세요.");
        if (mockReportTypes.some((t) => t.code === payload.code)) {
          throw new Error("이미 존재하는 Code입니다."); // 정책 4.1 유일성
        }
        const created = { ...payload, updatedAt: now };
        mockReportTypes.push(created);
        return created;
      }
      const idx = mockReportTypes.findIndex((t) => t.code === payload.code);
      if (idx < 0) throw new Error("보고서 유형을 찾을 수 없습니다.");
      const updated = { ...payload, updatedAt: now };
      mockReportTypes[idx] = updated;
      return updated;
    },
    async generateSkill(name) {
      await delay(500);
      return skillBody(name, "gen");
    },
    async listClassificationTypes() {
      await delay(150);
      return mockClassificationTypes;
    },
    async listApiKeys() {
      await delay(150);
      return mockApiKeys;
    },
    async saveApiKey(payload, isNew) {
      await delay();
      if (isNew) {
        const created = { ...payload, id: `k-${Date.now()}` };
        mockApiKeys.push(created);
        return created;
      }
      const idx = mockApiKeys.findIndex((k) => k.id === payload.id);
      if (idx < 0) throw new Error("API Key를 찾을 수 없습니다.");
      mockApiKeys[idx] = payload;
      return payload;
    },
    async toggleApiKey(id) {
      await delay(150);
      const found = mockApiKeys.find((k) => k.id === id);
      if (found) found.active = !found.active;
    },
    async testDbConnection(conn) {
      await delay(600);
      // 목: host/database/username이 모두 채워지면 연결 성공 (정책 2.3)
      const ok = Boolean(conn.host && conn.database && conn.username);
      // database 이름에 "collector"가 포함되면 필수 스키마가 이미 존재한다고 가정 → 마이그레이션 불필요
      const needsMigration = ok && !conn.database.toLowerCase().includes("collector");
      return { ok, needsMigration };
    },
    async migrateDb() {
      await delay(700);
      // 목: 스키마·테이블 생성 성공
    },
  };
}

// 실제 백엔드 연결 시 사용할 HTTP 구현. 공통 응답 envelope(result/errorMessage/data)를 언랩한다.
function createHttpApi(baseUrl: string): DataCollectorApi {
  async function req<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    const res = await $fetch<ApiResponse<T>>(`${baseUrl}${path}`, options);
    if (res.result !== 1) throw new Error(res.errorMessage || "요청 실패");
    return res.data as T;
  }
  return {
    login: (apiKey) => req<Session>("/auth/login", { method: "POST", body: { api_key: apiKey } }),
    adminLogin: (id, password) =>
      req<Session>("/auth/admin-login", { method: "POST", body: { id, password } }),
    getStats: () => req<DataStats>("/data/stats"),
    listRawData: (query) => req<RawData[]>("/data", { query: { q: query } }),
    getRawData: (id) => req<RawDataDetail>(`/data/${id}`),
    deleteRawData: (id) => req<void>(`/data/${id}`, { method: "DELETE" }),
    registerData: (payload) => req<{ jobId: string }>("/data", { method: "POST", body: payload }),
    getReview: (jobId) => req<FileReview[]>(`/jobs/${jobId}/review`),
    saveData: (jobId, payload) =>
      req<RawData[]>(`/jobs/${jobId}/save`, { method: "POST", body: payload }),
    reanalyze: (id) => req<void>(`/data/${id}/reanalyze`, { method: "POST" }),
    listReportTypes: () => req<ReportType[]>("/report-types"),
    getReportType: (code) => req<ReportType>(`/report-types/${code}`),
    saveReportType: (payload, isNew) =>
      req<ReportType>(isNew ? "/report-types" : `/report-types/${payload.code}`, {
        method: isNew ? "POST" : "PUT",
        body: payload,
      }),
    generateSkill: (name) =>
      req<string>("/report-types/skills/generate", { method: "POST", body: { name } }),
    listClassificationTypes: () => req<string[]>("/report-types/classification-types"),
    listApiKeys: () => req<ApiKey[]>("/admin/api-keys"),
    saveApiKey: (payload, isNew) =>
      req<ApiKey>(isNew ? "/admin/api-keys" : `/admin/api-keys/${payload.id}`, {
        method: isNew ? "POST" : "PUT",
        body: payload,
      }),
    toggleApiKey: (id) => req<void>(`/admin/api-keys/${id}/toggle`, { method: "POST" }),
    testDbConnection: (conn) =>
      req<DbTestResult>("/admin/db-connections/test", { method: "POST", body: conn }),
    migrateDb: (conn) =>
      req<void>("/admin/db-connections/migrate", { method: "POST", body: conn }),
  };
}

export function useApi(): DataCollectorApi {
  const config = useRuntimeConfig();
  return config.public.useMock
    ? createMockApi()
    : createHttpApi(config.public.apiBase as string);
}
