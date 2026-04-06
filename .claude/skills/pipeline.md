---
description: 게임 컨셉 파이프라인을 단계별로 실행한다. concept-clarifier가 저장한 user_input.json이 있어야 한다.
---

# pipeline 스킬

게임 컨셉 생성 파이프라인을 단계별로 실행한다. 각 주요 단계 후 사용자의 승인을 받는다.

> **핵심 원칙**: 각 단계는 Agent 툴로 서브에이전트를 dispatch해 실행한다. 상태는 output/session.json에 저장한다. 승인 게이트에서 사용자가 n을 입력하면 멈추고 pipeline-resume 스킬로 재개할 수 있다.

> **토큰 추적 원칙**: Agent 툴 호출 후, 보낸 프롬프트 글자 수 + 받은 응답 글자 수를 합산해 2.5로 나눈 값(정수)을 해당 단계 토큰 추정치로 기록한다. 한 단계에서 여러 번 dispatch한 경우(검증 루프 포함) 모두 합산한다. session.json의 `token_usage` 필드에 단계별 + 누적 합계를 저장한다.

---

## 로그 작성 원칙

모든 단계에서 아래 형식으로 `output/pipeline.log`에 로그를 기록한다.  
Bash 툴: `echo "$(date +%H:%M:%S) [메시지]" >> output/pipeline.log`

기록 시점:
- 단계 시작 시: `[N/7] {단계명} 중...`
- 검증 실패/재시도 시: `[N/7] {단계명} 검증 실패 -재시도 중... (M/10)`
- 단계 완료 시: `[N/7] {단계명} 완료 (시도: M회)`

Step 7 완료 후, export.py가 출력한 게임 폴더 경로를 확인하고 Bash 툴로 로그 파일을 이동한다:
```bash
mv output/pipeline.log "output/{게임폴더명}/pipeline.log"
```

---

## 시작 전 준비

1. `user_input.json`을 Read 툴로 읽는다. 없으면 오류 메시지 출력 후 종료:
   ```
   user_input.json이 없습니다. concept-clarifier 스킬을 먼저 실행하세요.
   ```

2. `output/session.json`이 있으면 Read 툴로 읽어 `completed_steps` 목록 파악. 없으면 `completed_steps = []`

3. TodoWrite로 진행 목록 생성:
   ```
   TodoWrite([
     { content: "Step 1: 레퍼런스 탐색",         status: completed_steps에 "reference" 있으면 completed 아니면 pending },
     { content: "Step 2+3: 재미/루프 분석",        status: ... },
     { content: "Step 4: 요약 정리",               status: ... },
     { content: "Step 5: 컨셉안 작성",             status: ... },
     { content: "Step 5.5: 컨셉 품질 평가",        status: ... },
     { content: "Step 6: UI 이미지 생성",          status: ... },
     { content: "Step 7: 파일 출력",               status: ... },
   ])
   ```

4. `user_input`의 필드를 아래 형식으로 프롬프트 문자열 `user_prompt`를 구성해 둔다 (이후 단계에서 재사용):
   ```
   장르: {genre}
   플랫폼: {platform 또는 미지정}
   타겟 유저: {target_user 또는 미지정}
   그래픽: {dimension 또는 미지정}
   레퍼런스 게임: {reference_games 쉼표 구분 또는 없음}
   플레이 방식: {play_mode 또는 미지정}
   전투/대결 방식: {combat_mode 또는 미지정}
   키워드: {keywords 쉼표 구분 또는 없음}
   코어 루프: {core_loop 또는 미지정}
   핵심 요소: {key_elements 쉼표 구분 또는 없음}
   필수 인게임 요소: {must_have_elements 쉼표 구분 또는 없음}
   추가 설명: {free_text 또는 없음}
   ```

---

## Step 1: 레퍼런스 탐색

`completed_steps`에 "reference"가 있으면 이 단계를 건너뛴다.

TodoWrite Step 1을 `in_progress`로 표시.

**1-1. 레퍼런스 탐색 서브에이전트 dispatch:**

`agents/prompts/reference_searcher.md`를 Read 툴로 읽는다.

Agent 툴로 서브에이전트 dispatch:
- 프롬프트: `[reference_searcher.md 전체 내용]\n\n[사용자 요구사항]\n{user_prompt}`
- 허용 툴: WebSearch

