"""Report Type 필수 Skill 생성 Agent (LangGraph StateGraph).

report_type의 필수 Skill 3종(WORKFLOW, CONCEPT_EXTRACTION, EVALUATION_POLICY)의
정의 문서(frontmatter + Markdown)를 API Key에 등록된 LLM으로 생성한다.
입력은 보고서 타입 컨텍스트(code/name/description)와 LlmSpec이며, skill_type에 따라
서로 다른 구조의 정의 문서를 만든다.

단계: prepare(skill_type → guide/stub 결정) → generate(LLM 호출 또는 stub 반환).
LLM 관련 로직(프롬프트·stub·complete 호출)은 모두 이 Agent 안에서 동작한다.
LLM_STUB_MODE 또는 secret 미설정 시 외부 호출 없이 결정적 stub 정의를 반환한다.
"""
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.services import llm
from app.services.llm import LlmSpec

WORKFLOW = "WORKFLOW"
CONCEPT_EXTRACTION = "CONCEPT_EXTRACTION"
EVALUATION_POLICY = "EVALUATION_POLICY"


class ReportSkillState(TypedDict, total=False):
    skill_type: str
    code: str
    name: str
    description: str
    llm: LlmSpec
    guide: str  # prepare 단계에서 결정되는 LLM 프롬프트 가이드
    stub: str  # prepare 단계에서 결정되는 stub 정의 문서
    content: str  # 최종 생성된 스킬 정의 문서


def _ctx_block(code: str, name: str, description: str) -> str:
    return (
        "다음 보고서 타입을 위한 Skill 정의를 작성하라.\n"
        f"- 보고서 타입 code: {code}\n"
        f"- 보고서 타입 이름: {name}\n"
        f"- 보고서 타입 상세: {description or '(없음)'}\n"
    )


