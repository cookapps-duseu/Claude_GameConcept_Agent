import pytest
from models.user_input import UserInput


def test_user_input_required_field():
    u = UserInput(genre="로그라이크 RPG")
    assert u.genre == "로그라이크 RPG"
    assert u.platform is None
    assert u.target_user is None
    assert u.keywords == []
    assert u.free_text is None


def test_user_input_full():
    u = UserInput(
        genre="로그라이크 RPG",
        platform="모바일",
        target_user="캐주얼 게이머",
        keywords=["짧은 플레이", "성장"],
        free_text="10분 단위 플레이 가능해야 함",
    )
    assert u.platform == "모바일"
    assert u.keywords == ["짧은 플레이", "성장"]


def test_user_input_to_prompt():
    u = UserInput(genre="퍼즐", platform="PC", keywords=["협동"])
    prompt = u.to_prompt()
    assert "퍼즐" in prompt
    assert "PC" in prompt
    assert "협동" in prompt


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
