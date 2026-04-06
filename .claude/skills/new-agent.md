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