결과(쉼표 구분 게임 목록) → `reference_games` 변수 저장

**1-2. 검증 루프 (최대 10회):**

`agents/prompts/reference_validator.md`를 Read 툴로 읽는다.

반복 (최대 10회):
1. Agent 툴로 검증 서브에이전트 dispatch:
   - 프롬프트: `[reference_validator.md 전체 내용]\n\n[사용자 요구사항]\n{user_prompt}\n\n[제안된 레퍼런스 게임 목록]\n{reference_games}`
   - 허용 툴: WebSearch
2. 응답 JSON 파싱. `passed: true`면 루프 종료
3. `passed: false`면 피드백 누적 후 reference_searcher 재실행:
   - 프롬프트에 `[이전 피드백]\n{feedback}` 추가
4. 10회 초과 시: "검증 실패 - 현재 결과로 진행합니다." 출력 후 루프 종료

**1-3. 상태 저장:**

`output/` 폴더가 없으면 Bash 툴로 `mkdir -p output` 실행.

이 단계에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산 (정수).

Write 툴로 `output/session.json` 저장:
```json
{
  "user_input": {user_input JSON},
  "completed_steps": ["reference"],
  "reference_games": ["{game1}", "{game2}", ...],
  "fun_analysis": null,
  "loop_analysis": null,
  "synthesis": null,
  "synthesis_key_points": null,
  "concept": null,
  "concept_quality_scores": null,
  "concept_quality_failure_reason": null,
  "concept_ui_svgs": [],
  "reference_images": [],
  "concept_diagram_mermaid": null,
  "token_usage": {
    "reference": {step_tokens},
    "fun_analysis": 0,
    "loop_analysis": 0,
    "synthesis": 0,
    "concept": 0,
    "concept_quality": 0,
    "images": 0,
    "total": {step_tokens}
  }
}
```

TodoWrite Step 1을 `completed`로 표시.

**[승인 게이트 1]**

```
[Step 1 완료] 레퍼런스 게임 탐색 완료
  {reference_games 목록}
  토큰 사용량: 이 단계 ~{step_tokens}

다음 단계(재미/루프 분석)로 진행할까요? (y/n)
```

`n`이면 종료. `y`이면 Step 2로.

---

## Step 2+3: 재미/루프 분석 (병렬)

`completed_steps`에 "fun_analysis"와 "loop_analysis"가 모두 있으면 건너뛴다.

TodoWrite Step 2+3을 `in_progress`로 표시.

`agents/prompts/fun_analyzer.md`와 `agents/prompts/loop_analyzer.md`를 Read 툴로 읽는다.

**재미 분석과 루프 분석을 별도 Agent 툴 호출로 실행한다 (순서 무관).**

**재미 분석 서브에이전트:**

Agent 툴 dispatch:
- 프롬프트: `[fun_analyzer.md 전체 내용]\n\n다음 레퍼런스 게임의 핵심 재미 요소를 분석해주세요:\n레퍼런스 게임: {reference_games}\n{user_prompt}`
- 허용 툴: WebSearch, WebFetch

결과 → `fun_analysis` 변수 저장

검증 루프 (최대 10회):
`agents/prompts/fun_validator.md` 읽기 후:
1. Agent dispatch (허용 툴: WebSearch, WebFetch):
   - 프롬프트: `[fun_validator.md]\n\n[검증할 핵심 재미 분석]\n{fun_analysis}`
2. passed=true면 종료. false면 피드백으로 fun_analyzer 재실행.
3. 10회 초과 시 현재 결과로 진행.

**루프 분석 서브에이전트:**

Agent 툴 dispatch:
- 프롬프트: `[loop_analyzer.md 전체 내용]\n\n다음 레퍼런스 게임의 핵심 게임 루프를 분석해주세요:\n레퍼런스 게임: {reference_games}\n{user_prompt}`
- 허용 툴: WebSearch, WebFetch

결과 → `loop_analysis` 변수 저장

검증 루프 (최대 10회):
`agents/prompts/loop_validator.md` 읽기 후:
1. Agent dispatch (허용 툴: WebSearch, WebFetch):
   - 프롬프트: `[loop_validator.md]\n\n[검증할 게임 루프 분석]\n{loop_analysis}`
