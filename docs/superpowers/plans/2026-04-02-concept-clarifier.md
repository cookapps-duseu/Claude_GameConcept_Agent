# 게임 컨셉 구체화 스킬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 Claude Code에 게임 컨셉 요청 시 `.claude/skills/concept-clarifier.md` 스킬이 트리거되어 대화형 컨셉 구체화를 진행한 뒤 자동으로 하네스를 실행한다.

**Architecture:** `UserInput` 모델에 4개 필드(`dimension`, `reference_games`, `play_mode`, `combat_mode`)를 추가하고 JSON 직렬화를 지원한다. `main.py`에 `--from-file` 플래그를 추가하여 스킬이 저장한 `user_input.json`을 읽어 파이프라인을 실행한다. 스킬 파일(`.claude/skills/concept-clarifier.md`)이 Phase A(대화) → Phase B(확인) → 파일 저장 → `python main.py --from-file` 실행의 전체 흐름을 안내한다.

**Tech Stack:** Python dataclasses, argparse, json, Claude Code skills (`.claude/skills/`)

---

## 파일 변경 목록

| 종류 | 파일 | 내용 |
|------|------|------|
| 수정 | `models/user_input.py` | 필드 4개 추가, `to_prompt()` 확장, `to_json()` / `from_json()` 추가 |
| 수정 | `tests/test_models.py` | `UserInput` 새 필드 및 JSON 직렬화 테스트 추가 |
| 수정 | `main.py` | `argparse`로 `--from-file` 플래그 처리 |
| 수정 | `tests/test_main.py` (신규) | `--from-file` 동작 테스트 |
| 신규 | `.claude/skills/concept-clarifier.md` | 스킬 파일 |

---

## Task 1: UserInput 모델 확장

**Files:**
- Modify: `models/user_input.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_models.py` 하단에 추가:

```python
def test_user_input_new_fields_defaults():
    u = UserInput(genre="로그라이크")
    assert u.dimension is None
    assert u.reference_games == []
    assert u.play_mode is None
    assert u.combat_mode is None


def test_user_input_to_json_roundtrip():
    u = UserInput(
        genre="로그라이크 덱빌딩",
        platform="모바일",
        target_user="바쁜 직장인",
        dimension="2D",
        reference_games=["슬레이 더 스파이어", "하데스"],
        play_mode="싱글",
        combat_mode="PvE",
        keywords=["짧은플레이", "성장"],
        free_text="출퇴근 시간용",
    )
    data = u.to_json()
    restored = UserInput.from_json(data)
    assert restored.genre == u.genre
    assert restored.dimension == u.dimension
    assert restored.reference_games == u.reference_games
    assert restored.play_mode == u.play_mode
    assert restored.combat_mode == u.combat_mode
    assert restored.keywords == u.keywords


def test_user_input_from_json_missing_new_fields():
    """기존 형식(새 필드 없음)도 from_json()이 정상 처리해야 한다."""
    data = {"genre": "퍼즐"}
    u = UserInput.from_json(data)
    assert u.genre == "퍼즐"
    assert u.dimension is None
    assert u.reference_games == []
    assert u.play_mode is None
    assert u.combat_mode is None


def test_user_input_to_prompt_includes_new_fields():
    u = UserInput(
        genre="액션",
        dimension="3D",
        reference_games=["엘든 링"],
        play_mode="싱글",
        combat_mode="PvE",
    )
    prompt = u.to_prompt()
    assert "3D" in prompt
    assert "엘든 링" in prompt
    assert "싱글" in prompt
    assert "PvE" in prompt
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_models.py::test_user_input_new_fields_defaults -v
```

Expected: `FAILED` — `UserInput` has no field `dimension`

- [ ] **Step 3: UserInput 모델 수정**

`models/user_input.py` 전체를 다음으로 교체:

