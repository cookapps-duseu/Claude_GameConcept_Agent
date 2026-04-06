# 컨셉안 품질 평가 + 이미지 품질 평가 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 컨셉안 품질 평가 루프(3개 기준, 80점 이상 통과, 최대 5회)와 씬별 SVG 이미지 품질 평가 루프(최대 10회, 최고 점수 채택)를 파이프라인에 추가한다.

**Architecture:** 두 개의 새 평가 에이전트(`ConceptQualityEvaluator`, `ConceptUiEvaluator`)를 추가하고, `GameConceptHarness`에 Step 4.5(컨셉 품질)와 Step 5 내부 씬별 루프를 추가한다. 파이프라인 총 단계는 6→7로 증가한다.

**Tech Stack:** Python asyncio, claude_agent_sdk, pytest-asyncio, 기존 BaseEvaluator 패턴

---

## 파일 구조

| 파일 | 변경 유형 | 역할 |
|------|-----------|------|
| `agents/concept_quality_evaluator.py` | 신규 | 3개 기준 100점 채점 |
| `agents/concept_ui_evaluator.py` | 신규 | SVG 씬 100점 채점 |
| `models/pipeline_state.py` | 수정 | concept_quality_scores, concept_quality_failure_reason 필드 추가 |
| `session_manager.py` | 수정 | 새 필드 직렬화/역직렬화 |
| `harness.py` | 수정 | Step 4.5 추가, Step 5 SVG 루프 변경, _TOTAL_STEPS 7로, _generate_scene_svg 메서드 추가 |
| `main.py` | 수정 | build_harness에 두 새 에이전트 주입 |
| `tests/test_concept_quality_evaluator.py` | 신규 | ConceptQualityEvaluator 테스트 |
| `tests/test_concept_ui_evaluator.py` | 신규 | ConceptUiEvaluator 테스트 |
| `tests/test_harness.py` | 수정 | 기존 픽스처 업데이트 + 새 동작 테스트 |

---

### Task 1: PipelineState + SessionManager 필드 추가

**Files:**
- Modify: `models/pipeline_state.py`
- Modify: `session_manager.py`
- Modify: `tests/test_session_manager.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_session_manager.py` 하단에 추가:

```python
def test_save_preserves_concept_quality_fields(tmp_session):
    state = make_state()
    state.concept_quality_scores = {"mechanism": 85, "fun": 90, "market": 78}
    state.concept_quality_failure_reason = "market 점수 미달"
    tmp_session.save(state, completed_steps=["concept_quality"])
    loaded_state, steps = tmp_session.load()
    assert loaded_state.concept_quality_scores == {"mechanism": 85, "fun": 90, "market": 78}
    assert loaded_state.concept_quality_failure_reason == "market 점수 미달"
    assert "concept_quality" in steps
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_session_manager.py::test_save_preserves_concept_quality_fields -v
```

Expected: FAIL with `AttributeError: 'PipelineState' object has no attribute 'concept_quality_scores'`

- [ ] **Step 3: PipelineState 필드 추가**

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
    synthesis_key_points: str | None = None
    concept: str | None = None
    output_word_path: str | None = None
    output_html_path: str | None = None
    reference_images: list[dict] = field(default_factory=list)
    concept_ui_svgs: list[dict] = field(default_factory=list)
    concept_diagram_mermaid: str | None = None
    concept_quality_scores: dict | None = None
    concept_quality_failure_reason: str | None = None
```

- [ ] **Step 4: SessionManager 직렬화/역직렬화 추가**

`session_manager.py`의 `save()` 메서드 `data` dict에 추가:

```python
"concept_quality_scores": state.concept_quality_scores,
"concept_quality_failure_reason": state.concept_quality_failure_reason,
```

`load()` 메서드에 추가:

```python
state.concept_quality_scores = data.get("concept_quality_scores")
state.concept_quality_failure_reason = data.get("concept_quality_failure_reason")
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_session_manager.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add models/pipeline_state.py session_manager.py tests/test_session_manager.py
git commit -m "feat: add concept_quality_scores and failure_reason fields to PipelineState"
```

---

### Task 2: ConceptQualityEvaluator 구현

**Files:**
- Create: `agents/concept_quality_evaluator.py`
- Create: `tests/test_concept_quality_evaluator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_concept_quality_evaluator.py` 전체:

```python
import pytest
from dataclasses import dataclass
from agents.concept_quality_evaluator import ConceptQualityEvaluator, ConceptQualityResult


