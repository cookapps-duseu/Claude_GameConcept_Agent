# Image Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 레퍼런스 게임에 스토어 링크를 추가하고, ConceptWriter가 컨셉 본문 내 지정 위치에 `[IMG_SCENE_N]` 플레이스홀더를 삽입하면 HtmlExporter가 해당 위치에 인게임 예시 SVG(최소 3개~최대 15개)를 인라인으로 치환해 표시한다.

**Architecture:** ConceptWriter ROLE이 `[IMG_SCENE_N]` 플레이스홀더와 `---SCENE_LIST---` JSON을 출력한다. harness 5단계에서 `parse_concept_scenes()`로 씬 목록을 분리 후 ConceptUiGenerator를 병렬 N회 호출한다. HtmlExporter가 `_inline_svgs()`로 플레이스홀더를 SVG div로 치환한다. ReferenceImageFetcher는 `store_url`도 함께 반환하고, HTML 템플릿은 이미지 로드 실패 시 스토어 링크를 표시한다.

**Tech Stack:** Python 3.11+, asyncio, Jinja2, python-docx, regex

---

## 파일 구조

| 파일 | 변경 종류 | 책임 |
|------|-----------|------|
| `models/pipeline_state.py` | Modify | `concept_ui_svg` 제거, `concept_ui_svgs: list[dict]` 추가 |
| `agents/concept_scene_parser.py` | Create | `parse_concept_scenes()` 함수 — `---SCENE_LIST---` 파싱 |
| `agents/concept_writer.py` | Modify | ROLE에 씬 플레이스홀더/씬 목록 출력 지침 추가 |
| `harness.py` | Modify | 5단계: 씬 파싱 + ConceptUiGenerator N회 병렬 호출 |
| `agents/html_exporter.py` | Modify | `_inline_svgs()` 추가, `export()` 에서 `concept_ui_svgs` 사용 |
| `templates/concept.html.j2` | Modify | Section 2 `concept_ui_svg` 블록 제거 + 레퍼런스 스토어 링크 fallback |
| `agents/word_exporter.py` | Modify | `[IMG_SCENE_N]` 줄 건너뛰기 |
| `agents/reference_image_fetcher.py` | Modify | ROLE에 `store_url` 출력 지침 추가 |
| `tests/test_concept_scene_parser.py` | Create | `parse_concept_scenes()` 단위 테스트 |
| `tests/test_html_exporter.py` | Create | `_inline_svgs()` 단위 테스트 |
| `tests/test_harness.py` | Modify | `concept_ui_svg` → `concept_ui_svgs` 참조 업데이트 |
| `tests/test_models.py` | Modify | `concept_ui_svg` → `concept_ui_svgs` 참조 업데이트 |

---

## Task 1: PipelineState — concept_ui_svg 제거, concept_ui_svgs 추가

**Files:**
- Modify: `models/pipeline_state.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py` 끝에 추가:

```python
def test_pipeline_state_concept_ui_svgs_initial():
    state = PipelineState(user_input=UserInput(genre="액션"))
    assert state.concept_ui_svgs == []


def test_pipeline_state_concept_ui_svgs_stores_list():
    state = PipelineState(user_input=UserInput(genre="액션"))
    state.concept_ui_svgs = [{"id": 1, "title": "채굴 화면", "svg": "<svg/>"}]
    assert state.concept_ui_svgs[0]["title"] == "채굴 화면"
```

그리고 기존 `test_pipeline_state_image_fields_initial` 수정:

```python
def test_pipeline_state_image_fields_initial():
    state = PipelineState(user_input=UserInput(genre="액션"))
    assert state.reference_images == []
    assert state.concept_ui_svgs == []
    assert state.concept_diagram_mermaid is None
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_models.py -v -k "concept_ui" 2>&1
```

Expected: FAIL — `concept_ui_svgs` attribute does not exist

- [ ] **Step 3: PipelineState 수정**

`models/pipeline_state.py` 전체를 다음으로 교체:

