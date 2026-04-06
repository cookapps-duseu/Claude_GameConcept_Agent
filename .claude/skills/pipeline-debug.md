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
