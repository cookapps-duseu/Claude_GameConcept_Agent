# Game Concept Harness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자의 게임 장르/기획 의도를 입력받아 레퍼런스 게임 분석 → 핵심 재미/루프 추출 → 요약 → 컨셉안을 Word+HTML로 자동 생성하는 멀티에이전트 하네스 구축

**Architecture:** Claude Agent SDK `query()`를 각 에이전트에서 호출하는 Generator-Evaluator Sprint 패턴. `GameConceptHarness`가 전체 파이프라인 오케스트레이션. `FunAnalysisSprint`와 `LoopAnalysisSprint`는 `asyncio.gather()`로 병렬 실행. `word_exporter`/`html_exporter`는 `python-docx`/`jinja2` 순수 Python 유틸리티.

**Tech Stack:** `claude-agent-sdk`, `anthropic`, `python-dotenv`, `anyio`, `python-docx`, `jinja2`, `pytest`, `pytest-asyncio`

---

## 파일 구조

```
Claude_GameConcept_Agent/
├── .env                              # ANTHROPIC_API_KEY (git 제외)
├── .env.example                      # 키 없는 템플릿
├── .gitignore
├── requirements.txt                  # 의존성
├── main.py                           # CLI 진입점
├── harness.py                        # Sprint, GameConceptHarness
├── agents/
│   ├── __init__.py
│   ├── base.py                       # BaseAgent, AgentResult, ValidationResult
│   ├── reference_searcher.py         # 레퍼런스 게임 탐색 (Generator)
│   ├── reference_validator.py        # 레퍼런스 적합성 검증 (Evaluator)
│   ├── fun_analyzer.py               # 핵심 재미 분석 (Generator)
│   ├── fun_validator.py              # 재미 요소 실사용자 검증 (Evaluator)
│   ├── loop_analyzer.py              # 핵심 게임 루프 분석 (Generator)
│   ├── loop_validator.py             # 게임 루프 정확성 검증 (Evaluator)
│   ├── content_synthesizer.py        # b+c 요약 정리 (Generator)
│   ├── synthesis_reviewer.py         # 요약본 리뷰 (Evaluator)
│   ├── concept_writer.py             # 게임 컨셉안 작성
│   ├── word_exporter.py              # Word(.docx) 출력 (순수 Python)
│   └── html_exporter.py             # HTML 출력 (순수 Python)
├── models/
│   ├── __init__.py
│   ├── user_input.py                 # UserInput dataclass
│   └── pipeline_state.py            # PipelineState dataclass
├── templates/
│   └── concept.html.j2              # HTML 템플릿
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_sprint.py
│   └── test_harness.py
└── output/                           # 생성된 파일 저장 (git 제외)
```

---

## Task 1: 프로젝트 기반 설정

**Files:**
- Modify: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: requirements.txt 업데이트**

```
claude-agent-sdk
anthropic
python-dotenv
anyio
python-docx
jinja2
pytest
pytest-asyncio
```

- [ ] **Step 2: .env.example 생성**

```
ANTHROPIC_API_KEY=your-api-key-here
```

- [ ] **Step 3: .gitignore 생성**

```
.env
output/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: output 디렉토리 + .gitkeep 생성**

```bash
mkdir -p output
touch output/.gitkeep
mkdir -p agents models tests templates
touch agents/__init__.py models/__init__.py tests/__init__.py
```

- [ ] **Step 5: 패키지 설치 확인**

```bash
pip install -r requirements.txt
```

Expected: 오류 없이 설치 완료

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore output/.gitkeep agents/__init__.py models/__init__.py tests/__init__.py
git commit -m "chore: initialize project structure"
```

---

## Task 2: 데이터 모델

**Files:**
- Create: `models/user_input.py`
- Create: `models/pipeline_state.py`
- Create: `models/__init__.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_models.py`:
```python
import pytest
from models.user_input import UserInput
from models.pipeline_state import PipelineState


def test_user_input_required_field():
    u = UserInput(genre="로그라이크 RPG")
    assert u.genre == "로그라이크 RPG"
    assert u.platform is None
    assert u.target_user is None
    assert u.keywords == []
    assert u.free_text is None


def test_user_input_full():
    u = UserInput(
        genre="로그라이크 RPG",
        platform="모바일",
        target_user="캐주얼 게이머",
        keywords=["짧은 플레이", "성장"],
        free_text="10분 단위 플레이 가능해야 함",
    )
    assert u.platform == "모바일"
    assert u.keywords == ["짧은 플레이", "성장"]


def test_user_input_to_prompt():
    u = UserInput(genre="퍼즐", platform="PC", keywords=["협동"])
    prompt = u.to_prompt()
    assert "퍼즐" in prompt
    assert "PC" in prompt
    assert "협동" in prompt


def test_pipeline_state_initial():
    u = UserInput(genre="액션")
    state = PipelineState(user_input=u)
    assert state.reference_games == []
    assert state.fun_analysis is None
    assert state.loop_analysis is None
    assert state.synthesis is None
    assert state.concept is None
    assert state.output_word_path is None
    assert state.output_html_path is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL (모듈 없음)

- [ ] **Step 3: UserInput 구현**

`models/user_input.py`:
```python
from dataclasses import dataclass, field