```python
from dataclasses import dataclass, field
from models.user_input import UserInput


@dataclass
class PipelineState:
    user_input: UserInput
    reference_games: list[str] = field(default_factory=list)
    fun_analysis: str | None = None
    loop_analysis: str | None = None
    synthesis: str | None = None
    synthesis_key_points: str | None = None
    concept: str | None = None
    output_word_path: str | None = None
    output_html_path: str | None = None
    reference_images: list[dict] = field(default_factory=list)
    concept_ui_svgs: list[dict] = field(default_factory=list)
    concept_diagram_mermaid: str | None = None
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_models.py -v 2>&1
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add models/pipeline_state.py tests/test_models.py && git commit -m "refactor: replace concept_ui_svg with concept_ui_svgs list in PipelineState"
```

---

## Task 2: parse_concept_scenes 파서 (TDD)

**Files:**
- Create: `agents/concept_scene_parser.py`
- Create: `tests/test_concept_scene_parser.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_concept_scene_parser.py` 생성:

```python
import pytest
from agents.concept_scene_parser import parse_concept_scenes


def test_parse_basic():
    text = (
        "컨셉 본문\n[IMG_SCENE_1]\n\n"
        "---SCENE_LIST---\n"
        '[{"id": 1, "title": "채굴 화면", "desc": "곡괭이 자동 작동"}]'
    )
    clean, scenes = parse_concept_scenes(text)
    assert "SCENE_LIST" not in clean
    assert "[IMG_SCENE_1]" in clean
    assert len(scenes) == 1
    assert scenes[0]["id"] == 1
    assert scenes[0]["title"] == "채굴 화면"


def test_parse_no_delimiter():
    text = "컨셉 본문만 있음"
    clean, scenes = parse_concept_scenes(text)
    assert clean == text
    assert scenes == []


def test_parse_invalid_json():
    text = "컨셉\n---SCENE_LIST---\nnot valid json"
    clean, scenes = parse_concept_scenes(text)
    assert scenes == []
    assert "SCENE_LIST" not in clean


def test_parse_with_code_fence():
    text = (
        "컨셉\n"
        "---SCENE_LIST---\n"
        "```json\n"
        '[{"id": 1, "title": "t", "desc": "d"}]\n'
        "```"
    )
    clean, scenes = parse_concept_scenes(text)
    assert len(scenes) == 1
    assert scenes[0]["title"] == "t"


def test_parse_multiple_scenes():
    scenes_json = (
        '[{"id": 1, "title": "A", "desc": "a"},'
        ' {"id": 2, "title": "B", "desc": "b"},'
        ' {"id": 3, "title": "C", "desc": "c"}]'
    )
    text = f"본문\n---SCENE_LIST---\n{scenes_json}"
    clean, scenes = parse_concept_scenes(text)
    assert len(scenes) == 3
    assert scenes[2]["id"] == 3


def test_parse_non_list_json_returns_empty():
    text = '본문\n---SCENE_LIST---\n{"id": 1}'
    clean, scenes = parse_concept_scenes(text)
    assert scenes == []


def test_clean_text_strips_trailing_whitespace():
    text = "본문   \n   \n---SCENE_LIST---\n[]"
    clean, _ = parse_concept_scenes(text)
    assert clean == clean.rstrip()
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_concept_scene_parser.py -v 2>&1
```

Expected: FAIL — `ModuleNotFoundError: No module named 'agents.concept_scene_parser'`

- [ ] **Step 3: 파서 구현**

`agents/concept_scene_parser.py` 생성:

```python
import json
import re


def parse_concept_scenes(text: str) -> tuple[str, list[dict]]:
    """컨셉 텍스트에서 ---SCENE_LIST--- 이후 JSON을 파싱해 씬 목록을 반환.

    Returns:
        (clean_concept_text, scenes_list)
        씬 목록 파싱 실패 시 (---SCENE_LIST--- 이전 텍스트, []) 반환.
    """
    delimiter = "---SCENE_LIST---"
    if delimiter not in text:
        return text, []

    parts = text.split(delimiter, 1)
    clean_text = parts[0].rstrip()
    scene_json = parts[1].strip()

    # 마크다운 코드 펜스 제거
    scene_json = re.sub(r"^```(?:json)?\s*", "", scene_json)
    scene_json = re.sub(r"\s*```$", "", scene_json)

    try:
        scenes = json.loads(scene_json.strip())
        if isinstance(scenes, list):
            return clean_text, scenes
        return clean_text, []
    except (json.JSONDecodeError, ValueError):
        return clean_text, []
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_concept_scene_parser.py -v 2>&1
```

Expected: 7개 테스트 PASS

- [ ] **Step 5: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add agents/concept_scene_parser.py tests/test_concept_scene_parser.py && git commit -m "feat: add parse_concept_scenes parser for scene list extraction"
```