def test_concept_quality_result_passed_when_all_above_threshold():
    result = ConceptQualityResult(
        passed=True,
        scores={"mechanism": 85, "fun": 90, "market": 82},
        feedback=None,
    )
    assert result.passed is True
    assert result.feedback is None


def test_concept_quality_result_failed_when_any_below_threshold():
    result = ConceptQualityResult(
        passed=False,
        scores={"mechanism": 85, "fun": 75, "market": 82},
        feedback="재미 요소가 구체적이지 않습니다.",
    )
    assert result.passed is False
    assert result.feedback is not None


def test_concept_quality_evaluator_parses_json():
    evaluator = ConceptQualityEvaluator()
    response = '{"scores": {"mechanism": 85, "fun": 90, "market": 82}, "feedback": null}'
    result = evaluator._parse_result(response)
    assert result.passed is True
    assert result.scores["mechanism"] == 85
    assert result.feedback is None


def test_concept_quality_evaluator_failed_when_score_below_80():
    evaluator = ConceptQualityEvaluator()
    response = '{"scores": {"mechanism": 79, "fun": 90, "market": 82}, "feedback": "메커니즘 설명 부족"}'
    result = evaluator._parse_result(response)
    assert result.passed is False
    assert result.scores["mechanism"] == 79
    assert result.feedback == "메커니즘 설명 부족"


def test_concept_quality_evaluator_boundary_exactly_80():
    evaluator = ConceptQualityEvaluator()
    response = '{"scores": {"mechanism": 80, "fun": 80, "market": 80}, "feedback": null}'
    result = evaluator._parse_result(response)
    assert result.passed is True


def test_concept_quality_evaluator_invalid_json_returns_failed():
    evaluator = ConceptQualityEvaluator()
    result = evaluator._parse_result("invalid json")
    assert result.passed is False
    assert result.feedback is not None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_concept_quality_evaluator.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agents.concept_quality_evaluator'`

- [ ] **Step 3: ConceptQualityEvaluator 구현**

`agents/concept_quality_evaluator.py` 전체:

```python
import json
from dataclasses import dataclass
from claude_agent_sdk import query
from agents.base import BaseEvaluator

ROLE = """당신은 게임 컨셉안 품질 평가 전문가입니다.
제시된 게임 컨셉안을 3개 기준으로 각 100점 만점 채점합니다.

채점 기준:
- mechanism (메커니즘 구체성): 핵심 게임 루프, 규칙, 수치가 구체적으로 기술되어 있는가
- fun (재미 요소 명확성): 플레이어가 왜 재미있는지 감정적 경험이 명확히 설명되는가
- market (시장성/수익화): 타겟 시장과 수익화 방향이 현실적으로 제시되어 있는가

각 기준을 독립적으로 평가하세요. 점수는 정수여야 합니다.
80점 미만 항목이 있으면 feedback에 구체적인 개선 방향을 작성하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"scores": {"mechanism": <0-100 정수>, "fun": <0-100 정수>, "market": <0-100 정수>}, "feedback": "<개선 방향 또는 null>"}"""

THRESHOLD = 80


@dataclass
class ConceptQualityResult:
    passed: bool
    scores: dict
    feedback: str | None


class ConceptQualityEvaluator(BaseEvaluator):
    ALLOWED_TOOLS = []

    def _parse_result(self, response: str) -> ConceptQualityResult:
        try:
            data = self._parse_json(response)
            scores = data["scores"]
            passed = all(scores.get(k, 0) >= THRESHOLD for k in ("mechanism", "fun", "market"))
            return ConceptQualityResult(
                passed=passed,
                scores=scores,
                feedback=data.get("feedback"),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return ConceptQualityResult(
                passed=False,
                scores={"mechanism": 0, "fun": 0, "market": 0},
                feedback=f"평가 응답 파싱 실패: {response[:200]}",
            )

    async def evaluate(self, concept: str) -> ConceptQualityResult:
        prompt = f"{ROLE}\n\n[평가할 게임 컨셉안]\n{concept}"
        response = ""
        async for message in query(
            prompt=prompt,
            options=self._options(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        return self._parse_result(response)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_concept_quality_evaluator.py -v
```