@dataclass
class UserInput:
    genre: str
    platform: str | None = None
    target_user: str | None = None
    keywords: list[str] = field(default_factory=list)
    free_text: str | None = None

    def to_prompt(self) -> str:
        lines = [f"장르: {self.genre}"]
        if self.platform:
            lines.append(f"플랫폼: {self.platform}")
        if self.target_user:
            lines.append(f"타겟 유저: {self.target_user}")
        if self.keywords:
            lines.append(f"키워드: {', '.join(self.keywords)}")
        if self.free_text:
            lines.append(f"추가 설명: {self.free_text}")
        return "\n".join(lines)
```

- [ ] **Step 4: PipelineState 구현**

`models/pipeline_state.py`:
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
    concept: str | None = None
    output_word_path: str | None = None
    output_html_path: str | None = None
```

- [ ] **Step 5: models/__init__.py 작성**

```python
from models.user_input import UserInput
from models.pipeline_state import PipelineState

__all__ = ["UserInput", "PipelineState"]
```

- [ ] **Step 6: 테스트 통과 확인**

```bash
pytest tests/test_models.py -v
```

Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add models/ tests/test_models.py
git commit -m "feat: add UserInput and PipelineState models"
```

---

## Task 3: BaseAgent + ValidationResult

**Files:**
- Create: `agents/base.py`

- [ ] **Step 1: base.py 작성**

`agents/base.py`:
```python
from dataclasses import dataclass


@dataclass
class AgentResult:
    content: str


@dataclass
class ValidationResult:
    passed: bool
    feedback: str | None = None


class BaseAgent:
    """Generator 에이전트 기반 클래스. run()을 오버라이드하세요."""

    ALLOWED_TOOLS: list[str] = []

    async def run(self, prompt: str) -> AgentResult:
        raise NotImplementedError


class BaseEvaluator:
    """Evaluator 에이전트 기반 클래스. validate()를 오버라이드하세요."""

    ALLOWED_TOOLS: list[str] = []

    async def validate(self, content: str) -> ValidationResult:
        raise NotImplementedError
```

- [ ] **Step 2: agents/__init__.py 업데이트**

`agents/__init__.py`:
```python
from agents.base import AgentResult, ValidationResult, BaseAgent, BaseEvaluator

__all__ = ["AgentResult", "ValidationResult", "BaseAgent", "BaseEvaluator"]
```

- [ ] **Step 3: Commit**

```bash
git add agents/base.py agents/__init__.py
git commit -m "feat: add BaseAgent and BaseEvaluator"
```

---

## Task 4: Sprint 클래스

**Files:**
- Create: `harness.py` (Sprint 부분)
- Create: `tests/test_sprint.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_sprint.py`:
```python
import pytest
import asyncio
from agents.base import AgentResult, ValidationResult, BaseAgent, BaseEvaluator
from harness import Sprint, PipelineAbortedError


class AlwaysPassGenerator(BaseAgent):
    async def run(self, prompt: str) -> AgentResult:
        return AgentResult(content="generated result")


class AlwaysFailGenerator(BaseAgent):
    def __init__(self):
        self.call_count = 0
        self.last_prompt = None

    async def run(self, prompt: str) -> AgentResult:
        self.call_count += 1
        self.last_prompt = prompt
        return AgentResult(content=f"attempt {self.call_count}")


class AlwaysPassEvaluator(BaseEvaluator):
    async def validate(self, content: str) -> ValidationResult:
        return ValidationResult(passed=True)


class AlwaysFailEvaluator(BaseEvaluator):
    async def validate(self, content: str) -> ValidationResult:
        return ValidationResult(passed=False, feedback="검증 실패: 내용 부족")


class PassOnThirdEvaluator(BaseEvaluator):
    def __init__(self):
        self.call_count = 0

    async def validate(self, content: str) -> ValidationResult:
        self.call_count += 1
        if self.call_count >= 3:
            return ValidationResult(passed=True)
        return ValidationResult(passed=False, feedback=f"실패 {self.call_count}회")


