"""업로드된 원문 파일을 텍스트/마크다운으로 파싱한다.

- PDF: pdfplumber로 페이지별 텍스트를 추출(다단계 폴백)해 마크다운으로 조립하고,
  번호 체계(`1.`, `1-1.`, `(1)`, `①` 등)를 규칙 기반으로 마크다운 헤딩으로 승격한다.
  이 헤딩 구조가 스킬 추출(목차 등)의 grounding 근거가 된다.
- md/txt: 인코딩을 추정해 그대로 읽는다.
(페이지 이미지 기반 LLM 재구성/표 복원은 후속 단계에서 확장.)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PARAGRAPH_GAP_RE = re.compile(r"\n{3,}")
_TEXT_ENCODINGS = ("utf-8", "utf-8-sig", "cp949", "euc-kr")

# 목차(TOC)의 점 리더 + 뒤따르는 페이지번호 제거용. 예: "1. 개요 ······· 1"
_DOT_LEADER_RE = re.compile(r"\s*[·.]{3,}\s*\d*\s*$")

# 대시 번호(1-1., 1-2-1. …): 세그먼트 깊이에 따라 레벨을 매긴다.
# 대시 1개(1-1.)→H3, 2개(1-2-1.)→H4 … 로 계층을 보존한다. (마침표 생략형 "4-2 …"도 허용)
_DASH_RE = re.compile(r"^(\d{1,2}(?:-\d{1,2}){1,3})(?:\.\s*|\s+).+$")
# 단일 번호(1.)→H2. 번호는 1~2자리로 제한해 연도(2018.) 오탐을 막는다.
_H2_RE = re.compile(r"^\d{1,2}\.\s*.+$")
# 그 외 고정 레벨 규칙. (정규식, 헤딩 레벨). 대시·H2보다 낮은 세부 레벨.
_HEADING_RULES: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^\(\d{1,2}\)\s*.+$"), 5),                      # (1)
    (re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]\s*.+$"), 6),               # ①
    (re.compile(r"^\[[^\]]{1,40}\]\s*$"), 5),                    # [대괄호 섹션]
    (re.compile(r"^\d{1,2}차년도\b.*$"), 5),                      # 1차년도
    (re.compile(r"^WP\d{1,2}\s*:\s*.+$", re.IGNORECASE), 5),     # WP1: ...
)

# 헤딩으로 승격하지 않을 줄의 시작 문자(불릿/표/기존 헤딩/설명형 'ㅇ' 등).
_SKIP_PREFIXES = ("|", "ㅇ", "#", ">", "*", "-", "•")
# 승격 후보 제목의 최대 길이(본문 문장 오탐 방지).
_HEADING_MAX_LEN = 60


def _clean_markdown(text: str) -> str:
    """연속 빈 줄 축약 + 줄 끝 공백 제거."""
    text = _PARAGRAPH_GAP_RE.sub("\n\n", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip() + "\n"


def _page_header(page_num: int, status: str = "") -> str:
    header = f"---\n**페이지 {page_num}**"
    if status:
        header += f" ({status})"
    return header + "\n---"


def _promote_line(line: str) -> str:
    """번호 체계로 시작하는 짧은 줄을 마크다운 헤딩으로 승격한다."""
    stripped = line.strip()
    if not stripped or stripped.startswith(_SKIP_PREFIXES):
        return line
    core = _DOT_LEADER_RE.sub("", stripped).strip()
    if not core or len(core) > _HEADING_MAX_LEN:
        return line
    dash = _DASH_RE.match(core)
    if dash:
        level = 2 + dash.group(1).count("-")  # 1-1→H3, 1-2-1→H4
        return f"{'#' * level} {core}"
    if _H2_RE.match(core):
        return f"## {core}"
    for pattern, level in _HEADING_RULES:
        if pattern.match(core):
            return f"{'#' * level} {core}"
    return line


def _promote_headings(text: str) -> str:
    """페이지 텍스트 전체에 헤딩 승격을 적용한다."""
    return "\n".join(_promote_line(ln) for ln in text.split("\n"))


def _extract_page_text(page: Any) -> str:
    """단일 페이지에서 텍스트를 추출한다. 실패 시 단계적으로 폴백한다."""
    for kwargs in ({}, {"layout": True}, {"x_tolerance": 3, "y_tolerance": 3}):
        try:
            text = page.extract_text(**kwargs)
        except Exception:
            continue
        if text and text.strip():
            return text
    # 최종 폴백: 문자 단위 조립.
    try:
        chars = page.chars
        if chars:
            text = "".join(c.get("text", "") for c in chars)
            if text.strip():
                return text
    except Exception:
        pass
    return ""


def _parse_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - 의존성 미설치 방어
        raise RuntimeError("pdfplumber가 설치되어 있지 않습니다. (pip install pdfplumber)") from exc

    lines: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = _extract_page_text(page)
            if text.strip():
                lines.append(_page_header(page_num))
                lines.append(_promote_headings(text))
            else:
                lines.append(_page_header(page_num, "텍스트 없음"))
            lines.append("")
    return _clean_markdown("\n".join(lines))


def _read_text(path: Path) -> str:
    for enc in _TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def parse_to_markdown(path: Path) -> str:
    """파일 확장자에 따라 원문을 마크다운/텍스트로 변환한다.

    지원하지 않는 확장자는 텍스트로 best-effort 읽기를 시도한다.
    """
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    return _read_text(path)


_MD_HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"
# 경로 정렬 시 대시 소절(작은 정수)과 겹치지 않도록 상대 마커에 오프셋을 준다.
_OFF_PAREN, _OFF_CIRC, _OFF_YEAR = 100, 200, 300


def _is_noise_line(text: str) -> bool:
    """분량 계산에서 제외할 줄(빈 줄·페이지 마커·구분선·헤딩)."""
    if not text:
        return True
    if text.startswith("#"):
        return True
    if text == "---" or text.startswith("**페이지"):
        return True
    return False


def _parse_marker(title: str) -> tuple[str | None, object]:
    """헤딩 제목 앞 번호/기호를 (종류, 값)으로 해석한다."""
    t = title.strip()
    m = re.match(r"^(\d{1,2}(?:-\d{1,2}){1,3})(?:\.|\s)", t)  # 1-1., 1-2-1.
    if m:
        return "dash", tuple(int(x) for x in m.group(1).split("-"))
    m = re.match(r"^(\d{1,2})(?:\.|\s)", t)  # 1.
    if m:
        return "single", (int(m.group(1)),)
    m = re.match(r"^\((\d{1,2})\)", t)  # (1)
    if m:
        return "paren", int(m.group(1))
    if t and t[0] in _CIRCLED:  # ①
        return "circ", _CIRCLED.index(t[0]) + 1
    m = re.match(r"^(\d{1,2})차년도", t)  # 1차년도
    if m:
        return "year", int(m.group(1))
    return None, None


def build_outline(md: str) -> str:
    """파싱된 마크다운에서 결정론적 구조 아웃라인을 만든다.

    헤딩(H2~H6)을 순회해 계층 트리를 그대로 재구성하고, 각 헤딩의 "직접 본문"
    (다음 헤딩 전까지의 내용) 글자 수와 하위 항목 수를 코드로 계산한다.
    스킬 추출 프롬프트에 '구조·분량 기준(결정론)'으로 주입해, 하위 뎁스 누락과
    분량 미측정(LLM이 17만 자에서 못 세는 문제)을 해소한다.
    """
    lines = md.split("\n")
    heads: list[tuple[int, int, str]] = []  # (line_idx, level, title)
    for i, ln in enumerate(lines):
        m = _MD_HEADING_RE.match(ln.strip())
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    if not heads:
        return "(구조 헤딩이 감지되지 않음 — 평면형(FLAT) 가능성. origin_document를 직접 관찰할 것.)"

    n = len(heads)

    def body_len(start_idx: int, end_idx: int) -> int:
        return sum(
            len(t)
            for j in range(start_idx + 1, end_idx)
            if not _is_noise_line(t := lines[j].strip())
        )

    def direct_body(k: int) -> int:
        end = heads[k + 1][0] if k + 1 < n else len(lines)
        return body_len(heads[k][0], end)

    # 숫자 경로로 트리를 재구성한다. 대시(1-1.)는 절대 경로, (1)/①/N차년도는 부모 경로 +
    # 오프셋 상대번호. 단일번호(1.)는 구조 노드로 쓰지 않고 '장 제목 사전'으로만 사용해
    # 본문·요약의 번호 나열 노이즈를 구조에서 배제한다.
    single_titles: dict[int, str] = {}
    path_node: dict[tuple, dict] = {}  # 같은 경로 중복 시 마지막(본문) 발생이 우선
    stack: list[tuple[int, tuple]] = []  # (heading_level, path)
    for k, (idx, level, title) in enumerate(heads):
        kind, val = _parse_marker(title)
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent = stack[-1][1] if stack else ()
        if kind == "single":
            # 진짜 장 제목만 채택: 바로 다음 헤딩이 접두번호가 일치하는 대시 자식일 때만.
            # (요약·본문의 번호 나열 "1. …"은 뒤에 "1-1."이 오지 않으므로 배제된다.)
            if k + 1 < n:
                nkind, nval = _parse_marker(heads[k + 1][2])
                if nkind == "dash" and nval[0] == val[0]:
                    single_titles.setdefault(val[0], title)
            # 단일번호는 부모 스택에 넣지 않는다 → (1)/① 등 상대 마커가 실제 대시 조상에 붙는다.
            continue
        if kind == "dash":
            path = val
        elif kind in ("paren", "circ", "year"):
            # 부모 대시가 없는 고아 상대 마커(참조/색인 페이지의 "(2) … p.141" 등)는 배제.
            if not parent:
                continue
            offset = {"paren": _OFF_PAREN, "circ": _OFF_CIRC, "year": _OFF_YEAR}[kind]
            path = parent + (offset + val,)
        else:
            continue
        stack.append((level, path))
        path_node[path] = {"title": title, "dbody": direct_body(k), "kind": kind}

    if not path_node:
        return "(번호 체계 헤딩이 없음 — 평면형(FLAT) 가능성. origin_document를 직접 관찰할 것.)"

    # 누락된 상위 장(길이 1 경로) 합성 — 제목은 단일번호 사전에서 가져온다.
    for p in list(path_node):
        chap = (p[0],)
        if chap not in path_node:
            path_node[chap] = {"title": single_titles.get(p[0], f"{p[0]}장"), "dbody": 0, "kind": "chapter"}

    paths = sorted(path_node)

    def children(p: tuple) -> list[tuple]:
        return [q for q in paths if len(q) == len(p) + 1 and q[: len(p)] == p]

    memo: dict[tuple, int] = {}

    def subtree_len(p: tuple) -> int:
        if p not in memo:
            memo[p] = path_node[p]["dbody"] + sum(subtree_len(c) for c in children(p))
        return memo[p]

    # 개체별 반복 묶음 축약: 같은 부모의 자식이 3개 이상이고, 마커 종류가 (1)/① 계열로
    # 동일하며, 분량이 서로 비슷하면(템플릿 반복 — 예: 기관·인원마다 같은 표) 첫 항목만
    # 대표로 남기고 나머지는 숨긴다. 연차처럼 분량이 들쭉날쭉하면 반복으로 보지 않고 유지.
    suppressed: set[tuple] = set()
    rep_count: dict[tuple, int] = {}
    for p in paths:
        kids = children(p)
        # 개수 4개 이상 + 분량이 서로 매우 유사(1.3배 이내)해야 '개체별 템플릿 반복'으로 본다.
        # (기술적/경제적/사회적 '측면' 3개처럼 개수가 적거나 내용이 다른 묶음은 유지.)
        if len(kids) < 4:
            continue
        kinds = {path_node[c]["kind"] for c in kids}
        lens = [subtree_len(c) for c in kids]
        if kinds <= {"circ", "paren"} and min(lens) > 0 and max(lens) <= min(lens) * 1.3:
            for kid in kids[1:]:
                suppressed.update(q for q in paths if q[: len(kid)] == kid)
            rep_count[kids[0]] = len(kids)

    max_depth = max(len(p) for p in paths)
    top_count = sum(1 for p in paths if len(p) == 1)
    doc_type = "계층형(HIERARCHICAL)" if max_depth > 1 else "평면형(FLAT)"
    out: list[str] = [
        f"[문서 구조 요약: {doc_type}, 최상위 {top_count}개, 최대 깊이 {max_depth}단]",
        "",
    ]
    for p in paths:
        if p in suppressed:
            continue
        node = path_node[p]
        cc = len(children(p))
        if p in rep_count:
            note = f"개체별 반복 총 {rep_count[p]}개 — 대표 1개만 표기(실제 개체 목록은 문서마다 다름)"
        elif cc:
            note = f"하위 포함 ~{subtree_len(p):,}자, 하위 {cc}개"
        else:
            note = f"본문 ~{node['dbody']:,}자"
        indent = "  " * (len(p) - 1)
        out.append(f"{indent}{'#' * (len(p) + 1)} {node['title']}  ({note})")
    return "\n".join(out)
