# 모델 티어링 + 커스텀 스킬 + 진행 표시 설계 스펙

**날짜**: 2026-04-02  
**상태**: 승인됨  
**기반**: 2026-04-02-pipeline-v2-design.md, 2026-04-02-image-integration-design.md

---

## 개요

세 가지 개선을 동시에 적용한다:

1. **모델 티어링 (A안)** — 역할별로 다른 모델을 사용해 토큰 비용 절감
2. **프로젝트 커스텀 스킬 (C안)** — 에이전트 추가/디버깅용 `.claude/skills/` 스킬 2개
3. **파이프라인 진행 표시** — 각 단계 시작·완료·재시도를 터미널에 출력

---

## 1. 모델 티어링

### 배경

현재 모든 에이전트가 `claude-opus-4-6` 단일 모델을 사용한다. Validator 5개는 JSON `{"passed": true/false}` 판단만 하므로 Opus는 낭비다.

### config.yaml 변경

```yaml
output:
  format: html  # word / html / both

models:
  generator: claude-sonnet-4-6           # 분석 에이전트
  validator: claude-haiku-4-5-20251001   # Validator 에이전트 (JSON 판단만)
  writer: claude-opus-4-6                # ConceptWriter (최종 산출물)
  image: claude-sonnet-4-6              # 이미지 생성 에이전트
```

### 역할별 모델 배정

| 에이전트 | 현재 | 변경 후 | 티어 키 | 이유 |
|---------|------|---------|--------|------|
| ReferenceSearcher | Opus | Sonnet | `generator` | 검색+목록 나열 |
| ReferenceValidator | Opus | Haiku | `validator` | JSON pass/fail만 |
| FunAnalyzer | Opus | Sonnet | `generator` | 분석 품질 유지 |
| FunValidator | Opus | Haiku | `validator` | JSON pass/fail만 |
| LoopAnalyzer | Opus | Sonnet | `generator` | 분석 품질 유지 |
| LoopValidator | Opus | Haiku | `validator` | JSON pass/fail만 |
| ContentSynthesizer | Opus | Sonnet | `generator` | 요약 정리 |
| SynthesisReviewer | Opus | Haiku | `validator` | JSON pass/fail만 |
| ConceptWriter | Opus | **Opus 유지** | `writer` | 최종 산출물, 품질 최우선 |
| ConceptValidator | Opus | Haiku | `validator` | JSON pass/fail만 |
| ReferenceImageFetcher | Opus | Sonnet | `image` | 이미지 URL 검색 |
| ConceptUiGenerator | Opus | Sonnet | `image` | SVG 생성 |
| ConceptDiagramGenerator | Opus | Sonnet | `image` | Mermaid 생성 |

### config.py 변경

기존 `load_model()` 유지 (하위 호환). `load_models()` 신규 추가:

```python
def load_models(config_path: str = "config.yaml") -> dict:
    """역할별 모델을 dict로 반환. 키: generator, validator, writer, image"""
    defaults = {
        "generator": None,
        "validator": None,
        "writer": None,
        "image": None,
    }
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        models = cfg.get("models", {})
        return {**defaults, **models}
    except FileNotFoundError:
        return defaults
```

### main.py 변경

`build_harness()`에서 `load_model()` 대신 `load_models()` 사용:

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
        word_exporter=...,
        html_exporter=...,
        word_validator=...,
        html_validator=...,
        output_format=output_format,
        session_manager=session_manager,
        reference_image_fetcher=ReferenceImageFetcher(model=models["image"]) if ... else None,
        concept_ui_generator=ConceptUiGenerator(model=models["image"]) if ... else None,
        concept_diagram_generator=ConceptDiagramGenerator(model=models["image"]) if ... else None,
    )
```

---

## 2. 파이프라인 진행 표시

### 출력 형태

```
[1/6] 레퍼런스 탐색 중...
[1/6] 레퍼런스 탐색 완료 (시도: 1회)

[2/6] 핵심 재미 분석 중...
[2/6] 핵심 게임 루프 분석 중...
[2/6] 핵심 재미 분석 완료
[2/6] 핵심 게임 루프 분석 완료

[3/6] 분석 요약 중...
[3/6] 분석 요약 검증 실패 — 재시도 중... (1/2)
[3/6] 분석 요약 완료 (시도: 2회)

[4/6] 게임 컨셉안 작성 중...
[4/6] 게임 컨셉안 작성 완료 (시도: 1회)

[5/6] 이미지 생성 중...
[5/6] 이미지 생성 완료

[6/6] HTML 출력 생성 중...
[6/6] 완료!
```

### 구현 방식

**`harness.py`에 모듈 레벨 헬퍼 추가:**

```python
def _log(step: int, total: int, message: str) -> None:
    print(f"[{step}/{total}] {message}", flush=True)
```

**`Sprint` 클래스에 `on_retry` 콜백 추가:**

```python
class Sprint:
    def __init__(
        self,
        generator: BaseAgent,
        evaluator: BaseEvaluator,
        max_retries: int = 2,
        on_retry: Callable[[int, int], None] | None = None,
    ):
        self.on_retry = on_retry

    async def run(self, initial_prompt: str) -> SprintResult:
        for attempt in range(self.max_retries + 1):
            result = await self.generator.run(prompt)
            validation = await self.evaluator.validate(result.content)
            if validation.passed:
                return SprintResult(...)
            if attempt < self.max_retries and self.on_retry:
                self.on_retry(attempt + 1, self.max_retries)
            ...