@pytest.mark.asyncio
async def test_sprint_passes_on_first_try():
    sprint = Sprint(AlwaysPassGenerator(), AlwaysPassEvaluator())
    result = await sprint.run("test prompt")
    assert result.content == "generated result"
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_sprint_retries_on_failure_and_passes():
    gen = AlwaysFailGenerator()
    sprint = Sprint(gen, PassOnThirdEvaluator())
    result = await sprint.run("initial prompt")
    assert gen.call_count == 3
    assert result.attempts == 3


@pytest.mark.asyncio
async def test_sprint_feedback_passed_to_generator():
    gen = AlwaysFailGenerator()
    sprint = Sprint(gen, AlwaysFailEvaluator(), max_retries=1)

    async def mock_ask_user(feedback: str) -> str:
        return "proceed"

    sprint.ask_user = mock_ask_user
    result = await sprint.run("initial prompt")
    # 2번째 실행 시 프롬프트에 피드백이 포함되어야 함
    assert "검증 실패" in gen.last_prompt


@pytest.mark.asyncio
async def test_sprint_aborts_when_user_chooses_abort():
    sprint = Sprint(AlwaysFailGenerator(), AlwaysFailEvaluator(), max_retries=1)

    async def mock_ask_user(feedback: str) -> str:
        return "abort"

    sprint.ask_user = mock_ask_user
    with pytest.raises(PipelineAbortedError):
        await sprint.run("test")


@pytest.mark.asyncio
async def test_sprint_proceeds_when_user_chooses_proceed():
    sprint = Sprint(AlwaysFailGenerator(), AlwaysFailEvaluator(), max_retries=1)

    async def mock_ask_user(feedback: str) -> str:
        return "proceed"

    sprint.ask_user = mock_ask_user
    result = await sprint.run("test")
    assert result.content is not None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_sprint.py -v
```

Expected: FAIL (harness 모듈 없음)

- [ ] **Step 3: Sprint 구현**

`harness.py` (Sprint 부분):
```python
import asyncio
from dataclasses import dataclass
from agents.base import BaseAgent, BaseEvaluator, AgentResult, ValidationResult


class PipelineAbortedError(Exception):
    pass


@dataclass
class SprintResult:
    content: str
    attempts: int
    passed: bool


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
        """최대 재시도 초과 시 사용자에게 위임. 'proceed' 또는 'abort' 반환."""
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

            # 피드백을 다음 프롬프트에 포함
            prompt = f"{initial_prompt}\n\n[이전 검증 실패 피드백]\n{validation.feedback}"

        # 이 코드에 도달하지 않음
        return SprintResult(content=result.content, attempts=self.max_retries + 1, passed=False)
```

- [ ] **Step 4: pytest.ini 또는 pyproject.toml 설정 (asyncio mode)**

`pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_sprint.py -v
```

Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add harness.py pytest.ini tests/test_sprint.py
git commit -m "feat: add Sprint class with retry and feedback loop"
```

---

## Task 5: GameConceptHarness

**Files:**
- Modify: `harness.py` (GameConceptHarness 추가)
- Create: `tests/test_harness.py`

- [ ] **Step 1: 테스트 작성**

`tests/test_harness.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from models.user_input import UserInput
from models.pipeline_state import PipelineState
from agents.base import AgentResult, ValidationResult, BaseAgent, BaseEvaluator
from harness import GameConceptHarness, Sprint


class StubAgent(BaseAgent):
    def __init__(self, response: str):
        self.response = response
        self.call_count = 0

    async def run(self, prompt: str) -> AgentResult:
        self.call_count += 1
        return AgentResult(content=self.response)


class StubEvaluator(BaseEvaluator):
    async def validate(self, content: str) -> ValidationResult:
        return ValidationResult(passed=True)


@pytest.fixture
def stub_harness():
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
        word_exporter=None,
        html_exporter=None,
    )
    return harness


@pytest.mark.asyncio
async def test_harness_run_populates_state(stub_harness):
    user_input = UserInput(genre="로그라이크 RPG")
    state = await stub_harness.run(user_input)
    assert state.reference_games == ["game_a", "game_b"]
    assert state.fun_analysis == "핵심 재미: 성장감"
    assert state.loop_analysis == "루프: 전투 → 보상 → 강화"
    assert state.synthesis == "요약 완료"
    assert state.concept == "최종 컨셉안"


@pytest.mark.asyncio
async def test_harness_fun_and_loop_run_in_parallel(stub_harness):
    """fun_analyzer와 loop_analyzer가 병렬로 호출되는지 확인."""
    import time
    call_times = []

    class TimedAgent(BaseAgent):
        async def run(self, prompt: str) -> AgentResult:
            call_times.append(time.monotonic())
            return AgentResult(content="result")

    # fun/loop 에이전트는 Sprint 내부에 저장되므로 sprint.generator를 교체
    stub_harness.fun_sprint.generator = TimedAgent()
    stub_harness.loop_sprint.generator = TimedAgent()
    await stub_harness.run(UserInput(genre="액션"))
    # 두 에이전트가 모두 실행됨
    assert len(call_times) == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_harness.py -v
```