Expected: 6개 테스트 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add agents/concept_quality_evaluator.py tests/test_concept_quality_evaluator.py
git commit -m "feat: add ConceptQualityEvaluator with 3-criteria 100-point scoring"
```

---

### Task 3: ConceptUiEvaluator 구현

**Files:**
- Create: `agents/concept_ui_evaluator.py`
- Create: `tests/test_concept_ui_evaluator.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_concept_ui_evaluator.py` 전체:

```python
import pytest
from agents.concept_ui_evaluator import ConceptUiEvaluator, UiEvalResult


def test_ui_eval_result_passed_when_above_threshold():
    result = UiEvalResult(passed=True, score=85, feedback=None)
    assert result.passed is True


def test_ui_eval_result_failed_when_below_threshold():
    result = UiEvalResult(passed=False, score=72, feedback="씬 설명과 다른 화면")
    assert result.passed is False


def test_concept_ui_evaluator_parses_json():
    evaluator = ConceptUiEvaluator()
    response = '{"score": 88, "feedback": null}'
    result = evaluator._parse_result(response)
    assert result.passed is True
    assert result.score == 88
    assert result.feedback is None


def test_concept_ui_evaluator_failed_when_below_80():
    evaluator = ConceptUiEvaluator()
    response = '{"score": 65, "feedback": "레이아웃이 게임 화면답지 않음"}'
    result = evaluator._parse_result(response)
    assert result.passed is False
    assert result.score == 65
    assert result.feedback == "레이아웃이 게임 화면답지 않음"


def test_concept_ui_evaluator_boundary_exactly_80():
    evaluator = ConceptUiEvaluator()
    response = '{"score": 80, "feedback": null}'
    result = evaluator._parse_result(response)
    assert result.passed is True


def test_concept_ui_evaluator_invalid_json_returns_failed():
    evaluator = ConceptUiEvaluator()
    result = evaluator._parse_result("not json")
    assert result.passed is False
    assert result.score == 0
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_concept_ui_evaluator.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agents.concept_ui_evaluator'`

- [ ] **Step 3: ConceptUiEvaluator 구현**

`agents/concept_ui_evaluator.py` 전체:

```python
import json
from dataclasses import dataclass
from claude_agent_sdk import query
from agents.base import BaseEvaluator

ROLE = """당신은 게임 UI 품질 평가 전문가입니다.
제시된 SVG 이미지가 씬 설명을 얼마나 잘 구현했는지 100점 만점으로 채점합니다.

채점 기준:
- 씬 제목/설명과 시각적 내용 일치도 (40점)
- 인게임 화면으로서의 적합성 — UI 요소, 레이아웃 구성 (35점)
- 장르/컨셉 분위기 반영 (25점)

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"score": <0-100 정수>, "feedback": "<개선 방향 또는 null>"}"""

THRESHOLD = 80


@dataclass
class UiEvalResult:
    passed: bool
    score: int
    feedback: str | None


class ConceptUiEvaluator(BaseEvaluator):
    ALLOWED_TOOLS = []

    def _parse_result(self, response: str) -> UiEvalResult:
        try:
            data = self._parse_json(response)
            score = int(data["score"])
            return UiEvalResult(
                passed=score >= THRESHOLD,
                score=score,
                feedback=data.get("feedback"),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return UiEvalResult(
                passed=False,
                score=0,
                feedback=f"평가 응답 파싱 실패: {response[:200]}",
            )

    async def evaluate(self, scene: dict, svg: str) -> UiEvalResult:
        prompt = (
            f"{ROLE}\n\n"
            f"[씬 제목] {scene.get('title', '')}\n"
            f"[씬 설명] {scene.get('desc', '')}\n\n"
            f"[SVG 이미지]\n{svg}"
        )
        response = ""
        async for message in query(
            prompt=prompt,
            options=self._options(allowed_tools=self.ALLOWED_TOOLS),
        ):
            if hasattr(message, "result"):
                response = message.result
        return self._parse_result(response)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_concept_ui_evaluator.py -v
```

