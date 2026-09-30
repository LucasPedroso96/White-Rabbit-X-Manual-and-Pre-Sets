"""Janelas Walk-Forward do EA (OnInit com AtivarWFO): ciclos In-Sample / Out-of-Sample consecutivos."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from .setfile import InvalidConfig

CUSTOM = -1


@dataclass
class WfoPlan:
    is_start: list = field(default_factory=list)
    is_end: list = field(default_factory=list)
    oos_start: list = field(default_factory=list)
    oos_end: list = field(default_factory=list)

    def in_sample(self, t: int) -> bool:
        return any(a <= t <= b for a, b in zip(self.is_start, self.is_end))

    def cycle_of(self, t: int):
        """WfoCycleOf(): (ciclo, em_IS) ou (-1, False)."""
        for i, (a, b, c, d) in enumerate(zip(self.is_start, self.is_end, self.oos_start, self.oos_end)):
            if a <= t <= b:
                return i, True
            if c <= t <= d:
                return i, False
        return -1, False


def parse_end(end: str) -> int:
    """StringToTime(input_end_date + ' 23:55')."""
    d = _dt.datetime.strptime(end.strip() + " 23:55", "%Y.%m.%d %H:%M")
    return int(d.replace(tzinfo=_dt.timezone.utc).timestamp())


def build_plan(v: dict, start: int) -> WfoPlan:
    end = parse_end(v["input_end_date"])
    if end <= start:
        raise InvalidConfig("WFO: a data final precisa ser depois do inicio do teste")
    total_days = int((end - start) // 86400) + 1
    win = v["wfo_windowSize"]
    is_days = v["wfo_customWindowSizeDays"] if (win == CUSTOM and v["wfo_customWindowSizeDays"] > 0) else win
    step = v["wfo_stepSize"]
    pct = v["wfo_customStepSizePercent"]
    if step == CUSTOM and pct != 0:
        oos_days = int(pct / 100.0 * is_days) if pct > 0 else -pct
    else:
        oos_days = step
    if is_days + oos_days > total_days or is_days <= 0 or oos_days <= 0:
        raise InvalidConfig("WFO: janelas IS/OOS invalidas (o EA recusa no OnInit)")
    plan = WfoPlan()
    cur = start
    while cur < end:
        is_s = cur
        is_e = min(is_s + is_days * 86400 - 1, end)
        oos_s = is_e + 1
        oos_e = min(oos_s + oos_days * 86400 - 1, end)
        plan.is_start.append(is_s)
        plan.is_end.append(is_e)
        plan.oos_start.append(oos_s)
        plan.oos_end.append(oos_e)
        if oos_e == end:
            break
        cur = oos_e + 1
        if cur >= end:
            break
    return plan