```

**`GameConceptHarness.run()`에서 각 단계 앞뒤에 로그 삽입:**

각 Sprint 생성 시 `on_retry` 람다 주입. `run()` 내부에서 단계별로 `_log()` 호출.

```python
TOTAL_STEPS = 6

# 1단계
_log(1, TOTAL_STEPS, "레퍼런스 탐색 중...")
ref_result = await self.reference_sprint.run(...)
_log(1, TOTAL_STEPS, f"레퍼런스 탐색 완료 (시도: {ref_result.attempts}회)")

# 2단계 (병렬)
_log(2, TOTAL_STEPS, "핵심 재미 분석 중...")
_log(2, TOTAL_STEPS, "핵심 게임 루프 분석 중...")
results = await asyncio.gather(...)
_log(2, TOTAL_STEPS, "핵심 재미 분석 완료")
_log(2, TOTAL_STEPS, "핵심 게임 루프 분석 완료")
...
```

**Sprint `on_retry` 콜백 예시:**

```python
self.reference_sprint = Sprint(
    reference_searcher, reference_validator, max_retries,
    on_retry=lambda attempt, max_r: _log(1, TOTAL_STEPS, f"레퍼런스 탐색 검증 실패 — 재시도 중... ({attempt}/{max_r})")
)
```

### 단계 번호 기준

| 단계 | 번호 |
|------|------|
| 레퍼런스 탐색 | 1 |
| 재미+루프 분석 (병렬) | 2 |
| 분석 요약 | 3 |
| 컨셉안 작성 | 4 |
| 이미지 생성 | 5 |
| 출력 생성 (word/html) | 6 |

---

## 3. 프로젝트 커스텀 스킬

### 파일 위치

```
.claude/
├── settings.json
└── skills/
    ├── new-agent.md
    └── pipeline-debug.md
```

### 스킬 1: `new-agent`

**트리거 예시**: "새 GenreAnalyzer 에이전트 만들어줘", "에이전트 추가해줘"

**체크리스트**:
1. Generator(`BaseAgent`)인지 Evaluator(`BaseEvaluator`)인지 확인
2. 필요한 tools 확인 (`WebSearch` / `WebFetch` / 없음)
3. config.yaml 모델 티어 선택 (generator/validator/writer/image)
4. 파일 생성: `agents/<name>.py` — ROLE, ALLOWED_TOOLS, run()/validate() 포함
5. Evaluator면 JSON 응답 형식(`passed`/`feedback`) 포함 확인
6. `main.py` import 및 `build_harness()` 등록
7. `harness.py` `GameConceptHarness.__init__` 파라미터 추가
8. `config.yaml` 모델 티어 키 사용 확인

### 스킬 2: `pipeline-debug`

**트리거 예시**: "3단계에서 계속 실패해", "Validator가 항상 false 반환해", "토큰이 너무 많이 써"

**체크리스트**:
1. 어느 Sprint/단계인지 확인
2. 해당 에이전트 ROLE 프롬프트 점검 (너무 길거나 모호한지)
3. Validator면: JSON 파싱 실패인지 / 기준 과도한지 구분
4. WebSearch 사용 에이전트면: 실제로 검색이 필요한지 재검토
5. 모델 티어 확인: Validator에 Opus가 쓰이지 않는지
6. 토큰 과다면: 컨텍스트에 전체 텍스트를 통째로 넘기는 부분 탐색
7. `SprintResult.attempts` 로그 확인 → 재시도 빈도 파악

---

## 파일 변경 목록

| 종류 | 파일 | 내용 |
|------|------|------|
| 수정 | `config.yaml` | `models` 섹션 추가 |
| 수정 | `config.py` | `load_models()` 함수 추가 |
| 수정 | `main.py` | `build_harness()`에서 역할별 모델 사용 |
| 수정 | `harness.py` | `_log()` 헬퍼 추가, Sprint에 `on_retry` 콜백 추가, 각 단계 로그 삽입 |
| 신규 | `.claude/skills/new-agent.md` | 에이전트 추가 스킬 |
| 신규 | `.claude/skills/pipeline-debug.md` | 파이프라인 디버깅 스킬 |

---

## 테스트 전략

- `test_config.py`: `load_models()` 정상 로드, 키 누락 시 None fallback
- `test_harness.py`: `on_retry` 콜백 호출 확인 (Sprint mock), 로그 출력 확인 (`capsys`)
- 기존 테스트 전부 통과 유지 (`load_model()` 제거하지 않으므로)

---

## 하위 호환성

- `load_model()` 함수 유지 → 기존 테스트 영향 없음
- `config.yaml`에 `models` 섹션 없으면 모두 `None` → SDK 기본 모델 사용 (기존 동작)
- `Sprint.on_retry` 기본값 `None` → 기존 Sprint 동작 변경 없음