```python
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class UserInput:
    genre: str
    platform: str | None = None
    target_user: str | None = None
    dimension: str | None = None
    reference_games: list[str] = field(default_factory=list)
    play_mode: str | None = None
    combat_mode: str | None = None
    keywords: list[str] = field(default_factory=list)
    free_text: str | None = None

    def to_prompt(self) -> str:
        lines = [f"장르: {self.genre}"]
        if self.platform:
            lines.append(f"플랫폼: {self.platform}")
        if self.target_user:
            lines.append(f"타겟 유저: {self.target_user}")
        if self.dimension:
            lines.append(f"그래픽: {self.dimension}")
        if self.reference_games:
            lines.append(f"레퍼런스 게임: {', '.join(self.reference_games)}")
        if self.play_mode:
            lines.append(f"플레이 방식: {self.play_mode}")
        if self.combat_mode:
            lines.append(f"전투/대결 방식: {self.combat_mode}")
        if self.keywords:
            lines.append(f"키워드: {', '.join(self.keywords)}")
        if self.free_text:
            lines.append(f"추가 설명: {self.free_text}")
        return "\n".join(lines)

    def to_json(self) -> dict:
        return {
            "genre": self.genre,
            "platform": self.platform,
            "target_user": self.target_user,
            "dimension": self.dimension,
            "reference_games": self.reference_games,
            "play_mode": self.play_mode,
            "combat_mode": self.combat_mode,
            "keywords": self.keywords,
            "free_text": self.free_text,
        }

    @classmethod
    def from_json(cls, data: dict) -> UserInput:
        return cls(
            genre=data["genre"],
            platform=data.get("platform"),
            target_user=data.get("target_user"),
            dimension=data.get("dimension"),
            reference_games=data.get("reference_games", []),
            play_mode=data.get("play_mode"),
            combat_mode=data.get("combat_mode"),
            keywords=data.get("keywords", []),
            free_text=data.get("free_text"),
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_models.py -v
```

Expected: 전체 PASS (기존 테스트 포함)

- [ ] **Step 5: 커밋**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add models/user_input.py tests/test_models.py
git commit -m "feat: extend UserInput with dimension, reference_games, play_mode, combat_mode"
```

---

## Task 2: main.py에 --from-file 플래그 추가

**Files:**
- Modify: `main.py`
- Test: `tests/test_main.py` (신규)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_main.py` 신규 생성:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from models.user_input import UserInput


def test_from_file_loads_user_input(tmp_path):
    """--from-file 경로의 JSON을 UserInput으로 로드한다."""
    data = {
        "genre": "로그라이크",
        "platform": "모바일",
        "target_user": None,
        "dimension": "2D",
        "reference_games": ["슬레이 더 스파이어"],
        "play_mode": "싱글",
        "combat_mode": "PvE",
        "keywords": ["짧은플레이"],
        "free_text": None,
    }
    input_file = tmp_path / "user_input.json"
    input_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    u = UserInput.from_json(json.loads(input_file.read_text(encoding="utf-8")))
    assert u.genre == "로그라이크"
    assert u.dimension == "2D"
    assert u.reference_games == ["슬레이 더 스파이어"]
    assert u.play_mode == "싱글"


def test_parse_args_from_file():
    """argparse가 --from-file 인자를 올바르게 파싱한다."""
    import sys
    sys.argv = ["main.py", "--from-file", "user_input.json"]
    from main import parse_args
    args = parse_args()
    assert args.from_file == "user_input.json"


def test_parse_args_no_flag():
    """--from-file 없이 실행 시 None이어야 한다."""
    import sys
    sys.argv = ["main.py"]
    from main import parse_args
    args = parse_args()
    assert args.from_file is None
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_main.py::test_parse_args_from_file -v
```

Expected: `FAILED` — `cannot import name 'parse_args' from 'main'`

- [ ] **Step 3: main.py 수정**

`main.py`에서 `import asyncio` 바로 아래에 `import argparse`, `import json` 추가 후 `get_user_input()` 함수 다음에 `parse_args()` 추가. `main()` 함수 상단에 `parse_args()` 호출 및 `--from-file` 분기 추가.

전체 `main.py`:

```python
import asyncio
import argparse
import json
from dotenv import load_dotenv
from config import load_output_format, load_model, load_models
from session_manager import SessionManager
from models.user_input import UserInput
from harness import GameConceptHarness
from agents.reference_searcher import ReferenceSearcher
from agents.reference_validator import ReferenceValidator
from agents.fun_analyzer import FunAnalyzer
from agents.fun_validator import FunValidator
from agents.loop_analyzer import LoopAnalyzer
from agents.loop_validator import LoopValidator
from agents.content_synthesizer import ContentSynthesizer
from agents.synthesis_reviewer import SynthesisReviewer
from agents.concept_writer import ConceptWriter
from agents.concept_validator import ConceptValidator
from agents.word_exporter import WordExporter
from agents.html_exporter import HtmlExporter
from agents.word_validator import WordValidator
from agents.html_validator import HtmlValidator
from agents.reference_image_fetcher import ReferenceImageFetcher
from agents.concept_ui_generator import ConceptUiGenerator
from agents.concept_diagram_generator import ConceptDiagramGenerator

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", type=str, default=None, dest="from_file")
    return parser.parse_args()