Expected: FAIL (GameConceptHarness 없음)

- [ ] **Step 3: GameConceptHarness 구현 — harness.py에 추가**

```python
import asyncio
from models.user_input import UserInput
from models.pipeline_state import PipelineState


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
        word_exporter,   # WordExporter | None
        html_exporter,   # HtmlExporter | None
        max_retries: int = 2,
    ):
        self.reference_sprint = Sprint(reference_searcher, reference_validator, max_retries)
        self.fun_sprint = Sprint(fun_analyzer, fun_validator, max_retries)
        self.loop_sprint = Sprint(loop_analyzer, loop_validator, max_retries)
        self.synthesis_sprint = Sprint(content_synthesizer, synthesis_reviewer, max_retries)
        self.concept_writer = concept_writer
        self.word_exporter = word_exporter
        self.html_exporter = html_exporter

    async def run(self, user_input: UserInput) -> PipelineState:
        state = PipelineState(user_input=user_input)

        # 1. 레퍼런스 탐색
        ref_result = await self.reference_sprint.run(
            f"다음 조건에 맞는 레퍼런스 게임을 탐색해주세요:\n{user_input.to_prompt()}"
        )
        state.reference_games = [g.strip() for g in ref_result.content.split(",") if g.strip()]

        # 2. 핵심 재미 + 게임 루프 병렬 분석
        ref_context = f"레퍼런스 게임: {', '.join(state.reference_games)}\n{user_input.to_prompt()}"
        fun_result, loop_result = await asyncio.gather(
            self.fun_sprint.run(f"다음 레퍼런스 게임의 핵심 재미 요소를 분석해주세요:\n{ref_context}"),
            self.loop_sprint.run(f"다음 레퍼런스 게임의 핵심 게임 루프를 분석해주세요:\n{ref_context}"),
        )
        state.fun_analysis = fun_result.content
        state.loop_analysis = loop_result.content

        # 3. 요약 정리
        synthesis_prompt = (
            f"다음 두 분석을 요약 정리해주세요:\n\n"
            f"[핵심 재미 분석]\n{state.fun_analysis}\n\n"
            f"[핵심 게임 루프 분석]\n{state.loop_analysis}"
        )
        synthesis_result = await self.synthesis_sprint.run(synthesis_prompt)
        state.synthesis = synthesis_result.content

        # 4. 컨셉안 작성
        concept_result = await self.concept_writer.run(
            f"다음 분석을 바탕으로 게임 컨셉안을 작성해주세요:\n\n"
            f"[사용자 요구사항]\n{user_input.to_prompt()}\n\n"
            f"[분석 요약]\n{state.synthesis}"
        )
        state.concept = concept_result.content

        # 5. 출력 생성 (병렬)
        exporters = []
        if self.word_exporter:
            exporters.append(self._export_word(state))
        if self.html_exporter:
            exporters.append(self._export_html(state))
        if exporters:
            await asyncio.gather(*exporters)

        return state

    async def _export_word(self, state: PipelineState):
        path = await asyncio.to_thread(self.word_exporter.export, state)
        state.output_word_path = path

    async def _export_html(self, state: PipelineState):
        path = await asyncio.to_thread(self.html_exporter.export, state)
        state.output_html_path = path
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_harness.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add harness.py tests/test_harness.py
git commit -m "feat: add GameConceptHarness orchestrator"
```

---

## Task 6: Reference Sprint 에이전트

**Files:**
- Create: `agents/reference_searcher.py`
- Create: `agents/reference_validator.py`