---

## Task 3: ConceptWriter ROLE 수정

**Files:**
- Modify: `agents/concept_writer.py`

- [ ] **Step 1: ROLE 수정**

`agents/concept_writer.py`의 `ROLE` 상수를 다음으로 교체:

```python
ROLE = """당신은 시니어 게임 기획자입니다.
분석 요약을 바탕으로 완성도 높은 게임 컨셉안을 작성합니다.

다음 구조로 작성하세요:

# 게임 컨셉안

## 1. 게임 개요
- 게임 타이틀 (가제)
- 장르
- 플랫폼
- 타겟 유저
- 한 줄 설명

## 2. 핵심 컨셉
- 게임의 핵심 정체성 (무엇이 이 게임을 특별하게 만드는가)
- 레퍼런스와의 차별점

## 3. 핵심 재미 요소
- 주요 재미 메커니즘 3가지
- 각 메커니즘이 플레이어에게 주는 감정적 경험

## 4. 핵심 게임 루프
- 코어 루프 (1회 플레이 사이클)
- 세션 루프 (1회 플레이 목표)
- 장기 루프 (성장/진행 구조)

## 5. 레퍼런스 게임
- 레퍼런스 목록과 각각에서 차용한 요소

## 6. 기획 의도
- 이 게임을 만드는 이유와 시장 기회

---

## 인게임 예시 화면 지침

컨셉안 본문에서 시각적으로 보여주면 이해에 도움이 되는 자리에 [IMG_SCENE_N] 태그를 삽입하세요 (N은 1부터 순서대로).

규칙:
- 최소 3개, 최대 15개
- 반드시 인게임 화면만 다룰 것 (타이틀 화면, 메뉴 화면 제외)
- 씬 간 내용이 겹치지 않을 것 (예: 전투 화면이 두 개면 안 됨)
- 태그는 해당 화면이 가장 자연스럽게 이해될 위치에 삽입

컨셉 본문 작성 완료 후 반드시 다음 형식을 문서 맨 끝에 추가하세요:

---SCENE_LIST---
[
  {"id": 1, "title": "씬 제목", "desc": "SVG로 그릴 화면의 상세 설명 (표시할 UI 요소, 레이아웃, 색상 톤, 수치 예시 등)"},
  {"id": 2, "title": "씬 제목2", "desc": "..."},
  ...
]"""
```

- [ ] **Step 2: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add agents/concept_writer.py && git commit -m "feat: add inline scene placeholder instructions to ConceptWriter ROLE"
```

---

## Task 4: harness.py — 씬 파싱 + 병렬 SVG 생성

**Files:**
- Modify: `harness.py`
- Modify: `tests/test_harness.py`

- [ ] **Step 1: test_harness.py 기존 테스트 수정**

`tests/test_harness.py`에서:

1. `image_stub_harness` 픽스처의 `concept_ui_generator` StubAgent 응답 유지 (변경 없음)

2. `test_harness_image_fields_populated` 수정:

```python
@pytest.mark.asyncio
async def test_harness_image_fields_populated(image_stub_harness):
    state = await image_stub_harness.run(UserInput(genre="액션"))
    assert state.reference_images == [{"game": "game_a", "url": "https://example.com/a.jpg", "store_url": None}]
    assert isinstance(state.concept_ui_svgs, list)
    assert state.concept_ui_svgs == []  # StubAgent concept="최종 컨셉안" — SCENE_LIST 없으므로 빈 리스트
    assert "flowchart" in state.concept_diagram_mermaid
