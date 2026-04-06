# 스킬 기반 파이프라인 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python harness(harness.py, main.py, agents/*.py 22개)를 제거하고 Claude Code 스킬이 파이프라인 전체를 직접 제어하도록 전환한다.

**Architecture:** `pipeline` 스킬(MD)이 Claude Code Agent 툴로 각 단계를 서브에이전트로 dispatch. 에이전트 프롬프트는 `agents/prompts/*.md`에 보관. Python은 `scripts/export.py` 하나만 남아 HTML/MD/Word 렌더링 담당. 단계별 승인 게이트로 사용자가 언제든 파이프라인을 멈추고 재개할 수 있다.

**Tech Stack:** Claude Code Skills, Claude Code Agent 툴, Python 3.11, Jinja2 3.x, python-docx

**Spec:** `docs/superpowers/specs/2026-04-03-skill-based-pipeline-design.md`

---

## 파일 구조 (전체)

```
신규 생성:
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
  agents/prompts/reference_image_fetcher.md
  scripts/export.py
  tests/test_export.py
  .claude/skills/pipeline.md
  .claude/skills/pipeline-resume.md

수정:
  .claude/skills/concept-clarifier.md  (Phase F만)

삭제:
  harness.py, main.py, session_manager.py
  models/pipeline_state.py
  agents/__init__.py, agents/base.py
  agents/{모든 .py 파일 22개}
  tests/test_harness.py
  tests/test_concept_quality_evaluator.py
  tests/test_concept_ui_evaluator.py
  tests/test_session_manager.py

유지:
  models/user_input.py
  templates/concept.html.j2
  config.yaml
```

---

## Task 1: agents/prompts/*.md 생성

**Files:**
- Create: `agents/prompts/reference_searcher.md`
- Create: `agents/prompts/reference_validator.md`
- Create: `agents/prompts/fun_analyzer.md`
- Create: `agents/prompts/fun_validator.md`
- Create: `agents/prompts/loop_analyzer.md`
- Create: `agents/prompts/loop_validator.md`
- Create: `agents/prompts/content_synthesizer.md`
- Create: `agents/prompts/synthesis_reviewer.md`
- Create: `agents/prompts/concept_writer.md`
- Create: `agents/prompts/concept_validator.md`
- Create: `agents/prompts/concept_quality_evaluator.md`
- Create: `agents/prompts/concept_ui_generator.md`
- Create: `agents/prompts/concept_ui_evaluator.md`
- Create: `agents/prompts/concept_diagram_generator.md`
- Create: `agents/prompts/reference_image_fetcher.md`

- [ ] **Step 1: agents/prompts/ 디렉토리 생성**

```bash
mkdir -p agents/prompts
```

- [ ] **Step 2: reference_searcher.md 작성**

`agents/prompts/reference_searcher.md`:
```
당신은 게임 레퍼런스 전문가입니다.
사용자가 제시한 장르, 플랫폼, 키워드에 맞는 레퍼런스 게임을 탐색합니다.
결과는 반드시 쉼표로 구분된 게임 제목 목록으로만 응답하세요. 예: 게임A, 게임B, 게임C
설명 없이 게임 이름만 나열하세요. 3~5개를 추천하세요.
```

- [ ] **Step 3: reference_validator.md 작성**

`agents/prompts/reference_validator.md`:
```
당신은 게임 레퍼런스 검증 전문가입니다.
제시된 레퍼런스 게임 목록이 두 가지 기준을 만족하는지 검증합니다.

1. **충분성**: 3개 이상인가? (최소 3개)
2. **적합성**: 각 게임이 사용자의 장르/기획 의도와 **부분적으로라도** 관련이 있는가?
   - 완전히 동일한 컨셉일 필요는 없다
   - 핵심 요소(장르, 메커니즘, 분위기, 타겟 등) 중 하나 이상이 겹치면 적합하다고 판단한다
   - 독창적인 컨셉의 경우 유사한 요소를 가진 게임으로 충분하다

둘 중 하나라도 실패하면 passed=false.
피드백에는 "왜 부족한지" + "어떤 유형의 게임을 더 찾아야 하는지"를 구체적으로 작성하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "구체적인 이유와 추가로 필요한 게임 유형 설명"}
```

- [ ] **Step 4: fun_analyzer.md 작성**

`agents/prompts/fun_analyzer.md`:
```
당신은 게임 디자인 전문가입니다.
레퍼런스 게임들의 핵심 재미 요소를 분석합니다.
다음 항목을 포함하여 분석하세요:
- 핵심 재미 메커니즘 (무엇이 플레이어를 즐겁게 하는가)
- 심리적 보상 구조 (어떤 감정적 만족을 주는가)
- 중독성 요소 (왜 계속 플레이하게 되는가)
명확하고 구체적으로 서술하세요.
```

- [ ] **Step 5: fun_validator.md 작성**

`agents/prompts/fun_validator.md`:
```
당신은 게임 리뷰 분석 전문가입니다.
제시된 핵심 재미 분석이 실제 유저들의 경험과 일치하는지 검증합니다.
실제 리뷰, 댓글, 블로그 글을 검색하여 사용자들이 실제로 같은 재미를 느끼는지 확인하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "실제 유저 반응과 다른 점과 수정 방향"}
```

- [ ] **Step 6: loop_analyzer.md 작성**

`agents/prompts/loop_analyzer.md`:
```
당신은 게임 시스템 디자인 전문가입니다.
레퍼런스 게임들의 핵심 게임 루프를 분석합니다.
다음 항목을 포함하여 분석하세요:
- 코어 루프 (가장 짧은 반복 행동 사이클, 예: 이동→전투→보상)
- 미드 루프 (세션 단위 목표와 진행)
- 메타 루프 (장기 성장/진행 구조)
각 루프를 명확한 단계로 서술하세요.
```