Expected: 6개 테스트 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add agents/concept_ui_evaluator.py tests/test_concept_ui_evaluator.py
git commit -m "feat: add ConceptUiEvaluator with 100-point SVG quality scoring"
```

---

### Task 4: Harness Step 4.5 — 컨셉 품질 평가 루프

**Files:**
- Modify: `harness.py`
- Modify: `tests/test_harness.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_harness.py` 하단에 추가:

```python
from agents.concept_quality_evaluator import ConceptQualityEvaluator, ConceptQualityResult


class StubQualityEvaluator:
    async def evaluate(self, concept: str) -> ConceptQualityResult:
        return ConceptQualityResult(
            passed=True,
            scores={"mechanism": 90, "fun": 85, "market": 88},
            feedback=None,
        )


class FailThenPassQualityEvaluator:
    def __init__(self, fail_count: int):
        self.calls = 0
        self.fail_count = fail_count

    async def evaluate(self, concept: str) -> ConceptQualityResult:
        self.calls += 1
        if self.calls <= self.fail_count:
            return ConceptQualityResult(
                passed=False,
                scores={"mechanism": 60, "fun": 90, "market": 88},
                feedback=f"메커니즘 개선 필요 (호출 {self.calls})",
            )
        return ConceptQualityResult(
            passed=True,
            scores={"mechanism": 85, "fun": 90, "market": 88},
            feedback=None,
        )


@pytest.fixture
def quality_stub_harness(tmp_path):
    return GameConceptHarness(
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
        html_exporter=None,
        html_validator=None,
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        concept_quality_evaluator=StubQualityEvaluator(),
    )


@pytest.mark.asyncio
async def test_harness_concept_quality_scores_saved(quality_stub_harness):
    """Step 4.5: 품질 평가 통과 시 scores가 state에 저장된다."""
    state = await quality_stub_harness.run(UserInput(genre="액션"))
    assert state.concept_quality_scores == {"mechanism": 90, "fun": 85, "market": 88}


@pytest.mark.asyncio
async def test_harness_concept_quality_retries_on_fail(tmp_path):
    """Step 4.5: 실패 후 재시도하면 ConceptWriter가 다시 호출된다."""
    evaluator = FailThenPassQualityEvaluator(fail_count=2)
    writer = StubAgent("최종 컨셉안")
    harness = GameConceptHarness(
        reference_searcher=StubAgent("game_a"),
        reference_validator=StubEvaluator(),
        fun_analyzer=StubAgent("재미"),
        fun_validator=StubEvaluator(),
        loop_analyzer=StubAgent("루프"),
        loop_validator=StubEvaluator(),
        content_synthesizer=StubAgent("[FULL_SUMMARY]\n요약\n[KEY_POINTS]\n- 핵심"),
        synthesis_reviewer=StubEvaluator(),
        concept_writer=writer,
        concept_validator=StubEvaluator(),
        html_exporter=None,
        html_validator=None,
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        concept_quality_evaluator=evaluator,
    )
    state = await harness.run(UserInput(genre="액션"))
    # 평가가 3번 호출됨 (2번 실패 + 1번 통과)
    assert evaluator.calls == 3
    assert state.concept_quality_scores["mechanism"] == 85
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_harness.py::test_harness_concept_quality_scores_saved tests/test_harness.py::test_harness_concept_quality_retries_on_fail -v
```

Expected: FAIL (GameConceptHarness에 concept_quality_evaluator 파라미터 없음)

- [ ] **Step 3: Harness __init__ 수정**

`harness.py`의 `GameConceptHarness.__init__` 파라미터 추가:

```python
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
    html_exporter,
    html_validator,
    session_manager=None,
    max_retries: int = 10,
    reference_image_fetcher: BaseAgent | None = None,
    concept_ui_generator: BaseAgent | None = None,
    concept_diagram_generator: BaseAgent | None = None,
    concept_quality_evaluator=None,
    concept_ui_evaluator=None,
):
    # ... 기존 Sprint 초기화 코드 그대로 ...
    self.concept_quality_evaluator = concept_quality_evaluator
    self.concept_ui_evaluator = concept_ui_evaluator