```

3. `test_harness_image_exception_does_not_abort` 수정 (`concept_ui_svg` 참조 제거):

```python
@pytest.mark.asyncio
async def test_harness_image_exception_does_not_abort(tmp_path):
    """이미지 에이전트가 예외를 발생시켜도 파이프라인이 계속된다."""
    class FailingAgent(BaseAgent):
        async def run(self, prompt: str) -> AgentResult:
            raise RuntimeError("이미지 생성 실패")

    harness = GameConceptHarness(
        reference_searcher=StubAgent("game_a, game_b"),
        reference_validator=StubEvaluator(),
        fun_analyzer=StubAgent("핵심 재미: 성장감"),
        fun_validator=StubEvaluator(),
        loop_analyzer=StubAgent("루프: 전투 → 보상 → 강화"),
        loop_validator=StubEvaluator(),
        content_synthesizer=StubAgent("요약 완료"),
        synthesis_reviewer=StubEvaluator(),
        concept_writer=StubAgent("최종 컨셉안"),
        concept_validator=StubEvaluator(),
        word_exporter=None,
        html_exporter=None,
        word_validator=None,
        html_validator=None,
        output_format="html",
        reference_image_fetcher=FailingAgent(),
        concept_ui_generator=FailingAgent(),
        concept_diagram_generator=FailingAgent(),
    )
    state = await harness.run(UserInput(genre="액션"))
    assert state.concept == "최종 컨셉안"
    assert state.reference_images == []
    assert state.concept_ui_svgs == []
    assert state.concept_diagram_mermaid == ""
```

4. `image_stub_harness` 픽스처의 `reference_image_fetcher` StubAgent 응답 업데이트:

```python
@pytest.fixture
def image_stub_harness(tmp_path):
    harness = GameConceptHarness(
        reference_searcher=StubAgent("game_a, game_b"),
        reference_validator=StubEvaluator(),
        fun_analyzer=StubAgent("핵심 재미: 성장감"),
        fun_validator=StubEvaluator(),
        loop_analyzer=StubAgent("루프: 전투 → 보상 → 강화"),
        loop_validator=StubEvaluator(),
        content_synthesizer=StubAgent("[FULL_SUMMARY]\n요약\n[KEY_POINTS]\n- 핵심: 성장"),
        synthesis_reviewer=StubEvaluator(),
        concept_writer=StubAgent("최종 컨셉안"),
        concept_validator=StubEvaluator(),
        word_exporter=None,
        html_exporter=None,
        word_validator=None,
        html_validator=None,
        output_format="html",
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        reference_image_fetcher=StubAgent('[{"game": "game_a", "url": "https://example.com/a.jpg", "store_url": null}]'),
        concept_ui_generator=StubAgent("<svg><rect width='100' height='100'/></svg>"),
        concept_diagram_generator=StubAgent("flowchart TD\n    A-->B"),
    )
    return harness
