# 스킬 기반 파이프라인 전환 설계

**Goal:** Python harness를 제거하고 Claude Code 스킬이 파이프라인 전체를 직접 제어하도록 전환한다. 에이전트 프롬프트는 MD 파일로, Python은 HTML/MD/Word 렌더링 스크립트 하나만 남긴다.

**Architecture:** `pipeline` 스킬이 Claude Code의 Agent 툴로 각 단계를 서브에이전트로 dispatch. 단계 사이마다 승인 게이트. 상태는 `output/session.json`을 Read/Write 툴로 직접 관리.

**Tech Stack:** Claude Code Skills, Claude Code Agent 툴, Python (export 스크립트만), Jinja2, python-docx

---

## 전체 파이프라인 흐름

```
Step 1: 레퍼런스 탐색          (서브에이전트, WebSearch)
         ↓ [승인 게이트]
Step 2: 재미 분석              (서브에이전트, WebSearch — 병렬)
Step 3: 루프 분석              (서브에이전트, WebSearch — 병렬)
         ↓ [승인 게이트]
Step 4: 요약 정리              (서브에이전트)
Step 5: 컨셉안 작성            (서브에이전트 + 검증 루프, 최대 10회)
Step 5.5: 컨셉 품질 평가       (서브에이전트 + 재시도 루프, 최대 5회 / 재시작 최대 3회)
         ↓ [승인 게이트]
Step 6: UI 이미지 생성         (서브에이전트, 씬별 품질 루프 최대 10회)
         ↓ [승인 게이트]
Step 7: 파일 출력              (Bash → scripts/export.py)
```

---

## 파일 구조 변경

### 삭제
```
harness.py
main.py
agents/__init__.py
agents/base.py
agents/fun_analyzer.py
agents/fun_validator.py
agents/loop_analyzer.py
agents/loop_validator.py
agents/content_synthesizer.py
agents/synthesis_reviewer.py
agents/concept_writer.py
agents/concept_validator.py
agents/concept_quality_evaluator.py
agents/concept_ui_generator.py
agents/concept_ui_evaluator.py
agents/concept_diagram_generator.py
agents/concept_scene_parser.py
agents/reference_searcher.py
agents/reference_validator.py
agents/reference_image_fetcher.py
agents/html_exporter.py
agents/html_validator.py
agents/word_exporter.py
agents/word_validator.py
models/pipeline_state.py
session_manager.py
```

### 신규 생성
```
.claude/skills/pipeline.md              ← 파이프라인 오케스트레이터 스킬
.claude/skills/pipeline-resume.md       ← 중단된 파이프라인 재개 스킬 (기존 pipeline-debug → 대체)
agents/prompts/reference_searcher.md
agents/prompts/reference_validator.md
agents/prompts/fun_analyzer.md
agents/prompts/fun_validator.md
agents/prompts/loop_analyzer.md
agents/prompts/loop_validator.md
agents/prompts/content_synthesizer.md
agents/prompts/synthesis_reviewer.md
agents/prompts/concept_writer.md
agents/prompts/concept_validator.md
agents/prompts/concept_quality_evaluator.md
agents/prompts/concept_ui_generator.md
agents/prompts/concept_ui_evaluator.md
agents/prompts/concept_diagram_generator.md
scripts/export.py                       ← HTML + MD + Word 렌더링 (남는 Python)
```

### 유지
```
models/user_input.py                    ← from_json / to_prompt 그대로 사용
templates/concept.html.j2               ← Jinja2 템플릿 그대로 사용
```

---

## 출력 폴더 구조

```
output/
├── session.json                        ← 파이프라인 실행 중 임시 상태
└── 20260403_다이스마인크로니클/          ← Step 7 완료 시 생성
    ├── concept.html
    ├── core_loop.md
    ├── core_fun.md
    └── session.json                    ← 최종 상태 이동
```

**폴더 이름**: `YYYYMMDD_<게임타이틀>` — 게임 타이틀은 컨셉안 `# 게임 컨셉안` 바로 다음 `게임 타이틀 (가제):` 항목에서 추출. 없으면 `YYYYMMDD_<장르명>` 사용.

---

## session.json 스키마

```json
{
  "user_input": {
    "genre": "...",
    "platform": "...",
    "target_user": "...",
    "dimension": "...",
    "reference_games": [],
    "play_mode": "...",
    "combat_mode": "...",
    "keywords": [],
    "free_text": "...",
    "core_loop": "...",
    "key_elements": [],
    "must_have_elements": []
  },
  "completed_steps": ["reference", "fun_analysis", "loop_analysis", "synthesis", "concept", "concept_quality", "images"],
  "reference_games": ["게임A", "게임B"],
  "reference_images": [{"game": "...", "url": "...", "store_url": "..."}],
  "fun_analysis": "...",
  "loop_analysis": "...",
  "synthesis": "...",
  "concept": "...",
  "concept_quality_scores": {"mechanism": 85, "fun": 82, "market": 80},
  "concept_quality_failure_reason": null,
  "concept_ui_svgs": [{"id": 1, "title": "...", "svg": "..."}],
  "concept_diagram_mermaid": "..."
}
```

