"""문서 1건 분석 Agent (LangGraph StateGraph).

단계: 원문 추출 → Summary 생성 → Chunk 생성 → Embedding 생성 → Report Skill 추출.
Embedding 노드에서 청크별 벡터와 키워드(keywords/keywords_text)를 함께 산출해
청크에 실어 둔다. 최종 저장(saveData)은 재계산 없이 이 값을 그대로 적재한다.

LLM_STUB_MODE 또는 secret 미설정 시 외부 호출 없이 결정적 결과를 만든다.
"""
import asyncio
import logging
import re
from math import ceil
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents import document_skills
from app.services import llm
from app.services.llm import EmbeddingSpec, LlmSpec

logger = logging.getLogger(__name__)

MAX_CHUNKS = 8  # 데모 저장용 청크 상한 (요청 chunk_count는 origin_data에 별도 기록)


class FileState(TypedDict, total=False):
    file_name: str
    file_path: str  # 로컬 스토리지 경로. 없으면 placeholder 원문으로 폴백.
    title: str  # 원문 제목(파일명 확장자 제거). 스킬 추출 프롬프트에 전달.
    report_type_name: str
    report_type_detail: str  # 보고서 타입 상세(참고용). 스킬 추출 프롬프트에 전달.
    skills: list[dict[str, Any]]  # [{name,status,content}]
    chunk_count: int
    llm: LlmSpec
    embed: EmbeddingSpec  # embedding 노드용 스펙
    text: str
    reporter: str  # 원문에서 추출한 보고자/작성 기관
    summary: str
    # chunk 노드는 [{order,text}], embedding 노드가 embedding/keywords/keywords_text를 덧붙인다.
    chunks: list[dict[str, Any]]
    results: list[dict[str, Any]]  # [{type,title,preview,content}]


