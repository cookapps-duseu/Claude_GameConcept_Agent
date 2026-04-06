# Image Integration Design — Game Concept HTML 출력에 이미지 삽입

**날짜**: 2026-04-02  
**상태**: 승인됨  
**기반**: 2026-04-02-pipeline-v2-design.md

---

## 개요

HTML 컨셉안 출력에 두 종류의 시각 자료를 인라인으로 삽입한다:

1. **레퍼런스 게임 이미지** — WebSearch로 각 게임의 공식 스크린샷/커버 URL 검색
2. **컨셉 게임 시각 자료** — Claude가 직접 생성하는 SVG UI 목업 + Mermaid 게임 루프 다이어그램

배치 방식: 각 섹션 **인라인** (섹션 본문 바로 아래)

- `## 2. 핵심 컨셉` 아래 → SVG UI 목업
- `## 4. 핵심 게임 루프` 아래 → Mermaid 다이어그램
- `## 5. 레퍼런스 게임` 아래 → 레퍼런스 이미지 갤러리

Word 출력에는 이미지 미포함 (HTML 전용).

---

## 아키텍처

```
[ConceptSprint 완료]
        ↓
asyncio.gather() 병렬:
  ├── ReferenceImageFetcher.run(reference_games)   → state.reference_images
  ├── ConceptUiGenerator.run(concept + user_input) → state.concept_ui_svg
  └── ConceptDiagramGenerator.run(synthesis)       → state.concept_diagram_mermaid
        ↓
_checkpoint(state, done | {"images"})
        ↓
[HtmlExporter] — 섹션 분리 후 템플릿 렌더링
        ↓
[HTML 출력]
```

---

## 신규/수정 파일

| 종류 | 파일 | 내용 |
|------|------|------|
| 신규 | `agents/reference_image_fetcher.py` | 레퍼런스 게임 이미지 URL 검색 |
| 신규 | `agents/concept_ui_generator.py` | SVG UI 목업 생성 |
| 신규 | `agents/concept_diagram_generator.py` | Mermaid 게임 루프 다이어그램 생성 |
| 수정 | `models/pipeline_state.py` | 이미지 관련 필드 3개 추가 |
| 수정 | `session_manager.py` | 이미지 필드 3개 저장/로드 추가 |
| 수정 | `harness.py` | concept 완료 후 이미지 병렬 생성 단계 추가 |
| 수정 | `agents/html_exporter.py` | 이미지 데이터를 템플릿에 전달, 섹션 분리 로직 |
| 수정 | `templates/concept.html.j2` | 섹션별 인라인 이미지 배치, Mermaid.js CDN 추가 |

---

## 상세 설계

### 1. agents/reference_image_fetcher.py

```python
class ReferenceImageFetcher(BaseAgent):
    ALLOWED_TOOLS = ["WebSearch"]
```

- 입력 프롬프트: 레퍼런스 게임 목록 (쉼표 구분 문자열)
- LLM에게 각 게임의 공식 스크린샷 또는 Steam/공식 사이트의 커버 이미지 URL 검색 지시
- 반환 형식: JSON `[{"game": "게임명", "url": "https://..."}]`
- URL을 찾지 못한 게임은 목록에서 제외
- JSON 파싱 실패 시 빈 리스트 반환 (파이프라인 중단 없음)

### 2. agents/concept_ui_generator.py

```python
class ConceptUiGenerator(BaseAgent):
    ALLOWED_TOOLS = []
```

- 입력 프롬프트: 컨셉안 텍스트 + 장르 정보
- LLM이 장르에 맞는 게임 화면 UI 목업을 SVG로 생성
  - RPG: 체력바, 스킬창, 미니맵 레이아웃
  - 퍼즐: 게임판, 점수판
  - 액션: HUD, 체력/스태미나 바
- 반환: `<svg>...</svg>` 문자열 (viewBox 포함)
- SVG 생성 실패 시 빈 문자열 반환

### 3. agents/concept_diagram_generator.py

```python
class ConceptDiagramGenerator(BaseAgent):
    ALLOWED_TOOLS = []
```

- 입력 프롬프트: synthesis 분석 요약
- LLM이 코어/세션/장기 루프 3단계를 Mermaid flowchart로 생성
- 반환: `flowchart TD\n...` 형식의 Mermaid 코드 문자열 (코드 블록 마커 제외)
- 생성 실패 시 빈 문자열 반환

### 4. models/pipeline_state.py 추가 필드

```python
reference_images: list[dict] = field(default_factory=list)
# [{"game": "게임명", "url": "https://..."}]

concept_ui_svg: str | None = None
# <svg>...</svg> 문자열

concept_diagram_mermaid: str | None = None
# Mermaid flowchart 코드 문자열
```

### 5. harness.py 수정

concept Sprint 완료 후, html export 전에 이미지 생성 단계 추가:

```python
# 5. 이미지 생성 (HTML 출력 시에만)
if "images" not in done and self.output_format in ("html", "both"):
    image_results = await asyncio.gather(
        self.reference_image_fetcher.run(...),
        self.concept_ui_generator.run(...),
        self.concept_diagram_generator.run(...),
        return_exceptions=True,
    )
    # 예외 발생한 에이전트는 빈 결과로 처리
    state.reference_images = _parse_reference_images(image_results[0])
    state.concept_ui_svg = _safe_content(image_results[1])
    state.concept_diagram_mermaid = _safe_content(image_results[2])
    done |= {"images"}
    self._checkpoint(state, done)
```

`GameConceptHarness.__init__`에 3개 에이전트 파라미터 추가:
- `reference_image_fetcher: BaseAgent | None = None`
- `concept_ui_generator: BaseAgent | None = None`
- `concept_diagram_generator: BaseAgent | None = None`

None이면 이미지 단계 전체 skip.

`_parse_reference_images(result)`: `harness.py` 모듈 레벨 private 함수. AgentResult 또는 Exception을 받아 JSON 파싱 후 리스트 반환. 실패 시 `[]`.  
`_safe_content(result)`: `harness.py` 모듈 레벨 private 함수. AgentResult 또는 Exception을 받아 content 반환. 실패 시 `""`.

### 6. agents/html_exporter.py 수정

`export()` 메서드에서 `concept_html`을 h2 섹션 기준으로 분리:

```python
def _split_concept_sections(self, concept_html: str) -> dict[str, str]:
    """h2 태그 기준으로 섹션 분리. 키: "1", "2", "3", "4", "5", "6" """
```

섹션 번호(1~6)를 키로 갖는 딕셔너리를 템플릿에 전달. 섹션 분리 실패 시 `{"all": concept_html}`로 fallback — 템플릿이 이 경우 전체를 한 번에 렌더링.

템플릿에 추가 전달:
- `concept_sections`: 섹션 딕셔너리
- `reference_images`: `state.reference_images`
- `concept_ui_svg`: `state.concept_ui_svg`
- `concept_diagram_mermaid`: `state.concept_diagram_mermaid`

### 7. templates/concept.html.j2 수정

- Mermaid.js CDN 스크립트 태그 추가 (`<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js">`)
- 섹션별 인라인 배치:

```
섹션 1 (게임 개요)
섹션 2 (핵심 컨셉)
  └── {% if concept_ui_svg %} <div class="ui-mockup">{{ concept_ui_svg | safe }}</div> {% endif %}
섹션 3 (핵심 재미 요소)
섹션 4 (핵심 게임 루프)
  └── {% if concept_diagram_mermaid %}
        <div class="mermaid">{{ concept_diagram_mermaid }}</div>
      {% endif %}
섹션 5 (레퍼런스 게임)
  └── {% if reference_images %}
        <div class="reference-gallery">
          {% for img in reference_images %}
            <figure>
              <img src="{{ img.url }}" alt="{{ img.game }}" onerror="this.style.display='none'">
              <figcaption>{{ img.game }}</figcaption>
            </figure>
          {% endfor %}
        </div>
      {% endif %}
섹션 6 (기획 의도)
```

`onerror="this.style.display='none'"` — 이미지 로드 실패 시 자동 숨김.

---

## 에러 처리 전략

| 상황 | 처리 |
|------|------|
| `ReferenceImageFetcher` 예외 | `state.reference_images = []`, 계속 진행 |
| `ConceptUiGenerator` 예외 | `state.concept_ui_svg = ""`, 계속 진행 |
| `ConceptDiagramGenerator` 예외 | `state.concept_diagram_mermaid = ""`, 계속 진행 |
| JSON 파싱 실패 (레퍼런스 이미지) | `[]` 반환 |
| 이미지 URL 로드 실패 (브라우저) | `onerror` JS로 자동 숨김 |
| 섹션 분리 실패 (html_exporter) | `{"all": concept_html}` fallback, 이미지는 하단에 모아서 렌더링 |

이미지 생성 실패는 어떤 경우에도 파이프라인을 중단시키지 않는다. (`asyncio.gather(return_exceptions=True)`)

---

## session_manager 호환성

`PipelineState`에 추가된 3개 필드는 모두 직렬화 가능 (`list[dict]`, `str | None`). `session_manager.py`의 `save()`/`load()` 메서드는 명시적 필드 매핑 방식이므로 3개 필드를 명시적으로 추가해야 한다.

---

## 테스트 전략

- `test_models.py`: 3개 신규 필드 초기값 확인
- `test_harness.py`: 이미지 에이전트 stub으로 `state.reference_images`, `state.concept_ui_svg`, `state.concept_diagram_mermaid` 채워지는지 확인; 에이전트 예외 시 빈 결과로 처리되는지 확인
- `test_session_manager.py`: 신규 필드 저장/로드 확인
- 에이전트 3개는 LLM 호출 포함이므로 통합 테스트 제외, stub 기반 테스트만

---

## 하위 호환성

- Word 출력에는 영향 없음
- `GameConceptHarness.__init__` 신규 파라미터는 모두 `None` 기본값 → 기존 코드 변경 불필요
- 기존 테스트 전부 통과 유지
