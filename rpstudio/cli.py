"""命令行入口：``python -m rpstudio <子命令>``。

刻意做成零依赖、纯 argparse——这个工具要在任何装了 Python 的机器上直接跑，
不该因为装不上库而用不了。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import (
    ADULT_AGE,
    Character,
    Event,
    Project,
    Relationship,
    Store,
    StudioError,
    validate,
)
from .render import context_pack, full_bible

DEFAULT_FILE = "studio.json"


# --------------------------------------------------------------------------- 工具


def _slug(name: str) -> str:
    text = name.strip().lower()
    for ch in (" ", "\t", "/", "\\"):
        text = text.replace(ch, "-")
    return text or "character"


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("、", ",").split(",") if item.strip()]


def _store(args: argparse.Namespace) -> Store:
    return Store(Path(args.file))


def _load(args: argparse.Namespace) -> Project:
    return _store(args).load()


def _save(args: argparse.Namespace, project: Project) -> None:
    _store(args).save(project)


def _print_problems(problems: list[str]) -> int:
    if not problems:
        print("✔ 校验通过")
        return 0
    print(f"✘ 发现 {len(problems)} 个问题：")
    for item in problems:
        print(f"  · {item}")
    return 1


# --------------------------------------------------------------------------- 子命令


def cmd_init(args: argparse.Namespace) -> int:
    store = Store(Path(args.file))
    if store.exists() and not args.force:
        print(f"工程已存在：{store.path}（要覆盖请加 --force）")
        return 1
    project = Project(title=args.title, premise=args.premise, setting=args.setting)
    store.save(project)
    print(f"✔ 已创建工程：{store.path}")
    print("下一步：")
    print("  python -m rpstudio character add 林夏 --age 28 --role 对方")
    print("  或直接看示例： python -m rpstudio demo --file demo.json")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """建一个立即可用的示例：两个明确为成年人的虚构角色。"""
    project = Project(
        title="示例工程 · 雨夜书店",
        premise="两个成年人在同一家旧书店反复偶遇，从陌生到暧昧，再到确定关系。",
        setting="南方城市的旧书店，雨天，晚上九点后客人很少。",
        tone="克制、留白，多用动作与环境暗示情绪，不直白解释心理",
        pov="第二人称（“你”＝读者代入的一方）",
    )
    a = Character(
        id="linxia",
        name="林夏",
        age=29,
        pronouns="她",
        role="书店常客，对方",
        appearance="短发，常穿深灰针织衫，左手腕戴旧表",
        background="做古籍修复，作息颠倒，话不多但观察力强",
        personality=["冷静", "话少", "偶尔突然直白", "不擅长主动"],
        speech_style="短句，少用语气词；紧张时会重复对方的话尾",
        boundaries=["不写任何非自愿情节"],
        preferences=["偏爱慢节奏、靠细节推进的暧昧", "喜欢在对话里留缺口"],
        notes="对雨声和旧纸味有明确偏好，可作为固定意象。",
    )
    b = Character(
        id="zhouyan",
        name="周砚",
        age=32,
        pronouns="他",
        role="书店店主",
        appearance="高个，衬衫袖子常卷到手肘，指节有旧伤",
        background="原本做建筑设计，三年前盘下这家店",
        personality=["温和", "习惯照顾人", "边界感强", "被戳中时会沉默"],
        speech_style="语速慢，喜欢用问句回应；答应事情时会重复一遍",
        boundaries=["不写任何非自愿情节"],
        preferences=["喜欢用日常动作（递伞、留灯）表达在意"],
        notes="店里的猫叫“阿七”，是他留下的唯一旧物。",
    )
    project.add_character(a)
    project.add_character(b)
    project.set_relationship(
        Relationship(
            a=a.id,
            b=b.id,
            stage="暧昧",
            intimacy=2,
            dynamic="他更主动照顾，她更主动试探；谁都不肯先说破",
            history=["第一次偶遇：她躲雨进店，他递了条干毛巾", "第二次：她留下一本修坏的旧书"],
            tensions=["她下个月可能要去外地半年", "他从没问过她为什么总在雨夜来"],
        )
    )
    project.add_event(
        Event(
            seq=0,
            title="雨夜递毛巾",
            participants=[a.id, b.id],
            summary="她躲雨进店，头发在滴水，他从柜台后递出一条干毛巾，没多说话。",
            tags=["初遇", "雨"],
            consequences="她记住了他收毛巾时避开视线的习惯。",
        )
    )
    project.add_event(
        Event(
            seq=0,
            title="留下的旧书",
            participants=[a.id, b.id],
            summary="她把一本修坏的书留在柜台，说“修不好也没关系”，转身就走。",
            tags=["试探"],
            consequences="他在扉页发现她写的一行小字，开始留意她的到店时间。",
        )
    )
    store = Store(Path(args.file))
    store.save(project)
    print(f"✔ 示例工程已创建：{store.path}")
    print("看看摘要：")
    print(f"  python -m rpstudio context --file {args.file} --characters 林夏,周砚")
    return 0


def cmd_character(args: argparse.Namespace) -> int:
    project = _load(args)
    if args.action == "add":
        character = Character(
            id=_slug(args.name),
            name=args.name,
            age=args.age,
            pronouns=args.pronouns or "",
            role=args.role or "",
            appearance=args.appearance or "",
            background=args.background or "",
            personality=_csv(args.personality),
            speech_style=args.speech or "",
            boundaries=_csv(args.boundaries),
            preferences=_csv(args.preferences),
            notes=args.notes or "",
        )
        project.add_character(character)
        _save(args, project)
        print(f"✔ 已加入角色：{character.name}（{character.age} 岁，id={character.id}）")
        return 0

    if args.action == "list":
        if not project.characters:
            print("还没有角色。")
            return 0
        print(f"{'id':<14}{'名字':<10}{'年龄':<6}{'定位'}")
        for item in project.characters:
            print(f"{item.id:<14}{item.name:<10}{item.age:<6}{item.role or '—'}")
        return 0

    if args.action == "show":
        character = project.find(args.name)
        from .render import character_card

        print(character_card(character, verbose=True))
        return 0

    raise SystemExit(f"未知 action：{args.action}")


def cmd_relationship(args: argparse.Namespace) -> int:
    project = _load(args)
    left = project.find(args.a)
    right = project.find(args.b)
    existing = project.relationship_of(left.id, right.id)
    relationship = existing or Relationship(a=left.id, b=right.id)
    if args.stage is not None:
        relationship.stage = args.stage
    if args.intimacy is not None:
        relationship.intimacy = args.intimacy
    if args.dynamic is not None:
        relationship.dynamic = args.dynamic
    if args.history:
        relationship.history.extend(_csv(args.history))
    if args.tensions:
        relationship.tensions.extend(_csv(args.tensions))
    project.set_relationship(relationship)
    _save(args, project)
    print(
        f"✔ {left.name} ↔ {right.name}：阶段={relationship.stage}，"
        f"亲密度={relationship.intimacy}/5"
    )
    return 0


def cmd_event(args: argparse.Namespace) -> int:
    project = _load(args)
    event = Event(
        seq=0,
        title=args.title,
        participants=[project.find(item).id for item in _csv(args.participants)],
        summary=args.summary or "",
        tags=_csv(args.tags),
        consequences=args.consequences or "",
    )
    project.add_event(event)
    _save(args, project)
    print(f"✔ 已记录事件 #{event.seq}：{event.title}")
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    project = _load(args)
    focus = _csv(args.characters) or None
    text = context_pack(project, focus=focus, recent=args.recent, verbose=args.verbose)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"✔ 已写入 {args.out}（{len(text)} 字符）")
    else:
        print(text)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    return _print_problems(validate(_load(args)))


def cmd_bible(args: argparse.Namespace) -> int:
    project = _load(args)
    text = full_bible(project)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"✔ 已写入 {args.out}（{len(text)} 字符）")
    else:
        print(text)
    return 0


# --------------------------------------------------------------------------- 解析


def build_parser() -> argparse.ArgumentParser:
    # --file 既允许写在子命令前（全局），也允许写在子命令后。
    # 共享父解析器用 SUPPRESS 作默认值，避免「子命令没写 --file」时
    # 用它自己的默认值把全局值覆盖掉。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--file",
        "-f",
        default=argparse.SUPPRESS,
        help=f"工程文件路径（默认 {DEFAULT_FILE}）",
    )

    parser = argparse.ArgumentParser(
        prog="rpstudio",
        parents=[common],
        description="成年角色虚构创作的设定工程：角色卡 / 关系状态 / 剧情连续性",
    )
    parser.set_defaults(file=DEFAULT_FILE)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", parents=[common], help="新建空工程")
    init.add_argument("--title", default="未命名工程")
    init.add_argument("--premise", default="")
    init.add_argument("--setting", default="")
    init.add_argument("--force", action="store_true", help="覆盖已存在的工程")
    init.set_defaults(func=cmd_init)

    demo = sub.add_parser("demo", parents=[common], help="创建含两个成年角色的示例工程")
    demo.set_defaults(func=cmd_demo)

    character = sub.add_parser("character", parents=[common], help="角色管理")
    char_sub = character.add_subparsers(dest="action", required=True)
    add = char_sub.add_parser("add", parents=[common], help="新增角色")
    add.add_argument("name")
    add.add_argument("--age", type=int, required=True, help=f"必须 >= {ADULT_AGE}")
    add.add_argument("--pronouns")
    add.add_argument("--role")
    add.add_argument("--appearance")
    add.add_argument("--background")
    add.add_argument("--personality", help="逗号分隔")
    add.add_argument("--speech")
    add.add_argument("--boundaries", help="逗号分隔：不写的方向")
    add.add_argument("--preferences", help="逗号分隔：偏好的互动方式")
    add.add_argument("--notes")
    add.set_defaults(func=cmd_character)
    char_sub.add_parser("list", parents=[common], help="列出角色").set_defaults(func=cmd_character)
    show = char_sub.add_parser("show", parents=[common], help="查看角色卡")
    show.add_argument("name")
    show.set_defaults(func=cmd_character)

    relationship = sub.add_parser("relationship", parents=[common], help="设置两人关系现状")
    relationship.add_argument("a")
    relationship.add_argument("b")
    relationship.add_argument("--stage")
    relationship.add_argument("--intimacy", type=int, choices=range(0, 6))
    relationship.add_argument("--dynamic")
    relationship.add_argument("--history", help="逗号分隔，追加")
    relationship.add_argument("--tensions", help="逗号分隔，追加")
    relationship.set_defaults(func=cmd_relationship)

    event = sub.add_parser("event", parents=[common], help="追加时间线事件")
    event.add_argument("title")
    event.add_argument("--participants", required=True, help="逗号分隔的角色名")
    event.add_argument("--summary")
    event.add_argument("--tags", help="逗号分隔")
    event.add_argument("--consequences")
    event.set_defaults(func=cmd_event)

    context = sub.add_parser("context", parents=[common], help="输出可粘贴的设定摘要")
    context.add_argument("--characters", help="逗号分隔，只输出这几个角色")
    context.add_argument("--recent", type=int, default=8, help="最近 N 条剧情")
    context.add_argument("--verbose", action="store_true")
    context.add_argument("--out")
    context.set_defaults(func=cmd_context)

    sub.add_parser("validate", parents=[common], help="校验工程一致性").set_defaults(
        func=cmd_validate
    )

    bible = sub.add_parser("bible", parents=[common], help="导出完整设定圣经")
    bible.add_argument("--out")
    bible.set_defaults(func=cmd_bible)

    return parser


def _strip_file_option(argv: list[str]) -> tuple[list[str], str | None]:
    """把 ``--file`` / ``-f`` 从任意位置抽出来。

    argparse 的子解析器用独立 namespace，导致「全局 --file 写在子命令前」会被
    子命令的默认值覆盖。与其依赖 argparse 的微妙行为，不如自己统一处理：
    抽出后单独赋值，两种写法都稳定可用。
    """
    rest: list[str] = []
    value: str | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ("--file", "-f"):
            if index + 1 < len(argv):
                value = argv[index + 1]
                index += 2
                continue
            index += 1
            continue
        if token.startswith("--file="):
            value = token.split("=", 1)[1]
            index += 1
            continue
        rest.append(token)
        index += 1
    return rest, value


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    cleaned, file_value = _strip_file_option(raw)
    parser = build_parser()
    args = parser.parse_args(cleaned)
    if file_value:
        args.file = file_value
    try:
        return args.func(args)
    except StudioError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