```

5. 씬 파싱 후 SVG 생성 테스트 추가:

```python
@pytest.mark.asyncio
async def test_harness_concept_ui_svgs_populated_from_scene_list(tmp_path):
    """concept에 ---SCENE_LIST--- 가 있으면 concept_ui_svgs가 채워진다."""
    concept_with_scenes = (
        "컨셉 본문\n[IMG_SCENE_1]\n[IMG_SCENE_2]\n[IMG_SCENE_3]\n"
        "---SCENE_LIST---\n"
        '[{"id": 1, "title": "채굴 화면", "desc": "자동 채굴"},'
        ' {"id": 2, "title": "인벤토리", "desc": "광석 목록"},'
        ' {"id": 3, "title": "상점", "desc": "구매 화면"}]'
    )
    svg_agent = StubAgent("<svg><rect/></svg>")
    harness = GameConceptHarness(
        reference_searcher=StubAgent("game_a"),
        reference_validator=StubEvaluator(),
        fun_analyzer=StubAgent("재미"),
        fun_validator=StubEvaluator(),
        loop_analyzer=StubAgent("루프"),
        loop_validator=StubEvaluator(),
        content_synthesizer=StubAgent("[FULL_SUMMARY]\n요약\n[KEY_POINTS]\n- 핵심"),
        synthesis_reviewer=StubEvaluator(),
        concept_writer=StubAgent(concept_with_scenes),
        concept_validator=StubEvaluator(),
        word_exporter=None,
        html_exporter=None,
        word_validator=None,
        html_validator=None,
        output_format="html",
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        reference_image_fetcher=StubAgent("[]"),
        concept_ui_generator=svg_agent,
        concept_diagram_generator=StubAgent(""),
    )
    state = await harness.run(UserInput(genre="채굴"))
    assert len(state.concept_ui_svgs) == 3
    assert state.concept_ui_svgs[0]["id"] == 1
    assert state.concept_ui_svgs[0]["title"] == "채굴 화면"
    assert "<svg>" in state.concept_ui_svgs[0]["svg"]
    assert svg_agent.call_count == 3
    # concept 본문에서 ---SCENE_LIST--- 가 제거되어야 함
    assert "---SCENE_LIST---" not in state.concept
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_harness.py -v 2>&1
```

Expected: 여러 테스트 FAIL (`concept_ui_svg` AttributeError, `concept_ui_svgs` 관련)

- [ ] **Step 3: harness.py 5단계 수정**

`harness.py` 파일 상단 import에 추가:

```python
from agents.concept_scene_parser import parse_concept_scenes
```

`harness.py`의 5단계 블록(`# 5. 이미지 생성` 부분)을 다음으로 교체:

```python
        # 5. 이미지 생성 (HTML 출력 시에만)
        if "images" not in done and self.output_format in ("html", "both"):
            run_image = any([
                self.reference_image_fetcher,
                self.concept_ui_generator,
                self.concept_diagram_generator,
            ])
            if run_image:
                _log(5, "이미지 생성 중...")

                # 컨셉에서 씬 목록 파싱 (---SCENE_LIST--- 제거)
                clean_concept, scenes = parse_concept_scenes(state.concept or "")
                state.concept = clean_concept

                ref_list = ", ".join(state.reference_games)

                ref_task = (
                    self.reference_image_fetcher.run(ref_list)
                    if self.reference_image_fetcher else _noop_result()
                )
                diagram_task = (
                    self.concept_diagram_generator.run(state.synthesis or "")
                    if self.concept_diagram_generator else _noop_result()
                )

                svg_tasks = []
                if self.concept_ui_generator and scenes:
                    svg_tasks = [
                        self.concept_ui_generator.run(
                            f"[씬 제목: {s['title']}]\n[씬 설명: {s['desc']}]\n\n"
                            f"[장르: {user_input.genre}]\n[게임 컨셉 요약]\n{(state.synthesis or '')[:500]}"
                        )
                        for s in scenes
                    ]

                all_results = await asyncio.gather(
                    ref_task, diagram_task, *svg_tasks, return_exceptions=True
                )
                state.reference_images = _parse_reference_images(all_results[0])
                state.concept_diagram_mermaid = _safe_content(all_results[1])

                svg_results = all_results[2:]
                state.concept_ui_svgs = [
                    {
                        "id": s["id"],
                        "title": s["title"],
                        "svg": r.content if not isinstance(r, Exception) else "",
                    }
                    for s, r in zip(scenes, svg_results)
                ]

                _log(5, "이미지 생성 완료")
            done |= {"images"}
            self._checkpoint(state, done)
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_harness.py -v 2>&1
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add harness.py tests/test_harness.py && git commit -m "feat: parse concept scenes and generate N SVGs in parallel at step 5"
```

---

## Task 5: HtmlExporter — _inline_svgs 추가

**Files:**
- Modify: `agents/html_exporter.py`
- Create: `tests/test_html_exporter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_html_exporter.py` 생성:

```python
import pytest
from agents.html_exporter import HtmlExporter


@pytest.fixture
def exporter(tmp_path):
    return HtmlExporter(output_dir=str(tmp_path), template_dir="templates")


def test_inline_svgs_replaces_placeholder(exporter):
    html = "<p>[IMG_SCENE_1]</p>"
    svgs = [{"id": 1, "title": "채굴 화면", "svg": "<svg><rect/></svg>"}]
    result = exporter._inline_svgs(html, svgs)
    assert "[IMG_SCENE_1]" not in result
    assert "<svg>" in result
    assert "채굴 화면" in result
    assert "ui-mockup" in result


def test_inline_svgs_appends_unmatched_scene(exporter):
    """플레이스홀더 없는 씬은 문서 끝에 추가된다."""
    html = "<p>본문</p>"
    svgs = [{"id": 1, "title": "전투 화면", "svg": "<svg/>"}]
    result = exporter._inline_svgs(html, svgs)
    assert "<svg/>" in result
    assert "전투 화면" in result


def test_inline_svgs_empty_svgs_returns_unchanged(exporter):
    html = "<p>본문</p>"
    result = exporter._inline_svgs(html, [])
    assert result == html


def test_inline_svgs_skips_empty_svg_content(exporter):
    """svg 내용이 빈 문자열인 씬은 삽입하지 않는다."""
    html = "<p>[IMG_SCENE_1]</p>"
    svgs = [{"id": 1, "title": "오류 씬", "svg": ""}]
    result = exporter._inline_svgs(html, svgs)
    assert "[IMG_SCENE_1]" not in result
    assert "<svg" not in result


def test_inline_svgs_multiple_scenes(exporter):
    html = "<p>[IMG_SCENE_1]</p><p>중간 본문</p><p>[IMG_SCENE_2]</p>"
    svgs = [
        {"id": 1, "title": "씬1", "svg": "<svg id='1'/>"},
        {"id": 2, "title": "씬2", "svg": "<svg id='2'/>"},
    ]
    result = exporter._inline_svgs(html, svgs)
    assert "id='1'" in result
    assert "id='2'" in result
    assert "[IMG_SCENE_1]" not in result
    assert "[IMG_SCENE_2]" not in result
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_html_exporter.py -v 2>&1
```

Expected: FAIL — `AttributeError: 'HtmlExporter' object has no attribute '_inline_svgs'`

- [ ] **Step 3: HtmlExporter 수정**

`agents/html_exporter.py`의 `export()` 메서드와 `_split_concept_sections()` 사이에 `_inline_svgs()` 추가:

```python
    def _inline_svgs(self, concept_html: str, svgs: list[dict]) -> str:
        """[IMG_SCENE_N] 플레이스홀더를 SVG div로 치환.
        플레이스홀더 없는 씬은 문서 끝에 추가한다."""
        if not svgs:
            return concept_html

        svg_map = {s["id"]: s for s in svgs}
        used_ids: set[int] = set()

        def replace_placeholder(m: re.Match) -> str:
            n = int(m.group(1))
            used_ids.add(n)
            scene = svg_map.get(n)
            if not scene or not scene.get("svg"):
                return ""
            return (
                f'<div class="ui-mockup">'
                f'<p class="scene-title">{scene["title"]}</p>'
                f'{scene["svg"]}'
                f'</div>'
            )

        result = re.sub(r'<p>\[IMG_SCENE_(\d+)\]</p>', replace_placeholder, concept_html)

        for scene in svgs:
            if scene["id"] not in used_ids and scene.get("svg"):
                result += (
                    f'<div class="ui-mockup">'
                    f'<p class="scene-title">{scene["title"]}</p>'
                    f'{scene["svg"]}'
                    f'</div>'
                )

        return result
```

`export()` 메서드를 다음으로 교체 (`concept_ui_svg` 제거):

```python
    def export(self, state: PipelineState) -> str:
        now = datetime.now()
        concept_html = self._markdown_to_html(state.concept or "")
        concept_html = self._inline_svgs(concept_html, state.concept_ui_svgs)
        concept_sections = self._split_concept_sections(concept_html)
        template = self.env.get_template("concept.html.j2")
        html = template.render(
            genre=state.user_input.genre,
            platform=state.user_input.platform,
            generated_at=now.strftime("%Y-%m-%d %H:%M"),
            concept_sections=concept_sections,
            reference_images=state.reference_images,
            concept_diagram_mermaid=state.concept_diagram_mermaid or "",
        )
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"concept_{timestamp}.html"
        output_path.write_text(html, encoding="utf-8")
        return str(output_path)
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_html_exporter.py -v 2>&1
```

