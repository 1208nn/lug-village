"""Linux 新手村 v3：系统识别 / 命令行猜词 / 发行版盲盒。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LevelDef:
    key: str
    name: str
    subtitle: str
    goal: str
    controls: str
    accent: tuple[int, int, int]


LEVELS = (
    LevelDef(
        "sort",
        "系统识别",
        "把桌面分到正确的系统",
        "看 10 张桌面画面，把它们分进 Linux 或 Windows。选对加分，选错或超时掉 1 条命，3 条命用完失败。",
        "← / → 或 A / D 分拣 · 鼠标点按钮 · Esc 暂停",
        (110, 200, 255),
    ),
    LevelDef(
        "command",
        "命令行猜词",
        "把正确的命令拼出来",
        "看中文任务，把命令块按顺序拼进终端，按 Enter 执行。6 个任务，3 条命，每个任务 12 秒。",
        "方向键选词块 · 空格加入 · Backspace 删除 · Enter 执行",
        (255, 199, 92),
    ),
    LevelDef(
        "box",
        "发行版盲盒",
        "记住 Logo，选中盲盒",
        "每轮会给出一个目标发行版，4 个盲盒短暂打开。盒子关上后，选中刚才出现目标 Logo 的那一个。8 轮，3 条命。",
        "方向键移动 · Enter 开盒 · 鼠标点击 · Esc 暂停",
        (214, 160, 255),
    ),
)


@dataclass
class Outcome:
    key: str
    won: bool
    score: int
    seconds: float
    stats: list[tuple[str, str]] = field(default_factory=list)


class Run:
    def __init__(self) -> None:
        self.index = 0
        self.outcomes: dict[str, Outcome] = {}
        self.started = time.monotonic()

    @property
    def level(self) -> LevelDef:
        return LEVELS[min(self.index, len(LEVELS) - 1)]

    @property
    def total_score(self) -> int:
        return sum(o.score for o in self.outcomes.values())

    @property
    def won_count(self) -> int:
        return sum(1 for o in self.outcomes.values() if o.won)

    @property
    def all_won(self) -> bool:
        return len(self.outcomes) == len(LEVELS) and self.won_count == len(LEVELS)

    @property
    def elapsed(self) -> float:
        return max(0.0, time.monotonic() - self.started)

    def record(self, outcome: Outcome) -> None:
        self.outcomes[outcome.key] = outcome

    def advance(self) -> None:
        self.index = min(len(LEVELS), self.index + 1)

    @property
    def finished(self) -> bool:
        return self.index >= len(LEVELS)