```

- [ ] **Step 4: _TOTAL_STEPS 업데이트 및 _build_failure_reason 추가**

`harness.py` 상단:

```python
_TOTAL_STEPS = 7
```

`harness.py`에 모듈 레벨 함수 추가 (클래스 밖):

```python
def _build_failure_reason(scores: dict, feedbacks: list[str]) -> str:
    lines = ["[컨셉 품질 평가 5회 실패 - 상세 이유]"]
    threshold = 80
    for key, label in [("mechanism", "메커니즘 구체성"), ("fun", "재미 요소 명확성"), ("market", "시장성/수익화")]:
        score = scores.get(key, 0)
        status = "통과" if score >= threshold else f"미달 ({score}점)"
        lines.append(f"- {label}: {status}")
    lines.append("\n[누적 피드백]")
    for i, fb in enumerate(feedbacks, 1):
        lines.append(f"[{i}차]\n{fb}")
    return "\n".join(lines)
```

- [ ] **Step 5: Step 4.5 루프 추가**

`harness.py`의 `run()` 메서드에서 Step 4 완료 직후 (Step 5 이전)에 추가:

```python
        # 4.5. 컨셉 품질 평가
        if "concept_quality" not in done and self.concept_quality_evaluator:
            _log(5, "컨셉 품질 평가 중...")
            MAX_QUALITY_RETRIES = 5
            all_quality_feedbacks: list[str] = []
            for attempt in range(MAX_QUALITY_RETRIES + 1):
                eval_result = await self.concept_quality_evaluator.evaluate(state.concept or "")
                state.concept_quality_scores = eval_result.scores
                if eval_result.passed:
                    _log(5, f"컨셉 품질 평가 통과 (시도: {attempt + 1}회) {eval_result.scores}")
                    break
                if eval_result.feedback:
                    all_quality_feedbacks.append(eval_result.feedback)
                if attempt >= MAX_QUALITY_RETRIES:
                    _log(5, "컨셉 품질 평가 5회 실패 - 분석 단계부터 재실행")
                    state.concept_quality_failure_reason = _build_failure_reason(
                        eval_result.scores, all_quality_feedbacks
                    )
                    done -= {"fun_analysis", "loop_analysis", "synthesis", "concept", "concept_quality"}
                    self._checkpoint(state, done)
                    return await self.run(user_input, resume_state=state, completed_steps=list(done))
                _log(5, f"컨셉 품질 평가 실패 - 재시도 중... ({attempt + 1}/{MAX_QUALITY_RETRIES})")
                feedback_text = "\n\n".join(
                    f"[{i+1}차 품질 피드백]\n{fb}" for i, fb in enumerate(all_quality_feedbacks)
                )
                concept_result = await self.concept_sprint.generator.run(
                    f"다음 품질 평가 피드백을 반영하여 컨셉안을 개선하세요:\n\n{feedback_text}\n\n"
                    f"[사용자 요구사항]\n{user_input.to_prompt()}\n\n"
                    f"[현재 컨셉안]\n{state.concept}"
                )
                state.concept = concept_result.content
            done |= {"concept_quality"}
            self._checkpoint(state, done)
        elif "concept_quality" not in done:
            done |= {"concept_quality"}
```

- [ ] **Step 6: 기존 로그 번호 수정**

`harness.py`에서 이미지 단계와 HTML 단계 로그 번호 업데이트:

```python
# 이미지 단계: _log(5, ...) → _log(6, ...)
# HTML 단계: _log(6, ...) → _log(7, ...)
```

- [ ] **Step 7: 기존 테스트의 로그 번호 검증 수정**

`tests/test_harness.py`의 `test_harness_logs_step_start_and_complete`:

```python
async def test_harness_logs_step_start_and_complete(stub_harness, capsys):
    await stub_harness.run(UserInput(genre="액션"))
    captured = capsys.readouterr()
    assert "[1/7]" in captured.out
    assert "[2/7]" in captured.out
    assert "[3/7]" in captured.out
    assert "[4/7]" in captured.out
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_harness.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 9: 커밋**

```bash
git add harness.py tests/test_harness.py
git commit -m "feat: add Step 4.5 concept quality evaluation loop with auto-retry to Step 2"
```