2. passed=true면 종료. false면 피드백으로 loop_analyzer 재실행.
3. 10회 초과 시 현재 결과로 진행.

재미 분석 + 루프 분석 + 각 검증 루프에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산.

**상태 저장:** session.json에 `fun_analysis`, `loop_analysis` 추가. `completed_steps`에 "fun_analysis", "loop_analysis" 추가. `token_usage.fun_analysis`와 `token_usage.loop_analysis`에 각각의 추정 토큰(재미/루프 분석 분량을 절반씩 배분)을 저장. `token_usage.total` 갱신.

TodoWrite Step 2+3을 `completed`로 표시.

**[승인 게이트 2]**

```
[Step 2+3 완료] 재미/루프 분석 완료

[핵심 재미 분석 요약]
{fun_analysis 앞 200자}...

[핵심 게임 루프 분석 요약]
{loop_analysis 앞 200자}...

토큰 사용량: 이 단계 ~{step_tokens} / 누적 ~{token_usage.total}

다음 단계(요약 정리)로 진행할까요? (y/n)
```

`n`이면 종료. `y`이면 Step 4로.

---

## Step 4: 요약 정리

`completed_steps`에 "synthesis"가 있으면 건너뛴다.

TodoWrite Step 4를 `in_progress`로 표시.

`agents/prompts/content_synthesizer.md`를 Read 툴로 읽는다.

**요약 서브에이전트 dispatch (검증 루프 최대 10회):**

반복:
1. Agent dispatch (허용 툴 없음):
   - 프롬프트: `[content_synthesizer.md]\n\n다음 두 분석을 요약 정리해주세요:\n\n[핵심 재미 분석]\n{fun_analysis}\n\n[핵심 게임 루프 분석]\n{loop_analysis}`
2. 결과에서 `[FULL_SUMMARY]` 이후 `[KEY_POINTS]` 이전 텍스트 → `synthesis` 변수
   `[KEY_POINTS]` 이후 텍스트 → `synthesis_key_points` 변수
   (두 구분자가 없으면 전체 → synthesis와 synthesis_key_points 모두)

검증:
`agents/prompts/synthesis_reviewer.md` 읽기 후:
1. Agent dispatch (허용 툴 없음):
   - 프롬프트: `[synthesis_reviewer.md]\n\n[원본 재미 분석]\n{fun_analysis}\n\n[원본 루프 분석]\n{loop_analysis}\n\n[요약본]\n{synthesis}`
2. passed=true면 종료. false면 피드백으로 재실행. 10회 초과 시 현재 결과로 진행.

이 단계에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산.

**상태 저장:** session.json에 `synthesis`, `synthesis_key_points` 추가. `completed_steps`에 "synthesis" 추가. `token_usage.synthesis = step_tokens`, `token_usage.total` 갱신.

TodoWrite Step 4를 `completed`로 표시.

---

## Step 5: 컨셉안 작성

`completed_steps`에 "concept"가 있으면 건너뛴다.

TodoWrite Step 5를 `in_progress`로 표시.

`agents/prompts/concept_writer.md`를 Read 툴로 읽는다.

**컨셉안 작성 서브에이전트 dispatch (검증 루프 최대 10회):**

반복:
1. Agent dispatch (허용 툴 없음):
   - 프롬프트: `[concept_writer.md]\n\n다음 분석을 바탕으로 게임 컨셉안을 작성해주세요:\n\n[사용자 요구사항]\n{user_prompt}\n\n[분석 요약]\n{synthesis}`
   - 피드백 있으면: `\n\n[누적 검증 실패 피드백 - 모두 반영하세요]\n{누적 피드백}`
2. 결과 → `concept` 변수

검증:
`agents/prompts/concept_validator.md` 읽기 후:
1. Agent dispatch (허용 툴 없음):
   - 프롬프트: `[concept_validator.md]\n\n[분석 요약 핵심 항목]\n{synthesis_key_points}\n\n[검증할 컨셉안]\n{concept}`
2. passed=true면 종료. false면 피드백 누적 후 재실행. 10회 초과 시 현재 결과로 진행.

이 단계에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산.

