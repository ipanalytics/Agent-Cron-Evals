"""Just enough cron arithmetic to know whether *now* is inside the job's window.

Without this, every job that runs 06:00-22:00 looks broken at 03:00, and the eval that is
supposed to find real failures turns into noise nobody reads.
"""

from __future__ import annotations

DAY_NAMES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def hours_in_window(expr: str, hour: int) -> bool:
    """True when ``hour`` falls inside the hours field of a 5-field cron expression.

    Handles ``*``, ``X-Y``, ``X,Y,Z``, ``*/N`` and a plain number. Anything it cannot read
    counts as "in window": a false alarm is worse than a missed nag.
    """
    fields = (expr or "").split()
    if len(fields) < 2:
        return True
    spec = fields[1]
    if spec in ("*", "?"):
        return True
    if spec.startswith("*/"):
        try:
            step = int(spec[2:])
        except ValueError:
            return True
        return step > 0 and hour % step == 0
    if "-" in spec and "," not in spec:
        try:
            low, high = (int(part) for part in spec.split("-", 1))
        except ValueError:
            return True
        return low <= hour <= high
    if "," in spec:
        try:
            return hour in {int(part) for part in spec.split(",")}
        except ValueError:
            return True
    try:
        return hour == int(spec)
    except ValueError:
        return True


def weekday_allowed(days, weekday: int) -> bool:
    """``days`` holds Python weekday numbers (Monday=0 … Sunday=6; 7 means Sunday) or short
    names ("mon", "sun"). An empty list means every day."""
    if not days:
        return True
    wanted = set()
    for item in days:
        if isinstance(item, int):
            wanted.add(6 if item == 7 else item)  # Python weekday numbers; 7 is Sunday
            continue
        key = str(item).strip().lower()[:3]
        if key in DAY_NAMES:
            wanted.add(DAY_NAMES[key])
    if not wanted:
        return True
    return weekday in wanted