---

### Task 5: Harness Step 5 — 씬별 SVG 품질 평가 루프

**Files:**
- Modify: `harness.py`
- Modify: `tests/test_harness.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_harness.py` 하단에 추가:

```python
from agents.concept_ui_evaluator import ConceptUiEvaluator, UiEvalResult


class StubUiEvaluator:
    def __init__(self, score: int = 90):
        self.score = score
        self.calls = 0

    async def evaluate(self, scene: dict, svg: str) -> UiEvalResult:
        self.calls += 1
        return UiEvalResult(
            passed=self.score >= 80,
            score=self.score,
            feedback=None if self.score >= 80 else "품질 미달",
        )


class BestPickUiEvaluator:
    """처음 9번은 70점, 마지막(10번째)도 70점 → 최고 점수(70) 선택"""
    def __init__(self):
        self.calls = 0
        self.scores = []

    async def evaluate(self, scene: dict, svg: str) -> UiEvalResult:
        self.calls += 1
        score = 70
        self.scores.append(score)
        return UiEvalResult(passed=False, score=score, feedback="개선 필요")


@pytest.mark.asyncio
async def test_harness_svg_quality_evaluator_called_per_scene(tmp_path):
    """씬별로 ui_evaluator가 호출된다."""
    concept_with_scenes = (
        "컨셉 본문\n[IMG_SCENE_1]\n[IMG_SCENE_2]\n"
        "---SCENE_LIST---\n"
        '[{"id": 1, "title": "씬1", "desc": "설명1"}, {"id": 2, "title": "씬2", "desc": "설명2"}]'
    )
    ui_evaluator = StubUiEvaluator(score=90)
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
        html_exporter=None,
        html_validator=None,
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        reference_image_fetcher=StubAgent("[]"),
        concept_ui_generator=StubAgent("<svg/>"),
        concept_diagram_generator=StubAgent(""),
        concept_ui_evaluator=ui_evaluator,
    )
    state = await harness.run(UserInput(genre="액션"))
    assert len(state.concept_ui_svgs) == 2
    assert ui_evaluator.calls == 2  # 씬 2개, 각 1회 통과


@pytest.mark.asyncio
async def test_harness_svg_best_score_selected_on_max_retries(tmp_path):
    """10회 모두 실패 시 최고 점수 SVG가 선택된다."""
    concept_with_scenes = (
        "컨셉 본문\n[IMG_SCENE_1]\n"
        "---SCENE_LIST---\n"
        '[{"id": 1, "title": "씬1", "desc": "설명1"}]'
    )
    ui_evaluator = BestPickUiEvaluator()
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
        html_exporter=None,
        html_validator=None,
        session_manager=SessionManager(session_path=str(tmp_path / "session.json")),
        reference_image_fetcher=StubAgent("[]"),
        concept_ui_generator=StubAgent("<svg/>"),
        concept_diagram_generator=StubAgent(""),
        concept_ui_evaluator=ui_evaluator,
    )
    state = await harness.run(UserInput(genre="액션"))
    assert ui_evaluator.calls == 11  # 10회 재시도 + 1회 초기
    assert len(state.concept_ui_svgs) == 1
    assert state.concept_ui_svgs[0]["svg"] == "<svg/>"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_harness.py::test_harness_svg_quality_evaluator_called_per_scene tests/test_harness.py::test_harness_svg_best_score_selected_on_max_retries -v
```

Expected: FAIL (concept_ui_evaluator 파라미터 없음 또는 평가 로직 없음)

- [ ] **Step 3: _generate_scene_svg 메서드 추가**

`harness.py`의 `GameConceptHarness` 클래스 내부에 추가:

```python
    async def _generate_scene_svg(self, scene: dict, user_input, synthesis: str) -> dict:
        MAX_SVG_RETRIES = 10
        best_svg = ""
        best_score = -1
        svg_feedback = ""
        base_prompt = (
            f"[씬 제목: {scene['title']}]\n[씬 설명: {scene['desc']}]\n\n"
            f"[장르: {user_input.genre}]\n[게임 컨셉 요약]\n{synthesis[:500]}"
        )
        for attempt in range(MAX_SVG_RETRIES + 1):
            prompt = base_prompt
            if svg_feedback:
                prompt += f"\n\n[이전 시도 피드백 - 반드시 반영하세요]\n{svg_feedback}"
            svg_result = await self.concept_ui_generator.run(prompt)
            svg_content = svg_result.content if svg_result.content else ""
            if self.concept_ui_evaluator:
                eval_result = await self.concept_ui_evaluator.evaluate(scene, svg_content)
                if eval_result.score > best_score:
                    best_score = eval_result.score
                    best_svg = svg_content
                if eval_result.passed:
                    break
                svg_feedback = eval_result.feedback or ""
            else:
                best_svg = svg_content
                break
        return {"id": scene["id"], "title": scene["title"], "svg": best_svg}
```

- [ ] **Step 4: Step 5 SVG 생성 코드 교체**

`harness.py`의 Step 5 내부에서 `svg_tasks` 생성 부분을 교체:

기존:
```python
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
```

교체 후:
```python
scene_tasks = []
if self.concept_ui_generator and scenes:
    scene_tasks = [
        self._generate_scene_svg(s, user_input, state.synthesis or "")
        for s in scenes
    ]

all_results = await asyncio.gather(
    ref_task, diagram_task, *scene_tasks, return_exceptions=True
)
state.reference_images = _parse_reference_images(all_results[0])
state.concept_diagram_mermaid = _safe_content(all_results[1])

scene_results = all_results[2:]
state.concept_ui_svgs = [
    r if not isinstance(r, Exception) else {"id": s["id"], "title": s["title"], "svg": ""}
    for s, r in zip(scenes, scene_results)
]
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_harness.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add harness.py tests/test_harness.py
git commit -m "feat: add per-scene SVG quality evaluation loop with best-score fallback"
```

---

### Task 6: main.py 연결

**Files:**
- Modify: `main.py`

- [ ] **Step 1: import 추가**

`main.py` 상단 import 블록에 추가:

```python
from agents.concept_quality_evaluator import ConceptQualityEvaluator
from agents.concept_ui_evaluator import ConceptUiEvaluator
```

- [ ] **Step 2: build_harness에 새 에이전트 주입**

`main.py`의 `build_harness()` 함수:

```python
def build_harness(session_manager: SessionManager) -> GameConceptHarness:
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
        html_exporter=HtmlExporter(),
        html_validator=HtmlValidator(),
        session_manager=session_manager,
        reference_image_fetcher=ReferenceImageFetcher(model=models["image"]),
        concept_ui_generator=ConceptUiGenerator(model=models["image"]),
        concept_diagram_generator=ConceptDiagramGenerator(model=models["image"]),
        concept_quality_evaluator=ConceptQualityEvaluator(model=models["validator"]),
        concept_ui_evaluator=ConceptUiEvaluator(model=models["validator"]),
    )
```

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/ -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add main.py
git commit -m "feat: wire ConceptQualityEvaluator and ConceptUiEvaluator into build_harness"
```

---

## Self-Review

**Spec coverage:**
- ✅ ConceptQualityEvaluator: 3개 기준(mechanism, fun, market), 100점 만점, 80점 이상 통과
- ✅ ConceptUiEvaluator: SVG 100점 만점, 80점 이상 통과
- ✅ Step 4.5: 최대 5회 재시도, 피드백 누적, 5회 실패 시 Step 2 자동 재실행 (reference 유지)
- ✅ Step 5: 씬별 최대 10회 재시도, 최고 점수 SVG 선택, asyncio.gather 병렬 처리
- ✅ PipelineState: concept_quality_scores, concept_quality_failure_reason 필드
- ✅ SessionManager: 새 필드 직렬화/역직렬화
- ✅ _TOTAL_STEPS: 6 → 7
- ✅ 로그 번호: 이미지 5→6, HTML 6→7

**Placeholder scan:** 없음

**Type consistency:**
- `ConceptQualityResult.scores: dict` ↔ `state.concept_quality_scores: dict | None` ✅
- `UiEvalResult.score: int` ↔ `best_score: int` ✅
- `_generate_scene_svg` 반환 `dict` ↔ `state.concept_ui_svgs: list[dict]` ✅