# ---------- WORKFLOW ----------
_WORKFLOW_GUIDE = """\
당신은 Agent Harness Runtime에서 사용할 **Workflow Skill 문서**를 생성하는 전문 작성자다.
당신의 역할은 보고서 본문을 작성하는 것이 아니라, Planner Agent와 Harness Runtime이 참조할
**Workflow 정의 문서**를 만드는 것이다. 즉 "무엇을, 어떤 순서로, 누가, 어떤 산출물로,
어떤 승인·검증 기준으로 수행하는가"를 정의한다.

출력은 frontmatter(name, description)로 시작하는 Markdown 문서 하나만 반환한다.
코드블록(```)으로 감싸지 말고, 앞뒤에 설명 문장을 붙이지 않는다.
위에 제시된 보고서 타입 정보(code/이름/상세)만 근거로 사용하고, 없는 내용은 지어내지 않는다.
상세 정보에 없는 필드명·금액 기준·승인 조건 등을 임의로 창작하지 말고, 불확실하면 "[확인 필요]"로 표기한다.

아래 템플릿 구조를 100% 그대로 따르되, 내용은 이 보고서 타입에 맞게 채운다.
섹션 제목과 순서는 임의로 바꾸지 않는다. 해당 사항이 없는 섹션(예: 버전 관리, 조건부 섹션)은
생략하거나 "해당 없음"으로 명시할 수 있다.

[템플릿 구조]

---
name: (code를 소문자 kebab-case로 변환)-workflow-skill
description: 이 Skill은 {name} 작성을 위한 Workflow를 정의한다.
---

# {name} Workflow Skill

## 목적
이 Skill이 결정하는 항목(단계 순서, 필수 단계, 섹션 구성 기본 규칙, 승인 지점,
출력 규칙, 검증 기준, 부분 재실행 범위)을 서술한다. 본문을 직접 작성하지 않음을 명시한다.

## 보고서 타입
`{code}`

## 핵심 원칙
1. Workflow는 독립 실행 가능한 단계 단위로 구성한다.
2. 전체 실행과 부분 재실행을 모두 지원한다.
3. 섹션(목차) 생성 단계에서는 분량이나 페이지 수를 관리하지 않는다.
4. (보고서 타입 특성에 맞는 검증 중심 원칙)
5. 중간 산출물은 Workspace Artifact로 저장한다.
6. 신규 섹션 구조 생성 또는 구조 변경 시 사용자 승인을 받아야 한다.
7. (보고서 타입에 특화된 추가 원칙이 있으면 기입)

## 필수 Workflow 단계
표준 6~10단계 골격을 사용한다. 각 단계는 WF-1, WF-2 ... 형식으로 번호를 매기고,
"**담당 Agent:**", "**필수 여부:**", 설명, "출력 산출물:"을 포함한다.
상세 정보에 없는 단계(문체 검토, 버전관리 등)는 생략하고, 생략·추가에 맞춰 WF 번호를 다시 매긴다.
표준 골격: WF-1 정보 분석(Planner Agent) / WF-2 섹션 구조 결정(Toc Agent, 유사 문서·TOC_STRUCTURE
Skill 활용, 승인 규칙 포함) / WF-3 근거 자료 검색(Search Agent, INTERNAL_ONLY 조건 반영) /
WF-4 섹션별 초안 작성(Drafting Agent) / WF-5 필수 항목 및 규칙 검증(Compliance Agent) /
[선택] 문체·논리 흐름 검토(Editorial Review Agent) / WF-N 최종 산출물 생성(Artifact Agent) /
[선택] 버전 관리(Version Agent, Git 연동 명시 시만).

## 섹션 기본 규칙
최대 depth, section_ref 형식(정형 문서는 depth 2 · `1`,`1.1` / 기획형은 depth 3 · `1`,`1-1`,`1-1-1`),
각 섹션이 가져야 할 정보(section_ref, title, depth, required, conditional, fields, writing guide 등)를 정의한다.
섹션에는 분량·페이지 수를 포함하지 않는다.

## 필수 섹션 커버리지
반드시 포함해야 하는 섹션 목록과, 조건에 따라 포함하는 조건부 섹션 목록을 명시한다.

## 승인 지점
승인이 필요한 경우와, 그때 반환할 정보(approval type, target artifact ref, allowed actions,
resume target, user-facing message)를 정의한다. 허용 action: APPROVE, REVISE, REJECT.

## 출력 규칙
각 단계는 파일을 직접 저장하지 않고 structured output을 반환하며, Artifact Manager가 Workspace에 저장한다.
중간 산출물 경로 규칙(planner/request_info.json, toc/toc_result.json, drafting/sections/,
review/, artifact/ 등)을 명시한다.

## 검증 기준
정보 수집 검증 / 섹션 구조 검증 / 초안 검증 / 최종 산출물 검증으로 나누어 확인 항목을 기술한다.

## 부분 재실행 규칙
수정 요청 시 전체 재실행하지 않고 변경 영향 범위에 따라 최소 단계만 재실행하는 규칙을 기술한다.

## 금지 사항
- 입력에 없는 수치(금액·환율 등)를 생성하지 않는다.
- 입력에 없는 기관명·담당자·항목을 생성하지 않는다.
- Toc Agent가 섹션 본문 초안을 작성하지 않는다.
- Planner Agent가 실제 Agent 실행을 수행하지 않는다.
- Orchestrator Agent가 artifact 파일을 직접 저장하지 않는다.
- 중간 산출물 content를 LangGraph State에 저장하지 않는다.
- 외부 검색 금지 조건이 있을 때 외부 검색을 수행하지 않는다.

[생성 규칙]
- 형식 고정: `---` 구분선, 헤딩 레벨, "**담당 Agent:**"/"**필수 여부:**" 표기를 유지한다.
- 정형 vs 기획형 판단: 상세 정보에 고정 양식/법정 서식/사내 표준 양식 뉘앙스가 있으면 정형(depth 2, `1`,`1.1`),
  제안/기획/보고서형이면 기획형(depth 3, `1`,`1-1`,`1-1-1`)을 따른다. 애매하면 정형으로 두고 "[확인 필요]"를 남긴다.
- 조건부 섹션은 반드시 "조건부 섹션"으로 별도 표기하고 발동 조건을 함께 적는다.
"""


