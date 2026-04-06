# Game Concept Harness v2 — 파이프라인 개선 설계 스펙

**날짜**: 2026-04-02  
**상태**: 승인됨  
**기반**: 2026-04-01-game-concept-harness-design.md (v1)

---

## 개요

v1 파이프라인에 4가지 개선 사항 적용:

1. **레퍼런스 개수 유연화** — a가 3~10개 탐색, a1이 충분성 검증 + 피드백으로 재탐색 유도
2. **컨셉안 검증 Sprint 추가** — concept_writer + concept_validator를 ConceptSprint으로 승격
3. **출력 포맷 설정화** — config.yaml로 word/html/both 선택, 기본값 word
4. **출력 검증 경량화** — word/html exporter는 Sprint 없이 export → validate → 1회 재시도

---

## 변경된 파이프라인 흐름

```
사용자 입력
  ↓
[ReferenceSprint]
  reference_searcher (3~10개 탐색)
  → reference_validator (충분성 + 적합성 검증, 피드백만 전달)
  ↓
[FunAnalysisSprint] ──┐
                       ├── asyncio.gather() 병렬
[LoopAnalysisSprint] ──┘
  ↓
[SynthesisSprint]
  content_synthesizer (전체 요약 + 검증용 핵심 요약 두 버전 생성)
  → synthesis_reviewer
  ↓
[ConceptSprint]  ← v2 신규
  concept_writer
  → concept_validator (synthesis_key_points 기반 검증)
  ↓
출력 (config.yaml output.format에 따라)
  word → word_validator → (실패 시 1회 재시도)   [format: word 또는 both]
  html → html_validator → (실패 시 1회 재시도)   [format: html 또는 both]
```

**Sprint 총 5개:** ReferenceSprint, FunAnalysisSprint, LoopAnalysisSprint, SynthesisSprint, ConceptSprint

---

## 변경 사항 상세

### 1. reference_validator.py 수정

기존: 적합성만 검증  
변경: **충분성 + 적합성** 동시 검증

- 충분성: 레퍼런스 개수가 장르 분석에 충분한가 (최소 3개, 권장 5개)
- 적합성: 각 게임이 사용자 장르/기획 의도에 맞는가
- 실패 시 피드백에 "왜 부족한지 + 어떤 유형의 게임을 더 찾아야 하는지" 포함
- reference_searcher는 피드백을 받아 알아서 더 다양하게 탐색 (개수 직접 지정 안 함)

### 2. content_synthesizer.py 수정

기존: 단일 요약 텍스트 반환  
변경: **두 섹션이 포함된 요약 반환**

반환 형식:
```
[FULL_SUMMARY]
(기존과 동일한 전체 요약)

[KEY_POINTS]
- 핵심 재미 메커니즘: ...
- 주요 게임 루프: ...
- 성공 공통 요인: ...
```

harness가 `[KEY_POINTS]` 섹션을 파싱해서 `state.synthesis_key_points`에 저장.  
`state.synthesis`에는 `[FULL_SUMMARY]` 섹션만 저장.  
파싱 실패 시(섹션 구분자 없음) `synthesis` 전체를 `synthesis_key_points`로 fallback.

### 3. concept_validator.py 신규

- `ConceptValidator(BaseEvaluator)`
- `synthesis_key_points` 속성을 harness로부터 주입받음
- 검증 기준: e가 만든 컨셉안이 d의 핵심 요약 내용을 반영하는가
- JSON 응답: `{"passed": true/false, "feedback": "..."}`

### 4. word_validator.py, html_validator.py 신규

- Sprint 없이 harness가 직접 관리
- `BaseEvaluator` 상속하지 않음 (시그니처가 다름)
- `validate(path: str) -> ValidationResult` 형태 (독립 클래스)
- 검증 항목:
  - **word**: 파일 존재, 핵심 섹션(게임 개요/핵심 컨셉/게임 루프) 포함 여부
  - **html**: 파일 존재, HTML 구조 유효, 핵심 섹션 포함 여부
