// 백엔드 공통 응답 envelope (설계 문서 7장)
export type { ApiResponse } from "./api";

// Job 상태 (설계 문서 5.2)
export type JobStatus = "WAITING" | "RUNNING" | "SUCCESS" | "FAILED";

// 데이터 분석 상태 배지
export type AnalysisBadge = "완료" | "분석중" | "대기" | "실패";

// 원본 데이터 목록 행
export interface RawData {
  id: string;
  title: string;
  fileName: string;
  reportTypeCode: string;
  reportTypeName: string;
  chunkCount: number;
  createdAt: string; // ISO
  status: JobStatus;
}

// 목록 조회 응답. total은 현재 필터·검색 조건의 전체 건수(페이지네이션 대비).
export interface RawDataList {
  total: number;
  items: RawData[];
}

// 상단 통계
export interface DataStats {
  total: number;
  done: number;
  ing: number;
  chunks: number;
}

// AI 분석 결과 항목 (Summary/Skill 등 유형별)
export interface AnalysisResult {
  type: string; // 예: SUMMARY, WORKFLOW, CONCEPT_EXTRACTION ...
  title: string;
  preview: string;
  content: string;
}

// 검토 단계: 업로드 파일별 분석 결과 (파일 1개 = 원본 데이터 1건)
export interface FileReview {
  fileId: string;
  fileName: string;
  results: AnalysisResult[];
}

// Chunk
export interface Chunk {
  order: number;
  text: string;
}

// 데이터 상세
export interface RawDataDetail extends RawData {
  summary: string;
  chunks: Chunk[];
  results: AnalysisResult[];
}

// 필수 Skill 등록 상태: 자동 생성 / 파일 업로드 / 미등록
export type SkillStatus = "none" | "gen" | "uploaded";

export interface ReportSkill {
  skillType: string; // WORKFLOW | CONCEPT_EXTRACTION | EVALUATION_POLICY
  name: string;
  description: string;
  status: SkillStatus;
  content: string;
}

// Report Type (설계/정책 문서 4장)
export interface ReportType {
  code: string; // 유일, 등록 후 변경 불가
  name: string;
  description: string;
  classificationTypes: string[]; // 다중 선택
  skills: ReportSkill[]; // 필수 Skill (정책 4.3, 모두 등록해야 저장 가능)
  updatedAt: string;
  active: boolean;
}

// 필수 Skill 기본값 (정책 문서 4.3): 3종 고정
export const DEFAULT_SKILLS: { skillType: string; name: string }[] = [
  { skillType: "WORKFLOW", name: "작성 Workflow" },
  { skillType: "CONCEPT_EXTRACTION", name: "핵심개념 추출" },
  { skillType: "EVALUATION_POLICY", name: "평가 기준" },
];

export function blankSkills(): ReportSkill[] {
  return DEFAULT_SKILLS.map((s) => ({ ...s, description: "", status: "none", content: "" }));
}

// LLM / Embedding 설정 (API Key에 귀속)
// kind: "LOCAL"(자격 불필요) | "CLOUD"(시크릿 필요)
// secret: 입력 전용(저장 후 응답에는 미포함). hasSecret: 저장된 시크릿 존재 여부(표시용)
export interface LlmConfig {
  provider: string;
  endpoint: string;
  model: string;
  kind: "LOCAL" | "CLOUD";
  secret?: string;
  hasSecret?: boolean;
}

export interface EmbeddingConfig {
  provider: string;
  endpoint: string;
  model: string;
  kind: "LOCAL" | "CLOUD";
  secret?: string;
  hasSecret?: boolean;
}

// 사용자 DB 연결정보 (정책 문서 2장)
export interface DbConnection {
  id: string;
  name: string;
  host: string;
  port: number;
  database: string;
  username: string;
  isDefault: boolean;
}

// 연결 테스트 결과 — 필수 스키마·테이블 존재 여부(마이그레이션 필요 여부)를 함께 반환 (정책 2.3)
export interface DbTestResult {
  ok: boolean;
  needsMigration: boolean; // true면 마이그레이션 승인 후에만 저장 가능
}

// API Key (정책 문서 1장)
export interface ApiKey {
  id: string;
  name: string;
  keyMasked: string;
  keyPlain?: string; // 발급 직후 1회만 반환되는 평문 토큰 (저장하지 않음)
  active: boolean;
  expireAt: string;
  lastUsedAt: string | null;
  llm: LlmConfig;
  embedding: EmbeddingConfig;
  dbConnections: DbConnection[];
}

// 로그인 세션
export interface Session {
  token: string;
  role: "user" | "admin";
  displayName: string;
}

// 업로드된 파일(마법사 내)
export interface UploadedFile {
  id: string;
  name: string;
  size: string;
}

// 데이터 등록 요청
export interface DataRegisterPayload {
  reportTypeCode: string;
  files: UploadedFile[];
  chunkCount: number;
}

// Job
export interface Job {
  jobId: string;
  status: JobStatus;
}

// 분석 진행 상태 (백엔드 GET /jobs/{id}/progress). current_step은 파이프라인 단계 키.
export interface JobProgress {
  status: "RUNNING" | "COMPLETED" | "FAILED";
  totalFiles: number;
  currentFileIndex: number;
  currentFileName: string;
  currentStep: PipelineStageKey | "DONE";
  errorMessage: string | null;
}

// AI 분석 파이프라인 단계 (정책 문서 5.1)
export type PipelineStageKey =
  | "EXTRACT"
  | "SUMMARY"
  | "CHUNK"
  | "EMBEDDING"
  | "SKILL";

export interface PipelineStage {
  key: PipelineStageKey;
  label: string;
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { key: "EXTRACT", label: "원문 추출" },
  { key: "SUMMARY", label: "Summary 생성" },
  { key: "CHUNK", label: "Chunk 생성" },
  { key: "EMBEDDING", label: "Embedding 생성" },
  { key: "SKILL", label: "Report Skill 생성" },
];