def _workflow_stub(code: str, name: str) -> str:
    return (
        f"---\nname: {code.lower()}-workflow-skill\n"
        f"description: 이 Skill은 {name} 작성을 위한 Workflow를 정의한다.\n---\n\n"
        f"# {name} Workflow Skill\n\n"
        f"## 목적\n이 Skill은 {name} 작성을 위한 Workflow를 정의한다. "
        "Planner Agent와 Harness Runtime은 이 Skill을 참조하여 단계 순서, 필수 단계, "
        "섹션 구성 기본 규칙, 승인 지점, 출력 규칙, 검증 기준, 부분 재실행 범위를 결정한다. "
        f"이 Skill은 {name} 본문을 직접 작성하지 않는다.\n\n"
        f"## 보고서 타입\n`{code}`\n\n"
        "## 핵심 원칙\n"
        "1. Workflow는 독립 실행 가능한 단계 단위로 구성한다.\n"
        "2. 전체 실행과 부분 재실행을 모두 지원한다.\n"
        "3. 섹션(목차) 생성 단계에서는 분량이나 페이지 수를 관리하지 않는다.\n"
        "4. 필수 필드 완성도와 규칙 정합성을 중심으로 검증한다.\n"
        "5. 중간 산출물은 Workspace Artifact로 저장한다.\n"
        "6. 신규 섹션 구조 생성 또는 구조 변경 시 사용자 승인을 받아야 한다.\n\n"
        "## 필수 Workflow 단계\n\n"
        "### WF-1. 정보 분석\n**담당 Agent:** Planner Agent  \n**필수 여부:** 필수\n\n"
        "입력·첨부 자료에서 작성에 필요한 기본 정보를 수집·분석한다. 정보 누락 시 사용자에게 추가 입력을 요청한다.\n\n"
        "출력 산출물: `planner/request_info.json`\n\n"
        "### WF-2. 섹션 구조 결정\n**담당 Agent:** Toc Agent  \n**필수 여부:** 필수\n\n"
        "유사 문서와 `TOC_STRUCTURE` Skill을 활용해 섹션 구조를 결정한다. 구조 생성 후 사용자 승인을 받으며, "
        "수정 요청 시 이 단계만 재실행한다.\n\n"
        "출력 산출물: `toc/toc_result.json`, `toc/section_guides.json`\n\n"
        "### WF-3. 섹션별 초안 작성\n**담당 Agent:** Drafting Agent  \n**필수 여부:** 필수\n\n"
        "section guide와 수집 정보를 기반으로 각 섹션 초안을 작성한다.\n\n"
        "출력 산출물: `drafting/sections/` 하위 Markdown 파일\n\n"
        "### WF-4. 필수 항목 및 규칙 검증\n**담당 Agent:** Compliance Agent  \n**필수 여부:** 필수\n\n"
        "초안이 필수 필드와 비즈니스 규칙을 충족하는지, 입력에 없는 수치·항목을 생성하지 않았는지 검증한다.\n\n"
        "출력 산출물: `review/` 하위 JSON 파일\n\n"
        "### WF-5. 최종 산출물 생성\n**담당 Agent:** Artifact Agent  \n**필수 여부:** 필수\n\n"
        "섹션별 Markdown 파일을 조합해 최종 문서를 생성한다.\n\n"
        "출력 산출물: `artifact/final.md`, `artifact/manifest.json`\n\n"
        "## 섹션 기본 규칙\n"
        "- 최대 depth는 2로 한다.\n- section reference 형식은 `1`, `1.1`을 사용한다.\n"
        "- 각 섹션은 section_ref, title, depth, required, conditional, fields, writing guide를 가진다.\n"
        "- 섹션에는 분량이나 페이지 수를 포함하지 않는다.\n\n"
        "## 필수 섹션 커버리지\n생성된 문서가 반드시 포함해야 할 섹션과 조건부 섹션을 명시한다. [확인 필요]\n\n"
        "## 승인 지점\n"
        "신규 섹션 구조 생성 또는 구조 변경 시 사용자 승인이 필요하다. "
        "승인 시 approval type, target artifact ref, allowed actions, resume target, user-facing message를 반환한다.\n"
        "허용 action: APPROVE, REVISE, REJECT\n\n"
        "## 출력 규칙\n"
        "각 단계는 파일을 직접 저장하지 않고 structured output을 반환하며, Artifact Manager가 Workspace에 저장한다.\n"
        "- 요청 정보는 `planner/request_info.json`에 저장한다.\n"
        "- Toc 결과는 `toc/toc_result.json`, section guide는 `toc/section_guides.json`에 저장한다.\n"
        "- Section draft는 `drafting/sections/` 하위 Markdown 파일로 저장한다.\n"
        "- 검증 결과는 `review/` 하위 JSON 파일로 저장한다.\n"
        "- 최종 산출물은 `artifact/` 하위에 저장한다.\n\n"
        "## 검증 기준\n"
        "- 정보 수집 검증: 필수 입력 항목이 모두 수집되었는지 확인한다.\n"
        "- 섹션 구조 검증: 필수 커버리지 반영·조건부 섹션 발동·중복 섹션 여부를 확인한다.\n"
        "- 초안 검증: 필수 필드 기재 여부와 입력에 없는 항목 생성 여부를 확인한다.\n"
        "- 최종 산출물 검증: 출력 형식·섹션 순서·누락 섹션을 확인한다.\n\n"
        "## 부분 재실행 규칙\n"
        "수정 요청 시 전체 Workflow를 재실행하지 않고 변경 영향 범위에 따라 최소 단계만 재실행한다.\n"
        "- 입력 정보 변경: WF-1 이후 영향 단계 재실행\n- 섹션 구조 변경: WF-2 이후 재실행\n"
        "- 특정 섹션 내용 수정: 해당 섹션의 WF-3 이후만 재실행\n- 검증 기준 변경: WF-4만 재실행\n"
        "- 출력 포맷 변경: 최종 산출물 생성 단계만 재실행\n\n"
        "## 금지 사항\n"
        "- 입력에 없는 수치(금액·환율 등)를 생성하지 않는다.\n"
        "- 입력에 없는 기관명·담당자·항목을 생성하지 않는다.\n"
        "- Toc Agent가 섹션 본문 초안을 작성하지 않는다.\n"
        "- Planner Agent가 실제 Agent 실행을 수행하지 않는다.\n"
        "- Orchestrator Agent가 artifact 파일을 직접 저장하지 않는다.\n"
        "- 중간 산출물 content를 LangGraph State에 저장하지 않는다.\n"
        "- 외부 검색 금지 조건이 있을 때 외부 검색을 수행하지 않는다.\n"
    )


