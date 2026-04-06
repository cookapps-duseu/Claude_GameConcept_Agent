# 게임 컨셉 구체화 스킬 설계 스펙

**날짜**: 2026-04-02  
**상태**: 승인됨  
**기반**: 2026-04-02-model-tiering-skills-design.md

---

## 개요

사용자가 Claude Code에 게임 컨셉 생성을 요청하면 `.claude/skills/concept-clarifier.md` 스킬이 자동으로 트리거된다.

스킬은 Claude Code 내에서 직접 대화하며 컨셉을 구체화한 뒤 `user_input.json`을 저장하고 `python main.py --from-file user_input.json`을 실행하여 하네스를 자동으로 구동한다.

---

## 전체 흐름

```
사용자: "게임 컨셉 만들어줘"
  ↓ (concept-clarifier 스킬 자동 트리거)
Phase A: Claude Code가 직접 질문 (1회에 1개, 자연스러운 대화)
  ↓ (9개 필드 모두 채워지면 자동 전환)
Phase B: 고정 확인 질문 7개 (수집된 값을 기본값으로 표시)
  ↓
user_input.json 저장
  ↓
Bash: python main.py --from-file user_input.json
  ↓
하네스 실행 (레퍼런스 탐색 → 분석 → 컨셉안 작성 → 출력)
```

---

## 수집 필드 (9개)

| 필드 | Phase | 필수 |
|------|-------|------|
| `genre` | A | 필수 |
| `target_user` | A | 선택 |
| `platform` | B | 선택 |
| `dimension` | B | 선택 |
| `reference_games` | B | 선택 |
| `play_mode` | B | 선택 |
| `combat_mode` | B | 선택 |
| `keywords` | B | 선택 |
| `free_text` | B | 선택 |

---

## 파일 변경 목록

| 종류 | 파일 | 내용 |
|------|------|------|
| 신규 | `.claude/skills/concept-clarifier.md` | 스킬 파일 |
| 수정 | `models/user_input.py` | 필드 4개 추가, `to_prompt()` 확장, `to_json()` / `from_json()` 추가 |
| 수정 | `main.py` | `--from-file` 플래그 처리 추가 |
| 수정 | `config.yaml` | `clarifier` 모델 키 제거 (스킬은 Claude Code 자체 사용) |

---

## 1. UserInput 모델 확장

### 추가 필드

```python
dimension: str | None = None        # "2D" / "3D" / "미정"
reference_games: list[str] = field(default_factory=list)
play_mode: str | None = None        # "싱글" / "멀티" / "둘다"
combat_mode: str | None = None      # "PvE" / "PvP" / "Co-op" / "PvPvE" / "없음"
```

### to_prompt() 확장

```python
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
```

### JSON 직렬화 (파일 저장/읽기용)

```python
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
def from_json(cls, data: dict) -> "UserInput":
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

---

## 2. main.py 변경

`--from-file` 플래그 처리:

```python
import argparse
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-file", type=str, default=None)
    return parser.parse_args()

async def main():
    args = parse_args()
    output_format = load_output_format()
    session_manager = SessionManager()

    # 세션 재개 처리 ...

    if resume_state is None:
        if args.from_file:
            with open(args.from_file, encoding="utf-8") as f:
                user_input = UserInput.from_json(json.load(f))
        else:
            user_input = get_user_input()  # 기존 대화형 입력 유지
        ...
```

`get_user_input()`은 제거하지 않고 유지 — `--from-file` 없이 직접 실행 시 기존 동작 보장.

---

## 3. concept-clarifier 스킬

### 파일 위치

`.claude/skills/concept-clarifier.md`

### 트리거 예시

- "게임 컨셉 만들어줘"
- "게임 기획 도와줘"
- "컨셉안 생성해줘"

### 스킬 내용 (요약)

**Phase A — 자연스러운 대화**

Claude Code가 게임 기획 컨설턴트 역할로 다음 9개 항목을 한 번에 하나씩 질문한다:
- 장르/컨셉 (`genre`)
- 타겟 유저 (`target_user`)

모든 항목이 채워지면 Phase B로 자동 전환.

**Phase B — 고정 확인 질문**

수집된 값을 기본값으로 표시하고 사용자가 Enter로 확인 또는 수정:

```
[컨셉 확인] 정리된 내용입니다. Enter로 확인, 수정하려면 새로 입력하세요.

플랫폼 [모바일]:
2D/3D [2D]:
레퍼런스 게임 [슬레이 더 스파이어, 하데스]:
싱글/멀티플레이 [싱글]:
전투/대결 방식 [PvE]:
키워드 [짧은플레이, 성장]:
추가 설명 [출퇴근 시간에 즐길 수 있는 게임]:
```

**Phase C — 최종 확인**

9개 전체 필드 요약 표시 후 "이대로 시작할까요? (y/n)" 확인.
`n` 입력 시 Phase B로 돌아가 재확인. `y` 또는 Enter 시 Phase D 진행.

**Phase D — 하네스 실행**

1. 수집된 필드를 `user_input.json`으로 저장
2. `python main.py --from-file user_input.json` 실행

---

## 4. Phase A/B/C 전체 예시

```
사용자: 게임 컨셉 만들어줘

Claude: 어떤 장르의 게임을 만들고 싶으신가요?
사용자: 로그라이크 덱빌딩이요

Claude: 누구를 위한 게임인가요? (타겟 유저)
사용자: 바쁜 직장인

[컨셉 확인] 정리된 내용입니다. Enter로 확인, 수정하려면 새로 입력하세요.

플랫폼 [없음]:
2D/3D [없음]:
레퍼런스 게임 [없음]: 슬레이 더 스파이어
싱글/멀티플레이 [없음]: 싱글
전투/대결 방식 [없음]: PvE
키워드 [없음]: 짧은플레이, 성장
추가 설명 [없음]: 출퇴근 시간에 즐길 수 있으면 좋겠어요

[최종 확인] 아래 내용으로 게임 컨셉안을 생성합니다.

- 장르/컨셉: 로그라이크 덱빌딩
- 타겟 유저: 바쁜 직장인
- 플랫폼: 모바일
- 그래픽: 2D
- 레퍼런스 게임: 슬레이 더 스파이어, 하데스
- 플레이 방식: 싱글
- 전투/대결 방식: PvE
- 키워드: 짧은플레이, 성장
- 추가 설명: 출퇴근 시간에 즐길 수 있으면 좋겠어요

이대로 시작할까요? (y/n, 기본값 y): y

→ user_input.json 저장
→ python main.py --from-file user_input.json 실행
→ [1/6] 레퍼런스 탐색 중...
```

---

## 테스트 전략

- `test_user_input.py`
  - `to_json()` / `from_json()` 왕복 직렬화
  - `to_prompt()` 새 필드 포함 확인
  - 새 필드 없는 기존 JSON도 `from_json()` 정상 처리 (하위 호환)
- `test_main.py`
  - `--from-file` 플래그 시 `UserInput.from_json()` 호출 확인
  - 파일 없을 때 기존 `get_user_input()` 호출 확인

---

## 하위 호환성

- `UserInput` 새 필드 모두 `None`/빈 리스트 기본값 → 기존 에이전트 프롬프트 영향 없음
- `get_user_input()` 유지 → `--from-file` 없이 직접 실행 시 기존 동작 유지
- 세션 재개 시 `--from-file` 무관하게 기존 재개 로직 동작