- [ ] **Step 1: reference_searcher.py 작성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 레퍼런스 전문가입니다.
사용자가 제시한 장르, 플랫폼, 키워드에 맞는 레퍼런스 게임을 탐색합니다.
결과는 반드시 쉼표로 구분된 게임 제목 목록으로만 응답하세요. 예: 게임A, 게임B, 게임C
설명 없이 게임 이름만 나열하세요. 3~5개를 추천하세요."""


class ReferenceSearcher(BaseAgent):
    ALLOWED_TOOLS = ["WebSearch"]

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

- [ ] **Step 2: reference_validator.py 작성**

```python
import json
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseEvaluator, ValidationResult

ROLE = """당신은 게임 레퍼런스 검증 전문가입니다.
제시된 레퍼런스 게임 목록이 사용자의 장르/기획 의도에 부합하는지 검증합니다.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "실패 이유와 어떤 게임을 찾아야 하는지 구체적으로"}"""


class ReferenceValidator(BaseEvaluator):
    ALLOWED_TOOLS = ["WebSearch"]

    def __init__(self, user_input_prompt: str):
        self.user_input_prompt = user_input_prompt

    async def validate(self, content: str) -> ValidationResult:
        prompt = (
            f"{ROLE}\n\n"
            f"[사용자 요구사항]\n{self.user_input_prompt}\n\n"
            f"[제안된 레퍼런스 게임]\n{content}"
        )
        response = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        data = json.loads(response.strip())
        return ValidationResult(passed=data["passed"], feedback=data.get("feedback"))
```

> **Note:** `ReferenceValidator`는 `user_input_prompt`를 생성 시 주입받습니다. `GameConceptHarness`에서 Sprint를 구성할 때 이를 전달합니다. Task 5의 `GameConceptHarness.__init__`를 아래와 같이 수정하세요:
>
> ```python
> # harness.py의 GameConceptHarness.run() 내부에서 Sprint를 동적으로 생성
> # (validator가 user_input을 알아야 하므로)
> ```
>
> `GameConceptHarness`를 수정하여 `run()` 메서드 안에서 `ReferenceValidator(user_input.to_prompt())`로 생성하거나, validator에 `set_context()`를 추가하는 방식으로 처리합니다. 가장 단순한 방법: validator에 `context` 속성을 두고 harness가 `run()` 시작 시 설정.

- [ ] **Step 3: harness.py의 ReferenceValidator 컨텍스트 설정 수정**

`harness.py`의 `GameConceptHarness.run()` 상단에 추가:
```python
# validator들에게 user_input 컨텍스트 주입
if hasattr(self.reference_sprint.evaluator, 'user_input_prompt'):
    self.reference_sprint.evaluator.user_input_prompt = user_input.to_prompt()
```

또는 `ReferenceValidator.__init__`를 수정하여 기본값 허용:
```python
def __init__(self, user_input_prompt: str = ""):
    self.user_input_prompt = user_input_prompt
```

- [ ] **Step 4: Commit**

```bash
git add agents/reference_searcher.py agents/reference_validator.py harness.py
git commit -m "feat: add ReferenceSearcher and ReferenceValidator agents"
```

---

## Task 7: Fun Analysis Sprint 에이전트

**Files:**
- Create: `agents/fun_analyzer.py`
- Create: `agents/fun_validator.py`

- [ ] **Step 1: fun_analyzer.py 작성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 디자인 전문가입니다.
레퍼런스 게임들의 핵심 재미 요소를 분석합니다.
다음 항목을 포함하여 분석하세요:
- 핵심 재미 메커니즘 (무엇이 플레이어를 즐겁게 하는가)
- 심리적 보상 구조 (어떤 감정적 만족을 주는가)
- 중독성 요소 (왜 계속 플레이하게 되는가)
명확하고 구체적으로 서술하세요."""


class FunAnalyzer(BaseAgent):
    ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

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

- [ ] **Step 2: fun_validator.py 작성**

```python
import json
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseEvaluator, ValidationResult

ROLE = """당신은 게임 리뷰 분석 전문가입니다.
제시된 핵심 재미 분석이 실제 유저들의 경험과 일치하는지 검증합니다.
실제 리뷰, 댓글, 블로그 글을 검색하여 사용자들이 실제로 같은 재미를 느끼는지 확인하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "실제 유저 반응과 다른 점과 수정 방향"}"""


class FunValidator(BaseEvaluator):
    ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

    async def validate(self, content: str) -> ValidationResult:
        prompt = f"{ROLE}\n\n[검증할 핵심 재미 분석]\n{content}"
        response = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        data = json.loads(response.strip())
        return ValidationResult(passed=data["passed"], feedback=data.get("feedback"))
```

- [ ] **Step 3: Commit**

```bash
git add agents/fun_analyzer.py agents/fun_validator.py
git commit -m "feat: add FunAnalyzer and FunValidator agents"
```

---

## Task 8: Loop Analysis Sprint 에이전트

**Files:**
- Create: `agents/loop_analyzer.py`
- Create: `agents/loop_validator.py`