Expected: 5개 테스트 PASS

- [ ] **Step 5: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add agents/html_exporter.py tests/test_html_exporter.py && git commit -m "feat: add _inline_svgs to HtmlExporter for inline concept SVG placement"
```

---

## Task 6: HTML 템플릿 — concept_ui_svg 블록 제거 + CSS 추가

**Files:**
- Modify: `templates/concept.html.j2`

- [ ] **Step 1: concept_ui_svg 블록 제거**

`templates/concept.html.j2`에서 Section 2 블록을 다음으로 변경:

변경 전:
```jinja2
      {% if concept_sections["2"] is defined %}
        {{ concept_sections["2"] | safe }}
        {% if concept_ui_svg %}
        <div class="ui-mockup">{{ concept_ui_svg | safe }}</div>
        {% endif %}
      {% endif %}
```

변경 후:
```jinja2
      {% if concept_sections["2"] is defined %}
        {{ concept_sections["2"] | safe }}
      {% endif %}
```

- [ ] **Step 2: CSS에 scene-title 추가**

`<style>` 블록에 다음 추가 (`.diagram-container` 다음):

```css
    .scene-title { font-size: 0.85em; color: #555; margin: 0 0 6px 0; font-weight: 600; }
```

- [ ] **Step 3: 전체 테스트 실행해 이상 없음 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest -v 2>&1
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add templates/concept.html.j2 && git commit -m "refactor: remove hardcoded concept_ui_svg from HTML template, SVGs now inlined by exporter"
```

---

## Task 7: WordExporter — [IMG_SCENE_N] 줄 건너뛰기

**Files:**
- Modify: `agents/word_exporter.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py` 끝에 추가 (또는 별도 파일 없이 여기에):

새 파일 `tests/test_word_exporter.py` 생성:

```python
import pytest
from unittest.mock import MagicMock, patch
from agents.word_exporter import WordExporter
from models.pipeline_state import PipelineState
from models.user_input import UserInput


def test_word_exporter_skips_img_scene_tags(tmp_path):
    """[IMG_SCENE_N] 줄은 Word 문서에 포함되지 않는다."""
    exporter = WordExporter(output_dir=str(tmp_path))
    state = PipelineState(user_input=UserInput(genre="액션"))
    state.concept = "## 2. 핵심 컨셉\n설명 텍스트\n[IMG_SCENE_1]\n\n## 3. 재미\n재미 내용"

    path = exporter.export(state)

    from docx import Document
    doc = Document(path)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "[IMG_SCENE_1]" not in full_text
    assert "설명 텍스트" in full_text
    assert "재미 내용" in full_text
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_word_exporter.py -v 2>&1
```

Expected: FAIL — `[IMG_SCENE_1]` 텍스트가 Word 문서에 포함됨

- [ ] **Step 3: WordExporter 수정**

`agents/word_exporter.py` 상단에 `import re` 추가.

`_write_markdown_to_doc()` 메서드의 `for line in text.split("\n"):` 루프 첫 줄에 추가:

```python
    def _write_markdown_to_doc(self, doc: Document, text: str):
        for line in text.split("\n"):
            line = line.rstrip()
            if re.match(r'^\[IMG_SCENE_\d+\]$', line):
                continue
            if line.startswith("# "):
                doc.add_heading(line[2:], level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("- "):
                doc.add_paragraph(line[2:], style="List Bullet")
            elif line == "":
                doc.add_paragraph()
            else:
                doc.add_paragraph(line)
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_word_exporter.py -v 2>&1
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add agents/word_exporter.py tests/test_word_exporter.py && git commit -m "fix: skip [IMG_SCENE_N] placeholder lines in WordExporter"
```

---

## Task 8: ReferenceImageFetcher — store_url 추가

**Files:**
- Modify: `agents/reference_image_fetcher.py`

- [ ] **Step 1: ROLE 수정**

`agents/reference_image_fetcher.py`의 `ROLE` 상수를 다음으로 교체:

```python
ROLE = """당신은 게임 이미지 검색 전문가입니다.
주어진 레퍼런스 게임 목록에서 각 게임의 공식 스크린샷 이미지 URL과 스토어 링크를 찾아주세요.

Steam 상점, Google Play, App Store, 공식 웹사이트, IGN, Metacritic 등에서 검색하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
[{"game": "게임명", "url": "이미지URL또는null", "store_url": "스토어URL또는null"}]

규칙:
- url: 직접 접근 가능한 이미지 URL (.jpg, .png, .webp). 찾지 못한 경우 null
- store_url: Steam/Google Play/App Store/공식 페이지 URL. 최대한 확보할 것
- url과 store_url 모두 null인 게임은 목록에서 제외
- 결과가 없으면 [] 반환"""
```

- [ ] **Step 2: 전체 테스트 실행해 이상 없음 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest -v 2>&1
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add agents/reference_image_fetcher.py && git commit -m "feat: add store_url to ReferenceImageFetcher output"
```

---

## Task 9: HTML 템플릿 — 레퍼런스 스토어 링크 fallback

**Files:**
- Modify: `templates/concept.html.j2`

- [ ] **Step 1: CSS에 store-link 스타일 추가**

`<style>` 블록의 `.reference-gallery figcaption` 다음에 추가:

```css
    .store-link { display: inline-block; padding: 4px 10px; background: #e94560; color: #fff; border-radius: 4px; font-size: 0.8em; text-decoration: none; margin-top: 4px; }
    .store-link:hover { background: #c73652; }
```

- [ ] **Step 2: 레퍼런스 갤러리 figure 블록 교체**

변경 전:
```jinja2
          {% for img in reference_images %}
          <figure>
            <img src="{{ img.url }}" alt="{{ img.game }}" onerror="this.style.display='none'">
            <figcaption>{{ img.game }}</figcaption>
          </figure>
          {% endfor %}
```

변경 후:
```jinja2
          {% for img in reference_images %}
          <figure>
            {% if img.url %}
            <img src="{{ img.url }}" alt="{{ img.game }}"
                 onerror="this.style.display='none'; var sl=this.parentElement.querySelector('.store-link'); if(sl) sl.style.display='inline-block';">
            {% endif %}
            {% if img.store_url %}
            <a href="{{ img.store_url }}" target="_blank" class="store-link"{% if img.url %} style="display:none"{% endif %}>
              {{ img.game }} 스토어 보기
            </a>
            {% endif %}
            <figcaption>{{ img.game }}</figcaption>
          </figure>
          {% endfor %}
```

- [ ] **Step 3: 전체 테스트 실행**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest -v 2>&1
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: Commit**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add templates/concept.html.j2 && git commit -m "feat: add store link fallback for reference images in HTML template"
```

---

## Self-Review

**스펙 커버리지 확인:**
- ✅ Feature 1 레퍼런스 스토어 링크: Task 8(fetcher) + Task 9(template)
- ✅ Feature 2 ConceptWriter 씬 지침: Task 3
- ✅ parse_concept_scenes 파서: Task 2
- ✅ harness 병렬 SVG 생성: Task 4
- ✅ HtmlExporter 인라인 치환: Task 5
- ✅ HTML 템플릿 concept_ui_svg 제거: Task 6
- ✅ WordExporter [IMG_SCENE_N] 건너뛰기: Task 7
- ✅ PipelineState 모델 변경: Task 1

**플레이스홀더 스캔:** TBD/TODO 없음

**타입 일관성:**
- `parse_concept_scenes()` → `tuple[str, list[dict]]` — Task 2에서 정의, Task 4에서 동일하게 사용
- `concept_ui_svgs: list[dict]` — `{"id": int, "title": str, "svg": str}` — Task 1에서 정의, Task 4/5에서 동일 구조 사용
- `_inline_svgs(html: str, svgs: list[dict]) -> str` — Task 5에서 정의, `export()`에서 동일하게 호출
- `reference_images` 구조: `{"game", "url", "store_url"}` — Task 8 fetcher, Task 9 template, Task 4 테스트 모두 일치