def get_user_input() -> UserInput:
    print("=" * 50)
    print("게임 컨셉 에이전트")
    print("=" * 50)
    print("\n입력 방식을 선택하세요:")
    print("1. 간단 입력 (장르 + 기획 의도)")
    print("2. 상세 입력 (장르/플랫폼/타겟/키워드 개별 입력)")
    mode = input("\n선택 (1/2, 기본값 1): ").strip() or "1"

    if mode == "2":
        genre = input("장르 (필수): ").strip()
        platform = input("플랫폼 (선택, 예: 모바일/PC/콘솔): ").strip() or None
        target_user = input("타겟 유저 (선택, 예: 캐주얼 게이머): ").strip() or None
        keywords_raw = input("키워드 (선택, 쉼표 구분, 예: 짧은플레이,성장): ").strip()
        keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
        free_text = input("추가 설명 (선택): ").strip() or None
    else:
        genre = input("장르와 기획 의도를 입력하세요 (예: 모바일 로그라이크 RPG, 10분 단위 플레이): ").strip()
        platform = None
        target_user = None
        keywords = []
        free_text = None

    return UserInput(
        genre=genre,
        platform=platform,
        target_user=target_user,
        keywords=keywords,
        free_text=free_text,
    )


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
        word_exporter=WordExporter() if output_format in ("word", "both") else None,
        html_exporter=HtmlExporter() if output_format in ("html", "both") else None,
        word_validator=WordValidator() if output_format in ("word", "both") else None,
        html_validator=HtmlValidator() if output_format in ("html", "both") else None,
        output_format=output_format,
        session_manager=session_manager,
        reference_image_fetcher=ReferenceImageFetcher(model=models["image"]) if output_format in ("html", "both") else None,
        concept_ui_generator=ConceptUiGenerator(model=models["image"]) if output_format in ("html", "both") else None,
        concept_diagram_generator=ConceptDiagramGenerator(model=models["image"]) if output_format in ("html", "both") else None,
    )