# ---------- CONCEPT_EXTRACTION ----------
_CONCEPT_GUIDE = """\
당신은 Agent Harness Runtime에서 사용할 핵심개념 추출(CONCEPT_EXTRACTION) Skill 문서를 생성하는
전문 작성자다. 당신의 역할은 문서 본문을 작성하거나 실제로 개념을 추출하는 것이 아니라,
"어떤 원문 입력에서 어떤 핵심개념들을, 어떤 기준으로 추출해 어떤 JSON 구조로 반환할지"를 정의하는
Skill 문서를 만드는 것이다.

출력은 frontmatter(name, description)로 시작하는 Markdown 문서 하나만 반환한다.
코드블록(```)으로 감싸지 말고, 앞뒤에 설명 문장을 붙이지 않는다.
위에 제시된 보고서 타입 정보(code/이름/상세)만 근거로 사용하고, 상세 정보에 없는 필드명·탐색 단서·값 예시를
임의로 창작하지 않는다. 불확실하면 "[확인 필요]"로 표기한다.

[핵심 설계 원칙 — 개념 개수는 고정하지 않는다]
- 핵심개념 개수는 보고서 타입마다 다르다. 숫자 10을 그대로 남겨두지 않는다.
- 상세 정보에 나열된 정보 항목들을 분석해, 서로 겹치지 않고(mutually exclusive) 문서 작성에 필요한
  최소한의 완전한 집합(collectively exhaustive)이 되도록 개념을 묶는다.
- 개수를 인위적으로 늘리거나 줄이지 않는다. 대략 5~15개가 흔하지만 이는 결과일 뿐 목표치가 아니다.
- 너무 잘게 쪼개진 개념(예: "단가"와 "수량")은 상위 개념(예: "구매 품목")으로 통합하고,
  이질적 정보가 억지로 묶인 개념은 분리한다.
- 개념 개수를 N이라 하고, 문서 전체에서 일관되게 "N개 핵심개념"으로 지칭한다.
- 개념 개수(N) 결정 과정을 출력 전에 내부적으로 수행한다:
  상세 정보의 정보 항목 목록화 → 의미 단위 그룹핑 → 중복/과도한 세분화 제거 → 최종 N개 확정.

[처리 원칙 3분류] 각 개념은 반드시 다음 중 하나로 분류한다.
1. "원문 추출, 실패 시 사용자 입력 필요" (원문에 있을 가능성이 높은 항목)
2. "원문 추출을 통해 [특정 부분]을 뽑고 [나머지]는 사용자에게 입력받는다" (부분 추출형/혼합형)
3. "사용자 입력 항목 (기본 `사용자 입력 필요`)" (원문 근거가 없고 사용자만 아는 항목)

[source 라벨] 문서 성격에 맞게 명명한다(구매품의서류는 DOCUMENT, RFP류는 RFP 등).
source 허용값: {원문라벨} / USER_INPUT / {원문라벨}+USER_INPUT / RECOMMENDED. 애매하면 "[확인 필요]".

다음 템플릿 구조를 그대로 따르되 내용을 이 보고서 타입에 맞게 채운다.

[템플릿 구조]

---
name: concept-extraction-(code를 소문자 kebab-case로 변환)
description: 이 Skill은 {name} 작성을 위한 핵심개념을 추출하기 위한 Skill이다.
---

# {name} 핵심개념 추출 스킬

주어진 입력은 **(원문 입력 형태)**와 **사용자 발화(user_feedback)**이다.
목표는 {name} 작성에 필요한 **고정 N개 핵심개념**을 추출해 정해진 JSON 구조로 정리하는 것이다.

## 기본 원칙
1. 원문에서 먼저 추출한다.
2. 원문에서 추출해야 하는 항목은 문서 근거로 최대한 채운다.
3. 문서에 없는 내용을 상식으로 보완·추정하지 않는다.
4. 약어만 있으면 가능한 한 원문 표현을 유지한다.
5. 값이 불명확하면 `사용자 입력 필요`로 둔다.
6. 사용자 입력 항목이라도 사용자 요청·user_feedback에 값이 제공되면 그 값으로 채운다.
   (제공된 정보 전체를 항목별로 점검해 일부만 반영하고 나머지를 빠뜨리지 않는다.)
7. 추천 위임 처리: 기본값이 `사용자 입력 필요`인 항목을 사용자가 "추천/알아서"로 위임하면
   원문·다른 개념·user_feedback을 근거로 가안(추천안)을 만들어 채우고 `source`를 `RECOMMENDED`로 둔다.
   (근거 없는 순수 창작 금지.)
8. 최종 출력은 출력 계약의 JSON 객체 하나만 반환한다. 코드블록·해설을 덧붙이지 않는다.

## N개 핵심개념 정의
표의 항목 수(N개)는 상세 정보에서 도출된 결과이며 고정된 숫자가 아니다.
| code | 의미 | 처리 원칙 | 탐색 단서 |
|------|------|-----------|-----------|
| (concept_code) | (의미) | (3분류 중 하나) | (원문에서 찾을 키워드·표현) |
| ... (N개까지) | | | |
값 표기 예외 규칙(미기입 표기, 빈 배열 허용 등)은 표 아래 각주로 명시한다.
위임 가능 항목별로 어떤 다른 개념을 조합해 가안을 도출하는지 구체적으로 서술한다.

## 출력 계약 (가장 중요 — 반드시 준수)
- 출력 구조는 배열 형태를 따른다: {"concepts": [ ... ]}.
- 위 N개 개념을 각각 하나의 항목으로 모두 포함한다(항상 N개, 누락 금지).
- 각 항목 필드: code(표의 고정 code, 변경 금지) / name / value(복수면 배열, 구조면 객체,
  못 뽑으면 정확히 "사용자 입력 필요") / source({원문라벨}/USER_INPUT/{원문라벨}+USER_INPUT/RECOMMENDED) /
  (위임 가안이면 선택적으로) basis(가안 도출 근거).
- 자유 이름을 새 개념으로 만들지 않는다. 해당 내용은 N개 code의 value 안에 넣는다.
- 출력 예시(JSON)를 상세 정보 기반 샘플 값으로 하나 제시한다.

## 값 정제 규칙
- 문서 표현을 유지하되 불필요한 수식어는 제거한다.
- 동일 의미 중복은 하나로 합치고, 긴 문장은 핵심 명사구로 축약한다.
- 수치·단위·날짜·고유명사(기관명·제품명·기술명)는 원문 그대로 보존한다.
- (상세 정보에 명시된 값 형식 규칙 — 금액 정수화, 날짜 YYYY-MM-DD 정규화 등)

## 반드시 지킬 것
- 최종 답변은 출력 계약의 JSON만 출력(코드블록·설명 금지).
- 항상 N개 code를 전부 포함(누락 금지). 못 뽑은 항목은 value를 "사용자 입력 필요"로.
- code 값은 표의 N개에서만 사용 — 새 code·자유 이름 개념 생성 금지.
- 사용자 제공 정보가 있으면 원문 추출 항목/사용자 입력 항목 모두 해당 값으로 갱신한다.
- 추정·창작 금지. 단, 사용자가 위임한 항목은 근거 기반 가안 허용(source=RECOMMENDED).
"""