---

## 승인 게이트 동작

각 게이트에서 결과 요약 표시 후 질문:

```
[Step 1 완료] 레퍼런스 게임 5개 탐색됨
  - 하데스, Slay the Spire, Dicey Dungeons, ...

다음 단계(재미/루프 분석)로 진행할까요? (y/n)
```

- `y` → 다음 단계 실행
- `n` → 여기서 멈춤. `pipeline-resume` 스킬로 이어서 재개 가능
- Claude Code auto-approve 켜져 있으면 → 자동으로 y 처리

**예외**: 컨셉 품질 평가가 5회 모두 실패하고 재시작 한도(3회)도 초과하면, auto-approve 상태와 무관하게 사용자에게 보고하고 판단 요청.

---

## 스킬 구조: pipeline.md

```
## 시작
1. user_input.json 읽기
2. session.json 있으면 읽어서 completed_steps 파악 (재개)
3. TodoWrite로 7단계 진행 목록 생성

## Step 1: 레퍼런스 탐색
- agents/prompts/reference_searcher.md 읽기
- Agent 툴로 서브에이전트 dispatch (WebSearch 툴 허용)
- 결과를 reference_validator.md 프롬프트로 검증
- session.json 업데이트
- [승인 게이트]

## Step 2+3: 재미/루프 분석 (병렬)
- 두 서브에이전트를 동시 dispatch (병렬)
- 각각 validator로 검증 (최대 10회 재시도 루프)
- session.json 업데이트
- [승인 게이트]

## Step 4: 요약 정리
- content_synthesizer + synthesis_reviewer 검증 루프
- session.json 업데이트

## Step 5: 컨셉안 작성
- concept_writer + concept_validator 검증 루프 (최대 10회)
- session.json 업데이트

## Step 5.5: 컨셉 품질 평가
- concept_quality_evaluator로 채점 (최대 5회)
- 실패 시 concept_writer 재실행 (피드백 누적)
- 5회 실패 시 Step 2부터 재시작 (최대 3회)
- [승인 게이트]

## Step 6: UI 이미지 생성
- 씬 목록 파싱 (컨셉안에서 ---SCENE_LIST--- 추출)
- 씬별 concept_ui_generator + concept_ui_evaluator 루프 (최대 10회, 최고점 채택)
- 병렬 처리 (각 씬 내부는 순차)
- session.json 업데이트
- [승인 게이트]

## Step 7: 파일 출력
- Bash: python scripts/export.py --session output/session.json
- 출력 폴더 생성, concept.html + core_loop.md + core_fun.md + session.json 저장
```

---

## scripts/export.py 역할

**입력**: `--session output/session.json`

**출력**: `output/YYYYMMDD_<타이틀>/` 폴더에
- `concept.html` — Jinja2 템플릿 렌더링 + SVG 인라인 + 마크다운→HTML + 표 변환
- `core_loop.md` — session의 loop_analysis + concept에서 루프 섹션 추출 + 마크다운 정리
- `core_fun.md` — session의 fun_analysis + concept에서 재미 섹션 추출 + 마크다운 정리
- `session.json` — 임시 파일 이동

**씬 파싱**: 컨셉안에서 `---SCENE_LIST---` 구분자로 씬 JSON을 추출하는 로직은 `scripts/export.py` 내부에 인라인으로 포함. 별도 파일 불필요.

**Word 출력**: 별도 `--word` 플래그로 선택적 생성 (기본 비활성)

---

## concept-clarifier 스킬 변경

Phase F에서 `main.py` 실행 대신 `pipeline` 스킬을 직접 실행:

```
# 기존
mkdir -p output && PYTHONUTF8=1 .venv/Scripts/python main.py --from-file user_input.json ...

# 변경
pipeline 스킬 실행 (user_input.json을 읽어서 시작)
```

---

## 마이그레이션 순서

1. `agents/prompts/*.md` 생성 (기존 ROLE 문자열 이전)
2. `scripts/export.py` 작성 (html_exporter + word_exporter 통합)
3. `pipeline.md` 스킬 작성
4. `pipeline-resume.md` 스킬 작성
5. 기존 Python 파일 삭제
6. `concept-clarifier.md` Phase F 수정
7. tests/ 정리 (Python 에이전트 테스트 삭제)