async def main():
    args = parse_args()
    output_format = load_output_format()
    session_manager = SessionManager()

    resume_state = None
    completed_steps = []

    if session_manager.has_session():
        print("\n[미완료 세션 발견] 이전에 중단된 작업이 있습니다.")
        choice = input("이어서 진행하시겠습니까? (y/n, 기본값 y): ").strip().lower() or "y"
        if choice == "y":
            result = session_manager.load()
            if result:
                resume_state, completed_steps = result
                print(f"완료된 단계: {', '.join(completed_steps) or '없음'}")
                print("[이어서 진행합니다]\n")
        else:
            session_manager.clear()

    harness = build_harness(output_format, session_manager)

    if resume_state is None:
        if args.from_file:
            with open(args.from_file, encoding="utf-8") as f:
                user_input = UserInput.from_json(json.load(f))
        else:
            user_input = get_user_input()
        print(f"\n[시작] 게임 컨셉 생성 중... (출력 포맷: {output_format})\n")
        state = await harness.run(user_input, completed_steps=completed_steps)
    else:
        print(f"\n[재개] 게임 컨셉 생성 재개 중... (출력 포맷: {output_format})\n")
        state = await harness.run(
            resume_state.user_input,
            resume_state=resume_state,
            completed_steps=completed_steps,
        )

    print("\n" + "=" * 50)
    print("완료!")
    if state.output_word_path:
        print(f"Word 파일: {state.output_word_path}")
    if state.output_html_path:
        print(f"HTML 파일: {state.output_html_path}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest tests/test_main.py -v
```

Expected: 3개 PASS

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python -m pytest -v
```

Expected: 전체 PASS

- [ ] **Step 6: 커밋**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add main.py tests/test_main.py
git commit -m "feat: add --from-file flag to main.py for skill-driven input"
```

---

## Task 3: concept-clarifier 스킬 파일 작성

**Files:**
- Create: `.claude/skills/concept-clarifier.md`

스킬은 코드가 아니라 Claude Code가 따를 지침이므로 테스트 없음.

- [ ] **Step 1: 스킬 파일 생성**

`.claude/skills/concept-clarifier.md`:

```markdown
---
description: 게임 컨셉 생성 요청 시 사용. 대화로 컨셉을 구체화하고 자동으로 하네스를 실행한다.
---

# concept-clarifier 스킬

사용자가 게임 컨셉 생성을 요청하면 이 스킬을 실행한다.

**트리거 예시**: "게임 컨셉 만들어줘", "게임 기획 도와줘", "컨셉안 생성해줘", "게임 아이디어 구체화해줘"

---

## Phase A — 컨셉 대화

게임 기획 컨설턴트 역할로 다음 2개 항목을 **한 번에 하나씩** 자연스럽게 질문한다.
이미 사용자가 언급한 정보는 다시 묻지 않는다.

수집 항목:
- `genre`: 장르와 핵심 컨셉 (필수)
- `target_user`: 타겟 유저 (선택 — 사용자가 "없음" / "모름"으로 답해도 완료)

2개 항목이 모두 채워지면 Phase B로 넘어간다.

---

## Phase B — 고정 확인 질문

Phase A에서 수집한 값을 기본값으로 표시한다. Enter면 그대로, 새로 입력하면 덮어쓴다.
선택 항목은 Enter로 건너뛸 수 있다.

```
[컨셉 확인] 정리된 내용입니다. Enter로 확인, 수정하려면 새로 입력하세요.

플랫폼 [{platform 또는 없음}]:
2D/3D [{dimension 또는 없음}]:
레퍼런스 게임 [{쉼표 구분 목록 또는 없음}]:
싱글/멀티플레이 [{play_mode 또는 없음}]:
전투/대결 방식 (PvE/PvP/Co-op/PvPvE/없음) [{combat_mode 또는 없음}]:
키워드 [{쉼표 구분 목록 또는 없음}]:
추가 설명 [{free_text 또는 없음}]:
```

---

## Phase C — 최종 확인

Phase B 완료 후 수집된 **9개 전체 필드**를 요약 표시하고 사용자 확인을 받는다:

```
[최종 확인] 아래 내용으로 게임 컨셉안을 생성합니다.

- 장르/컨셉: <genre>
- 타겟 유저: <target_user 또는 미지정>
- 플랫폼: <platform 또는 미지정>
- 그래픽: <dimension 또는 미지정>
- 레퍼런스 게임: <목록 또는 없음>
- 플레이 방식: <play_mode 또는 미지정>
- 전투/대결 방식: <combat_mode 또는 미지정>
- 키워드: <목록 또는 없음>
- 추가 설명: <free_text 또는 없음>

이대로 시작할까요? (y/n, 기본값 y):
```

- `y` 또는 Enter → Phase D로 진행
- `n` → Phase B로 돌아가 다시 확인

---

## Phase D — 파일 저장 및 하네스 실행

1. 수집된 모든 필드를 `user_input.json`으로 저장한다:

```json
{
  "genre": "<값>",
  "platform": "<값 또는 null>",
  "target_user": "<값 또는 null>",
  "dimension": "<값 또는 null>",
  "reference_games": ["<값>", ...],
  "play_mode": "<값 또는 null>",
  "combat_mode": "<값 또는 null>",
  "keywords": ["<값>", ...],
  "free_text": "<값 또는 null>"
}
```

2. 다음 명령을 실행한다:

```bash
cd e:/Github/Claude_GameConcept_Agent && .venv/Scripts/python main.py --from-file user_input.json
```

---

## 주의사항

- Phase A는 최대한 자연스럽게 대화한다. 형식적인 목록 나열 금지.
- Phase B에서 "없음"으로 Enter한 선택 항목은 `null`로 저장한다.
- 리스트 필드(`reference_games`, `keywords`)에서 빈 입력은 `[]`로 저장한다.
- 하네스 실행 후에는 별도 작업 없이 파이프라인이 자동으로 진행된다.
```

- [ ] **Step 2: 스킬이 로드되는지 확인**

Claude Code 터미널에서:
```
/concept-clarifier
```
또는 "게임 컨셉 만들어줘"라고 입력했을 때 스킬이 트리거되는지 확인.

- [ ] **Step 3: 커밋**

```bash
cd e:/Github/Claude_GameConcept_Agent && git add .claude/skills/concept-clarifier.md
git commit -m "feat: add concept-clarifier skill for game concept clarification"
```