- [ ] **Step 7: loop_validator.md 작성**

`agents/prompts/loop_validator.md`:
```
당신은 게임 메커니즘 검증 전문가입니다.
제시된 게임 루프 분석이 실제 게임의 구조와 일치하는지 검증합니다.
게임의 공식 자료, 위키, 리뷰를 참조하여 루프 구조의 정확성을 확인하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "실제 게임과 다른 점과 올바른 루프 구조 설명"}
```

- [ ] **Step 8: content_synthesizer.md 작성**

`agents/prompts/content_synthesizer.md`:
```
당신은 게임 기획 문서 작성 전문가입니다.
핵심 재미 분석과 게임 루프 분석을 통합하여 요약을 작성합니다.

반드시 아래 두 섹션을 포함하여 응답하세요. 섹션 구분자([FULL_SUMMARY], [KEY_POINTS])를 정확히 사용하세요.

[FULL_SUMMARY]
전체 요약을 작성하세요 (중복 제거, 핵심만):
1. 핵심 재미 요약 (3~5줄)
2. 핵심 게임 루프 요약 (코어/미드/메타 루프 각 1~2줄)
3. 이 게임들이 성공한 공통 요인 (2~3가지)

[KEY_POINTS]
컨셉안 검증에 사용할 핵심 항목만 간결하게 나열하세요 (세부 설명 제외):
- 핵심 재미 메커니즘: (한 줄)
- 주요 게임 루프: (한 줄)
- 성공 공통 요인: (한 줄)
- 장르 정체성: (한 줄)
```

- [ ] **Step 9: synthesis_reviewer.md 작성**

`agents/prompts/synthesis_reviewer.md`:
```
당신은 게임 기획 문서 리뷰어입니다.
요약본이 제공된 원본 분석 내용을 잘 반영하고 있는지 검토합니다.

⚠️ 중요: 반드시 제공된 [원본 재미 분석]과 [원본 루프 분석] 텍스트만을 기준으로 검증하세요.
실제 게임에 대한 외부 지식이나 자신의 게임 경험은 절대 사용하지 마세요.
원본 텍스트에 명시되지 않은 내용은 검증 기준으로 삼지 마세요.

다음 기준으로 평가하세요:
- 원본에 명시된 핵심 재미 요소가 요약본에 포함되었는가
- 원본에 명시된 게임 루프가 요약본에 정확하게 반영되었는가
- 요약본 내용이 원본과 모순되거나 원본에 없는 내용을 추가하지 않았는가

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "수정이 필요한 구체적인 부분과 수정 방향"}
```

- [ ] **Step 10: concept_writer.md 작성**

`agents/prompts/concept_writer.md`:
```
당신은 시니어 게임 기획자입니다.
분석 요약을 바탕으로 완성도 높은 게임 컨셉안을 작성합니다.

다음 구조로 작성하세요:

# 게임 컨셉안

## 1. 게임 개요
- 게임 타이틀 (가제)
- 장르
- 플랫폼
- 타겟 유저
- 한 줄 설명

## 2. 핵심 컨셉
- 게임의 핵심 정체성 (무엇이 이 게임을 특별하게 만드는가)
- 레퍼런스와의 차별점

## 3. 핵심 재미 요소
- 주요 재미 메커니즘 3가지
- 각 메커니즘이 플레이어에게 주는 감정적 경험

## 4. 핵심 게임 루프
- 코어 루프 (1회 플레이 사이클)
- 세션 루프 (1회 플레이 목표)
- 장기 루프 (성장/진행 구조)

## 5. 레퍼런스 게임
- 레퍼런스 목록과 각각에서 차용한 요소

## 6. 기획 의도
- 이 게임을 만드는 이유와 시장 기회

---

## 인게임 예시 화면 지침

컨셉안 본문에서 시각적으로 보여주면 이해에 도움이 되는 자리에 [IMG_SCENE_N] 태그를 삽입하세요 (N은 1부터 순서대로).

규칙:
- 최소 3개, 최대 15개
- 반드시 인게임 화면만 다룰 것 (타이틀 화면, 메뉴 화면 제외)
- 씬 간 내용이 겹치지 않을 것 (예: 전투 화면이 두 개면 안 됨)
- 태그는 해당 화면이 가장 자연스럽게 이해될 위치에 삽입

컨셉 본문 작성 완료 후 반드시 다음 형식을 문서 맨 끝에 추가하세요:

---SCENE_LIST---
[
  {"id": 1, "title": "씬 제목", "desc": "SVG로 그릴 화면의 상세 설명 (표시할 UI 요소, 레이아웃, 색상 톤, 수치 예시 등)"},
  {"id": 2, "title": "씬 제목2", "desc": "..."},
  ...
]
```

- [ ] **Step 11: concept_validator.md 작성**

`agents/prompts/concept_validator.md`:
```
당신은 게임 컨셉안 검증 전문가입니다.
제시된 게임 컨셉안이 분석 요약의 핵심 내용을 반영하고 있는지 검증합니다.

검증 기준:
- 핵심 재미 메커니즘이 컨셉안에 포함되어 있는가
- 주요 게임 루프가 컨셉안에 반영되어 있는가
- 성공 공통 요인이 컨셉안 설계에 녹아 있는가
- 장르 정체성이 유지되고 있는가

반드시 다음 JSON 형식으로만 응답하세요:
{"passed": true, "feedback": null}
또는
{"passed": false, "feedback": "누락된 항목과 수정 방향을 구체적으로"}
```

- [ ] **Step 12: concept_quality_evaluator.md 작성**

