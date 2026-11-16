"""把工程渲染成「给模型看的设定摘要」。

两条设计原则：

1. **省 token 但信息密度高**。长对话里每轮都塞一大段设定会迅速吃满上下文，
   所以 :func:`context_pack` 是可裁剪的（可选角色、可选事件条数）。
2. **边界与年龄必须是显式文本**，不藏在备注里。这样任何模型读到的第一屏
   就包含「这些是成年人」「这些方向不写」，而不是靠它猜。
"""

from __future__ import annotations

from .core import Character, Event, Project, Relationship

__all__ = ["context_pack", "character_card", "full_bible"]


_INTIMACY_LABEL = {
    0: "尚未亲近",
    1: "初次心动",
    2: "明显暧昧",
    3: "亲密关系",
    4: "深度亲密",
    5: "长期伴侣",
}


def _bullets(items: list[str], *, empty: str = "（未设定）") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def character_card(character: Character, *, verbose: bool = False) -> str:
    """单个角色卡。第一行就标明成年状态。"""
    lines: list[str] = []
    head = f"### {character.name}"
    if character.pronouns:
        head += f"（{character.pronouns}）"
    lines.append(head)
    lines.append(f"- 年龄：{character.age}（成年人）")
    if character.role:
        lines.append(f"- 关系定位：{character.role}")
    if character.appearance:
        lines.append(f"- 外形：{character.appearance}")
    if character.personality:
        lines.append(f"- 性格：{'、'.join(character.personality)}")
    if character.speech_style:
        lines.append(f"- 说话方式：{character.speech_style}")
    if verbose and character.background:
        lines.append(f"- 背景：{character.background}")
    if character.boundaries:
        lines.append("- **不写的方向**：" + "；".join(character.boundaries))
    if character.preferences:
        lines.append("- 偏好：" + "；".join(character.preferences))
    if verbose and character.notes:
        lines.append(f"- 备注：{character.notes}")
    return "\n".join(lines)


def _relationship_block(relationship: Relationship, project: Project) -> str:
    left = project.maybe_find(relationship.a)
    right = project.maybe_find(relationship.b)
    left_name = left.name if left else relationship.a
    right_name = right.name if right else relationship.b
    lines = [f"### {left_name} ↔ {right_name}"]
    lines.append(f"- 阶段：{relationship.stage}")
    lines.append(
        f"- 亲密度：{relationship.intimacy}/{5}"
        f"（{_INTIMACY_LABEL.get(relationship.intimacy, '未定义')}）"
    )
    if relationship.dynamic:
        lines.append(f"- 相处模式：{relationship.dynamic}")
    if relationship.history:
        lines.append("- 已发生：" + "；".join(relationship.history))
    if relationship.tensions:
        lines.append("- **未解决的张力**：" + "；".join(relationship.tensions))
    return "\n".join(lines)


def _event_line(event: Event, project: Project) -> str:
    names = []
    for participant in event.participants:
        found = project.maybe_find(participant)
        names.append(found.name if found else participant)
    who = "、".join(names) if names else "—"
    text = f"{event.seq}. **{event.title}**（{who}）：{event.summary}"
    if event.consequences:
        text += f" → 后果：{event.consequences}"
    return text


def context_pack(
    project: Project,
    *,
    focus: list[str] | None = None,
    recent: int = 8,
    verbose: bool = False,
) -> str:
    """生成可以直接贴进任意模型的「设定摘要」。

    ``focus`` 给角色 id/名字时只输出这几个角色及其相互关系，适合单场景对话；
    留空则输出全部角色。
    """
    selected: list[Character]
    if focus:
        selected = [project.find(item) for item in focus]
    else:
        selected = list(project.characters)

    selected_ids = {item.id for item in selected}
    blocks: list[str] = []

    title = project.title
    blocks.append(f"# 设定摘要 · {title}")
    adults = ", ".join(f"{item.name}({item.age}岁)" for item in selected)
    blocks.append(
        "> 本作为成年人的虚构创作。涉及角色均为成年人："
        + (adults or "（未指定）")
        + "。所有互动均为双方自愿的虚构情节。"
    )

    if project.premise:
        blocks.append(f"**前提**：{project.premise}")
    if project.setting:
        blocks.append(f"**场景设定**：{project.setting}")
    if project.tone or project.pov:
        style = []
        if project.pov:
            style.append(f"视角：{project.pov}")
        if project.tone:
            style.append(f"语气：{project.tone}")
        blocks.append(f"**叙事约定**：{'；'.join(style)}")

    blocks.append("## 角色")
    for character in selected:
        blocks.append(character_card(character, verbose=verbose))

    related = [
        item
        for item in project.relationships
        if item.a in selected_ids and item.b in selected_ids
    ]
    if related:
        blocks.append("## 关系现状")
        for relationship in related:
            blocks.append(_relationship_block(relationship, project))

    events = project.recent_events(recent, participants=list(selected_ids)) if recent else []
    if events:
        blocks.append(f"## 最近剧情（最近 {len(events)} 条）")
        for event in events:
            blocks.append(_event_line(event, project))

    boundaries = sorted({b for item in selected for b in item.boundaries})
    if boundaries:
        blocks.append("## 共同边界")
        blocks.append(_bullets(boundaries))

    blocks.append("## 写作要求")
    blocks.append("- 保持角色语气与称呼一致，不要跳出设定解释自己。")
    blocks.append("- 关系推进要基于「最近剧情」，不要凭空跳跃阶段。")
    blocks.append("- 遇到未设定的细节，优先沿用已有设定，或明确询问而不是自造。")

    return "\n\n".join(blocks)


def full_bible(project: Project) -> str:
    """完整人物/剧情圣经（用于存档、换模型时迁移上下文）。"""
    return context_pack(project, focus=None, recent=10_000, verbose=True)
