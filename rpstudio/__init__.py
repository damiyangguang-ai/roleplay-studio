"""RoleplayStudio：成年角色虚构创作的设定工程工具。

只做创作工程（角色卡 / 关系状态 / 剧情连续性），不生成正文、不调用模型 API、
不触碰任何内容过滤。
"""

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
from .render import character_card, context_pack, full_bible

__all__ = [
    "ADULT_AGE",
    "Character",
    "Event",
    "Project",
    "Relationship",
    "Store",
    "StudioError",
    "validate",
    "character_card",
    "context_pack",
    "full_bible",
]

__version__ = "0.1.0"