- 실패 시 exporter 재실행 1회 (state.concept 동일하게 재사용)

### 5. models/pipeline_state.py 수정

추가 필드:
```python
synthesis_key_points: str | None = None  # concept_validator에 전달용
```

### 6. config.yaml 신규

```yaml
output:
  format: word  # word / html / both
```

- `pyyaml` 의존성 추가
- harness 초기화 시 config.yaml 로드
- 파일 없으면 기본값 `word` 사용

### 7. harness.py 수정

- `ConceptSprint` 추가 (concept_writer + concept_validator)
- `synthesis_key_points` 파싱 로직 추가
- `concept_validator.synthesis_key_points` 컨텍스트 주입
- export 로직: config.yaml format에 따라 word/html/both 선택
- export 후 validator 호출, 실패 시 1회 재시도

### 8. session_manager.py 신규

파이프라인 중단/재개를 위한 체크포인트 시스템.

- `output/latest_session.json`에 현재 세션 상태 저장
- 각 Sprint 완료 시마다 자동 저장
- 저장 내용: `PipelineState` 전체 + `completed_steps` 목록 + `user_input`
- `completed_steps` 값: `reference`, `fun_analysis`, `loop_analysis`, `synthesis`, `concept`, `word_export`, `html_export`

**자동 감지 흐름:**
```
main.py 실행
  ↓
latest_session.json 존재?
  → YES: "미완료 세션 발견. 이어서 진행하시겠습니까? (y/n)"
    → y: 세션 로드, 완료된 단계 건너뛰고 이어서 실행
    → n: 새 세션 시작 (이전 파일 덮어씀)
  → NO: 새 세션 시작
```

**완료 시:** `latest_session.json` 삭제 (또는 `completed_session_TIMESTAMP.json`으로 이름 변경)

### 9. main.py 수정

- `pyyaml`로 config.yaml 로드
- harness 생성 시 format 옵션 전달
- `session_manager` 통해 미완료 세션 자동 감지 및 이어하기 처리

---

## 파일 변경 목록

| 종류 | 파일 | 내용 |
|------|------|------|
| 수정 | `agents/reference_validator.py` | 충분성 + 적합성 검증으로 확장 |
| 수정 | `agents/content_synthesizer.py` | FULL_SUMMARY + KEY_POINTS 두 섹션 출력 |
| 신규 | `agents/concept_validator.py` | ConceptSprint의 evaluator |
| 신규 | `agents/word_validator.py` | Word 출력 검증 (Sprint 없이 사용) |
| 신규 | `agents/html_validator.py` | HTML 출력 검증 (Sprint 없이 사용) |
| 수정 | `models/pipeline_state.py` | synthesis_key_points 필드 추가 |
| 신규 | `session_manager.py` | 체크포인트 저장/로드/자동 감지 |
| 신규 | `config.yaml` | output.format 설정 |
| 수정 | `requirements.txt` | pyyaml 추가 |
| 수정 | `harness.py` | ConceptSprint, export 로직, 파싱 로직, 체크포인트 저장 |
| 수정 | `main.py` | config.yaml 로드, 세션 자동 감지 |

---

## 테스트 전략

기존 11개 테스트는 모두 유지. 추가 테스트:

- `test_models.py`: `synthesis_key_points` 필드 초기값 None 확인
- `test_sprint.py`: 기존 그대로 (Sprint 로직 변경 없음)
- `test_harness.py`: ConceptSprint 포함 파이프라인 흐름 확인, KEY_POINTS 파싱 확인
- `test_config.py`: config.yaml 로드, 기본값 fallback 확인
- `test_session_manager.py`: 저장/로드/삭제, 미완료 세션 감지

---

## 하위 호환성

- `synthesis` 필드는 기존과 동일하게 유지 (FULL_SUMMARY 내용)
- `synthesis_key_points`는 신규 필드 (기본값 None)
- config.yaml 없을 시 기본값 word로 동작 → 기존 동작과 동일