**상태 저장:** session.json에 `concept` 추가. `completed_steps`에 "concept" 추가. `token_usage.concept = step_tokens`, `token_usage.total` 갱신.

TodoWrite Step 5를 `completed`로 표시.

---

## Step 5.5: 컨셉 품질 평가

`completed_steps`에 "concept_quality"가 있으면 건너뛴다.

TodoWrite Step 5.5를 `in_progress`로 표시.

`agents/prompts/concept_quality_evaluator.md`를 Read 툴로 읽는다.

**품질 평가 루프 (최대 5회, 재시작 최대 3회):**

`quality_restart_count` = session.json의 `quality_restart_count` 값 (없으면 0)
`all_quality_feedbacks` = []

반복 (최대 6번 = 0~5):
1. Agent dispatch (허용 툴 없음):
   - 프롬프트: `[concept_quality_evaluator.md]\n\n[게임 컨셉안]\n{concept}`
2. 응답 JSON 파싱:
   - `scores.mechanism`, `scores.fun`, `scores.market` 모두 80 이상이면 passed=true
3. passed=true면:
   - `concept_quality_failure_reason = null`
   - session.json에 `concept_quality_scores` 저장
   - 루프 종료
4. passed=false면:
   - feedback을 `all_quality_feedbacks`에 추가
   - 5회 미만이면: concept_writer로 컨셉안 재작성 (누적 피드백 포함)
     - Agent dispatch:
       ```
       [concept_writer.md]

       다음 품질 평가 피드백을 반영하여 컨셉안을 개선하세요:

       {누적 피드백}

       [사용자 요구사항]
       {user_prompt}

       [현재 컨셉안]
       {concept}
       ```
     - 결과 → `concept` 업데이트
   - 5회 모두 실패 시:
     - `quality_restart_count` 확인
     - `quality_restart_count` >= 3이면: "품질 평가 재시작 한도 초과 - 현재 결과로 진행합니다." 출력 후 루프 종료
     - `quality_restart_count` < 3이면:
       - `concept_quality_failure_reason` 생성 (실패 점수 + 누적 피드백 요약)
       - session.json에서 `completed_steps`에서 "fun_analysis", "loop_analysis", "synthesis", "concept", "concept_quality" 제거
       - session.json에 `quality_restart_count: quality_restart_count + 1` 저장
       - **사용자에게 재시작 보고:**
         ```
         [컨셉 품질 평가 5회 실패]
         mechanism: {score}, fun: {score}, market: {score}
         
         Step 2(재미/루프 분석)부터 재시작합니다.
         재시작 횟수: {quality_restart_count + 1}/3
         ```
       - Step 2로 돌아가 재실행

이 단계에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산.

**상태 저장:** session.json에 `concept_quality_scores` 저장. `completed_steps`에 "concept_quality" 추가. `token_usage.concept_quality = step_tokens`, `token_usage.total` 갱신.

TodoWrite Step 5.5를 `completed`로 표시.

**[승인 게이트 3]**

```
[Step 5.5 완료] 컨셉 품질 평가 통과
  mechanism: {score}, fun: {score}, market: {score}

[컨셉안 요약 - 처음 500자]
{concept 앞 500자}...

토큰 사용량: 이 단계 ~{step_tokens} / 누적 ~{token_usage.total}

다음 단계(UI 이미지 생성)로 진행할까요? (y/n)
```

`n`이면 종료. `y`이면 Step 6으로.

---

## Step 6: 이미지 생성

`completed_steps`에 "images"가 있으면 건너뛴다.

TodoWrite Step 6을 `in_progress`로 표시.

**6-1. 컨셉안에서 씬 목록 추출:**

`concept` 텍스트에서 `---SCENE_LIST---` 이후 JSON 파싱 → `scenes` 목록
`concept`에서 `---SCENE_LIST---` 이후 제거 → `clean_concept`로 저장 (session.json에도 반영)

**6-2. 레퍼런스 이미지 검색 (Agent dispatch):**

`agents/prompts/reference_image_fetcher.md` 읽기 후:
Agent dispatch (허용 툴: WebSearch):
- 프롬프트: `[reference_image_fetcher.md]\n\n[레퍼런스 게임 목록]\n{reference_games 쉼표 구분}`

결과 JSON 파싱 → `reference_images` 변수

