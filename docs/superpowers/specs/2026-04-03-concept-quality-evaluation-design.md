# 컨셉안 품질 평가 + 이미지 품질 평가 구현 설계

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 컨셉안과 인게임 예시 이미지에 대한 품질 평가 루프를 파이프라인에 추가한다.

**Architecture:** 기존 Sprint 패턴을 유지하면서 두 개의 새 평가 단계를 하네스에 추가한다. 컨셉 품질 평가는 Step 4와 Step 5 사이에, 이미지 품질 평가는 Step 5 내부 씬별 루프에 포함된다.

**Tech Stack:** Python, claude_agent_sdk, 기존 BaseEvaluator 패턴

---

## 전체 파이프라인 흐름

```
Step 1: 레퍼런스 탐색
Step 2: 재미/루프 분석 (병렬)
Step 3: 요약 정리
Step 4: 컨셉안 작성
Step 4.5: 컨셉안 품질 평가 루프  ← 신규
Step 5: 이미지 생성 (씬별 품질 평가 루프 포함)  ← 변경
Step 6: HTML 출력
```

---

## 신규 파일

### `agents/concept_quality_evaluator.py`

3개 기준으로 컨셉안을 100점 만점 채점하는 평가 에이전트.

- 모델: Sonnet (config.yaml `validator` 키 사용)
- 입력: 컨셉안 전문
- 출력: JSON `{"scores": {"mechanism": int, "fun": int, "market": int}, "feedback": str | null}`
- 3개 기준:
  - `mechanism`: 메커니즘 구체성 — 핵심 게임 루프, 규칙, 수치가 구체적으로 기술되어 있는가
  - `fun`: 재미 요소 명확성 — 플레이어가 왜 재미있는지 감정적 경험이 명확히 설명되는가
  - `market`: 시장성/수익화 — 타겟 시장과 수익화 방향이 현실적으로 제시되어 있는가
- 모든 점수가 80 이상이면 `passed=True`

### `agents/concept_ui_evaluator.py`

씬 설명 대비 SVG 이미지 품질을 100점 만점 채점하는 평가 에이전트.

- 모델: Sonnet (config.yaml `validator` 키 사용)
- 입력: 씬 제목, 씬 설명, SVG 문자열
- 출력: JSON `{"score": int, "feedback": str | null}`
- 채점 기준:
  - 씬 제목/설명과 시각적 내용 일치도
  - 인게임 화면으로서의 적합성 (UI 요소, 레이아웃 구성)
  - 장르/컨셉 분위기 반영
- 80점 이상이면 `passed=True`

---

## 수정 파일

### `models/pipeline_state.py`

필드 추가:
- `concept_quality_scores: dict | None = None` — 마지막 품질 평가 점수 `{"mechanism": int, "fun": int, "market": int}`
- `concept_quality_failure_reason: str | None = None` — 5회 실패 시 상세 실패 이유

### `harness.py`

#### Step 4.5 추가 — 컨셉 품질 평가 루프

```python
# Step 4.5: 컨셉 품질 평가
MAX_CONCEPT_QUALITY_RETRIES = 5
CONCEPT_QUALITY_THRESHOLD = 80

all_quality_feedbacks = []
for attempt in range(MAX_CONCEPT_QUALITY_RETRIES + 1):
    eval_result = await concept_quality_evaluator.evaluate(state.concept)
    state.concept_quality_scores = eval_result.scores
    if eval_result.passed:
        break
    all_quality_feedbacks.append(eval_result.feedback)
    if attempt >= MAX_CONCEPT_QUALITY_RETRIES:
        # 실패 이유 정리 후 Step 2부터 재실행
        state.concept_quality_failure_reason = _build_failure_reason(eval_result.scores, all_quality_feedbacks)
        done -= {"fun_analysis", "loop_analysis", "synthesis", "concept", "concept_quality"}
        # harness.run() 재귀 호출 (레퍼런스 유지)
        return await self.run(user_input, resume_state=state, completed_steps=list(done))
    # 피드백 누적해서 ConceptWriter 재실행
    feedback_text = "\n\n".join(f"[{i+1}차 피드백]\n{fb}" for i, fb in enumerate(all_quality_feedbacks))
    concept_result = await self.concept_sprint.generator.run(
        f"다음 피드백을 반영하여 컨셉안을 개선하세요:\n\n{feedback_text}\n\n[현재 컨셉안]\n{state.concept}"
    )
    state.concept = concept_result.content
done |= {"concept_quality"}
```

#### Step 5 변경 — 씬별 이미지 품질 평가 루프

기존: 씬마다 SVG 한 번 생성 후 저장  
변경: 씬마다 최대 10회 생성+채점 루프, 최고 점수 SVG 채택

```python
MAX_SVG_RETRIES = 10
SVG_QUALITY_THRESHOLD = 80

for scene in scenes:
    best_svg = ""
    best_score = -1
    svg_feedback = ""
    for attempt in range(MAX_SVG_RETRIES + 1):
        prompt = f"[씬 제목: {scene['title']}]\n[씬 설명: {scene['desc']}]\n..."
        if svg_feedback:
            prompt += f"\n\n[이전 피드백]\n{svg_feedback}"
        svg_result = await concept_ui_generator.run(prompt)
        eval_result = await concept_ui_evaluator.evaluate(scene, svg_result.content)
        if eval_result.score > best_score:
            best_score = eval_result.score
            best_svg = svg_result.content
        if eval_result.passed:
            break
        svg_feedback = eval_result.feedback
    # best_svg를 state.concept_ui_svgs에 저장
```

---

## 인터페이스 정의

### ConceptQualityEvaluator

```python
@dataclass
class ConceptQualityResult:
    passed: bool
    scores: dict  # {"mechanism": int, "fun": int, "market": int}
    feedback: str | None

class ConceptQualityEvaluator:
    async def evaluate(self, concept: str) -> ConceptQualityResult: ...
```

### ConceptUiEvaluator

```python
@dataclass
class UiEvalResult:
    passed: bool
    score: int
    feedback: str | None

class ConceptUiEvaluator:
    async def evaluate(self, scene: dict, svg: str) -> UiEvalResult: ...
```

---

## _TOTAL_STEPS 업데이트

`harness.py`의 `_TOTAL_STEPS = 6` → `_TOTAL_STEPS = 7` (Step 4.5를 독립 단계로 표시)

---

## 테스트

- `tests/test_concept_quality_evaluator.py` — 점수 파싱, passed 판정, 80점 경계 케이스
- `tests/test_concept_ui_evaluator.py` — 점수 파싱, passed 판정
- `tests/test_harness.py` — Step 4.5 루프 동작, 5회 실패 시 Step 2 재실행, SVG 최고 점수 선택

---

## 제약사항

- Step 4.5 재실행 시 `done`에서 `fun_analysis`, `loop_analysis`, `synthesis`, `concept`, `concept_quality`를 제거하고 `reference`는 유지
- 씬별 SVG 평가는 씬마다 독립적이므로 `asyncio.gather`로 병렬 처리 (각 씬의 재시도 루프는 씬 내부에서 순차)
- `concept_quality_scores`는 세션 파일에도 저장 (session_manager.py 수정 필요)
