# Image Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** HTML 컨셉안 출력에 레퍼런스 게임 이미지, SVG UI 목업, Mermaid 게임 루프 다이어그램을 섹션별 인라인으로 삽입한다.

**Architecture:** 에이전트 3개(ReferenceImageFetcher, ConceptUiGenerator, ConceptDiagramGenerator)를 concept Sprint 완료 후 `asyncio.gather(return_exceptions=True)`로 병렬 실행한다. 결과를 PipelineState에 저장하고 html_exporter가 Jinja2 템플릿에 섹션별로 주입한다. 이미지 생성 실패는 어떤 경우에도 파이프라인을 중단하지 않는다.

**Tech Stack:** 기존(`claude-agent-sdk`, `jinja2`, `pytest-asyncio`) — 신규 의존성 없음

---

## 파일 구조

```
신규:
  agents/reference_image_fetcher.py   — WebSearch로 레퍼런스 게임 이미지 URL 검색
  agents/concept_ui_generator.py      — SVG UI 목업 생성
  agents/concept_diagram_generator.py — Mermaid 게임 루프 다이어그램 생성

수정:
  models/pipeline_state.py            — 이미지 필드 3개 추가
  session_manager.py                  — 이미지 필드 저장/로드 추가
  harness.py                          — 이미지 생성 단계 + 헬퍼 함수 추가, __init__ 파라미터 추가
  agents/html_exporter.py             — 섹션 분리 + 이미지 템플릿 전달
  templates/concept.html.j2           — 섹션별 인라인 이미지 배치, Mermaid.js CDN

수정(테스트):
  tests/test_models.py                — 이미지 필드 초기값 확인
  tests/test_session_manager.py       — 이미지 필드 저장/로드 확인
  tests/test_harness.py               — 이미지 단계 stub 테스트
```

---

## Task 1: PipelineState 이미지 필드 추가 + session_manager 업데이트

**Files:**
- Modify: `models/pipeline_state.py`
- Modify: `session_manager.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_session_manager.py`

- [ ] **Step 1: test_models.py에 테스트 추가**

`tests/test_models.py` 파일 끝에 추가:

```python
def test_pipeline_state_image_fields_initial():
    state = PipelineState(user_input=UserInput(genre="액션"))
    assert state.reference_images == []
    assert state.concept_ui_svg is None
    assert state.concept_diagram_mermaid is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/pytest tests/test_models.py::test_pipeline_state_image_fields_initial -v
```
Expected: FAIL (AttributeError)

- [ ] **Step 3: pipeline_state.py 수정**

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
    concept_ui_svg: str | None = None
    concept_diagram_mermaid: str | None = None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/Scripts/pytest tests/test_models.py -v
```
Expected: 8 passed

- [ ] **Step 5: test_session_manager.py에 이미지 필드 테스트 추가**

`tests/test_session_manager.py` 파일의 `test_save_preserves_all_state_fields` 함수를 다음으로 교체 (기존 assert에 이미지 필드 추가):

```python
def test_save_preserves_all_state_fields(tmp_session):
    state = make_state()
    state.fun_analysis = "재미 분석 내용"
    state.loop_analysis = "루프 내용"
    state.synthesis = "요약"
    state.synthesis_key_points = "핵심"
    state.concept = "컨셉안"
    state.output_word_path = "output/test.docx"
    state.output_html_path = "output/test.html"
    state.reference_images = [{"game": "게임A", "url": "https://example.com/a.jpg"}]
    state.concept_ui_svg = "<svg>test</svg>"
    state.concept_diagram_mermaid = "flowchart TD\nA-->B"
    tmp_session.save(state, completed_steps=["reference", "fun_analysis"])
    loaded_state, steps = tmp_session.load()
    assert loaded_state.fun_analysis == "재미 분석 내용"
    assert loaded_state.loop_analysis == "루프 내용"
    assert loaded_state.synthesis_key_points == "핵심"
    assert loaded_state.concept == "컨셉안"
    assert loaded_state.output_word_path == "output/test.docx"
    assert loaded_state.output_html_path == "output/test.html"
    assert loaded_state.reference_images == [{"game": "게임A", "url": "https://example.com/a.jpg"}]
    assert loaded_state.concept_ui_svg == "<svg>test</svg>"
    assert loaded_state.concept_diagram_mermaid == "flowchart TD\nA-->B"
    assert steps == ["reference", "fun_analysis"]
