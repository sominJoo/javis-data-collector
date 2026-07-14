import type {
  ApiKey,
  ApiResponse,
  DataRegisterPayload,
  DataStats,
  DbConnection,
  DbTestResult,
  FileReview,
  JobProgress,
  RawData,
  RawDataDetail,
  RawDataList,
  ReportType,
  Session,
  UploadedFile,
} from "~/types";

// 데이터 수집기 API 인터페이스. 실제 백엔드(공통 응답 envelope)와 연동한다.
export interface DataCollectorApi {
  login(apiKey: string): Promise<Session>;
  adminLogin(id: string, password: string): Promise<Session>;
  getStats(): Promise<DataStats>;
  listRawData(query?: string, reportTypeCode?: string): Promise<RawDataList>;
  getRawData(id: string): Promise<RawDataDetail>;
  deleteRawData(id: string): Promise<void>;
  uploadFile(file: File): Promise<{ fileId: string }>;
  registerData(payload: DataRegisterPayload): Promise<{ jobId: string }>;
  getJobProgress(jobId: string): Promise<JobProgress>;
  getReview(jobId: string, files: UploadedFile[]): Promise<FileReview[]>;
  saveData(jobId: string, payload: DataRegisterPayload): Promise<RawData[]>;
  reanalyze(id: string): Promise<void>;
  listReportTypes(): Promise<ReportType[]>;
  getReportType(code: string): Promise<ReportType>;
  saveReportType(payload: ReportType, isNew: boolean): Promise<ReportType>;
  generateSkill(skillType: string, reportType: ReportType): Promise<string>;
  listClassificationTypes(): Promise<string[]>;
  listApiKeys(): Promise<ApiKey[]>;
  saveApiKey(payload: ApiKey, isNew: boolean): Promise<ApiKey>;
  toggleApiKey(id: string): Promise<void>;
  testDbConnection(conn: Omit<DbConnection, "id" | "isDefault">): Promise<DbTestResult>;
  migrateDb(conn: Omit<DbConnection, "id" | "isDefault">): Promise<void>;
}

// $fetch가 던지는 저수준 오류(FetchError)를 사용자에게 보여줄 안전한 메시지로 변환한다.
// 서버 URL·스택 등 기술적 원문은 절대 노출하지 않는다.
// $fetch(FetchError)에서 HTTP 상태 코드를 추출한다. 응답이 없으면(네트워크·CORS) undefined.
function httpStatus(e: unknown): number | undefined {
  return (
    (e as { statusCode?: number })?.statusCode ??
    (e as { response?: { status?: number } })?.response?.status
  );
}
function toUserMessage(e: unknown): string {
  // 백엔드가 공통 envelope로 내려준 errorMessage는 사용자용으로 안전하므로 그대로 사용한다.
  const data = (e as { data?: Partial<ApiResponse<unknown>> })?.data;
  if (data && typeof data === "object" && data.errorMessage) {
    return String(data.errorMessage);
  }
  const status = httpStatus(e);
  if (status === 401 || status === 403) return "인증에 실패했습니다. 다시 로그인해주세요.";
  if (status === 404) return "요청한 정보를 찾을 수 없습니다.";
  if (typeof status === "number" && status >= 500) {
    return "서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.";
  }
  // statusCode가 없으면 네트워크 미연결(Failed to fetch)·CORS 등으로 응답 자체가 없는 경우다.
  return "서버에 연결할 수 없습니다. 네트워크 상태를 확인한 뒤 다시 시도해주세요.";
}

// 실제 백엔드 연결 구현. 공통 응답 envelope(result/errorMessage/data)를 언랩한다.
function createHttpApi(baseUrl: string): DataCollectorApi {
  // 저장된 세션(localStorage)의 JWT를 Authorization 헤더로 첨부한다.
  function authHeaders(): Record<string, string> {
    if (!import.meta.client) return {};
    try {
      const raw = localStorage.getItem("session");
      const token = raw ? (JSON.parse(raw) as { token?: string }).token : undefined;
      return token ? { Authorization: `Bearer ${token}` } : {};
    } catch {
      return {};
    }
  }
  async function req<T>(path: string, options: Record<string, unknown> = {}): Promise<T> {
    let res: ApiResponse<T>;
    try {
      res = await $fetch<ApiResponse<T>>(`${baseUrl}${path}`, {
        ...options,
        headers: { ...(options.headers as Record<string, string> | undefined), ...authHeaders() },
      });
    } catch (e) {
      // 401: 저장된 토큰이 무효·만료된 경우. 세션을 정리하고 로그인 화면으로 보낸다.
      // (토큰이 없는 상태의 401은 로그인 시도 실패이므로 리다이렉트하지 않는다.)
      if (import.meta.client && httpStatus(e) === 401 && localStorage.getItem("session")) {
        useAuthStore().logout();
        await navigateTo("/login");
      }
      // 네트워크 미연결·CORS·HTTP 오류 등 저수준 오류의 원문은 화면에 노출하지 않는다.
      // 항상 사용자용 안전 메시지로 변환해 던진다.
      throw new Error(toUserMessage(e));
    }
    if (res.result !== 1) throw new Error(res.errorMessage || "요청을 처리하지 못했습니다.");
    return res.data as T;
  }
  return {
    login: (apiKey) => req<Session>("/auth/login", { method: "POST", body: { api_key: apiKey } }),
    adminLogin: (id, password) =>
      req<Session>("/auth/admin-login", { method: "POST", body: { id, password } }),
    getStats: () => req<DataStats>("/data/stats"),
    listRawData: (query, reportTypeCode) =>
      req<RawDataList>("/data", {
        query: { q: query || undefined, report_type_code: reportTypeCode || undefined },
      }),
    getRawData: (id) => req<RawDataDetail>(`/data/${id}`),
    deleteRawData: (id) => req<void>(`/data/${id}`, { method: "DELETE" }),
    uploadFile: (file) => {
      // multipart/form-data. Content-Type은 브라우저가 boundary와 함께 자동 설정한다.
      const form = new FormData();
      form.append("file", file);
      return req<{ fileId: string }>("/files", { method: "POST", body: form });
    },
    registerData: (payload) => req<{ jobId: string }>("/data", { method: "POST", body: payload }),
    getJobProgress: (jobId) => req<JobProgress>(`/jobs/${jobId}/progress`),
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
    generateSkill: (skillType, reportType) =>
      req<string>("/report-types/skills/generate", {
        method: "POST",
        body: {
          skillType,
          reportTypeCode: reportType.code,
          reportTypeName: reportType.name,
          reportTypeDescription: reportType.description,
        },
      }),
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
  return createHttpApi(config.public.apiBase as string);
}
