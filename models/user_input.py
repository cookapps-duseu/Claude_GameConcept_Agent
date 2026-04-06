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
    core_loop: str | None = None
    key_elements: list[str] = field(default_factory=list)
    must_have_elements: list[str] = field(default_factory=list)

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
        if self.core_loop:
            lines.append(f"코어 루프: {self.core_loop}")
        if self.key_elements:
            lines.append(f"핵심 요소: {', '.join(self.key_elements)}")
        if self.must_have_elements:
            lines.append(f"필수 인게임 요소: {', '.join(self.must_have_elements)}")
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
            "core_loop": self.core_loop,
            "key_elements": self.key_elements,
            "must_have_elements": self.must_have_elements,
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
            core_loop=data.get("core_loop"),
            key_elements=data.get("key_elements", []),
            must_have_elements=data.get("must_have_elements", []),
        )