```

- [ ] **Step 6: 테스트 실행 — 실패 확인**

```bash
.venv/Scripts/pytest tests/test_session_manager.py::test_save_preserves_all_state_fields -v
```
Expected: FAIL (이미지 필드가 session_manager에 없으므로)

- [ ] **Step 7: session_manager.py 수정**

`session_manager.py`의 `save`와 `load` 메서드를 다음으로 교체:

```python
    def save(self, state: PipelineState, completed_steps: list[str]) -> None:
        self.session_path.parent.mkdir(exist_ok=True)
        data = {
            "completed_steps": completed_steps,
            "user_input": dataclasses.asdict(state.user_input),
            "reference_games": state.reference_games,
            "fun_analysis": state.fun_analysis,
            "loop_analysis": state.loop_analysis,
            "synthesis": state.synthesis,
            "synthesis_key_points": state.synthesis_key_points,
            "concept": state.concept,
            "output_word_path": state.output_word_path,
            "output_html_path": state.output_html_path,
            "reference_images": state.reference_images,
            "concept_ui_svg": state.concept_ui_svg,
            "concept_diagram_mermaid": state.concept_diagram_mermaid,
        }
        self.session_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> tuple[PipelineState, list[str]] | None:
        if not self.has_session():
            return None
        data = json.loads(self.session_path.read_text(encoding="utf-8"))
        user_input = UserInput(**data["user_input"])
        state = PipelineState(user_input=user_input)
        state.reference_games = data.get("reference_games", [])
        state.fun_analysis = data.get("fun_analysis")
        state.loop_analysis = data.get("loop_analysis")
        state.synthesis = data.get("synthesis")
        state.synthesis_key_points = data.get("synthesis_key_points")
        state.concept = data.get("concept")
        state.output_word_path = data.get("output_word_path")
        state.output_html_path = data.get("output_html_path")
        state.reference_images = data.get("reference_images", [])
        state.concept_ui_svg = data.get("concept_ui_svg")
        state.concept_diagram_mermaid = data.get("concept_diagram_mermaid")
        return state, data.get("completed_steps", [])
```

- [ ] **Step 8: 전체 테스트 통과 확인**

```bash
.venv/Scripts/pytest tests/ -v
```
Expected: 28 passed

- [ ] **Step 9: Commit**

```bash
git add models/pipeline_state.py session_manager.py tests/test_models.py tests/test_session_manager.py
git commit -m "feat: add image fields to PipelineState and SessionManager"
```

---

## Task 2: ReferenceImageFetcher 에이전트

**Files:**
- Create: `agents/reference_image_fetcher.py`

- [ ] **Step 1: agents/reference_image_fetcher.py 생성**

```python
import json
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 이미지 검색 전문가입니다.
주어진 레퍼런스 게임 목록에서 각 게임의 공식 스크린샷 또는 커버 이미지 URL을 찾아주세요.

Steam 상점 페이지, 공식 웹사이트, IGN, Metacritic 등에서 검색하세요.
반드시 직접 접근 가능한 이미지 URL(.jpg, .png, .webp)만 반환하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
[{"game": "게임명", "url": "https://..."}]