def _concept_stub(code: str, name: str) -> str:
    return (
        f"---\nname: concept-extraction-{code.lower()}\n"
        f"description: 이 Skill은 {name} 작성을 위한 핵심개념을 추출하기 위한 Skill이다.\n---\n\n"
        f"# {name} 핵심개념 추출 스킬\n\n"
        f"주어진 입력은 **{name} 원문**과 **사용자 발화(user_feedback)**이다. "
        f"목표는 {name} 작성에 필요한 **고정 N개 핵심개념**을 추출해 정해진 JSON 구조로 정리하는 것이다. "
        "(N은 보고서 타입 상세 정보에서 도출된 결과이며 고정된 숫자가 아니다.)\n\n"
        "## 기본 원칙\n"
        "1. 원문에서 먼저 추출한다.\n"
        "2. 원문에서 추출해야 하는 항목은 문서 근거로 최대한 채운다.\n"
        "3. 문서에 없는 내용을 상식으로 보완·추정하지 않는다.\n"
        "4. 약어만 있으면 가능한 한 원문 표현을 유지한다.\n"
        "5. 값이 불명확하면 `사용자 입력 필요`로 둔다.\n"
        "6. 사용자 입력 항목이라도 user_feedback에 값이 제공되면 그 값으로 채운다.\n"
        "7. 위임(\"추천/알아서\") 시 근거 기반 가안으로 채우고 `source`를 `RECOMMENDED`로 둔다.\n"
        "8. 최종 출력은 출력 계약의 JSON 객체 하나만 반환한다.\n\n"
        "## N개 핵심개념 정의\n"
        "표의 항목 수(N개)는 상세 정보에서 도출된 결과이며 고정된 숫자가 아니다. [확인 필요]\n"
        "| code | 의미 | 처리 원칙 | 탐색 단서 |\n|------|------|-----------|-----------|\n"
        "| `concept_1` | (핵심개념 1) | 원문 추출, 실패 시 사용자 입력 필요 | — |\n"
        "| ... | ... | ... | ... |\n\n"
        "## 출력 계약\n"
        '- 출력 구조는 `{"concepts": [ ... ]}` 배열 형태를 따른다.\n'
        "- 위 N개 개념을 각각 하나의 항목으로 모두 포함한다(항상 N개, 누락 금지).\n"
        "- 각 항목은 `code`, `name`, `value`, `source`(DOCUMENT/USER_INPUT/DOCUMENT+USER_INPUT/RECOMMENDED)를 가진다.\n"
        "- 자유 이름을 새 개념으로 만들지 않는다. 해당 내용은 N개 code의 `value` 안에 넣는다.\n\n"
        "## 값 정제 규칙\n"
        "- 문서 표현을 유지하되 불필요한 수식어는 제거한다.\n"
        "- 동일 의미 중복은 하나로 합치고, 긴 문장은 핵심 명사구로 축약한다.\n"
        "- 수치·단위·날짜·고유명사는 원문 그대로 보존한다.\n\n"
        "## 반드시 지킬 것\n"
        "- 최종 답변은 JSON만 출력한다 (코드블록·설명 금지).\n"
        "- 항상 N개 code를 전부 포함한다. 못 뽑은 항목은 `value`를 `\"사용자 입력 필요\"`로 둔다.\n"
        "- `code` 값은 표의 N개에서만 사용하고 새 code를 생성하지 않는다.\n"
    )