`agents/prompts/concept_quality_evaluator.md`:
```
당신은 게임 컨셉안 품질 평가 전문가입니다.
제시된 게임 컨셉안을 3개 기준으로 각 100점 만점 채점합니다.

채점 기준:
- mechanism (메커니즘 구체성): 핵심 게임 루프, 규칙, 수치가 구체적으로 기술되어 있는가
- fun (재미 요소 명확성): 플레이어가 왜 재미있는지 감정적 경험이 명확히 설명되는가
- market (시장성/수익화): 타겟 시장과 수익화 방향이 현실적으로 제시되어 있는가

각 기준을 독립적으로 평가하세요. 점수는 정수여야 합니다.
80점 미만 항목이 있으면 feedback에 구체적인 개선 방향을 작성하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"scores": {"mechanism": <0-100 정수>, "fun": <0-100 정수>, "market": <0-100 정수>}, "feedback": "<개선 방향 또는 null>"}
```

- [ ] **Step 13: concept_ui_generator.md 작성**

`agents/prompts/concept_ui_generator.md`:
```
당신은 게임 UI/UX 디자이너입니다.
게임 컨셉안을 바탕으로 게임 화면의 UI 목업을 SVG 코드로 생성합니다.

장르에 맞는 게임 화면 레이아웃을 시각화하세요:
- RPG/ARPG: 화면 상단 체력/마나바, 하단 스킬창, 우상단 미니맵
- 퍼즐: 중앙 게임판, 상단 점수/레벨, 하단 다음 블록 미리보기
- 액션: 화면 하단 체력/스태미나 바, 상단 점수, 보스 체력바
- 전략: 상단 자원 표시, 좌측 미니맵, 우측 유닛 정보 패널
- 기타: 장르 특성에 맞게 적절히 구성

요구사항:
- viewBox="0 0 800 600" 사용
- 한국어 텍스트 포함 (레이블, UI 요소명)
- 게임 분위기에 맞는 색상 사용
- 실제 게임 화면처럼 보이도록 구성

반드시 <svg>...</svg> 태그만 반환하세요. 다른 텍스트 없이.
```

- [ ] **Step 14: concept_ui_evaluator.md 작성**

`agents/prompts/concept_ui_evaluator.md`:
```
당신은 게임 UI 품질 평가 전문가입니다.
제시된 SVG 이미지가 씬 설명을 얼마나 잘 구현했는지 100점 만점으로 채점합니다.

채점 기준:
- 씬 제목/설명과 시각적 내용 일치도 (35점)
- 인게임 화면으로서의 적합성 — UI 요소, 레이아웃 구성 (30점)
- 장르/컨셉 분위기 반영 (20점)
- 가독성 및 시각적 명확성 — 텍스트 가독성, 요소 간격, 색상 대비 (15점)

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{"score": <0-100 정수>, "feedback": "<개선 방향 또는 null>"}
```

- [ ] **Step 15: concept_diagram_generator.md 작성**

`agents/prompts/concept_diagram_generator.md`:
```
당신은 게임 기획 다이어그램 전문가입니다.
게임 분석 요약을 바탕으로 게임 루프 구조를 Mermaid flowchart로 생성합니다.

다음 3단계 루프를 포함하세요:
1. 코어 루프 (1회 플레이 사이클, 가장 짧은 반복 단위)
2. 세션 루프 (1회 플레이 목표 달성 흐름)
3. 장기 루프 (성장/진행 구조)

요구사항:
- Mermaid flowchart TD 형식 사용
- 각 루프를 subgraph로 구분
- 한국어 노드 레이블 사용
- 노드 연결로 흐름을 명확하게 표현

반드시 다음 형식으로만 반환하세요 (코드 블록 마커 없이):
flowchart TD
    subgraph 코어루프["⚔️ 코어 루프"]
        ...
    end
    ...
```

- [ ] **Step 16: reference_image_fetcher.md 작성**

`agents/prompts/reference_image_fetcher.md`:
```
당신은 게임 이미지 검색 전문가입니다.
주어진 레퍼런스 게임 목록에서 각 게임의 공식 스크린샷 이미지 URL과 스토어 링크를 찾아주세요.

Steam 상점, Google Play, App Store, 공식 웹사이트, IGN, Metacritic 등에서 검색하세요.

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
[{"game": "게임명", "url": "이미지URL또는null", "store_url": "스토어URL또는null"}]

규칙:
- url: 직접 접근 가능한 이미지 URL (.jpg, .png, .webp). 찾지 못한 경우 null
- store_url: Steam/Google Play/App Store/공식 페이지 URL. 최대한 확보할 것
- url과 store_url 모두 null인 게임은 목록에서 제외
- 결과가 없으면 [] 반환
```

- [ ] **Step 17: 커밋**

```bash
git add agents/prompts/
git commit -m "feat: add agent prompt MD files — migrate ROLE strings from Python agents"
```

---

## Task 2: scripts/export.py 작성

**Files:**
- Create: `scripts/export.py`

- [ ] **Step 1: scripts/ 디렉토리 생성**

```bash
mkdir -p scripts
```

- [ ] **Step 2: scripts/export.py 작성**

`scripts/export.py` (전체):