URL을 찾지 못한 게임은 목록에서 제외하세요. 결과가 없으면 [] 반환."""


class ReferenceImageFetcher(BaseAgent):
    ALLOWED_TOOLS = ["WebSearch"]

    async def run(self, prompt: str) -> AgentResult:
        full_prompt = f"{ROLE}\n\n[레퍼런스 게임 목록]\n{prompt}"
        result_content = ""
        async for message in query(
            prompt=full_prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                result_content = message.result
        return AgentResult(content=result_content)
```

- [ ] **Step 2: 전체 테스트 이상 없는지 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/pytest tests/ -v
```
Expected: 28 passed

- [ ] **Step 3: Commit**

```bash
git add agents/reference_image_fetcher.py
git commit -m "feat: add ReferenceImageFetcher agent"
```

---

## Task 3: ConceptUiGenerator 에이전트

**Files:**
- Create: `agents/concept_ui_generator.py`

- [ ] **Step 1: agents/concept_ui_generator.py 생성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 UI/UX 디자이너입니다.
게임 컨셉안을 바탕으로 게임 화면의 UI 목업을 SVG 코드로 생성합니다.

장르에 맞는 게임 화면 레이아웃을 시각화하세요:
- RPG/ARPG: 화면 상단 체력/마나바, 하단 스킬창, 우상단 미니맵
- 퍼즐: 중앙 게임판, 상단 점수/레벨, 하단 다음 블록 미리보기
- 액션: 화면 하단 체력/스태미나 바, 상단 점수, 보스 체력바
- 전략: 상단 자원 표시, 좌측 미니맵, 우측 유닛 정보 패널
- 기타: 장르 특성에 맞게 적절히 구성

요구사항:
- viewBox="0 0 800 600" 사용
- 한국어 텍스트 포함 (레이블, UI 요소명)
- 게임 분위기에 맞는 색상 사용
- 실제 게임 화면처럼 보이도록 구성

반드시 <svg>...</svg> 태그만 반환하세요. 다른 텍스트 없이."""


class ConceptUiGenerator(BaseAgent):
    ALLOWED_TOOLS = []

    async def run(self, prompt: str) -> AgentResult:
        full_prompt = f"{ROLE}\n\n{prompt}"
        result_content = ""
        async for message in query(
            prompt=full_prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                result_content = message.result
        return AgentResult(content=result_content)
```

- [ ] **Step 2: 전체 테스트 이상 없는지 확인**

```bash
.venv/Scripts/pytest tests/ -v
```
Expected: 28 passed

- [ ] **Step 3: Commit**

```bash
git add agents/concept_ui_generator.py
git commit -m "feat: add ConceptUiGenerator agent"
```

---

## Task 4: ConceptDiagramGenerator 에이전트

**Files:**
- Create: `agents/concept_diagram_generator.py`

- [ ] **Step 1: agents/concept_diagram_generator.py 생성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 기획 다이어그램 전문가입니다.
게임 분석 요약을 바탕으로 게임 루프 구조를 Mermaid flowchart로 생성합니다.

다음 3단계 루프를 포함하세요:
1. 코어 루프 (1회 플레이 사이클, 가장 짧은 반복 단위)
2. 세션 루프 (1회 플레이 목표 달성 흐름)
3. 장기 루프 (성장/진행 구조)

요구사항:
- Mermaid flowchart TD 형식 사용
- 각 루프를 subgraph로 구분
- 한국어 노드 레이블 사용
- 노드 연결로 흐름을 명확하게 표현

반드시 다음 형식으로만 반환하세요 (코드 블록 마커 없이):
flowchart TD
    subgraph 코어루프["⚔️ 코어 루프"]
        ...
    end
    ..."""


class ConceptDiagramGenerator(BaseAgent):
    ALLOWED_TOOLS = []

    async def run(self, prompt: str) -> AgentResult:
        full_prompt = f"{ROLE}\n\n[분석 요약]\n{prompt}"
        result_content = ""
        async for message in query(
            prompt=full_prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                result_content = message.result
        return AgentResult(content=result_content)
```

- [ ] **Step 2: 전체 테스트 이상 없는지 확인**

```bash
.venv/Scripts/pytest tests/ -v
```
Expected: 28 passed

- [ ] **Step 3: Commit**

```bash
git add agents/concept_diagram_generator.py
git commit -m "feat: add ConceptDiagramGenerator agent"
```

---

## Task 5: harness.py — 이미지 생성 단계 추가

**Files:**
- Modify: `harness.py`
- Modify: `tests/test_harness.py`

- [ ] **Step 1: test_harness.py에 이미지 단계 테스트 추가**

`tests/test_harness.py` 파일 끝에 다음을 추가 (기존 import 줄에 `from models.user_input import UserInput`는 이미 있음):

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
        reference_image_fetcher=StubAgent('[{"game": "game_a", "url": "https://example.com/a.jpg"}]'),
        concept_ui_generator=StubAgent("<svg><rect width='100' height='100'/></svg>"),
        concept_diagram_generator=StubAgent("flowchart TD\n    A-->B"),
    )
    return harness