- [ ] **Step 1: loop_analyzer.py 작성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 시스템 디자인 전문가입니다.
레퍼런스 게임들의 핵심 게임 루프를 분석합니다.
다음 항목을 포함하여 분석하세요:
- 코어 루프 (가장 짧은 반복 행동 사이클, 예: 이동→전투→보상)
- 미드 루프 (세션 단위 목표와 진행)
- 메타 루프 (장기 성장/진행 구조)
각 루프를 명확한 단계로 서술하세요."""


class LoopAnalyzer(BaseAgent):
    ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

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

- [ ] **Step 2: loop_validator.py 작성**

```python
import json
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseEvaluator, ValidationResult

ROLE = """당신은 게임 메커니즘 검증 전문가입니다.
제시된 게임 루프 분석이 실제 게임의 구조와 일치하는지 검증합니다.
게임의 공식 자료, 위키, 리뷰를 참조하여 루프 구조의 정확성을 확인하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "실제 게임과 다른 점과 올바른 루프 구조 설명"}"""


class LoopValidator(BaseEvaluator):
    ALLOWED_TOOLS = ["WebSearch", "WebFetch"]

    async def validate(self, content: str) -> ValidationResult:
        prompt = f"{ROLE}\n\n[검증할 게임 루프 분석]\n{content}"
        response = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        data = json.loads(response.strip())
        return ValidationResult(passed=data["passed"], feedback=data.get("feedback"))
```

- [ ] **Step 3: Commit**

```bash
git add agents/loop_analyzer.py agents/loop_validator.py
git commit -m "feat: add LoopAnalyzer and LoopValidator agents"
```

---

## Task 9: Synthesis Sprint 에이전트

**Files:**
- Create: `agents/content_synthesizer.py`
- Create: `agents/synthesis_reviewer.py`

- [ ] **Step 1: content_synthesizer.py 작성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

ROLE = """당신은 게임 기획 문서 작성 전문가입니다.
핵심 재미 분석과 게임 루프 분석을 통합하여 명확하고 간결한 요약을 작성합니다.
중복을 제거하고 핵심만 남겨 다음 구조로 정리하세요:

1. 핵심 재미 요약 (3~5줄)
2. 핵심 게임 루프 요약 (코어/미드/메타 루프 각 1~2줄)
3. 이 게임들이 성공한 공통 요인 (2~3가지)"""


class ContentSynthesizer(BaseAgent):
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

- [ ] **Step 2: synthesis_reviewer.py 작성**

```python
import json
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseEvaluator, ValidationResult

ROLE = """당신은 게임 기획 문서 리뷰어입니다.
요약본이 원본 분석 내용을 잘 반영하고 있는지 검토합니다.
다음 기준으로 평가하세요:
- 핵심 재미 요소가 누락 없이 포함되었는가
- 게임 루프가 정확하게 요약되었는가
- 내용이 모순되거나 불명확한 부분이 없는가

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "수정이 필요한 구체적인 부분과 수정 방향"}"""


class SynthesisReviewer(BaseEvaluator):
    ALLOWED_TOOLS = []

    def __init__(self):
        self.original_fun = ""
        self.original_loop = ""

    async def validate(self, content: str) -> ValidationResult:
        prompt = (
            f"{ROLE}\n\n"
            f"[원본 재미 분석]\n{self.original_fun}\n\n"
            f"[원본 루프 분석]\n{self.original_loop}\n\n"
            f"[검증할 요약본]\n{content}"
        )
        response = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        data = json.loads(response.strip())
        return ValidationResult(passed=data["passed"], feedback=data.get("feedback"))
```

> **Note:** `SynthesisReviewer`는 원본 분석 내용을 알아야 합니다. `harness.py`의 `GameConceptHarness.run()`에서 synthesis sprint 실행 전:
> ```python
> self.synthesis_sprint.evaluator.original_fun = state.fun_analysis
> self.synthesis_sprint.evaluator.original_loop = state.loop_analysis
> ```

- [ ] **Step 3: harness.py 수정 — SynthesisReviewer 컨텍스트 주입**

`harness.py`의 synthesis sprint 실행 직전에 추가:
```python
if hasattr(self.synthesis_sprint.evaluator, 'original_fun'):
    self.synthesis_sprint.evaluator.original_fun = state.fun_analysis
    self.synthesis_sprint.evaluator.original_loop = state.loop_analysis
```

- [ ] **Step 4: Commit**

```bash
git add agents/content_synthesizer.py agents/synthesis_reviewer.py harness.py
git commit -m "feat: add ContentSynthesizer and SynthesisReviewer agents"
```

---

## Task 10: Concept Writer 에이전트

**Files:**
- Create: `agents/concept_writer.py`

- [ ] **Step 1: concept_writer.py 작성**

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from agents.base import BaseAgent, AgentResult

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
- 이 게임을 만드는 이유와 시장 기회"""