class DocumentAnalysisAgent:
    """문서 1건을 추출·요약·청킹하고 Report Skill을 추출하는 분석 Agent."""

    async def _extract_node(self, state: FileState) -> dict[str, Any]:
        name = state["file_name"]
        # 재분석: 이미 확보한 실제 원문이 있으면 그대로 재사용한다.
        existing = state.get("text", "")
        if existing.strip():
            return {"text": existing}
        path = state.get("file_path", "")
        if path:
            from pathlib import Path

            from app.services import document_parser

            try:
                text = document_parser.parse_to_markdown(Path(path))
            except Exception:
                logger.exception("원문 파싱 실패: file=%s path=%s", name, path)
                text = ""
            if text.strip():
                return {"text": text}
            logger.error("원문 파싱 결과가 비어 있음: file=%s path=%s", name, path)
        else:
            logger.error("원문 파일 경로가 없음: file=%s", name)

        # 원문 확보 실패. 실제 LLM 모드에서는 placeholder를 원문인 것처럼 넘기면
        # 실제 문서가 아닌 가짜 텍스트로 스킬(목차 등)이 생성되므로 명시적으로 실패시킨다.
        spec: LlmSpec = state["llm"]
        if not llm._use_stub(spec.secret):
            raise RuntimeError(
                f"원문을 확보하지 못했습니다 (file={name}). "
                "파일 경로와 파싱 상태를 확인하세요. "
                "placeholder 텍스트로 스킬을 생성하지 않습니다."
            )
        # stub 모드(secret 미설정/LLM_STUB_MODE): 파이프라인 검증용 placeholder만 허용한다.
        logger.warning("stub 모드 placeholder 원문 사용: file=%s", name)
        text = (
            f"{name} 문서의 원문입니다. "
            f"본 문서는 {state.get('report_type_name', '')} 유형으로 분류되며, "
            "개요·현황·분석·결론의 구조로 구성됩니다. "
            "핵심 주제와 근거, 결론을 포함합니다."
        )
        return {"text": text}

    async def _summary_node(self, state: FileState) -> dict[str, Any]:
        text = state.get("text", "")
        spec: LlmSpec = state["llm"]
        if llm._use_stub(spec.secret):
            summary = f"{state['file_name']} 문서의 핵심 내용을 요약한 결과입니다. 주요 주제와 결론을 담고 있습니다."
            return {"summary": summary, "reporter": ""}
        # summary는 중요 산출물이 아니므로 전체 요약 대신 앞부분만 예산 내로 잘라 1회 호출한다.
        # (map-reduce는 큰 문서에서 조각 수만큼 순차 호출해 지연이 커진다.)
        head = llm.clip_for_prompt(text, reserve_tokens=256)
        summary = await llm.complete(f"다음 문서를 3문장으로 요약하라:\n{head}", spec)
        # 보고자/작성 기관도 문서 앞부분(표지·머리말)에 나오므로 같은 앞부분에서 추출한다.
        reporter = await llm.complete(
            "다음 문서의 작성 기관 또는 보고자(작성자)명만 한 줄로 답하라. "
            "명확하지 않으면 빈 줄로 답하라. 다른 설명 금지.\n" + head,
            spec,
        )
        return {"summary": summary, "reporter": reporter.strip()[:100]}

    async def _chunk_node(self, state: FileState) -> dict[str, Any]:
        n = max(1, min(state.get("chunk_count", 1), MAX_CHUNKS))
        text = state.get("text", "").strip()
        if not text:
            return {"chunks": []}
        # 실제 원문을 n등분해 청크로 만든다(가짜 placeholder 텍스트 금지).
        # 저장되는 content(청크 join)와 재분석(rerun) 원문이 실제 원문을 보존해야
        # 이후 재분석·임베딩이 가짜 텍스트가 아닌 실제 원문을 사용한다.
        size = ceil(len(text) / n)
        chunks: list[dict[str, Any]] = []
        for i in range(n):
            seg = text[i * size : (i + 1) * size]
            if seg.strip():
                chunks.append({"order": len(chunks) + 1, "text": seg})
        return {"chunks": chunks}

    async def _embedding_node(self, state: FileState) -> dict[str, Any]:
        """청크별 임베딩 벡터와 키워드를 생성해 청크에 실어 둔다.

        여기서 계산한 embedding/keywords/keywords_text를 저장 단계에서 재계산 없이 그대로 쓴다.
        keywords_text는 report_chunk_data.mecab_tsv(C가중치) 전문검색에 사용된다.
        """
        chunks = state.get("chunks", [])
        if not chunks:
            return {"chunks": []}
        embed_spec: EmbeddingSpec = state["embed"]
        llm_spec: LlmSpec = state["llm"]
        texts = [c["text"] for c in chunks]
        vectors = await llm.embed(texts, embed_spec)
        enriched: list[dict[str, Any]] = []
        for c, vec in zip(chunks, vectors):
            keywords = await self._extract_keywords(c["text"], llm_spec)
            enriched.append(
                {
                    **c,
                    "embedding": vec,
                    "keywords": keywords,
                    "keywords_text": " ".join(keywords),
                }
            )
        return {"chunks": enriched}

    async def _extract_keywords(self, text: str, spec: LlmSpec) -> list[str]:
        """청크 텍스트에서 핵심 키워드를 추출한다(전문검색 C가중치용)."""
        if llm._use_stub(spec.secret):
            # 결정적: 2글자 이상 토큰을 등장 순서대로 중복 제거해 상위 5개.
            seen: list[str] = []
            for tok in re.findall(r"[0-9A-Za-z가-힣]{2,}", text):
                if tok not in seen:
                    seen.append(tok)
                if len(seen) >= 5:
                    break
            return seen
        raw = await llm.complete(
            "다음 텍스트의 핵심 키워드만 쉼표로 구분해 5개 이내로 답하라. "
            "설명·문장 없이 키워드만.\n" + llm.clip_for_prompt(text, reserve_tokens=128),
            spec,
        )
        kws = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
        return kws[:10]

    async def _skill_node(self, state: FileState) -> dict[str, Any]:
        """원문(origin_document)을 근거로 문서 스킬을 추출한다. 현재: 목차 스킬(TOC), 문체 스킬(STYLE)."""
        spec: LlmSpec = state["llm"]
        text = state.get("text", "")
        summary = state.get("summary", "")
        title = state.get("title", "")
        report_type_name = state.get("report_type_name", "")
        report_type_detail = state.get("report_type_detail", "")
        use_stub = llm._use_stub(spec.secret)

        results: list[dict[str, Any]] = [
            {
                "type": "SUMMARY",
                "title": "Summary",
                "preview": summary[:60],
                "content": summary,
            }
        ]

        if use_stub:
            toc = document_skills.toc_skill_stub(report_type_name)
            style = document_skills.style_skill_stub(report_type_name)
        else:
            from app.services import document_parser

            # 목차 스킬(TOC): origin_document + 결정론적 구조 아웃라인 기반 재사용 규칙 SKILL.md.
            # 아웃라인(계층·번호·제목·섹션별 분량)을 코드로 뽑아 프롬프트에 주입하면
            # 하위 뎁스 누락과 분량 미측정(LLM이 대용량 원문에서 못 세는 문제)이 해소된다.
            # 템플릿+아웃라인이 차지하는 토큰을 뺀 예산으로 원문을 잘라 넣는다(컨텍스트 한도 초과 방지).
            outline = document_parser.build_outline(text)
            toc_base = document_skills.build_toc_prompt(
                report_type_name, report_type_detail, "", outline
            )
            toc_doc = llm.clip_for_prompt(text, reserve_tokens=llm.count_tokens(toc_base) + 128)
            toc_prompt = document_skills.build_toc_prompt(
                report_type_name, report_type_detail, toc_doc, outline
            )

            # 문체 스킬(STYLE): HOW(문체·형식)만 규정하는 재사용 STYLE 가이드.
            style_base = document_skills.build_style_prompt(
                report_type_name, report_type_detail, title, ""
            )
            style_doc = llm.clip_for_prompt(
                text, reserve_tokens=llm.count_tokens(style_base) + 128
            )
            style_prompt = document_skills.build_style_prompt(
                report_type_name, report_type_detail, title, style_doc
            )

            # TOC/STYLE는 서로 독립적인 LLM 호출이라 동시에 실행해 skill 노드 지연을 줄인다.
            toc, style = await asyncio.gather(
                llm.complete(toc_prompt, spec),
                llm.complete(style_prompt, spec),
            )

        results.append(
            {"type": "TOC", "title": "목차 스킬", "preview": toc[:60], "content": toc}
        )
        results.append(
            {"type": "STYLE", "title": "문체 스킬", "preview": style[:60], "content": style}
        )
        return {"results": results}

    def build(self) -> CompiledStateGraph:
        g = StateGraph(FileState)
        g.add_node("extract", self._extract_node)
        g.add_node("summary", self._summary_node)
        g.add_node("chunk", self._chunk_node)
        g.add_node("embedding", self._embedding_node)
        g.add_node("skill", self._skill_node)
        g.add_edge(START, "extract")
        g.add_edge("extract", "summary")
        g.add_edge("summary", "chunk")
        g.add_edge("chunk", "embedding")
        g.add_edge("embedding", "skill")
        g.add_edge("skill", END)
        return g.compile()


def build_document_analysis_agent() -> CompiledStateGraph:
    """진입점: 문서 분석 Agent 그래프를 반환."""
    return DocumentAnalysisAgent().build()


document_analysis_agent = build_document_analysis_agent()