@pytest.mark.asyncio
async def test_harness_image_fields_populated(image_stub_harness):
    state = await image_stub_harness.run(UserInput(genre="액션"))
    assert state.reference_images == [{"game": "game_a", "url": "https://example.com/a.jpg"}]
    assert "<svg>" in state.concept_ui_svg
    assert "flowchart" in state.concept_diagram_mermaid


@pytest.mark.asyncio
async def test_harness_image_step_skipped_when_word_format(tmp_path):
    """output_format=word일 때 이미지 단계가 실행되지 않는다."""
    image_fetcher = StubAgent('[{"game": "game_a", "url": "https://example.com/a.jpg"}]')
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
        output_format="word",
        reference_image_fetcher=image_fetcher,
        concept_ui_generator=StubAgent("<svg/>"),
        concept_diagram_generator=StubAgent("flowchart TD"),
    )
    state = await harness.run(UserInput(genre="액션"))
    assert image_fetcher.call_count == 0
    assert state.reference_images == []


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
    assert state.concept_ui_svg == ""
    assert state.concept_diagram_mermaid == ""
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
.venv/Scripts/pytest tests/test_harness.py::test_harness_image_fields_populated tests/test_harness.py::test_harness_image_step_skipped_when_word_format tests/test_harness.py::test_harness_image_exception_does_not_abort -v
```
Expected: FAIL (GameConceptHarness에 이미지 파라미터 없음)

- [ ] **Step 3: harness.py 수정 — 헬퍼 함수 + __init__ + run 업데이트**

`harness.py` 전체를 다음으로 교체:

```python
import asyncio
import json
from dataclasses import dataclass
from agents.base import BaseAgent, BaseEvaluator, AgentResult, ValidationResult
from agents.content_synthesizer import parse_synthesis
from models.user_input import UserInput
from models.pipeline_state import PipelineState


class PipelineAbortedError(Exception):
    pass


@dataclass
class SprintResult:
    content: str
    attempts: int
    passed: bool


def _parse_reference_images(result) -> list[dict]:
    """AgentResult 또는 Exception을 받아 JSON 파싱 후 리스트 반환. 실패 시 []."""
    if isinstance(result, Exception):
        return []
    try:
        data = json.loads(result.content.strip())
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, AttributeError):
        return []


def _safe_content(result) -> str:
    """AgentResult 또는 Exception을 받아 content 반환. 실패 시 ''."""
    if isinstance(result, Exception):
        return ""
    return result.content if result.content else ""


