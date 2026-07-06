import type { ApiKey, RawDataDetail, ReportSkill, ReportType } from "~/types";
import { DEFAULT_SKILLS } from "~/types";

// Skill 파일(YAML) 목 본문 생성 — 자동 생성/업로드 결과를 구분해 보여준다.
export function skillBody(name: string, mode: "gen" | "uploaded"): string {
  return `# ${name}\n# ${mode === "uploaded" ? "(업로드된 스킬 파일)" : "(LLM 자동 생성)"}\n\nrole: >\n  ${name}을(를) 수행하여 문서에서\n  핵심 정보를 추출·분류·평가한다.\n\ninput:\n  - document_text   # 원문 텍스트\n\noutput:\n  - items[]         # 추출 결과 목록\n  - confidence      # 0.0 ~ 1.0\n\nsteps:\n  1. 원문에서 관련 구간을 식별한다.\n  2. 정의된 기준에 따라 분류/평가한다.\n  3. 구조화된 결과(JSON)를 반환한다.`;
}

function filledSkills(modes: Array<"gen" | "uploaded">): ReportSkill[] {
  return DEFAULT_SKILLS.map((name, i) => ({
    name,
    status: modes[i],
    content: skillBody(name, modes[i]),
  }));
}

// Classification Type 선택 옵션 (입력값 설정 다중 select, API로 조회)
export const mockClassificationTypes: string[] = [
  "문서",
  "보고서",
  "법무",
  "계약",
  "기술",
  "운영",
  "정책",
  "재무",
  "인사",
  "마케팅",
];

export const mockReportTypes: ReportType[] = [
  {
    code: "GENERAL",
    name: "일반 문서",
    description: "범용 문서 분석. 요약과 개념 추출을 수행합니다.",
    classificationTypes: ["문서", "보고서"],
    skills: filledSkills(["gen", "uploaded", "gen"]),
    updatedAt: "2026-06-20T09:00:00Z",
    active: true,
  },
  {
    code: "CONTRACT",
    name: "계약서",
    description: "계약 조항, 당사자, 기간 등 핵심 항목을 추출합니다.",
    classificationTypes: ["법무", "계약"],
    skills: filledSkills(["uploaded", "uploaded", "gen"]),
    updatedAt: "2026-06-22T11:30:00Z",
    active: true,
  },
  {
    code: "MANUAL",
    name: "매뉴얼",
    description: "절차 및 워크플로우 중심으로 구조화합니다.",
    classificationTypes: ["기술", "운영"],
    skills: filledSkills(["gen", "gen", "uploaded"]),
    updatedAt: "2026-06-25T14:10:00Z",
    active: true,
  },
  {
    code: "POLICY",
    name: "정책 문서",
    description: "정책·규정을 평가 기준과 함께 정리합니다.",
    classificationTypes: ["정책"],
    skills: filledSkills(["gen", "uploaded", "uploaded"]),
    updatedAt: "2026-06-29T08:45:00Z",
    active: false,
  },
];

export const mockRawData: RawDataDetail[] = [
  {
    id: "d-1001",
    title: "2026년 1분기 사업 계획 보고서",
    fileName: "biz_plan_2026Q1.pdf",
    reportTypeCode: "GENERAL",
    reportTypeName: "일반 문서",
    chunkCount: 24,
    createdAt: "2026-06-28T10:12:00Z",
    status: "SUCCESS",
    summary:
      "2026년 1분기 핵심 사업 목표와 예산 배분, 주요 리스크를 정리한 보고서입니다. 신규 데이터 수집기 도입과 AI 분석 자동화가 주요 과제로 제시되었습니다.",
    chunks: [
      { order: 1, text: "1. 개요 — 2026년 1분기 사업 방향..." },
      { order: 2, text: "2. 예산 배분 — 부문별 예산 계획..." },
      { order: 3, text: "3. 리스크 — 주요 대응 방안..." },
    ],
    results: [
      {
        type: "WORKFLOW",
        title: "워크플로우",
        preview: "계획 수립 → 예산 확정 → 실행 → 점검",
        content: "계획 수립 → 예산 확정 → 실행 → 분기 점검 → 피드백 반영",
      },
      {
        type: "CONCEPT_EXTRACTION",
        title: "개념 추출",
        preview: "사업목표, 예산, 리스크, 자동화",
        content: "핵심 개념: 사업목표, 예산 배분, 리스크 관리, AI 자동화, 데이터 수집기",
      },
    ],
  },
  {
    id: "d-1002",
    title: "공급 계약서 (A사)",
    fileName: "contract_A_2026.pdf",
    reportTypeCode: "CONTRACT",
    reportTypeName: "계약서",
    chunkCount: 12,
    createdAt: "2026-06-27T14:40:00Z",
    status: "SUCCESS",
    summary: "A사와의 공급 계약서. 계약 기간, 단가, 위약 조항이 포함되어 있습니다.",
    chunks: [
      { order: 1, text: "제1조 (목적)..." },
      { order: 2, text: "제2조 (계약 기간)..." },
    ],
    results: [
      {
        type: "CONCEPT_EXTRACTION",
        title: "개념 추출",
        preview: "당사자, 기간, 단가, 위약금",
        content: "당사자: A사 / 기간: 12개월 / 단가: 협의 / 위약금: 계약금의 10%",
      },
    ],
  },
  {
    id: "d-1003",
    title: "데이터 수집기 운영 매뉴얼",
    fileName: "collector_manual_v2.docx",
    reportTypeCode: "MANUAL",
    reportTypeName: "매뉴얼",
    chunkCount: 0,
    createdAt: "2026-07-01T09:05:00Z",
    status: "RUNNING",
    summary: "",
    chunks: [],
    results: [],
  },
  {
    id: "d-1004",
    title: "정보보안 정책 2026",
    fileName: "security_policy_2026.hwp",
    reportTypeCode: "POLICY",
    reportTypeName: "정책 문서",
    chunkCount: 0,
    createdAt: "2026-07-02T16:22:00Z",
    status: "WAITING",
    summary: "",
    chunks: [],
    results: [],
  },
];

export const mockApiKeys: ApiKey[] = [
  {
    id: "k-1",
    name: "기본 서비스 키",
    keyMasked: "sk-graphio-••••••••••3f2a",
    active: true,
    expireAt: "2026-12-31T23:59:59Z",
    lastUsedAt: "2026-07-02T16:20:00Z",
    llm: { provider: "openai", endpoint: "https://api.openai.com/v1", model: "gpt-4o-mini" },
    embedding: {
      provider: "openai",
      endpoint: "https://api.openai.com/v1",
      model: "text-embedding-3-small",
    },
    dbConnections: [
      {
        id: "db-1",
        name: "운영 사용자 DB",
        host: "db.internal",
        port: 5432,
        database: "jarivs_data_collector",
        username: "collector",
        isDefault: true,
      },
    ],
  },
];
