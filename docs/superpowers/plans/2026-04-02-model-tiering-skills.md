# 모델 티어링 + 커스텀 스킬 + 진행 표시 구현 플랜

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 역할별 모델 티어링으로 토큰 비용을 절감하고, 파이프라인 진행 상태를 터미널에 표시하며, 에이전트 추가/디버깅용 프로젝트 커스텀 스킬 2개를 추가한다.

**Architecture:** `config.yaml`에 역할별 모델 설정을 추가하고 `config.py`의 `load_models()`로 읽어 `main.py`에서 에이전트 생성 시 주입한다. `harness.py`의 `Sprint`에 `on_retry` 콜백을 추가하고 `_log()` 헬퍼로 각 단계 진행을 출력한다. `.claude/skills/`에 마크다운 스킬 파일 2개를 생성한다.

**Tech Stack:** Python 3.11+, pyyaml, claude-agent-sdk, pytest, pytest-asyncio

---

## 파일 변경 목록

| 종류 | 파일 | 내용 |
|------|------|------|
| 수정 | `config.yaml` | `models` 섹션 추가 |
| 수정 | `config.py` | `load_models()` 함수 추가 |
| 수정 | `tests/test_config.py` | `load_models()` 테스트 추가 |
| 수정 | `main.py` | `build_harness()`에서 역할별 모델 사용 |
| 수정 | `harness.py` | `_log()` 추가, `Sprint.on_retry` 콜백 추가, 단계별 로그 삽입 |
| 수정 | `tests/test_sprint.py` | `on_retry` 콜백 테스트 추가 |
| 수정 | `tests/test_harness.py` | 로그 출력 테스트 추가 |
| 신규 | `.claude/skills/new-agent.md` | 에이전트 추가 스킬 |
| 신규 | `.claude/skills/pipeline-debug.md` | 파이프라인 디버깅 스킬 |

---

### Task 1: `load_models()` 함수 추가 (config.py)

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config.py` 끝에 추가:

```python
from config import load_models


def test_load_models_returns_all_keys(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "models:\n"
        "  generator: claude-sonnet-4-6\n"
        "  validator: claude-haiku-4-5-20251001\n"
        "  writer: claude-opus-4-6\n"
        "  image: claude-sonnet-4-6\n",
        encoding="utf-8",
    )
    models = load_models(str(cfg_file))
    assert models["generator"] == "claude-sonnet-4-6"
    assert models["validator"] == "claude-haiku-4-5-20251001"
    assert models["writer"] == "claude-opus-4-6"
    assert models["image"] == "claude-sonnet-4-6"


def test_load_models_missing_file_returns_none_defaults(tmp_path):
    models = load_models(str(tmp_path / "nonexistent.yaml"))
    assert models == {"generator": None, "validator": None, "writer": None, "image": None}