class Sprint:
    def __init__(
        self,
        generator: BaseAgent,
        evaluator: BaseEvaluator,
        max_retries: int = 2,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.max_retries = max_retries

    async def ask_user(self, feedback: str) -> str:
        print(f"\n[검증 실패 — 최대 재시도 횟수 초과]\n피드백: {feedback}")
        print("1. 현재 결과로 진행")
        print("2. 파이프라인 중단")
        while True:
            choice = input("선택 (1/2): ").strip()
            if choice == "1":
                return "proceed"
            if choice == "2":
                return "abort"

    async def run(self, initial_prompt: str) -> SprintResult:
        prompt = initial_prompt
        result: AgentResult | None = None

        for attempt in range(self.max_retries + 1):
            result = await self.generator.run(prompt)
            validation = await self.evaluator.validate(result.content)

            if validation.passed:
                return SprintResult(content=result.content, attempts=attempt + 1, passed=True)

            if attempt >= self.max_retries:
                decision = await self.ask_user(validation.feedback or "")
                if decision == "abort":
                    raise PipelineAbortedError("사용자가 파이프라인을 중단했습니다.")
                return SprintResult(content=result.content, attempts=attempt + 1, passed=False)

            prompt = f"{initial_prompt}\n\n[이전 검증 실패 피드백]\n{validation.feedback}"

        return SprintResult(content=result.content, attempts=self.max_retries + 1, passed=False)


class GameConceptHarness:
    def __init__(
        self,
        reference_searcher: BaseAgent,
        reference_validator: BaseEvaluator,
        fun_analyzer: BaseAgent,
        fun_validator: BaseEvaluator,
        loop_analyzer: BaseAgent,
        loop_validator: BaseEvaluator,
        content_synthesizer: BaseAgent,
        synthesis_reviewer: BaseEvaluator,
        concept_writer: BaseAgent,
        concept_validator: BaseEvaluator,
        word_exporter,
        html_exporter,
        word_validator,
        html_validator,
        output_format: str = "word",
        session_manager=None,
        max_retries: int = 2,
        reference_image_fetcher: BaseAgent | None = None,
        concept_ui_generator: BaseAgent | None = None,
        concept_diagram_generator: BaseAgent | None = None,
    ):
        self.reference_sprint = Sprint(reference_searcher, reference_validator, max_retries)
        self.fun_sprint = Sprint(fun_analyzer, fun_validator, max_retries)
        self.loop_sprint = Sprint(loop_analyzer, loop_validator, max_retries)
        self.synthesis_sprint = Sprint(content_synthesizer, synthesis_reviewer, max_retries)
        self.concept_sprint = Sprint(concept_writer, concept_validator, max_retries)
        self.word_exporter = word_exporter
        self.html_exporter = html_exporter
        self.word_validator = word_validator
        self.html_validator = html_validator
        self.output_format = output_format
        self.session_manager = session_manager
        self.reference_image_fetcher = reference_image_fetcher
        self.concept_ui_generator = concept_ui_generator
        self.concept_diagram_generator = concept_diagram_generator

    async def run(
        self,
        user_input: UserInput,
        resume_state: PipelineState | None = None,
        completed_steps: list[str] | None = None,
    ) -> PipelineState:
        state = resume_state or PipelineState(user_input=user_input)
        done = set(completed_steps or [])

        # validator 컨텍스트 주입
        if hasattr(self.reference_sprint.evaluator, 'user_input_prompt'):
            self.reference_sprint.evaluator.user_input_prompt = user_input.to_prompt()

        # 1. 레퍼런스 탐색
        if "reference" not in done:
            ref_result = await self.reference_sprint.run(
                f"다음 조건에 맞는 레퍼런스 게임을 3개 이상 10개 이하로 탐색해주세요:\n{user_input.to_prompt()}"
            )
            state.reference_games = [g.strip() for g in ref_result.content.split(",") if g.strip()]
            done |= {"reference"}
            self._checkpoint(state, done)

        # 2. 핵심 재미 + 게임 루프 병렬 분석
        if "fun_analysis" not in done or "loop_analysis" not in done:
            ref_context = f"레퍼런스 게임: {', '.join(state.reference_games)}\n{user_input.to_prompt()}"
            tasks = []
            if "fun_analysis" not in done:
                tasks.append(self.fun_sprint.run(f"다음 레퍼런스 게임의 핵심 재미 요소를 분석해주세요:\n{ref_context}"))
            if "loop_analysis" not in done:
                tasks.append(self.loop_sprint.run(f"다음 레퍼런스 게임의 핵심 게임 루프를 분석해주세요:\n{ref_context}"))
            results = await asyncio.gather(*tasks)
            idx = 0
            if "fun_analysis" not in done:
                state.fun_analysis = results[idx].content
                idx += 1
            if "loop_analysis" not in done:
                state.loop_analysis = results[idx].content
            done |= {"fun_analysis", "loop_analysis"}
            self._checkpoint(state, done)

        # 3. 요약 정리
        if "synthesis" not in done:
            if hasattr(self.synthesis_sprint.evaluator, 'original_fun'):
                self.synthesis_sprint.evaluator.original_fun = state.fun_analysis
                self.synthesis_sprint.evaluator.original_loop = state.loop_analysis

            synthesis_prompt = (
                f"다음 두 분석을 요약 정리해주세요:\n\n"
                f"[핵심 재미 분석]\n{state.fun_analysis}\n\n"
                f"[핵심 게임 루프 분석]\n{state.loop_analysis}"
            )
            synthesis_result = await self.synthesis_sprint.run(synthesis_prompt)
            full_summary, key_points = parse_synthesis(synthesis_result.content)
            state.synthesis = full_summary
            state.synthesis_key_points = key_points
            done |= {"synthesis"}
            self._checkpoint(state, done)

        # 4. 컨셉안 작성 (ConceptSprint)
        if "concept" not in done:
            if hasattr(self.concept_sprint.evaluator, 'synthesis_key_points'):
                self.concept_sprint.evaluator.synthesis_key_points = state.synthesis_key_points or ""

            concept_result = await self.concept_sprint.run(
                f"다음 분석을 바탕으로 게임 컨셉안을 작성해주세요:\n\n"
                f"[사용자 요구사항]\n{user_input.to_prompt()}\n\n"
                f"[분석 요약]\n{state.synthesis}"
            )
            state.concept = concept_result.content
            done |= {"concept"}
            self._checkpoint(state, done)

        # 5. 이미지 생성 (HTML 출력 시에만)
        if "images" not in done and self.output_format in ("html", "both"):
            image_tasks = []
            run_image = any([
                self.reference_image_fetcher,
                self.concept_ui_generator,
                self.concept_diagram_generator,
            ])
            if run_image:
                ref_list = ", ".join(state.reference_games)
                image_tasks = [
                    self.reference_image_fetcher.run(ref_list) if self.reference_image_fetcher
                    else _noop_result(),
                    self.concept_ui_generator.run(
                        f"[장르: {user_input.genre}]\n\n[컨셉안]\n{state.concept}"
                    ) if self.concept_ui_generator else _noop_result(),
                    self.concept_diagram_generator.run(state.synthesis or "") if self.concept_diagram_generator
                    else _noop_result(),
                ]
                image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
                state.reference_images = _parse_reference_images(image_results[0])
                state.concept_ui_svg = _safe_content(image_results[1])
                state.concept_diagram_mermaid = _safe_content(image_results[2])
            done |= {"images"}
            self._checkpoint(state, done)

        # 6. 출력 생성
        if self.output_format in ("word", "both") and "word_export" not in done:
            await self._export_with_validation(
                state, self.word_exporter, self.word_validator, "word_export", done
            )
        if self.output_format in ("html", "both") and "html_export" not in done:
            await self._export_with_validation(
                state, self.html_exporter, self.html_validator, "html_export", done
            )

        # 완료 — 세션 파일 삭제
        if self.session_manager:
            self.session_manager.clear()

        return state

    def _checkpoint(self, state: PipelineState, completed_steps: set[str]) -> None:
        if self.session_manager:
            self.session_manager.save(state, list(completed_steps))

    async def _export_with_validation(
        self, state: PipelineState, exporter, validator, step_name: str, done: set
    ):
        if exporter is None:
            return
        for attempt in range(2):
            path = await asyncio.to_thread(exporter.export, state)
            if step_name == "word_export":
                state.output_word_path = path
            else:
                state.output_html_path = path
            if validator is None:
                break
            result = await validator.validate(path)
            if result.passed:
                break
            if attempt == 0:
                print(f"[출력 검증 실패] {result.feedback} — 재시도 중...")
        done |= {step_name}
        self._checkpoint(state, done)


async def _noop_result() -> AgentResult:
    return AgentResult(content="")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/Scripts/pytest tests/test_harness.py -v
```
Expected: 7 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
.venv/Scripts/pytest tests/ -v
```
Expected: 31 passed

- [ ] **Step 6: Commit**

```bash
git add harness.py tests/test_harness.py
git commit -m "feat: add image generation step to harness pipeline"
```

---

## Task 6: html_exporter.py 수정 + 템플릿 업데이트

**Files:**
- Modify: `agents/html_exporter.py`
- Modify: `templates/concept.html.j2`

- [ ] **Step 1: agents/html_exporter.py 전체 교체**

```python
import re
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from models.pipeline_state import PipelineState


class HtmlExporter:
    def __init__(self, output_dir: str = "output", template_dir: str = "templates"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def export(self, state: PipelineState) -> str:
        now = datetime.now()
        concept_html = self._markdown_to_html(state.concept or "")
        concept_sections = self._split_concept_sections(concept_html)
        template = self.env.get_template("concept.html.j2")
        html = template.render(
            genre=state.user_input.genre,
            platform=state.user_input.platform,
            generated_at=now.strftime("%Y-%m-%d %H:%M"),
            concept_sections=concept_sections,
            reference_images=state.reference_images,
            concept_ui_svg=state.concept_ui_svg or "",
            concept_diagram_mermaid=state.concept_diagram_mermaid or "",
        )
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"concept_{timestamp}.html"
        output_path.write_text(html, encoding="utf-8")
        return str(output_path)

    def _split_concept_sections(self, concept_html: str) -> dict[str, str]:
        """h2 태그 기준으로 섹션 분리. 키: "1"~"6". 실패 시 {"all": concept_html}."""
        pattern = re.compile(r'(<h2>[^<]*</h2>)', re.IGNORECASE)
        parts = pattern.split(concept_html)
        if len(parts) <= 1:
            return {"all": concept_html}

        sections: dict[str, str] = {}
        current_num = None
        buffer = []

        for part in parts:
            h2_match = re.match(r'<h2>(\d+)\.\s', part, re.IGNORECASE)
            if h2_match:
                if current_num is not None:
                    sections[current_num] = "".join(buffer)
                current_num = h2_match.group(1)
                buffer = [part]
            else:
                if current_num is None:
                    # h2 이전 내용 (제목 h1 등)
                    sections["0"] = sections.get("0", "") + part
                else:
                    buffer.append(part)

        if current_num is not None:
            sections[current_num] = "".join(buffer)

        return sections if sections else {"all": concept_html}

    def _markdown_to_html(self, text: str) -> str:
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line == "":
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>")
        return "\n".join(html_lines)
```

- [ ] **Step 2: templates/concept.html.j2 전체 교체**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>게임 컨셉안 — {{ genre }}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
  <style>
    body { font-family: 'Noto Sans KR', sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; line-height: 1.7; }
    h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }
    h2 { color: #16213e; border-left: 4px solid #e94560; padding-left: 12px; margin-top: 32px; }
    h3 { color: #0f3460; }
    .meta { background: #f4f4f8; padding: 12px 16px; border-radius: 6px; font-size: 0.9em; color: #555; margin-bottom: 24px; }
    ul { padding-left: 20px; }
    li { margin-bottom: 6px; }
    .concept-body { background: #fff; }
    .ui-mockup { margin: 16px 0; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #f9f9f9; padding: 12px; }
    .ui-mockup svg { display: block; max-width: 100%; height: auto; }
    .diagram-container { margin: 16px 0; padding: 16px; background: #f9f9f9; border-radius: 8px; border: 1px solid #ddd; }
    .reference-gallery { display: flex; flex-wrap: wrap; gap: 12px; margin: 16px 0; }
    .reference-gallery figure { margin: 0; text-align: center; width: 180px; }
    .reference-gallery img { width: 180px; height: 100px; object-fit: cover; border-radius: 6px; border: 1px solid #ddd; display: block; }
    .reference-gallery figcaption { font-size: 0.8em; color: #555; margin-top: 4px; }
  </style>
</head>
<body>
  <h1>게임 컨셉안</h1>
  <div class="meta">
    생성일: {{ generated_at }} | 장르: {{ genre }}{% if platform %} | 플랫폼: {{ platform }}{% endif %}
  </div>
  <div class="concept-body">
    {% if concept_sections.all is defined %}
      {{ concept_sections.all | safe }}
    {% else %}
      {% if concept_sections["0"] is defined %}{{ concept_sections["0"] | safe }}{% endif %}

      {% if concept_sections["1"] is defined %}{{ concept_sections["1"] | safe }}{% endif %}

      {% if concept_sections["2"] is defined %}
        {{ concept_sections["2"] | safe }}
        {% if concept_ui_svg %}
        <div class="ui-mockup">{{ concept_ui_svg | safe }}</div>
        {% endif %}
      {% endif %}

      {% if concept_sections["3"] is defined %}{{ concept_sections["3"] | safe }}{% endif %}

      {% if concept_sections["4"] is defined %}
        {{ concept_sections["4"] | safe }}
        {% if concept_diagram_mermaid %}
        <div class="diagram-container">
          <div class="mermaid">{{ concept_diagram_mermaid }}</div>
        </div>
        {% endif %}
      {% endif %}

      {% if concept_sections["5"] is defined %}
        {{ concept_sections["5"] | safe }}
        {% if reference_images %}
        <div class="reference-gallery">
          {% for img in reference_images %}
          <figure>
            <img src="{{ img.url }}" alt="{{ img.game }}" onerror="this.style.display='none'">
            <figcaption>{{ img.game }}</figcaption>
          </figure>
          {% endfor %}
        </div>
        {% endif %}
      {% endif %}

      {% if concept_sections["6"] is defined %}{{ concept_sections["6"] | safe }}{% endif %}
    {% endif %}
  </div>
</body>
</html>
```

- [ ] **Step 3: 전체 테스트 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/pytest tests/ -v
```
Expected: 31 passed

- [ ] **Step 4: Commit**

```bash
git add agents/html_exporter.py templates/concept.html.j2
git commit -m "feat: html_exporter injects images into concept sections"
```

---

## Task 7: main.py — 이미지 에이전트 연결

**Files:**
- Modify: `main.py`

- [ ] **Step 1: main.py 수정**

`main.py`의 import 블록 끝 부분에 3개 추가하고 `build_harness` 함수를 수정:

import 블록 (기존 `from agents.html_validator import HtmlValidator` 아래에 추가):
```python
from agents.reference_image_fetcher import ReferenceImageFetcher
from agents.concept_ui_generator import ConceptUiGenerator
from agents.concept_diagram_generator import ConceptDiagramGenerator
```

`build_harness` 함수 전체 교체:
```python
def build_harness(output_format: str, session_manager: SessionManager) -> GameConceptHarness:
    return GameConceptHarness(
        reference_searcher=ReferenceSearcher(),
        reference_validator=ReferenceValidator(),
        fun_analyzer=FunAnalyzer(),
        fun_validator=FunValidator(),
        loop_analyzer=LoopAnalyzer(),
        loop_validator=LoopValidator(),
        content_synthesizer=ContentSynthesizer(),
        synthesis_reviewer=SynthesisReviewer(),
        concept_writer=ConceptWriter(),
        concept_validator=ConceptValidator(),
        word_exporter=WordExporter() if output_format in ("word", "both") else None,
        html_exporter=HtmlExporter() if output_format in ("html", "both") else None,
        word_validator=WordValidator() if output_format in ("word", "both") else None,
        html_validator=HtmlValidator() if output_format in ("html", "both") else None,
        output_format=output_format,
        session_manager=session_manager,
        reference_image_fetcher=ReferenceImageFetcher() if output_format in ("html", "both") else None,
        concept_ui_generator=ConceptUiGenerator() if output_format in ("html", "both") else None,
        concept_diagram_generator=ConceptDiagramGenerator() if output_format in ("html", "both") else None,
    )
```

- [ ] **Step 2: import 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python.exe -c "import main; print('OK')"
```
Expected: OK

- [ ] **Step 3: 전체 테스트 확인**

```bash
.venv/Scripts/pytest tests/ -v
```
Expected: 31 passed

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: wire image agents into main.py build_harness"
```

---

## Self-Review

**Spec coverage:**
- ✅ ReferenceImageFetcher (Task 2)
- ✅ ConceptUiGenerator (Task 3)
- ✅ ConceptDiagramGenerator (Task 4)
- ✅ PipelineState 필드 3개 (Task 1)
- ✅ session_manager 필드 저장/로드 (Task 1)
- ✅ harness 병렬 실행 + 예외처리 (Task 5)
- ✅ html_exporter 섹션 분리 (Task 6)
- ✅ 템플릿 인라인 배치 (Task 6)
- ✅ Mermaid.js CDN (Task 6)
- ✅ onerror 이미지 숨김 (Task 6)
- ✅ main.py 연결 (Task 7)
- ✅ 에러처리: 예외 시 빈 결과 (Task 5 `return_exceptions=True`)
- ✅ word 출력 시 이미지 단계 skip (Task 5)

**Type consistency:**
- `_parse_reference_images` → `list[dict]` → `state.reference_images: list[dict]` ✅
- `_safe_content` → `str` → `state.concept_ui_svg: str | None`, `state.concept_diagram_mermaid: str | None` ✅
- `concept_sections: dict[str, str]` → 템플릿에서 `concept_sections["2"]` 접근 ✅
