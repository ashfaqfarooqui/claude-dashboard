#!/usr/bin/env python3
"""Report Claude usage-limit headroom for campaign:run's usage gate.

Reads the snapshot the status line writes to ~/.cache/claude-usage.json (the status line is the
only place Claude Code exposes rate_limits). Prints one line and exits with:

  0  go       — 5-hour usage below the caution level, 7-day below its limit
  1  caution  — 5-hour usage within 20 points of --max: dispatch only haiku/sonnet issues
  2  stop     — 5-hour usage at or over --max, or 7-day at or over --max-week
  3  unknown  — no snapshot, or older than --stale minutes: ask the user

Usage: usage.py [--max 80] [--max-week 95] [--stale 15]
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Points below --max where Opus issues wait. A guess, not a measurement: an Opus issue costs
# several times a Sonnet one, so leave it room to finish. Tune it if runs still overshoot.
CAUTION_MARGIN = 20


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=float, default=80, help="5-hour %% at which dispatching stops")
    ap.add_argument("--max-week", type=float, default=95, help="7-day %% at which dispatching stops")
    ap.add_argument("--stale", type=float, default=15, help="minutes after which the snapshot is unknown")
    args = ap.parse_args()

    path = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "claude-usage.json"
    try:
        snap = json.loads(path.read_text())
    except (OSError, ValueError):
        print(f"unknown: no usage snapshot at {path} (the status line writes it on Pro/Max plans)")
        return 3
    age_min = (time.time() - snap.get("at", 0)) / 60
    limits = snap.get("rate_limits") or {}

    def window(name: str) -> tuple[float | None, str]:
        w = limits.get(name) or {}
        pct, reset = w.get("used_percentage"), w.get("resets_at")
        if pct is None:
            return None, f"{name}: n/a"
        when = datetime.fromtimestamp(reset).strftime("%a %H:%M") if reset else "?"
        if reset and reset < time.time():  # window rolled over since the snapshot
            return 0.0, f"{name}: reset at {when}"
        return float(pct), f"{name}: {pct:.0f}% (resets {when})"

    five, five_s = window("five_hour")
    week, week_s = window("seven_day")
    line = f"{five_s} · {week_s} · snapshot {age_min:.0f} min old"

    if age_min > args.stale or five is None:
        print(f"unknown: {line}")
        return 3
    if five >= args.max or (week is not None and week >= args.max_week):
        print(f"stop: {line}")
        return 2
    if five >= args.max - CAUTION_MARGIN:
        print(f"caution: {line}")
        return 1
    print(f"go: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