def test_load_models_partial_config_fills_missing_with_none(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("models:\n  writer: claude-opus-4-6\n", encoding="utf-8")
    models = load_models(str(cfg_file))
    assert models["writer"] == "claude-opus-4-6"
    assert models["generator"] is None
    assert models["validator"] is None
    assert models["image"] is None


def test_load_models_no_models_section_returns_none_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("output:\n  format: word\n", encoding="utf-8")
    models = load_models(str(cfg_file))
    assert models == {"generator": None, "validator": None, "writer": None, "image": None}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd "e:/Github/Claude_GameConcept_Agent" && python -m pytest tests/test_config.py::test_load_models_returns_all_keys -v
```

Expected: `FAILED` — `ImportError: cannot import name 'load_models'`

- [ ] **Step 3: `load_models()` 구현**

`config.py`에 추가 (기존 `load_model()` 아래):

```python
def load_models(config_path: str = "config.yaml") -> dict:
    """역할별 모델을 dict로 반환. 키: generator, validator, writer, image.
    누락된 키는 None으로 채운다."""
    defaults = {
        "generator": None,
        "validator": None,
        "writer": None,
        "image": None,
    }
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        models = cfg.get("models", {}) or {}
        return {**defaults, **models}
    except FileNotFoundError:
        return defaults
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 기존 5개 + 신규 4개 = 9개 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add load_models() for per-role model configuration"
```

---

### Task 2: config.yaml에 모델 섹션 추가

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: config.yaml 수정**

`config.yaml` 전체를 다음으로 교체:

```yaml
output:
  format: html  # word / html / both

models:
  generator: claude-sonnet-4-6           # 분석 에이전트 (ReferenceSearcher, FunAnalyzer, LoopAnalyzer, ContentSynthesizer)
  validator: claude-haiku-4-5-20251001   # 검증 에이전트 (JSON pass/fail 판단만)
  writer: claude-opus-4-6                # 최종 컨셉안 작성 (ConceptWriter)
  image: claude-sonnet-4-6              # 이미지 생성 에이전트
```

- [ ] **Step 2: 기존 config 테스트 통과 확인**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 9개 모두 PASS (`test_config_default_format_is_html` 포함)

- [ ] **Step 3: 커밋**

```bash
git add config.yaml
git commit -m "feat: add models section to config.yaml for model tiering"
```

---

### Task 3: main.py에서 역할별 모델 사용

**Files:**
- Modify: `main.py`

- [ ] **Step 1: `load_models` import 추가 및 `build_harness()` 수정**

`main.py`의 import 줄 수정:

```python
from config import load_output_format, load_model, load_models
```

`build_harness()` 함수 전체를 다음으로 교체:

```python
def build_harness(output_format: str, session_manager: SessionManager) -> GameConceptHarness:
    models = load_models()
    return GameConceptHarness(
        reference_searcher=ReferenceSearcher(model=models["generator"]),
        reference_validator=ReferenceValidator(model=models["validator"]),
        fun_analyzer=FunAnalyzer(model=models["generator"]),
        fun_validator=FunValidator(model=models["validator"]),
        loop_analyzer=LoopAnalyzer(model=models["generator"]),
        loop_validator=LoopValidator(model=models["validator"]),
        content_synthesizer=ContentSynthesizer(model=models["generator"]),
        synthesis_reviewer=SynthesisReviewer(model=models["validator"]),
        concept_writer=ConceptWriter(model=models["writer"]),
        concept_validator=ConceptValidator(model=models["validator"]),
        word_exporter=WordExporter() if output_format in ("word", "both") else None,
        html_exporter=HtmlExporter() if output_format in ("html", "both") else None,
        word_validator=WordValidator() if output_format in ("word", "both") else None,
        html_validator=HtmlValidator() if output_format in ("html", "both") else None,
        output_format=output_format,
        session_manager=session_manager,
        reference_image_fetcher=ReferenceImageFetcher(model=models["image"]) if output_format in ("html", "both") else None,
        concept_ui_generator=ConceptUiGenerator(model=models["image"]) if output_format in ("html", "both") else None,
        concept_diagram_generator=ConceptDiagramGenerator(model=models["image"]) if output_format in ("html", "both") else None,
    )
```

- [ ] **Step 2: 전체 테스트 통과 확인**

```bash
python -m pytest -v
```

Expected: 기존 테스트 전부 PASS (main.py는 직접 테스트 없음, import 오류 없음 확인)

- [ ] **Step 3: 커밋**

```bash
git add main.py
git commit -m "feat: use role-based model tiering in build_harness()"
```

---

### Task 4: Sprint에 on_retry 콜백 추가

**Files:**
- Modify: `harness.py`
- Test: `tests/test_sprint.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_sprint.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_sprint_on_retry_callback_called_on_failure():
    """재시도 시 on_retry 콜백이 호출된다."""
    retry_calls = []

    def on_retry(attempt: int, max_r: int) -> None:
        retry_calls.append((attempt, max_r))

    gen = AlwaysFailGenerator()
    sprint = Sprint(AlwaysFailGenerator(), PassOnThirdEvaluator(), max_retries=2, on_retry=on_retry)

    async def mock_ask_user(feedback: str) -> str:
        return "proceed"

    sprint.ask_user = mock_ask_user
    await sprint.run("test")
    # 2번 실패 → 콜백 2번 호출
    assert len(retry_calls) == 2
    assert retry_calls[0] == (1, 2)
    assert retry_calls[1] == (2, 2)


@pytest.mark.asyncio
async def test_sprint_no_on_retry_callback_does_not_error():
    """on_retry=None일 때 오류 없이 동작한다."""
    sprint = Sprint(AlwaysPassGenerator(), AlwaysPassEvaluator(), on_retry=None)
    result = await sprint.run("test")
    assert result.passed is True
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_sprint.py::test_sprint_on_retry_callback_called_on_failure -v
```

Expected: `FAILED` — `TypeError: Sprint.__init__() got an unexpected keyword argument 'on_retry'`

- [ ] **Step 3: Sprint 클래스에 on_retry 추가**

`harness.py`의 `Sprint.__init__` 시그니처 수정:

```python
from collections.abc import Callable

class Sprint:
    def __init__(
        self,
        generator: BaseAgent,
        evaluator: BaseEvaluator,
        max_retries: int = 2,
        on_retry: Callable[[int, int], None] | None = None,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.max_retries = max_retries
        self.on_retry = on_retry
```

`Sprint.run()` 메서드의 재시도 부분 수정 — 기존 `if attempt >= self.max_retries:` 블록 이전에 콜백 호출 삽입:

```python
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

            if self.on_retry:
                self.on_retry(attempt + 1, self.max_retries)

            prompt = f"{initial_prompt}\n\n[이전 검증 실패 피드백]\n{validation.feedback}"

        return SprintResult(content=result.content, attempts=self.max_retries + 1, passed=False)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_sprint.py -v
```

Expected: 기존 5개 + 신규 2개 = 7개 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add harness.py tests/test_sprint.py
git commit -m "feat: add on_retry callback to Sprint for progress reporting"
```

---

### Task 5: _log() 헬퍼 및 단계별 진행 표시

**Files:**
- Modify: `harness.py`
- Test: `tests/test_harness.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_harness.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_harness_logs_step_start_and_complete(stub_harness, capsys):
    """파이프라인 실행 시 각 단계 로그가 출력된다."""
    await stub_harness.run(UserInput(genre="액션"))
    captured = capsys.readouterr()
    assert "[1/6]" in captured.out
    assert "[2/6]" in captured.out
    assert "[3/6]" in captured.out
    assert "[4/6]" in captured.out


@pytest.mark.asyncio
async def test_harness_logs_retry_on_failure(capsys):
    """검증 실패 시 재시도 로그가 출력된다."""
    class FailOnceThenPassEvaluator(BaseEvaluator):
        def __init__(self):
            self.calls = 0
        async def validate(self, content: str) -> ValidationResult:
            self.calls += 1
            return ValidationResult(passed=self.calls > 1)

    harness = GameConceptHarness(
        reference_searcher=StubAgent("game_a"),
        reference_validator=FailOnceThenPassEvaluator(),
        fun_analyzer=StubAgent("재미"),
        fun_validator=StubEvaluator(),
        loop_analyzer=StubAgent("루프"),
        loop_validator=StubEvaluator(),
        content_synthesizer=StubAgent("요약"),
        synthesis_reviewer=StubEvaluator(),
        concept_writer=StubAgent("컨셉"),
        concept_validator=StubEvaluator(),
        word_exporter=None,
        html_exporter=None,
        word_validator=None,
        html_validator=None,
    )
    await harness.run(UserInput(genre="액션"))
    captured = capsys.readouterr()
    assert "재시도" in captured.out
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_harness.py::test_harness_logs_step_start_and_complete -v
```

Expected: `FAILED` — `[1/6]`이 출력에 없음

- [ ] **Step 3: `_log()` 헬퍼 및 Sprint on_retry 람다 추가**

`harness.py` 상단 import 아래, `PipelineAbortedError` 위에 `_log()` 추가:

```python
_TOTAL_STEPS = 6


def _log(step: int, message: str) -> None:
    print(f"[{step}/{_TOTAL_STEPS}] {message}", flush=True)
```

`GameConceptHarness.__init__`에서 각 Sprint 생성 시 `on_retry` 람다 주입:

```python
        self.reference_sprint = Sprint(
            reference_searcher, reference_validator, max_retries,
            on_retry=lambda attempt, max_r: _log(1, f"레퍼런스 탐색 검증 실패 — 재시도 중... ({attempt}/{max_r})")
        )
        self.fun_sprint = Sprint(
            fun_analyzer, fun_validator, max_retries,
            on_retry=lambda attempt, max_r: _log(2, f"핵심 재미 분석 검증 실패 — 재시도 중... ({attempt}/{max_r})")
        )
        self.loop_sprint = Sprint(
            loop_analyzer, loop_validator, max_retries,
            on_retry=lambda attempt, max_r: _log(2, f"핵심 게임 루프 분석 검증 실패 — 재시도 중... ({attempt}/{max_r})")
        )
        self.synthesis_sprint = Sprint(
            content_synthesizer, synthesis_reviewer, max_retries,
            on_retry=lambda attempt, max_r: _log(3, f"분석 요약 검증 실패 — 재시도 중... ({attempt}/{max_r})")
        )
        self.concept_sprint = Sprint(
            concept_writer, concept_validator, max_retries,
            on_retry=lambda attempt, max_r: _log(4, f"컨셉안 작성 검증 실패 — 재시도 중... ({attempt}/{max_r})")
        )
```

- [ ] **Step 4: `GameConceptHarness.run()`에 단계별 로그 삽입**

`GameConceptHarness.run()` 내부 각 단계 앞뒤에 `_log()` 호출 추가:

```python
    async def run(self, user_input, resume_state=None, completed_steps=None):
        state = resume_state or PipelineState(user_input=user_input)
        done = set(completed_steps or [])

        if hasattr(self.reference_sprint.evaluator, 'user_input_prompt'):
            self.reference_sprint.evaluator.user_input_prompt = user_input.to_prompt()

        # 1. 레퍼런스 탐색
        if "reference" not in done:
            _log(1, "레퍼런스 탐색 중...")
            ref_result = await self.reference_sprint.run(
                f"다음 조건에 맞는 레퍼런스 게임을 3개 이상 10개 이하로 탐색해주세요:\n{user_input.to_prompt()}"
            )
            state.reference_games = [g.strip() for g in ref_result.content.split(",") if g.strip()]
            done |= {"reference"}
            _log(1, f"레퍼런스 탐색 완료 (시도: {ref_result.attempts}회)")
            self._checkpoint(state, done)

        # 2. 핵심 재미 + 게임 루프 병렬 분석
        if "fun_analysis" not in done or "loop_analysis" not in done:
            ref_context = f"레퍼런스 게임: {', '.join(state.reference_games)}\n{user_input.to_prompt()}"
            tasks = []
            if "fun_analysis" not in done:
                _log(2, "핵심 재미 분석 중...")
                tasks.append(self.fun_sprint.run(f"다음 레퍼런스 게임의 핵심 재미 요소를 분석해주세요:\n{ref_context}"))
            if "loop_analysis" not in done:
                _log(2, "핵심 게임 루프 분석 중...")
                tasks.append(self.loop_sprint.run(f"다음 레퍼런스 게임의 핵심 게임 루프를 분석해주세요:\n{ref_context}"))
            results = await asyncio.gather(*tasks)
            idx = 0
            if "fun_analysis" not in done:
                state.fun_analysis = results[idx].content
                _log(2, f"핵심 재미 분석 완료 (시도: {results[idx].attempts}회)")
                idx += 1
            if "loop_analysis" not in done:
                state.loop_analysis = results[idx].content
                _log(2, f"핵심 게임 루프 분석 완료 (시도: {results[idx].attempts}회)")
            done |= {"fun_analysis", "loop_analysis"}
            self._checkpoint(state, done)

        # 3. 요약 정리
        if "synthesis" not in done:
            if hasattr(self.synthesis_sprint.evaluator, 'original_fun'):
                self.synthesis_sprint.evaluator.original_fun = state.fun_analysis
                self.synthesis_sprint.evaluator.original_loop = state.loop_analysis
            _log(3, "분석 요약 중...")
            synthesis_result = await self.synthesis_sprint.run(
                f"다음 두 분석을 요약 정리해주세요:\n\n"
                f"[핵심 재미 분석]\n{state.fun_analysis}\n\n"
                f"[핵심 게임 루프 분석]\n{state.loop_analysis}"
            )
            full_summary, key_points = parse_synthesis(synthesis_result.content)
            state.synthesis = full_summary
            state.synthesis_key_points = key_points
            done |= {"synthesis"}
            _log(3, f"분석 요약 완료 (시도: {synthesis_result.attempts}회)")
            self._checkpoint(state, done)

        # 4. 컨셉안 작성
        if "concept" not in done:
            if hasattr(self.concept_sprint.evaluator, 'synthesis_key_points'):
                self.concept_sprint.evaluator.synthesis_key_points = state.synthesis_key_points or ""
            _log(4, "게임 컨셉안 작성 중...")
            concept_result = await self.concept_sprint.run(
                f"다음 분석을 바탕으로 게임 컨셉안을 작성해주세요:\n\n"
                f"[사용자 요구사항]\n{user_input.to_prompt()}\n\n"
                f"[분석 요약]\n{state.synthesis}"
            )
            state.concept = concept_result.content
            done |= {"concept"}
            _log(4, f"게임 컨셉안 작성 완료 (시도: {concept_result.attempts}회)")
            self._checkpoint(state, done)

        # 5. 이미지 생성 (HTML 출력 시에만)
        if "images" not in done and self.output_format in ("html", "both"):
            run_image = any([
                self.reference_image_fetcher,
                self.concept_ui_generator,
                self.concept_diagram_generator,
            ])
            if run_image:
                _log(5, "이미지 생성 중...")
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
                _log(5, "이미지 생성 완료")
            done |= {"images"}
            self._checkpoint(state, done)

        # 6. 출력 생성
        if self.output_format in ("word", "both") and "word_export" not in done:
            _log(6, "Word 출력 생성 중...")
            await self._export_with_validation(
                state, self.word_exporter, self.word_validator, "word_export", done
            )
            _log(6, "Word 출력 완료!")
        if self.output_format in ("html", "both") and "html_export" not in done:
            _log(6, "HTML 출력 생성 중...")
            await self._export_with_validation(
                state, self.html_exporter, self.html_validator, "html_export", done
            )
            _log(6, "HTML 출력 완료!")

        if self.output_format not in ("word", "both") and self.output_format not in ("html", "both"):
            _log(6, "완료!")
        elif "word_export" in done or "html_export" in done:
            pass  # 위에서 각각 완료 로그 출력

        if self.session_manager:
            self.session_manager.clear()

        return state
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/test_harness.py tests/test_sprint.py -v
```

Expected: 전부 PASS

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
python -m pytest -v
```

Expected: 전부 PASS

- [ ] **Step 7: 커밋**

```bash
git add harness.py tests/test_harness.py
git commit -m "feat: add pipeline step logging with _log() and Sprint on_retry callbacks"
```

---

### Task 6: 프로젝트 커스텀 스킬 파일 생성

**Files:**
- Create: `.claude/skills/new-agent.md`
- Create: `.claude/skills/pipeline-debug.md`

- [ ] **Step 1: `.claude/skills/` 디렉토리 생성 확인 후 new-agent.md 작성**

`.claude/skills/new-agent.md` 생성:

```markdown
---
description: 이 프로젝트에 새 에이전트를 추가할 때 사용. Generator(BaseAgent)와 Evaluator(BaseEvaluator) 패턴, 모델 티어, harness 등록까지 체크리스트로 안내.
---

# new-agent 스킬

이 프로젝트의 에이전트를 추가할 때 다음 체크리스트를 순서대로 실행하세요.

## 체크리스트

- [ ] **1. 역할 확인**: 새 에이전트가 Generator(`BaseAgent`)인지 Evaluator(`BaseEvaluator`)인지 사용자에게 확인한다.

- [ ] **2. 도구 확인**: `WebSearch` / `WebFetch` 가 필요한지 확인한다. 불필요한 WebSearch는 토큰 낭비다.

- [ ] **3. 모델 티어 선택**: `config.yaml`의 `models` 섹션 중 어느 키를 쓸지 결정한다.
  - `generator` — 분석/탐색 에이전트 (Sonnet)
  - `validator` — JSON pass/fail 판단만 하는 Evaluator (Haiku)
  - `writer` — 최종 산출물 생성 (Opus)
  - `image` — 시각 자료 생성 (Sonnet)

- [ ] **4. 파일 생성**: `agents/<snake_case_name>.py` 생성.

  Generator 템플릿:
  ```python
  from claude_agent_sdk import query
  from agents.base import BaseAgent, AgentResult

  ROLE = """역할 설명을 여기에 작성하세요."""


  class MyAgent(BaseAgent):
      ALLOWED_TOOLS = []  # 필요한 도구만: ["WebSearch", "WebFetch"]

      async def run(self, prompt: str) -> AgentResult:
          full_prompt = f"{ROLE}\n\n{prompt}"
          result_content = ""
          async for message in query(
              prompt=full_prompt,
              options=self._options(allowed_tools=self.ALLOWED_TOOLS),
          ):
              if hasattr(message, "result"):
                  result_content = message.result
          return AgentResult(content=result_content)
  ```

  Evaluator 템플릿 (JSON 응답 필수):
  ```python
  import json
  from claude_agent_sdk import query
  from agents.base import BaseEvaluator, ValidationResult

  ROLE = """검증 역할 설명.

  반드시 다음 JSON 형식으로만 응답하세요:
  {"passed": true, "feedback": null}
  또는
  {"passed": false, "feedback": "수정 방향"}"""


  class MyValidator(BaseEvaluator):
      ALLOWED_TOOLS = []

      async def validate(self, content: str) -> ValidationResult:
          prompt = f"{ROLE}\n\n[검증할 내용]\n{content}"
          response = ""
          async for message in query(
              prompt=prompt,
              options=self._options(allowed_tools=self.ALLOWED_TOOLS),
          ):
              if hasattr(message, "result"):
                  response = message.result
          try:
              data = json.loads(response.strip())
              return ValidationResult(passed=data["passed"], feedback=data.get("feedback"))
          except (json.JSONDecodeError, KeyError):
              return ValidationResult(passed=False, feedback=f"검증 응답 파싱 실패: {response[:200]}")
  ```

- [ ] **5. main.py 등록**: `from agents.<name> import <ClassName>` import 추가. `build_harness()`에서 `models["<tier>"]` 모델로 인스턴스 생성.

- [ ] **6. harness.py 등록**: `GameConceptHarness.__init__` 파라미터에 추가. 필요한 Sprint 또는 단계에 연결.

- [ ] **7. 진행 로그 추가**: 새 단계라면 `_TOTAL_STEPS` 값 증가 및 `_log(step, ...)` 호출 추가.
```

- [ ] **Step 2: pipeline-debug.md 작성**

`.claude/skills/pipeline-debug.md` 생성:

```markdown
---
description: 파이프라인 단계 실패, Validator 오작동, 토큰 과다 사용 등을 진단할 때 사용.
---

# pipeline-debug 스킬

파이프라인 문제를 진단할 때 다음 순서로 점검하세요.

## 체크리스트

- [ ] **1. 실패 단계 특정**: `[N/6]` 로그에서 어느 단계인지 확인. `harness.py`의 단계 번호 기준:
  - 1 = 레퍼런스 탐색 (ReferenceSearcher / ReferenceValidator)
  - 2 = 재미+루프 분석 (FunAnalyzer, LoopAnalyzer / 각 Validator)
  - 3 = 분석 요약 (ContentSynthesizer / SynthesisReviewer)
  - 4 = 컨셉안 작성 (ConceptWriter / ConceptValidator)
  - 5 = 이미지 생성 (ReferenceImageFetcher, ConceptUiGenerator, ConceptDiagramGenerator)
  - 6 = 출력 (HtmlExporter / WordExporter)

- [ ] **2. 해당 에이전트 파일 읽기**: `agents/<name>.py`의 `ROLE` 프롬프트 점검.
  - ROLE이 너무 길거나 모호하지 않은지
  - 출력 형식 지시가 명확한지

- [ ] **3. Evaluator 진단** (Validator가 계속 false 반환 시):
  - JSON 파싱 실패인지 확인 — `"검증 응답 파싱 실패:"` 피드백 문자열 포함 여부
  - 기준이 과도하게 엄격한지 (ROLE 프롬프트 완화 검토)
  - `synthesis_key_points` 등 주입 의존 속성이 비어있지 않은지 확인

- [ ] **4. WebSearch 필요성 재검토**: `ALLOWED_TOOLS`에 `WebSearch`가 있다면,
  - 이 단계에서 실제로 외부 검색이 필요한가?
  - Validator가 WebSearch를 쓴다면 → 제거 검토 (논리 일관성 체크만으로 충분)

- [ ] **5. 모델 티어 확인**: `config.yaml`의 `models` 섹션 확인.
  - Validator에 `claude-opus-4-6`이 쓰이고 있지 않은지
  - `main.py`의 `build_harness()`에서 `models["validator"]`를 올바르게 주입하는지

- [ ] **6. 컨텍스트 크기 점검** (토큰 과다 시):
  - `harness.py`에서 해당 단계로 넘기는 텍스트가 전체 분석 원문인지 확인
  - `synthesis_key_points` (압축본) 대신 `synthesis` (전문)을 넘기고 있다면 교체 검토

- [ ] **7. 재시도 빈도 확인**: `SprintResult.attempts` 값이 로그에 표시됨.
  - 항상 max_retries까지 소모한다면 ROLE 프롬프트 또는 Validator 기준 조정 필요
```

- [ ] **Step 3: 스킬 파일 정상 인식 확인**

Claude Code에서 `/` 입력 후 `new-agent`, `pipeline-debug` 가 목록에 나타나는지 확인한다. (Claude Code가 `.claude/skills/*.md` 를 자동 인식)

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/new-agent.md .claude/skills/pipeline-debug.md
git commit -m "feat: add new-agent and pipeline-debug project skills"
```

---

## 셀프 리뷰

**스펙 커버리지 확인:**
- ✅ 모델 티어링: Task 1 (load_models), Task 2 (config.yaml), Task 3 (main.py)
- ✅ 진행 표시: Task 4 (on_retry), Task 5 (_log + 단계별 로그)
- ✅ 커스텀 스킬: Task 6 (new-agent.md, pipeline-debug.md)

**타입 일관성 확인:**
- `load_models()` 반환: `dict[str, str | None]` — Task 1, 3 모두 동일하게 사용
- `on_retry: Callable[[int, int], None] | None` — Task 4 정의, Task 5에서 람다로 주입
- `_log(step: int, message: str)` — Task 5 정의, Task 5에서 사용

**Placeholder 없음** — 모든 코드 블록 완성됨
