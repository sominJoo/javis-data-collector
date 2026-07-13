"""LLM/Embedding 호출 래퍼.

API Key의 llm/embedding config(provider/endpoint/model + 암호화된 secret)를 사용한다.
`LLM_STUB_MODE=true` 이거나 secret이 없으면 외부 호출 없이 결정적 stub을 반환한다.

원문이 큰 문서는 프롬프트가 모델 컨텍스트 한도를 넘어 400(BadRequest)이 나므로,
전체 원문을 넣는 프롬프트(요약/보고자/TOC/STYLE/키워드)는 clip_for_prompt()로
토큰 예산(llm_max_input_tokens) 이하로 잘라 넣는다.
토큰 카운트는 cl100k_base로 측정한다. 한글은 이 인코더에서 토큰이 과대 추정되는 경향이라,
실제 대상 모델 한도(예: 32768) 대비 보수적(안전한) 예산이 된다.
"""
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings


@dataclass
class LlmSpec:
    endpoint: str
    model: str
    secret: str | None = None


@dataclass
class EmbeddingSpec:
    endpoint: str
    model: str
    dimension: int = 1536
    secret: str | None = None


def _effective_secret(secret: str | None) -> str | None:
    """per-key secret 우선, 없으면 전역 OPENAI_API_KEY로 fallback."""
    return secret or get_settings().openai_api_key


def _use_stub(secret: str | None) -> bool:
    return get_settings().llm_stub_mode or not _effective_secret(secret)


async def complete(prompt: str, spec: LlmSpec) -> str:
    if _use_stub(spec.secret):
        return f"[stub:{spec.model}]\n{prompt.strip()[:400]}"
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        base_url=spec.endpoint,
        api_key=_effective_secret(spec.secret),
        model=spec.model,
        temperature=0.2,
        # extra_body={"chat_template_kwargs": {"enable_thinking": False}},  # ← 추론 OFF  
    )
    resp = await llm.ainvoke(prompt)
    return resp.content if isinstance(resp.content, str) else str(resp.content)


# ---------- 토큰 예산 유틸 ----------
@lru_cache
def _encoder():
    """토큰 카운트용 인코더. cl100k_base는 한글 토큰을 과대 추정하므로 안전측(보수적)."""
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text or ""))


def clip_to_tokens(text: str, max_tokens: int) -> str:
    """text를 max_tokens 이하로 자른다(초과분 절단)."""
    if max_tokens <= 0:
        return ""
    enc = _encoder()
    toks = enc.encode(text or "")
    if len(toks) <= max_tokens:
        return text
    return enc.decode(toks[:max_tokens])


def clip_for_prompt(document: str, reserve_tokens: int = 0) -> str:
    """전체 원문을 넣는 프롬프트용 원문 클리핑.

    reserve_tokens: 프롬프트 템플릿·지시문·출력에 남겨둘 토큰 여유.
    (llm_max_input_tokens - reserve_tokens) 예산으로 원문을 자른다.
    """
    budget = get_settings().llm_max_input_tokens - max(0, reserve_tokens)
    return clip_to_tokens(document, budget)


async def embed(texts: list[str], spec: EmbeddingSpec) -> list[list[float]]:
    if _use_stub(spec.secret):
        # 결정적 pseudo-embedding: 텍스트 해시 기반. 실제 유사도 의미는 없고 파이프라인 검증용.
        import hashlib

        out: list[list[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode()).digest()
            vec = [((h[i % len(h)] / 255.0) * 2 - 1) for i in range(spec.dimension)]
            out.append(vec)
        return out

    from langchain_openai import OpenAIEmbeddings

    client = OpenAIEmbeddings(
        base_url=spec.endpoint, api_key=_effective_secret(spec.secret), model=spec.model
    )
    return await client.aembed_documents(texts)