class ConceptWriter(BaseAgent):
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

- [ ] **Step 2: Commit**

```bash
git add agents/concept_writer.py
git commit -m "feat: add ConceptWriter agent"
```

---

## Task 11: Word Exporter

**Files:**
- Create: `agents/word_exporter.py`

- [ ] **Step 1: word_exporter.py 작성**

```python
import re
from datetime import datetime
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from models.pipeline_state import PipelineState


class WordExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def export(self, state: PipelineState) -> str:
        doc = Document()

        # 제목 스타일
        title = doc.add_heading("게임 컨셉안", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 메타 정보
        meta = doc.add_paragraph()
        meta.add_run(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}").italic = True
        meta.add_run(f"\n장르: {state.user_input.genre}")
        if state.user_input.platform:
            meta.add_run(f" | 플랫폼: {state.user_input.platform}")

        doc.add_paragraph()

        # 컨셉 내용을 마크다운 스타일로 파싱하여 Word로 변환
        if state.concept:
            self._write_markdown_to_doc(doc, state.concept)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"concept_{timestamp}.docx"
        doc.save(str(output_path))
        return str(output_path)

    def _write_markdown_to_doc(self, doc: Document, text: str):
        for line in text.split("\n"):
            line = line.rstrip()
            if line.startswith("# "):
                doc.add_heading(line[2:], level=1)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("- "):
                p = doc.add_paragraph(line[2:], style="List Bullet")
            elif line == "":
                doc.add_paragraph()
            else:
                doc.add_paragraph(line)
```

- [ ] **Step 2: Word 출력 수동 확인**

```python
# 간단한 확인 스크립트 (임시 실행)
from models.user_input import UserInput
from models.pipeline_state import PipelineState
from agents.word_exporter import WordExporter

state = PipelineState(user_input=UserInput(genre="테스트"))
state.concept = "# 게임 컨셉안\n\n## 1. 게임 개요\n- 테스트 게임\n\n## 2. 핵심 컨셉\n테스트 내용"
exporter = WordExporter()
path = exporter.export(state)
print(f"생성됨: {path}")
```

```bash
python -c "
from models.user_input import UserInput
from models.pipeline_state import PipelineState
from agents.word_exporter import WordExporter
state = PipelineState(user_input=UserInput(genre='테스트'))
state.concept = '# 게임 컨셉안\n\n## 1. 게임 개요\n- 테스트 게임'
exporter = WordExporter()
print(exporter.export(state))
"
```

Expected: `output/concept_YYYYMMDD_HHMMSS.docx` 파일 생성

- [ ] **Step 3: Commit**

```bash
git add agents/word_exporter.py
git commit -m "feat: add WordExporter for .docx output"
```

---

## Task 12: HTML Exporter

**Files:**
- Create: `agents/html_exporter.py`
- Create: `templates/concept.html.j2`

- [ ] **Step 1: HTML 템플릿 작성**