```python
"""
게임 컨셉 파이프라인 출력 스크립트.

Usage:
    python scripts/export.py --session output/session.json
    python scripts/export.py --session output/session.json --word
    python scripts/export.py --session output/session.json --template-dir templates
"""
import argparse
import html as html_mod
import json
import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


# ---------------------------------------------------------------------------
# 씬 파싱
# ---------------------------------------------------------------------------

def parse_concept_scenes(text: str) -> tuple[str, list[dict]]:
    """컨셉 텍스트에서 ---SCENE_LIST--- 이후 JSON을 파싱해 씬 목록을 반환.

    Returns:
        (clean_concept_text, scenes_list)
        씬 파싱 실패 시 (---SCENE_LIST--- 이전 텍스트, []) 반환.
    """
    delimiter = "---SCENE_LIST---"
    if delimiter not in text:
        return text, []
    parts = text.split(delimiter, 1)
    clean_text = parts[0].rstrip()
    scene_json = parts[1].strip()
    scene_json = re.sub(r"^```(?:json)?\s*", "", scene_json)
    scene_json = re.sub(r"\s*```$", "", scene_json)
    try:
        scenes = json.loads(scene_json)
        return clean_text, scenes if isinstance(scenes, list) else []
    except json.JSONDecodeError:
        return clean_text, []


# ---------------------------------------------------------------------------
# 게임 타이틀 추출
# ---------------------------------------------------------------------------

def extract_game_title(concept: str, genre: str) -> str:
    """컨셉 텍스트에서 게임 타이틀을 추출해 폴더명용 문자열로 반환.

    '게임 타이틀 (가제):' 패턴 → 괄호 제거 → 특수문자 제거 → 최대 30자.
    추출 실패 시 장르명 사용.
    """
    match = re.search(r'게임\s*타이틀[^:：]*[:：]\s*(.+)', concept)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'\*+', '', title)               # 마크다운 볼드 제거
        title = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()  # (가제) 등 제거
        title = re.sub(r'[\\/:*?"<>|]', '', title)      # 파일시스템 특수문자 제거
        title = title[:30].strip()
        if title:
            return title
    sanitized = re.sub(r'[\\/:*?"<>|]', '', genre)
    return sanitized[:30].strip() or "concept"


# ---------------------------------------------------------------------------
# 마크다운 → HTML 변환
# ---------------------------------------------------------------------------