**6-3. Mermaid 다이어그램 생성 (Agent dispatch):**

`agents/prompts/concept_diagram_generator.md` 읽기 후:
Agent dispatch (허용 툴 없음):
- 프롬프트: `[concept_diagram_generator.md]\n\n[분석 요약]\n{synthesis}`

결과 → `concept_diagram_mermaid` 변수

**6-4. 씬별 SVG 생성 (씬마다 순차 실행):**

`agents/prompts/concept_ui_generator.md`와 `agents/prompts/concept_ui_evaluator.md` 읽기.

각 씬에 대해 (씬 순서대로):
```
best_svg = ""
best_score = -1
svg_feedback = ""

반복 (최대 11번 = 0~10):
  base_prompt = "[concept_ui_generator.md]\n\n[씬 제목: {scene.title}]\n[씬 설명: {scene.desc}]\n\n[장르: {genre}]\n[게임 컨셉 요약]\n{synthesis 앞 500자}"
  피드백 있으면 base_prompt += "\n\n[이전 시도 피드백 - 반드시 반영하세요]\n{svg_feedback}"

  Agent dispatch (허용 툴 없음):
  - 프롬프트: base_prompt

  SVG 결과 → svg_content

  Agent dispatch (평가, 허용 툴 없음):
  - 프롬프트: "[concept_ui_evaluator.md]\n\n[씬 제목] {scene.title}\n[씬 설명] {scene.desc}\n\n[SVG 이미지]\n{svg_content}"

  평가 JSON 파싱:
  - score > best_score면: best_score = score, best_svg = svg_content
  - score >= 80이면 루프 종료
  - 아니면 svg_feedback = feedback

씬 결과: {"id": scene.id, "title": scene.title, "svg": best_svg}
```

모든 씬 완료 → `concept_ui_svgs` 변수에 저장

6-2~6-4에서 dispatch한 모든 Agent 호출의 (프롬프트 글자 수 + 응답 글자 수) 합 ÷ 2.5 → `step_tokens` 계산 (SVG는 코드 비중이 높으므로 ÷ 3.5 적용).

**상태 저장:** session.json에 `concept` (clean), `reference_images`, `concept_diagram_mermaid`, `concept_ui_svgs` 저장. `completed_steps`에 "images" 추가. `token_usage.images = step_tokens`, `token_usage.total` 갱신.

TodoWrite Step 6을 `completed`로 표시.

**[승인 게이트 4]**

```
[Step 6 완료] 이미지 생성 완료
  씬 수: {scenes 수}개
  레퍼런스 이미지: {reference_images 수}개
  토큰 사용량: 이 단계 ~{step_tokens} / 누적 ~{token_usage.total}

다음 단계(파일 출력)로 진행할까요? (y/n)
```

`n`이면 종료. `y`이면 Step 7로.

---

## Step 7: 파일 출력

TodoWrite Step 7을 `in_progress`로 표시.

Bash 툴로 실행:
```bash
PYTHONUTF8=1 .venv/Scripts/python scripts/export.py --session output/session.json
```

출력된 폴더 경로(`output/{폴더명}`)를 파악하고, pipeline.log를 해당 폴더로 이동:
```bash
mv output/pipeline.log "output/{폴더명}/pipeline.log"
```

출력 결과 메시지:

```
[완료] 컨셉안이 생성됐습니다.

출력 폴더: output/{폴더명}/
  - concept.html    게임 컨셉안 HTML
  - core_loop.md    핵심 게임 루프 요약
  - core_fun.md     핵심 재미 요소 요약
  - session.json    파이프라인 실행 데이터

[토큰 사용량 요약 (추정치)]
  Step 1 레퍼런스 탐색:      ~{token_usage.reference}
  Step 2 재미 분석:           ~{token_usage.fun_analysis}
  Step 3 루프 분석:           ~{token_usage.loop_analysis}
  Step 4 요약 정리:           ~{token_usage.synthesis}
  Step 5 컨셉안 작성:         ~{token_usage.concept}
  Step 5.5 품질 평가:         ~{token_usage.concept_quality}
  Step 6 이미지 생성:         ~{token_usage.images}
  ─────────────────────────────────
  총 합계:                    ~{token_usage.total}
```

TodoWrite Step 7을 `completed`로 표시.