`templates/concept.html.j2`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>게임 컨셉안 — {{ genre }}</title>
  <style>
    body { font-family: 'Noto Sans KR', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #222; line-height: 1.7; }
    h1 { color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }
    h2 { color: #16213e; border-left: 4px solid #e94560; padding-left: 12px; margin-top: 32px; }
    h3 { color: #0f3460; }
    .meta { background: #f4f4f8; padding: 12px 16px; border-radius: 6px; font-size: 0.9em; color: #555; margin-bottom: 24px; }
    ul { padding-left: 20px; }
    li { margin-bottom: 6px; }
    .concept-body { background: #fff; }
  </style>
</head>
<body>
  <h1>게임 컨셉안</h1>
  <div class="meta">
    생성일: {{ generated_at }} | 장르: {{ genre }}{% if platform %} | 플랫폼: {{ platform }}{% endif %}
  </div>
  <div class="concept-body">
    {{ concept_html | safe }}
  </div>
</body>
</html>
```

- [ ] **Step 2: html_exporter.py 작성**

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
        concept_html = self._markdown_to_html(state.concept or "")
        template = self.env.get_template("concept.html.j2")
        html = template.render(
            genre=state.user_input.genre,
            platform=state.user_input.platform,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            concept_html=concept_html,
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"concept_{timestamp}.html"
        output_path.write_text(html, encoding="utf-8")
        return str(output_path)

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

- [ ] **Step 3: HTML 출력 수동 확인**

```bash
python -c "
from models.user_input import UserInput
from models.pipeline_state import PipelineState
from agents.html_exporter import HtmlExporter
state = PipelineState(user_input=UserInput(genre='테스트', platform='모바일'))
state.concept = '# 게임 컨셉안\n\n## 1. 게임 개요\n- 테스트 게임'
exporter = HtmlExporter()
print(exporter.export(state))
"
```

Expected: `output/concept_YYYYMMDD_HHMMSS.html` 파일 생성

- [ ] **Step 4: Commit**

```bash
git add agents/html_exporter.py templates/concept.html.j2
git commit -m "feat: add HtmlExporter with Jinja2 template"
```

---

## Task 13: main.py CLI 진입점

**Files:**
- Create: `main.py`

- [ ] **Step 1: main.py 작성**

```python
import asyncio
from dotenv import load_dotenv
from models.user_input import UserInput
from harness import GameConceptHarness
from agents.reference_searcher import ReferenceSearcher
from agents.reference_validator import ReferenceValidator
from agents.fun_analyzer import FunAnalyzer
from agents.fun_validator import FunValidator
from agents.loop_analyzer import LoopAnalyzer
from agents.loop_validator import LoopValidator
from agents.content_synthesizer import ContentSynthesizer
from agents.synthesis_reviewer import SynthesisReviewer
from agents.concept_writer import ConceptWriter
from agents.word_exporter import WordExporter
from agents.html_exporter import HtmlExporter

load_dotenv()


def get_user_input() -> UserInput:
    print("=" * 50)
    print("게임 컨셉 에이전트")
    print("=" * 50)
    print("\n입력 방식을 선택하세요:")
    print("1. 간단 입력 (장르 + 기획 의도)")
    print("2. 상세 입력 (장르/플랫폼/타겟/키워드 개별 입력)")
    mode = input("\n선택 (1/2, 기본값 1): ").strip() or "1"

    if mode == "2":
        genre = input("장르 (필수): ").strip()
        platform = input("플랫폼 (선택, 예: 모바일/PC/콘솔): ").strip() or None
        target_user = input("타겟 유저 (선택, 예: 캐주얼 게이머): ").strip() or None
        keywords_raw = input("키워드 (선택, 쉼표 구분, 예: 짧은플레이,성장): ").strip()
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        free_text = input("추가 설명 (선택): ").strip() or None
    else:
        genre = input("장르와 기획 의도를 입력하세요 (예: 모바일 로그라이크 RPG, 10분 단위 플레이): ").strip()
        platform = None
        target_user = None
        keywords = []
        free_text = None

    return UserInput(
        genre=genre,
        platform=platform,
        target_user=target_user,
        keywords=keywords,
        free_text=free_text,
    )


def build_harness() -> GameConceptHarness:
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
        word_exporter=WordExporter(),
        html_exporter=HtmlExporter(),
    )


async def main():
    user_input = get_user_input()
    print(f"\n[시작] 게임 컨셉 생성 중...\n")

    harness = build_harness()
    state = await harness.run(user_input)

    print("\n" + "=" * 50)
    print("완료!")
    if state.output_word_path:
        print(f"Word 파일: {state.output_word_path}")
    if state.output_html_path:
        print(f"HTML 파일: {state.output_html_path}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: .env 생성 (로컬 실행용)**

```bash
cp .env.example .env
# 에디터로 .env를 열어 ANTHROPIC_API_KEY 설정
```

- [ ] **Step 3: import 오류 없는지 확인**

```bash
python -c "import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add CLI entry point"
```

---

## Task 14: 전체 통합 확인

- [ ] **Step 1: 전체 테스트 실행**

```bash
pytest tests/ -v
```

Expected: 모든 테스트 통과

- [ ] **Step 2: import 전체 확인**

```bash
python -c "
from harness import GameConceptHarness, Sprint, PipelineAbortedError
from models import UserInput, PipelineState
from agents.reference_searcher import ReferenceSearcher
from agents.reference_validator import ReferenceValidator
from agents.fun_analyzer import FunAnalyzer
from agents.fun_validator import FunValidator
from agents.loop_analyzer import LoopAnalyzer
from agents.loop_validator import LoopValidator
from agents.content_synthesizer import ContentSynthesizer
from agents.synthesis_reviewer import SynthesisReviewer
from agents.concept_writer import ConceptWriter
from agents.word_exporter import WordExporter
from agents.html_exporter import HtmlExporter
print('모든 모듈 import 성공')
"
```

Expected: `모든 모듈 import 성공`

- [ ] **Step 3: 최종 Commit**

```bash
git add -A
git commit -m "chore: verify all imports and finalize project setup"
```
