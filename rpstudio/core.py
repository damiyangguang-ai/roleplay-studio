"""角色卡 / 关系状态 / 剧情连续性 的数据核心。

定位：**创作工程**，不是内容生成器，也不是过滤器。
本模块只做三件事：
  1. 把「角色设定」结构化保存，避免人设漂移；
  2. 把「关系状态」变成一个可查询的显式对象（阶段 / 亲密度 / 张力）；
  3. 把「已发生事件」记成时间线，让长剧情不靠模型自己记。

设计约束（刻意为之）：
  * 角色年龄是**必填且必须是成年人**（>= 18）。这不是道德审查，而是你要的
    "明确成年角色"这条验收标准的技术落地——写死在数据层，避免以后模糊。
  * 边界（boundaries）与偏好（preferences）是一等字段，不是备注。
    成熟的虚构创作里，这两项本来就应该先谈清楚。
  * 不生成任何正文，不调用任何模型 API。它只产出"给模型看的设定摘要"。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
ADULT_AGE = 18
INTIMACY_MIN, INTIMACY_MAX = 0, 5


class StudioError(Exception):
    """数据层错误（带可读原因）。"""


# --------------------------------------------------------------------------- 模型


@dataclass
class Character:
    """一个虚构角色。``age`` 必须是成年人。"""

    id: str
    name: str
    age: int
    pronouns: str = ""
    role: str = ""          # 在故事里的位置，如「对方」「前任」
    appearance: str = ""
    background: str = ""
    personality: list[str] = field(default_factory=list)
    speech_style: str = ""  # 语气、口癖、称呼方式
    boundaries: list[str] = field(default_factory=list)   # 明确不写的方向
    preferences: list[str] = field(default_factory=list)  # 偏好的互动方式
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "pronouns": self.pronouns,
            "role": self.role,
            "appearance": self.appearance,
            "background": self.background,
            "personality": list(self.personality),
            "speech_style": self.speech_style,
            "boundaries": list(self.boundaries),
            "preferences": list(self.preferences),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            age=int(data["age"]),
            pronouns=str(data.get("pronouns", "")),
            role=str(data.get("role", "")),
            appearance=str(data.get("appearance", "")),
            background=str(data.get("background", "")),
            personality=[str(item) for item in data.get("personality") or []],
            speech_style=str(data.get("speech_style", "")),
            boundaries=[str(item) for item in data.get("boundaries") or []],
            preferences=[str(item) for item in data.get("preferences") or []],
            notes=str(data.get("notes", "")),
        )

    @property
    def is_adult(self) -> bool:
        return self.age >= ADULT_AGE


@dataclass
class Relationship:
    """两人之间的关系现状（可随时间推进而更新）。"""

    a: str
    b: str
    stage: str = "初识"          # 初识 / 暧昧 / 交往 / 同居 / 分手后 …
    intimacy: int = 0            # 0–5，粗粒度标度，不存细节
    dynamic: str = ""            # 权力关系、拉扯方式、谁更主动
    history: list[str] = field(default_factory=list)
    tensions: list[str] = field(default_factory=list)  # 未解决的矛盾

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": self.a,
            "b": self.b,
            "stage": self.stage,
            "intimacy": self.intimacy,
            "dynamic": self.dynamic,
            "history": list(self.history),
            "tensions": list(self.tensions),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relationship":
        return cls(
            a=str(data["a"]),
            b=str(data["b"]),
            stage=str(data.get("stage", "初识")),
            intimacy=int(data.get("intimacy", 0)),
            dynamic=str(data.get("dynamic", "")),
            history=[str(item) for item in data.get("history") or []],
            tensions=[str(item) for item in data.get("tensions") or []],
        )

    @staticmethod
    def key(a: str, b: str) -> tuple[str, str]:
        return tuple(sorted((a, b)))  # type: ignore[return-value]


@dataclass
class Event:
    """时间线上的一个已发生事件。"""

    seq: int
    title: str
    participants: list[str] = field(default_factory=list)
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    consequences: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "title": self.title,
            "participants": list(self.participants),
            "summary": self.summary,
            "tags": list(self.tags),
            "consequences": self.consequences,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            seq=int(data["seq"]),
            title=str(data["title"]),
            participants=[str(item) for item in data.get("participants") or []],
            summary=str(data.get("summary", "")),
            tags=[str(item) for item in data.get("tags") or []],
            consequences=str(data.get("consequences", "")),
        )


# --------------------------------------------------------------------------- 工程


@dataclass
class Project:
    """一个创作工程（一个故事 / 一组角色）。"""

    title: str = "未命名工程"
    premise: str = ""
    setting: str = ""
    tone: str = ""            # 叙事语气，如「克制、留白、第二人称」
    pov: str = ""             # 视角约定
    characters: list[Character] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)

    # -- 查找 ---------------------------------------------------------------
    def find(self, needle: str) -> Character:
        """按 id 或名字（不区分大小写）找角色，找不到就抛错。"""
        text = needle.strip().lower()
        for character in self.characters:
            if character.id.lower() == text or character.name.lower() == text:
                return character
        raise StudioError(f"找不到角色：{needle}")

    def maybe_find(self, needle: str) -> Character | None:
        try:
            return self.find(needle)
        except StudioError:
            return None

    def relationship_of(self, a: str, b: str) -> Relationship | None:
        target = Relationship.key(a, b)
        for relationship in self.relationships:
            if Relationship.key(relationship.a, relationship.b) == target:
                return relationship
        return None

    # -- 变更 ---------------------------------------------------------------
    def add_character(self, character: Character) -> None:
        if not character.is_adult:
            raise StudioError(
                f"角色 {character.name} 的年龄是 {character.age}：本工程只接受成年人角色（>= {ADULT_AGE}）"
            )
        if any(item.id == character.id for item in self.characters):
            raise StudioError(f"角色 id 已存在：{character.id}")
        if any(item.name.lower() == character.name.lower() for item in self.characters):
            raise StudioError(f"角色名字已存在：{character.name}")
        self.characters.append(character)

    def set_relationship(self, relationship: Relationship) -> Relationship:
        for endpoint in (relationship.a, relationship.b):
            if self.maybe_find(endpoint) is None:
                raise StudioError(f"关系引用了不存在的角色：{endpoint}")
        if not (INTIMACY_MIN <= relationship.intimacy <= INTIMACY_MAX):
            raise StudioError(
                f"intimacy 必须在 {INTIMACY_MIN}–{INTIMACY_MAX} 之间，收到 {relationship.intimacy}"
            )
        target = Relationship.key(relationship.a, relationship.b)
        for index, existing in enumerate(self.relationships):
            if Relationship.key(existing.a, existing.b) == target:
                self.relationships[index] = relationship
                return relationship
        self.relationships.append(relationship)
        return relationship

    def add_event(self, event: Event) -> Event:
        for participant in event.participants:
            if self.maybe_find(participant) is None:
                raise StudioError(f"事件引用了不存在的角色：{participant}")
        event.seq = max((item.seq for item in self.events), default=0) + 1
        self.events.append(event)
        return event

    def recent_events(self, limit: int, participants: Iterable[str] | None = None) -> list[Event]:
        wanted = {item.lower() for item in participants or ()}
        pool = self.events
        if wanted:
            pool = [
                event
                for event in pool
                if {p.lower() for p in event.participants} & wanted
            ]
        return sorted(pool, key=lambda item: item.seq)[-limit:] if limit > 0 else []

    # -- 序列化 -------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "title": self.title,
            "premise": self.premise,
            "setting": self.setting,
            "tone": self.tone,
            "pov": self.pov,
            "characters": [item.to_dict() for item in self.characters],
            "relationships": [item.to_dict() for item in self.relationships],
            "events": [item.to_dict() for item in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            title=str(data.get("title", "未命名工程")),
            premise=str(data.get("premise", "")),
            setting=str(data.get("setting", "")),
            tone=str(data.get("tone", "")),
            pov=str(data.get("pov", "")),
            characters=[Character.from_dict(item) for item in data.get("characters") or []],
            relationships=[
                Relationship.from_dict(item) for item in data.get("relationships") or []
            ],
            events=[Event.from_dict(item) for item in data.get("events") or []],
        )


# --------------------------------------------------------------------------- 存取


class Store:
    """单个 JSON 文件的读写（原子替换，避免写坏工程）。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> Project:
        if not self.path.exists():
            raise StudioError(f"工程文件不存在：{self.path}（先运行 init）")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StudioError(f"工程文件不是合法 JSON：{exc}") from exc
        if not isinstance(data, dict):
            raise StudioError("工程文件顶层必须是对象")
        return Project.from_dict(data)

    def save(self, project: Project) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(project.to_dict(), ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(payload + "\n", encoding="utf-8")
        tmp.replace(self.path)


# --------------------------------------------------------------------------- 校验


def validate(project: Project) -> list[str]:
    """返回问题列表；空列表表示通过。"""
    problems: list[str] = []
    ids = [item.id for item in project.characters]
    if len(ids) != len(set(ids)):
        problems.append("存在重复的角色 id")
    names = [item.name.lower() for item in project.characters]
    if len(names) != len(set(names)):
        problems.append("存在重复的角色名字")
    for character in project.characters:
        if not character.is_adult:
            problems.append(f"角色 {character.name} 未成年（{character.age}）")
        if not character.name.strip():
            problems.append(f"角色 {character.id} 没有名字")
    for relationship in project.relationships:
        for endpoint in (relationship.a, relationship.b):
            if project.maybe_find(endpoint) is None:
                problems.append(f"关系引用了不存在的角色：{endpoint}")
        if not (INTIMACY_MIN <= relationship.intimacy <= INTIMACY_MAX):
            problems.append(
                f"关系 {relationship.a}↔{relationship.b} 的 intimacy 越界：{relationship.intimacy}"
            )
    seqs = [event.seq for event in project.events]
    if len(seqs) != len(set(seqs)):
        problems.append("时间线存在重复的 seq")
    for event in project.events:
        for participant in event.participants:
            if project.maybe_find(participant) is None:
                problems.append(f"事件「{event.title}」引用了不存在的角色：{participant}")
    if len(project.characters) == 0:
        problems.append("还没有任何角色")
    return problems
