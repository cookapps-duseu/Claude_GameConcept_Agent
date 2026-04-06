# Game Concept Harness — 설계 스펙

**날짜**: 2026-04-01  
**상태**: 승인됨

---

## 개요

사용자가 장르/기획 의도를 입력하면 레퍼런스 게임 분석을 거쳐 게임 컨셉안(Word + HTML)을 자동 생성하는 멀티에이전트 하네스.

Claude Agent SDK의 `query()` + `asyncio` 기반으로 구현. Generator-Evaluator Sprint 패턴(Anthropic Harness Design 블로그 참조) 적용.

---

## 아키텍처

### 파이프라인 흐름

```
사용자 입력 (UserInput)
    ↓
[ReferenceSprint]
  reference_searcher → reference_validator
    ↓
[FunAnalysisSprint] ──┐
  fun_analyzer         ├── asyncio.gather() 병렬
[LoopAnalysisSprint] ──┘
  loop_analyzer
    ↓
[SynthesisSprint]
  content_synthesizer → synthesis_reviewer
    ↓
[concept_writer]
    ↓
[word_exporter] ──┐
                   ├── asyncio.gather() 병렬
[html_exporter] ──┘
```

### 프로젝트 구조

```
Claude_GameConcept_Agent/
├── .env
├── requirements.txt
├── main.py
├── harness.py                  # GameConceptHarness, Sprint
├── agents/
│   ├── __init__.py
│   ├── reference_searcher.py
│   ├── reference_validator.py
│   ├── fun_analyzer.py
│   ├── fun_validator.py
│   ├── loop_analyzer.py
│   ├── loop_validator.py
│   ├── content_synthesizer.py
│   ├── synthesis_reviewer.py
│   ├── concept_writer.py
│   ├── word_exporter.py
│   └── html_exporter.py
├── models/
│   ├── __init__.py
│   ├── user_input.py
│   └── pipeline_state.py
└── output/
```

---

## 핵심 클래스

### Sprint (harness.py)

재시도 로직과 피드백 루프를 캡슐화.

- 최대 2회 재시도 (총 3회 실행 기회)
- 실패 시 evaluator의 피드백 텍스트를 generator에 전달
- 2회 초과 시 `AskUserQuestion`으로 사용자에게 위임 (진행 / 재시도 / 중단)

```python
class Sprint:
    def __init__(self, generator, evaluator, max_retries=2): ...
    async def run(self, input_data, state) -> SprintResult: ...
```

### GameConceptHarness (harness.py)

파이프라인 오케스트레이터.

```python
class GameConceptHarness:
    async def run(self, user_input: UserInput) -> PipelineState: ...
    async def _sprint_reference(self, state): ...
    async def _sprint_analysis(self, state): ...   # b+c 병렬
    async def _sprint_synthesis(self, state): ...
    async def _run_outputs(self, state): ...        # e1+e2 병렬
```

---

## 데이터 모델

### UserInput (models/user_input.py)

| 필드 | 타입 | 설명 |
|------|------|------|
| `genre` | str | 필수. 예: "로그라이크 RPG" |
| `platform` | str \| None | 예: "모바일" |
| `target_user` | str \| None | 예: "캐주얼 게이머" |
| `keywords` | list[str] | 예: ["짧은 플레이", "성장"] |
| `free_text` | str \| None | 자유 형식 보충 설명 |

### PipelineState (models/pipeline_state.py)

에이전트 간 공유 상태. 각 Sprint 결과를 누적.

| 필드 | 타입 | 담당 에이전트 |
|------|------|--------------|
| `user_input` | UserInput | - |
| `reference_games` | list[str] | ReferenceSprint |
| `fun_analysis` | str | FunAnalysisSprint |
| `loop_analysis` | str | LoopAnalysisSprint |
| `synthesis` | str | SynthesisSprint |
| `concept` | str | concept_writer |
| `output_word_path` | str \| None | word_exporter |
| `output_html_path` | str \| None | html_exporter |

---

## 에이전트 역할

| 에이전트 | 역할 | 주요 도구 |
|---------|------|----------|
| `reference_searcher` | 장르/키워드 기반 레퍼런스 게임 탐색 | WebSearch |
| `reference_validator` | 레퍼런스가 사용자 의도에 부합하는지 검증 | WebSearch |
| `fun_analyzer` | 레퍼런스 게임의 핵심 재미 요소 분석 | WebSearch, WebFetch |
| `fun_validator` | 실사용자 리뷰/댓글/블로그로 재미 요소 검증 | WebSearch, WebFetch |
| `loop_analyzer` | 핵심 게임 루프 분석 | WebSearch, WebFetch |
| `loop_validator` | 게임 루프가 실제 게임과 일치하는지 검증 | WebSearch, WebFetch |
| `content_synthesizer` | fun_analysis + loop_analysis 요약 정리 | - |
| `synthesis_reviewer` | 요약본 품질 리뷰, 수정 요청 | - |
| `concept_writer` | 최종 게임 컨셉안 작성 | - |
| `word_exporter` | 컨셉안을 Word(.docx)로 출력 | Bash (python-docx) |
| `html_exporter` | 컨셉안을 HTML로 출력 | Bash (jinja2) |

---

## 기술 스택

```
claude-agent-sdk    # 에이전트 실행
anthropic           # API 클라이언트
python-dotenv       # 환경 변수
anyio               # 비동기
python-docx         # Word 파일 생성
jinja2              # HTML 템플릿
```

---

## 재시도 / 피드백 정책

- `reference_validator` 실패 → 실패 이유 → `reference_searcher` 재탐색
- `fun_validator` 실패 → 실패 이유 → `fun_analyzer` 재분석
- `loop_validator` 실패 → 실패 이유 → `loop_analyzer` 재분석
- `synthesis_reviewer` 실패 → 수정 요청 → `content_synthesizer` 재작성
- 2회 초과 시 사용자에게 질문: "진행 / 재시도 / 중단"

---

## 출력물

- `output/concept_<timestamp>.docx` — Word 컨셉안
- `output/concept_<timestamp>.html` — HTML 컨셉안
