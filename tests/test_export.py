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