# ---------- EVALUATION_POLICY ----------
_EVALUATION_GUIDE = """\
당신은 Agent Harness Runtime에서 사용할 평가 기준(EVALUATION_POLICY) Skill 문서를 생성하는
전문 작성자다. 당신의 역할은 실제로 문서를 평가하는 것이 아니라, "완성된 문서의 각 섹션이 어떤
목차/항목에 해당하는지 판별하고, 그 항목에 어떤 기준표로 품질을 채점할지"를 정의하는 Skill 문서를
만드는 것이다.

출력은 frontmatter(name, description)로 시작하는 Markdown 문서 하나만 반환한다.
코드블록(```)으로 감싸지 말고, 앞뒤에 설명 문장을 붙이지 않는다.
위에 제시된 보고서 타입 정보(code/이름/상세)만 근거로 사용하고, 상세 정보에 없는 장·절·평가항목·배점을
임의로 창작하지 않는다. 목차 구조나 배점 총합이 불명확하면 "[확인 필요]"로 표기한다.

[핵심 설계 원칙 — 구조는 문서 성격에 따라 계층형/평면형으로 분기한다]
상세 정보의 목차 구조를 보고 다음 중 하나로 판단한다. 애매하면 "[확인 필요]"로 두고 계층/평면을 단순화하지 않는다.
- 계층형(제안서형): 장(1장, 2장…) 아래에 절(1.1, 1.2…)이 있고, 각 절마다 평가표가 있으며,
  각 장 끝에 그 장에 대한 "종합(구성·표현)" 표가 별도로 붙는다.
- 평면형(정형 문서형): 장 구분 없이 섹션이 번호순으로 나열되고, 각 섹션마다 평가표가 있으며,
  "종합(구성·표현)" 표는 문서 전체 맨 끝에 한 번만 붙는다.
목차/섹션 개수와 각 절의 평가 세부항목 개수는 고정값이 아니다. 상세 정보의 목차·평가 관점 개수만큼 만든다.

[평가 기준표 공통 열]
| No | 평가 대영역 | 평가 세부항목 | 평가 기준 (상세 설명) | 배점 | 우수 (상) | 보통 (중) | 미흡 (하) |

다음 템플릿을 판단된 구조(계층형/평면형)에 맞게 채운다.

[템플릿 구조]

---
name: evaluation-(code를 소문자 kebab-case로 변환)
description: {name}의 각 섹션이 요구 기준을 충족하는지 평가하는 스킬. 목차/항목별 평가 기준표를 적용하여 평가 관점을 평가한다.
---

# 개요
이 스킬은 작성된 {name}의 품질을 평가할 때 사용한다.
평가 대상 섹션이 어떤 목차/항목에 해당하는지 먼저 판단한 뒤, 해당 목차/항목의 평가 기준표를 적용하여
내용의 (평가 관점 — 예: 적절성·충실성·구체성 / 완성도·정확성·충분성)을 평가한다.

# 평가 기준표

[계층형인 경우] 아래 패턴을 장 수만큼 반복한다.
## (장 번호)장
### (절 번호) (절 제목)   ← 조건부 절이면 제목 옆에 "(해당 시)" 표기
| No | 평가 대영역 | 평가 세부항목 | 평가 기준 (상세 설명) | 배점 | 우수 (상) | 보통 (중) | 미흡 (하) |
(절 반복 후) 각 장 끝에:
### 종합(구성·표현)   ← 목차 체계성·시각자료 활용 등을 그 장 성격에 맞게 평가

[평면형인 경우] 아래 패턴을 섹션 수만큼 반복한다.
## (N). (섹션명)   ← 조건부 섹션이면 "(해당 시)" 표기
| No | 평가 대영역 | 평가 세부항목 | 평가 기준 (상세 설명) | 배점 | 우수 (상) | 보통 (중) | 미흡 (하) |
(섹션 반복 후) 문서 전체 맨 끝에 한 번만:
## 종합 (구성·표현)

[생성 규칙]
1. 평가 세부항목은 확인 가능한 질문형으로 작성한다("~가 명확히 정의되었는가?"). 추상적 형용사만 나열하지 않는다.
2. 3단계 등급(우수/보통/미흡)은 항상 구체적 조건 차이로 구분한다. 등급명만 바꾸지 않는다.
   ("우수"는 어떤 요소가 몇 개 이상 어떤 형태로 포함되는지, "미흡"은 어떤 누락/추상 상태인지 명확히.)
3. 배점 설계: 총점이 명시되면 항목 배점 합이 정확히 그 총점과 일치하도록 배분한다.
   명시가 없으면 총점 100점을 가정하고 그 가정을 명시하며, 핵심 항목(최종 목표·금액 정합성 등)에 더 높은 배점을 준다.
4. 평가 대영역·세부항목은 같은 보고서 타입의 Workflow Skill "필수 섹션"과 Concept Extraction "핵심개념"의
   항목명·용어를 그대로 재사용해, 세 Skill 간 용어가 어긋나지 않도록 한다.
5. 조건부 섹션은 제목에 "(해당 시)"를 표기하고 상세 설명에 발동 조건(외화 포함, 렌탈 품목, 공개SW 활용 등)을 명시한다.
6. 종합(구성·표현) 배치: 계층형은 각 장 끝에(장마다 시각자료 종류를 다르게 구체화), 평면형은 문서 맨 끝에 한 번만.
"""


