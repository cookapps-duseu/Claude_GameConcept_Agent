# Image Enhancement Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 레퍼런스 게임에 스토어 링크를 추가하고, 컨셉안 본문 내 지정 위치에 인게임 예시 SVG 이미지를 3~15개 인라인 삽입한다.

**Architecture:** ConceptWriter가 컨셉 본문에 `[IMG_SCENE_N]` 플레이스홀더를 직접 삽입하고 문서 끝에 `---SCENE_LIST---` JSON을 첨부한다. 5단계에서 씬 목록을 파싱해 ConceptUiGenerator를 N번 병렬 호출해 SVG를 생성하고, HtmlExporter가 플레이스홀더를 SVG `<div>`로 치환한다. 레퍼런스 이미지는 ReferenceImageFetcher가 스토어 링크도 함께 반환하도록 확장한다.

**Tech Stack:** Python asyncio, Jinja2, claude_agent_sdk, SVG

---

## Feature 1: 레퍼런스 게임 스토어 링크

### 변경 파일

- Modify: `agents/reference_image_fetcher.py` — ROLE 수정, JSON 출력에 `store_url` 추가
- Modify: `templates/concept.html.j2` — 이미지 로드 실패 시 스토어 링크 버튼 표시

### 설계 상세

**ReferenceImageFetcher ROLE 변경점:**
- 이미지 URL과 함께 Steam/Google Play/App Store 등 스토어 링크도 탐색
- 반환 JSON: `[{"game": "...", "url": "이미지URL또는null", "store_url": "https://store.steampowered.com/..."}]`
- 이미지 URL을 찾지 못한 경우 `"url": null`로 반환 (스토어 링크는 최대한 확보)

**HTML 템플릿 변경점:**
- 이미지가 있으면 `<img>` 표시
- `onerror` 핸들러: 이미지 로드 실패 시 이미지를 숨기고 `<a href="store_url">` 링크 버튼 노출
- `store_url`도 없으면 게임명 텍스트만 표시

---

## Feature 2: 컨셉 기반 인라인 인게임 예시 이미지

### 변경 파일

- Modify: `agents/concept_writer.py` — ROLE에 플레이스홀더/씬 목록 출력 지침 추가
- Modify: `agents/concept_ui_generator.py` — 단일 씬 description을 받아 SVG 1개 생성하도록 ROLE 정밀화
- Add: `agents/concept_scene_parser.py` — `parse_concept_scenes()` 함수
- Modify: `models/pipeline_state.py` — `concept_ui_svgs: list[dict]` 추가, `concept_ui_svg` 제거
- Modify: `harness.py` — 5단계에서 씬 파싱 및 병렬 SVG 생성 로직 추가
- Modify: `agents/html_exporter.py` — `[IMG_SCENE_N]` 플레이스홀더를 SVG `<div>`로 치환
- Modify: `templates/concept.html.j2` — Section 2의 `concept_ui_svg` 하드코딩 제거

### 설계 상세

**ConceptWriter ROLE 추가 지침:**
```
컨셉안 본문에서 시각적으로 보여주면 이해에 도움이 되는 자리에
[IMG_SCENE_N] 태그를 삽입하세요 (N은 1부터 순서대로).
최소 3개, 최대 15개. 반드시 인게임 화면만 다루며, 씬 간 내용이 겹치면 안 됩니다.

컨셉 본문 작성 완료 후 반드시 다음 형식을 문서 맨 끝에 추가하세요:

---SCENE_LIST---
[
  {"id": 1, "title": "씬 제목", "desc": "SVG로 그릴 화면 상세 설명 (UI 요소, 색상, 레이아웃 등)"},
  ...
]
```

**parse_concept_scenes() 함수:**
```python
def parse_concept_scenes(concept_text: str) -> tuple[str, list[dict]]:
    """
    ---SCENE_LIST--- 구분자로 분리.
    반환: (플레이스홀더가 포함된 본문, 씬 목록)
    씬 목록 파싱 실패 시 (원본 텍스트, []) 반환.
    """
```

**harness.py 5단계 변경:**
```python
# 컨셉 파싱
clean_concept, scenes = parse_concept_scenes(state.concept)
state.concept = clean_concept  # 본문에서 ---SCENE_LIST--- 이후 제거

# SVG 병렬 생성
svg_tasks = [
    concept_ui_generator.run(
        f"[씬 제목: {s['title']}]\n[씬 설명: {s['desc']}]\n\n[게임 컨셉]\n{state.concept[:500]}"
    )
    for s in scenes
]
svg_results = await asyncio.gather(*svg_tasks, return_exceptions=True)
state.concept_ui_svgs = [
    {"id": s["id"], "title": s["title"], "svg": r.content if not isinstance(r, Exception) else ""}
    for s, r in zip(scenes, svg_results)
]
```

**HtmlExporter._inline_svgs() 신규 메서드:**
- `_markdown_to_html()` 결과에서 `<p>[IMG_SCENE_N]</p>` 패턴 탐색
- 매칭 시 해당 씬의 SVG `<div class="ui-mockup">` 으로 치환
- 매칭되지 않는 씬은 문서 끝에 추가 (누락 방지)

**PipelineState 변경:**
```python
# 제거
concept_ui_svg: str | None = None

# 추가
concept_ui_svgs: list[dict] = field(default_factory=list)
# 형태: [{"id": 1, "title": "...", "svg": "<svg>...</svg>"}, ...]
```

**HTML 템플릿 변경:**
- `concept_sections["2"]` 뒤의 `concept_ui_svg` 블록 제거
- SVG 치환은 HtmlExporter에서 처리된 `concept_html` 변수로 전달

---

## 데이터 흐름 요약

```
ConceptWriter
  └─ 본문에 [IMG_SCENE_N] 삽입 + ---SCENE_LIST--- JSON 첨부
       │
parse_concept_scenes()
  └─ clean_concept (본문만) + scenes list 분리
       │
asyncio.gather(*[ConceptUiGenerator(scene) for scene in scenes])
  └─ state.concept_ui_svgs = [{"id", "title", "svg"}, ...]
       │
HtmlExporter._inline_svgs(concept_html, svgs)
  └─ [IMG_SCENE_N] → <div class="ui-mockup"><svg>...</svg></div>
```

---

## 하위 호환 및 에러 처리

- `---SCENE_LIST---` 파싱 실패 시: `concept_ui_svgs = []`, 이미지 없이 진행
- `[IMG_SCENE_N]` 플레이스홀더가 본문에 없으면: 해당 SVG를 문서 맨 끝에 추가
- SVG 생성 Exception: 해당 씬은 빈 문자열로 처리, 나머지는 정상 삽입
- `concept_ui_svg` (구 필드): `harness.py`와 템플릿에서 참조 제거