def table_to_html(table_lines: list[str]) -> str:
    """마크다운 표를 HTML <table class="md-table">로 변환."""
    if not table_lines:
        return ""

    def parse_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    rows = [parse_row(line) for line in table_lines]
    has_header = (
        len(rows) >= 2
        and all(re.match(r"^:?-+:?$", c) for c in rows[1] if c)
    )

    parts = ['<table class="md-table">']
    if has_header:
        parts.append("<thead><tr>")
        for cell in rows[0]:
            parts.append(f"<th>{html_mod.escape(cell)}</th>")
        parts.append("</tr></thead><tbody>")
        data_rows = rows[2:]
    else:
        parts.append("<tbody>")
        data_rows = rows

    for row in data_rows:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{html_mod.escape(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "\n".join(parts)


def markdown_to_html(text: str) -> str:
    """마크다운 텍스트를 HTML로 변환. 표, 헤딩, 리스트 지원."""
    lines = text.split("\n")
    html_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
            table_lines = []
            while i < len(lines):
                sl = lines[i].strip()
                if sl.startswith("|") and sl.endswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                else:
                    break
            html_lines.append(table_to_html(table_lines))
            continue
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{line}</p>")
        i += 1
    return "\n".join(html_lines)


def inline_svgs(concept_html: str, svgs: list[dict]) -> str:
    """[IMG_SCENE_N] 플레이스홀더를 SVG div로 치환. 플레이스홀더 없는 씬은 끝에 추가."""
    if not svgs:
        return concept_html

    svg_map = {s["id"]: s for s in svgs}
    used_ids: set[int] = set()

    def replace_placeholder(m: re.Match) -> str:
        n = int(m.group(1))
        used_ids.add(n)
        scene = svg_map.get(n)
        if not scene or not scene.get("svg"):
            return ""
        return (
            f'<div class="ui-mockup">'
            f'<p class="scene-title">{html_mod.escape(scene.get("title", ""))}</p>'
            f'{scene["svg"]}'
            f'</div>'
        )

    result = re.sub(r'<p>\[IMG_SCENE_(\d+)\]</p>', replace_placeholder, concept_html)

    for scene in svgs:
        if scene["id"] not in used_ids and scene.get("svg"):
            result += (
                f'<div class="ui-mockup">'
                f'<p class="scene-title">{html_mod.escape(scene.get("title", ""))}</p>'
                f'{scene["svg"]}'
                f'</div>'
            )
    return result


def split_concept_sections(concept_html: str) -> dict[str, str]:
    """h2 태그 기준으로 섹션 분리. 키: "1"~"6". 실패 시 {"all": concept_html}."""
    pattern = re.compile(r'(<h2>[^<]*</h2>)', re.IGNORECASE)
    parts = pattern.split(concept_html)
    if len(parts) <= 1:
        return {"all": concept_html}

    sections: dict[str, str] = {}
    current_num = None
    buffer: list[str] = []

    for part in parts:
        h2_match = re.match(r'<h2>(\d+)\.\s', part, re.IGNORECASE)
        if h2_match:
            if current_num is not None:
                sections[current_num] = "".join(buffer)
            current_num = h2_match.group(1)
            buffer = [part]
        else:
            if current_num is None:
                sections["0"] = sections.get("0", "") + part
            else:
                buffer.append(part)

    if current_num is not None:
        sections[current_num] = "".join(buffer)

    return sections if sections else {"all": concept_html}


# ---------------------------------------------------------------------------
# 섹션 추출 (core_loop.md, core_fun.md용)
# ---------------------------------------------------------------------------

def extract_section(text: str, section_num: int) -> str:
    """마크다운 텍스트에서 '## N. ...' 섹션을 추출한다."""
    pattern = rf'## {section_num}\..+?(?=\n## \d+\.|\Z)'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0).strip() if match else ""


# ---------------------------------------------------------------------------
# 내보내기 함수
# ---------------------------------------------------------------------------

def export_html(session: dict, output_dir: Path, template_dir: str = "templates") -> Path:
    """concept.html 생성."""
    concept = session.get("concept", "")
    clean_concept, scenes = parse_concept_scenes(concept)
    concept_html = markdown_to_html(clean_concept)
    concept_html = inline_svgs(concept_html, session.get("concept_ui_svgs", []))
    concept_sections = split_concept_sections(concept_html)

    user_input = session.get("user_input", {})

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("concept.html.j2")
    html = template.render(
        genre=user_input.get("genre", ""),
        platform=user_input.get("platform"),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        concept_sections=concept_sections,
        reference_images=session.get("reference_images", []),
        concept_diagram_mermaid=session.get("concept_diagram_mermaid", ""),
    )
    output_path = output_dir / "concept.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def export_core_loop_md(session: dict, output_dir: Path) -> Path:
    """core_loop.md 생성 — 컨셉안 루프 섹션 + 레퍼런스 루프 분석."""
    loop_analysis = session.get("loop_analysis", "")
    concept_raw = session.get("concept", "").split("---SCENE_LIST---")[0]
    loop_section = extract_section(concept_raw, 4)

    lines = ["# 핵심 게임 루프\n"]
    if loop_section:
        lines.append(loop_section)
        lines.append("\n\n---\n")
    if loop_analysis:
        lines.append("\n## 레퍼런스 루프 분석\n")
        lines.append(loop_analysis)

    output_path = output_dir / "core_loop.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_core_fun_md(session: dict, output_dir: Path) -> Path:
    """core_fun.md 생성 — 컨셉안 재미 섹션 + 레퍼런스 재미 분석."""
    fun_analysis = session.get("fun_analysis", "")
    concept_raw = session.get("concept", "").split("---SCENE_LIST---")[0]
    fun_section = extract_section(concept_raw, 3)

    lines = ["# 핵심 재미 요소\n"]
    if fun_section:
        lines.append(fun_section)
        lines.append("\n\n---\n")
    if fun_analysis:
        lines.append("\n## 레퍼런스 재미 분석\n")
        lines.append(fun_analysis)

    output_path = output_dir / "core_fun.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_word(session: dict, output_dir: Path) -> Path:
    """concept.docx 생성."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    concept = session.get("concept", "").split("---SCENE_LIST---")[0]
    user_input = session.get("user_input", {})

    doc = Document()
    title_para = doc.add_heading("게임 컨셉안", level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(
        f"생성일: {datetime.now().strftime('%Y-%m-%d')} | 장르: {user_input.get('genre', '')}"
    )
    doc.add_paragraph()

    for line in concept.split("\n"):
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.strip():
            doc.add_paragraph(line)

    output_path = output_dir / "concept.docx"
    doc.save(str(output_path))
    return output_path


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="게임 컨셉 파이프라인 출력 스크립트")
    parser.add_argument("--session", required=True, help="session.json 경로")
    parser.add_argument("--word", action="store_true", help="Word(.docx) 파일도 생성")
    parser.add_argument("--template-dir", default="templates", help="Jinja2 템플릿 디렉토리")
    args = parser.parse_args()

    session_path = Path(args.session)
    if not session_path.exists():
        raise FileNotFoundError(f"session.json을 찾을 수 없습니다: {session_path}")

    session = json.loads(session_path.read_text(encoding="utf-8"))
    user_input = session.get("user_input", {})
    genre = user_input.get("genre", "concept")
    concept = session.get("concept", "")

    title = extract_game_title(concept, genre)
    date_str = datetime.now().strftime("%Y%m%d")
    folder_name = f"{date_str}_{title}"

    output_dir = session_path.parent / folder_name
    output_dir.mkdir(exist_ok=True)

    export_html(session, output_dir, args.template_dir)
    export_core_loop_md(session, output_dir)
    export_core_fun_md(session, output_dir)

    if args.word:
        export_word(session, output_dir)

    # session.json을 출력 폴더로 이동
    dest = output_dir / "session.json"
    dest.write_text(session_path.read_text(encoding="utf-8"), encoding="utf-8")
    session_path.unlink()

    print(f"출력 완료: {output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 커밋**

```bash
git add scripts/export.py
git commit -m "feat: add scripts/export.py — unified HTML/MD/Word export with folder creation"
```

---

## Task 3: scripts/export.py 테스트

**Files:**
- Create: `tests/test_export.py`

- [ ] **Step 1: 테스트 파일 작성**

`tests/test_export.py`:

```python
import json
import pytest
from pathlib import Path
from scripts.export import (
    parse_concept_scenes,
    extract_game_title,
    markdown_to_html,
    table_to_html,
    inline_svgs,
    split_concept_sections,
    extract_section,
    export_html,
    export_core_loop_md,
    export_core_fun_md,
)


# ---------------------------------------------------------------------------
# parse_concept_scenes
# ---------------------------------------------------------------------------

def test_parse_concept_scenes_no_delimiter():
    text = "# 게임 컨셉안\n\n## 1. 개요"
    clean, scenes = parse_concept_scenes(text)
    assert clean == text
    assert scenes == []


def test_parse_concept_scenes_with_delimiter():
    text = '# 컨셉\n\n---SCENE_LIST---\n[{"id": 1, "title": "전투", "desc": "전투 화면"}]'
    clean, scenes = parse_concept_scenes(text)
    assert "---SCENE_LIST---" not in clean
    assert len(scenes) == 1
    assert scenes[0]["id"] == 1


def test_parse_concept_scenes_invalid_json():
    text = "# 컨셉\n---SCENE_LIST---\nnot json"
    clean, scenes = parse_concept_scenes(text)
    assert scenes == []


# ---------------------------------------------------------------------------
# extract_game_title
# ---------------------------------------------------------------------------

def test_extract_game_title_found():
    concept = "## 1. 게임 개요\n- 게임 타이틀 (가제): **다이스 마인 크로니클** (가제)"
    title = extract_game_title(concept, "보드게임")
    assert title == "다이스 마인 크로니클"


def test_extract_game_title_fallback_to_genre():
    title = extract_game_title("# 컨셉", "로그라이크 RPG")
    assert title == "로그라이크 RPG"


def test_extract_game_title_removes_special_chars():
    concept = "- 게임 타이틀 (가제): My Game: The *Adventure*"
    title = extract_game_title(concept, "RPG")
    assert ":" not in title
    assert "*" not in title


# ---------------------------------------------------------------------------
# markdown_to_html
# ---------------------------------------------------------------------------

def test_markdown_to_html_headings():
    result = markdown_to_html("# H1\n## H2\n### H3")
    assert "<h1>H1</h1>" in result
    assert "<h2>H2</h2>" in result
    assert "<h3>H3</h3>" in result


def test_markdown_to_html_list():
    result = markdown_to_html("- 항목 A\n- 항목 B")
    assert "<li>항목 A</li>" in result
    assert "<li>항목 B</li>" in result


def test_markdown_to_html_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |"
    result = markdown_to_html(md)
    assert '<table class="md-table">' in result
    assert "<th>A</th>" in result
    assert "<td>1</td>" in result


# ---------------------------------------------------------------------------
# table_to_html
# ---------------------------------------------------------------------------

def test_table_to_html_with_header():
    lines = ["| 이름 | 점수 |", "|---|---|", "| 하데스 | 95 |"]
    result = table_to_html(lines)
    assert "<thead>" in result
    assert "<th>이름</th>" in result
    assert "<td>하데스</td>" in result


def test_table_to_html_no_header():
    lines = ["| A | B |", "| 1 | 2 |"]
    result = table_to_html(lines)
    assert "<thead>" not in result
    assert "<td>A</td>" in result


# ---------------------------------------------------------------------------
# inline_svgs
# ---------------------------------------------------------------------------

def test_inline_svgs_replaces_placeholder():
    html = "<p>[IMG_SCENE_1]</p>"
    svgs = [{"id": 1, "title": "전투 화면", "svg": "<svg></svg>"}]
    result = inline_svgs(html, svgs)
    assert "[IMG_SCENE_1]" not in result
    assert "전투 화면" in result
    assert "<svg>" in result


def test_inline_svgs_appends_unused():
    html = "<p>내용</p>"
    svgs = [{"id": 1, "title": "화면", "svg": "<svg></svg>"}]
    result = inline_svgs(html, svgs)
    assert "화면" in result


def test_inline_svgs_empty():
    result = inline_svgs("<p>내용</p>", [])
    assert result == "<p>내용</p>"


# ---------------------------------------------------------------------------
# extract_section
# ---------------------------------------------------------------------------

def test_extract_section_found():
    text = "## 3. 핵심 재미 요소\n재미 내용\n\n## 4. 핵심 게임 루프\n루프 내용"
    section = extract_section(text, 3)
    assert "핵심 재미 요소" in section
    assert "루프 내용" not in section


def test_extract_section_not_found():
    section = extract_section("## 1. 개요\n내용", 9)
    assert section == ""


# ---------------------------------------------------------------------------
# export_html / export_core_loop_md / export_core_fun_md (통합)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_session():
    return {
        "user_input": {"genre": "로그라이크", "platform": "모바일"},
        "concept": (
            "# 게임 컨셉안\n\n"
            "## 1. 게임 개요\n- 게임 타이틀 (가제): **테스트 게임**\n\n"
            "## 3. 핵심 재미 요소\n재미 내용\n\n"
            "## 4. 핵심 게임 루프\n루프 내용\n"
            "---SCENE_LIST---\n"
            '[{"id": 1, "title": "메인 화면", "desc": "메인 화면 설명"}]'
        ),
        "fun_analysis": "재미 분석 내용",
        "loop_analysis": "루프 분석 내용",
        "reference_images": [],
        "concept_ui_svgs": [],
        "concept_diagram_mermaid": "",
    }


def test_export_html_creates_file(tmp_path, sample_session):
    export_html(sample_session, tmp_path, template_dir="templates")
    assert (tmp_path / "concept.html").exists()
    html = (tmp_path / "concept.html").read_text(encoding="utf-8")
    assert "<html" in html
    assert "로그라이크" in html


def test_export_core_loop_md_creates_file(tmp_path, sample_session):
    export_core_loop_md(sample_session, tmp_path)
    md = (tmp_path / "core_loop.md").read_text(encoding="utf-8")
    assert "핵심 게임 루프" in md
    assert "루프 분석 내용" in md


def test_export_core_fun_md_creates_file(tmp_path, sample_session):
    export_core_fun_md(sample_session, tmp_path)
    md = (tmp_path / "core_fun.md").read_text(encoding="utf-8")
    assert "핵심 재미 요소" in md
    assert "재미 분석 내용" in md
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_export.py -v
```

Expected: 일부 FAIL (scripts/export.py가 아직 없으므로 ImportError)

- [ ] **Step 3: 테스트 실행 — 통과 확인**

scripts/export.py가 Task 2에서 작성됐으므로:

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/test_export.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 4: 커밋**

```bash
git add tests/test_export.py
git commit -m "test: add test_export.py for scripts/export.py"
```

---

## Task 4: pipeline.md 스킬 작성

**Files:**
- Create: `.claude/skills/pipeline.md`

- [ ] **Step 1: pipeline.md 작성**

`.claude/skills/pipeline.md`:

```markdown
---
description: 게임 컨셉 파이프라인을 단계별로 실행한다. concept-clarifier가 저장한 user_input.json이 있어야 한다.
---

# pipeline 스킬

게임 컨셉 생성 파이프라인을 단계별로 실행한다. 각 주요 단계 후 사용자의 승인을 받는다.

> **핵심 원칙**: 각 단계는 Agent 툴로 서브에이전트를 dispatch해 실행한다. 상태는 output/session.json에 저장한다. 승인 게이트에서 사용자가 n을 입력하면 멈추고 pipeline-resume 스킬로 재개할 수 있다.

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
  "concept_diagram_mermaid": null
}
```

TodoWrite Step 1을 `completed`로 표시.

**[승인 게이트 1]**

```
[Step 1 완료] 레퍼런스 게임 탐색 완료
  {reference_games 목록}

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

**상태 저장:** session.json에 `fun_analysis`, `loop_analysis` 추가. `completed_steps`에 "fun_analysis", "loop_analysis" 추가.

TodoWrite Step 2+3을 `completed`로 표시.

**[승인 게이트 2]**

```
[Step 2+3 완료] 재미/루프 분석 완료

[핵심 재미 분석 요약]
{fun_analysis 앞 200자}...

[핵심 게임 루프 분석 요약]
{loop_analysis 앞 200자}...

다음 단계(요약 정리)로 진행할까요? (y/n)
```

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

**상태 저장:** session.json에 `synthesis`, `synthesis_key_points` 추가. `completed_steps`에 "synthesis" 추가.

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

**상태 저장:** session.json에 `concept` 추가. `completed_steps`에 "concept" 추가.

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
     - Agent dispatch (concept_writer.md + 피드백 + 현재 concept):
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

**상태 저장:** session.json에 `concept_quality_scores` 저장. `completed_steps`에 "concept_quality" 추가.

TodoWrite Step 5.5를 `completed`로 표시.

**[승인 게이트 3]**

```
[Step 5.5 완료] 컨셉 품질 평가 통과
  mechanism: {score}, fun: {score}, market: {score}

[컨셉안 요약 - 처음 500자]
{concept 앞 500자}...

다음 단계(UI 이미지 생성)로 진행할까요? (y/n)
```

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

**상태 저장:** session.json에 `concept` (clean), `reference_images`, `concept_diagram_mermaid`, `concept_ui_svgs` 저장. `completed_steps`에 "images" 추가.

TodoWrite Step 6을 `completed`로 표시.

**[승인 게이트 4]**

```
[Step 6 완료] 이미지 생성 완료
  씬 수: {scenes 수}개
  레퍼런스 이미지: {reference_images 수}개

다음 단계(파일 출력)로 진행할까요? (y/n)
```

---

## Step 7: 파일 출력

TodoWrite Step 7을 `in_progress`로 표시.

Bash 툴로 실행:
```bash
PYTHONUTF8=1 .venv/Scripts/python scripts/export.py --session output/session.json
```

출력된 폴더 경로를 확인하고:

```
[완료] 컨셉안이 생성됐습니다.

출력 폴더: output/{폴더명}/
  - concept.html    게임 컨셉안 HTML
  - core_loop.md    핵심 게임 루프 요약
  - core_fun.md     핵심 재미 요소 요약
  - session.json    파이프라인 실행 데이터
```

TodoWrite Step 7을 `completed`로 표시.
```

- [ ] **Step 2: 커밋**

```bash
git add .claude/skills/pipeline.md
git commit -m "feat: add pipeline.md skill — Claude Code skill-based pipeline orchestrator"
```

---

## Task 5: pipeline-resume.md 스킬 작성

**Files:**
- Create: `.claude/skills/pipeline-resume.md`

- [ ] **Step 1: pipeline-resume.md 작성**

`.claude/skills/pipeline-resume.md`:

```markdown
---
description: 중단된 파이프라인을 output/session.json에서 읽어 이어서 실행한다.
---

# pipeline-resume 스킬

중단된 게임 컨셉 파이프라인을 재개한다.

## 실행 방법

1. `output/session.json`을 Read 툴로 읽는다.
   없으면 오류 메시지 출력 후 종료:
   ```
   output/session.json이 없습니다. 재개할 파이프라인이 없습니다.
   pipeline 스킬을 처음부터 실행하세요.
   ```

2. session.json에서 `completed_steps` 목록을 확인한다.

3. 현재 상태 요약 출력:
   ```
   [파이프라인 재개]
   완료된 단계: {completed_steps}
   
   이어서 실행할까요? (y/n)
   ```

4. y이면 → `pipeline` 스킬을 실행한다 (session.json의 completed_steps를 활용해 완료된 단계는 건너뜀)
5. n이면 → 종료
```

- [ ] **Step 2: 커밋**

```bash
git add .claude/skills/pipeline-resume.md
git commit -m "feat: add pipeline-resume.md skill — resume interrupted pipeline from session.json"
```

---

## Task 6: concept-clarifier.md Phase F 수정

**Files:**
- Modify: `.claude/skills/concept-clarifier.md`

- [ ] **Step 1: Phase F의 하네스 실행 부분 수정**

현재 Phase F Step 2:
```
mkdir -p output && PYTHONUTF8=1 .venv/Scripts/python main.py --from-file user_input.json ...
```

새 Phase F Step 2:
```
Write 툴로 user_input.json을 저장한다.
그 다음 pipeline 스킬을 실행한다.
```

`.claude/skills/concept-clarifier.md`의 Phase F 섹션에서 아래 부분을 교체한다:

**교체 대상 (현재):**
```
2. 다음 명령을 Bash 툴로 실행한다.
   - `run_in_background` = **false** (대화창이 파이프라인 완료까지 대기)
   - `timeout` = **600000** (10분, 파이프라인 완료까지 대기)

```bash
mkdir -p output && PYTHONUTF8=1 .venv/Scripts/python main.py --from-file user_input.json & PID=$!; echo $PID > output/pipeline.pid; wait $PID; EXIT=$?; rm -f output/pipeline.pid; exit $EXIT
```

3. 하네스 출력에 `검증 실패 - 최대 재시도 횟수 초과` 메시지가 있으면 다음 순서로 진행한다:
   - `pipeline-debug` 스킬을 실행하여 실패한 단계를 진단한다
   - 진단 완료 후 하네스를 **한 번 더 재실행**한다 (같은 명령, `run_in_background: false`, `timeout: 600000`)
   - 재실행에서도 실패하면 그대로 계속 진행한다 (Python 코드가 자동으로 현재 결과로 넘어감)

4. 하네스가 정상 완료되면 "컨셉안 생성 (하네스)"를 `completed`로 표시한다.
```

**교체 내용 (새 버전):**
```
2. `pipeline` 스킬을 실행한다:
   - Skill 툴로 `pipeline` 스킬 호출
   - 파이프라인이 단계별 승인 게이트를 거쳐 완료될 때까지 진행

3. 파이프라인이 완료되면 "컨셉안 생성 (하네스)"를 `completed`로 표시한다.
```

- [ ] **Step 2: 커밋**

```bash
git add .claude/skills/concept-clarifier.md
git commit -m "refactor: concept-clarifier Phase F — call pipeline skill instead of Python harness"
```

---

## Task 7: 기존 Python 파일 삭제 및 정리

**Files:**
- Delete: `harness.py`, `main.py`, `session_manager.py`, `models/pipeline_state.py`
- Delete: `agents/__init__.py`, `agents/base.py`, `agents/*.py` (22개)
- Delete: `tests/test_harness.py`, `tests/test_concept_quality_evaluator.py`, `tests/test_concept_ui_evaluator.py`, `tests/test_session_manager.py`

- [ ] **Step 1: 기존 Python 에이전트/하네스 파일 삭제**

```bash
rm harness.py main.py session_manager.py
rm models/pipeline_state.py
rm agents/__init__.py agents/base.py
rm agents/fun_analyzer.py agents/fun_validator.py
rm agents/loop_analyzer.py agents/loop_validator.py
rm agents/content_synthesizer.py agents/synthesis_reviewer.py
rm agents/concept_writer.py agents/concept_validator.py
rm agents/concept_quality_evaluator.py
rm agents/concept_ui_generator.py agents/concept_ui_evaluator.py
rm agents/concept_diagram_generator.py agents/concept_scene_parser.py
rm agents/reference_searcher.py agents/reference_validator.py
rm agents/reference_image_fetcher.py
rm agents/html_exporter.py agents/html_validator.py
rm agents/word_exporter.py agents/word_validator.py
```

- [ ] **Step 2: 기존 Python 테스트 파일 삭제**

```bash
rm tests/test_harness.py
rm tests/test_concept_quality_evaluator.py
rm tests/test_concept_ui_evaluator.py
rm tests/test_session_manager.py
```

- [ ] **Step 3: 남은 테스트만 실행 — 모두 통과 확인**

```bash
PYTHONUTF8=1 .venv/Scripts/python -m pytest tests/ -v
```

Expected: test_export.py 포함 남은 테스트 모두 PASS. test_word_exporter.py가 있으면 함께 확인.

- [ ] **Step 4: main.py에 의존성 있던 config.yaml 확인**

```bash
cat config.yaml
```

config.yaml은 삭제하지 않는다. pipeline.md 스킬에서는 직접 사용하지 않지만, 참고 문서로 유지.

- [ ] **Step 5: Stop 훅 명령 정리**

`.claude/settings.json`의 Stop 훅에서 `pipeline.pid` kill 명령은 더 이상 필요하지 않다.
pipeline이 Python 백그라운드 프로세스가 아닌 스킬로 실행되므로 Stop 훅을 비운다:

```json
{
  "permissions": {
    "allow": ["Bash(git:*)"],
    "ask": ["Bash(git commit:*)", "Bash(git merge:*)", "Bash(git push:*)"]
  }
}
```

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "refactor: remove Python harness — migration to skill-based pipeline complete"
```

---

## Self-Review

**스펙 커버리지 확인:**
- [x] agents/prompts/*.md — Task 1 (15개 파일)
- [x] scripts/export.py — Task 2 (HTML + core_loop.md + core_fun.md + Word + 폴더 생성)
- [x] session.json 스키마 — Task 4 pipeline.md 내 Step 1-3에 반영
- [x] 승인 게이트 4개 — Task 4 pipeline.md에 모두 포함
- [x] 컨셉 품질 평가 루프 (5회 재시도, 3회 재시작) — Task 4 Step 5.5
- [x] SVG 품질 루프 (10회, 최고점 채택) — Task 4 Step 6-4
- [x] 출력 폴더 구조 (YYYYMMDD_타이틀) — Task 2 export_html/main
- [x] session.json → 출력 폴더로 이동 — Task 2 main()
- [x] pipeline-resume.md — Task 5
- [x] concept-clarifier Phase F 수정 — Task 6
- [x] 기존 Python 파일 삭제 — Task 7
- [x] Stop 훅 정리 — Task 7 Step 5

**플레이스홀더 없음 확인:** 모든 단계에 실제 코드/내용 포함됨.

**타입 일관성:** `parse_concept_scenes()`, `extract_game_title()`, `extract_section()` 등 Task 2에서 정의한 함수들이 Task 3 테스트와 이름 일치.