def _evaluation_stub(code: str, name: str) -> str:
    return (
        f"---\nname: evaluation-{code.lower()}\n"
        f"description: {name}의 각 섹션이 요구 기준을 충족하는지 평가하는 스킬. "
        "목차/항목별 평가 기준표를 적용하여 평가 관점을 평가한다.\n---\n\n"
        "# 개요\n"
        f"이 스킬은 작성된 {name}의 품질을 평가할 때 사용한다. "
        "평가 대상 섹션이 어떤 목차/항목에 해당하는지 먼저 판단한 뒤, 해당 목차/항목의 평가 기준표를 적용하여 "
        "내용의 완성도·정확성·충분성을 평가한다.\n\n"
        "> 목차 구조(계층형/평면형)와 배점 총합은 보고서 타입 상세 정보에서 도출한다. [확인 필요]\n\n"
        "# 평가 기준표\n\n## 1. (섹션명)\n\n"
        "| No | 평가 대영역 | 평가 세부항목 | 평가 기준 (상세 설명) | 배점 | 우수 (상) | 보통 (중) | 미흡 (하) |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | (대영역) | (세부항목이 명확히 정의되었는가?) | (구체적 확인 질문) | 10 | (상 조건) | (중 조건) | (하 조건) |\n\n"
        "## 종합 (구성·표현)\n\n"
        "| No | 평가 대영역 | 평가 세부항목 | 평가 기준 (상세 설명) | 배점 | 우수 (상) | 보통 (중) | 미흡 (하) |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | 구성 체계 | 항목 순서 및 누락 여부 | 필수 항목이 모두 포함되고 순서가 자연스러운지 | 5 | (상) | (중) | (하) |\n"
        "| 2 | 표현 명확성 | 수치·날짜 표기 일관성 | 표기 형식이 문서 전체에서 일관되는지 | 5 | (상) | (중) | (하) |\n"
    )


# skill_type(code) → (LLM 프롬프트 가이드, stub 생성 함수)
_SKILLS: dict[str, tuple[str, Any]] = {
    WORKFLOW: (_WORKFLOW_GUIDE, _workflow_stub),
    CONCEPT_EXTRACTION: (_CONCEPT_GUIDE, _concept_stub),
    EVALUATION_POLICY: (_EVALUATION_GUIDE, _evaluation_stub),
}


class ReportSkillAgent:
    """보고서 타입 컨텍스트로 skill_type에 맞는 스킬 정의 문서를 생성하는 Agent."""

    async def _prepare_node(self, state: ReportSkillState) -> dict[str, Any]:
        skill_type = state["skill_type"]
        entry = _SKILLS.get(skill_type)
        if entry is None:
            raise ValueError(f"지원하지 않는 skill_type: {skill_type}")
        guide, stub_fn = entry
        stub = stub_fn(state["code"], state["name"])
        return {"guide": guide, "stub": stub}

    async def _generate_node(self, state: ReportSkillState) -> dict[str, Any]:
        spec: LlmSpec = state["llm"]
        if llm._use_stub(spec.secret):
            return {"content": state["stub"]}
        filled = state["guide"].replace("{name}", state["name"]).replace("{code}", state["code"])
        prompt = _ctx_block(state["code"], state["name"], state.get("description", "")) + "\n" + filled
        content = await llm.complete(prompt, spec)
        return {"content": content}

    def build(self) -> CompiledStateGraph:
        g = StateGraph(ReportSkillState)
        g.add_node("prepare", self._prepare_node)
        g.add_node("generate", self._generate_node)
        g.add_edge(START, "prepare")
        g.add_edge("prepare", "generate")
        g.add_edge("generate", END)
        return g.compile()


def build_report_skill_agent() -> CompiledStateGraph:
    """진입점: 스킬 정의 생성 Agent 그래프를 반환."""
    return ReportSkillAgent().build()


report_skill_agent = build_report_skill_agent()
 