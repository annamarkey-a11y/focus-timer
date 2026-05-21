#!/usr/bin/env python3
"""Focus Timer — Pomodoro-style work sessions with logging and daily stats."""

import json
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
WORK_MIN = 25
SHORT_BREAK_MIN = 5
LONG_BREAK_MIN = 15
LONG_BREAK_AFTER = 4  # pomodoros before a long break

LOG_FILE = Path(__file__).parent / "sessions.json"

COLORS = {
    "red":    "\033[91m",
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "cyan":   "\033[96m",
    "bold":   "\033[1m",
    "reset":  "\033[0m",
}

def c(text, *styles):
    if not sys.stdout.isatty():
        return text
    prefix = "".join(COLORS[s] for s in styles)
    return f"{prefix}{text}{COLORS['reset']}"


# ── Logging ──────────────────────────────────────────────────────────────────
def load_log():
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            return json.load(f)
    return []

def save_log(sessions):
    with open(LOG_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

def record_session(label, duration_min, session_type="work"):
    sessions = load_log()
    sessions.append({
        "date": date.today().isoformat(),
        "time": datetime.now().strftime("%H:%M"),
        "type": session_type,
        "label": label,
        "minutes": duration_min,
    })
    save_log(sessions)


# ── Timer display ─────────────────────────────────────────────────────────────
def clear_line():
    print("\r" + " " * 60 + "\r", end="", flush=True)

def countdown(minutes, label, color="green"):
    total = minutes * 60
    try:
        for remaining in range(total, -1, -1):
            mins, secs = divmod(remaining, 60)
            bar_filled = int((total - remaining) / total * 20)
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            line = f"  {c(label, 'bold')}  {c(f'{mins:02d}:{secs:02d}', color, 'bold')}  [{bar}]"
            print(f"\r{line}", end="", flush=True)
            if remaining > 0:
                time.sleep(1)
        print()
        return True
    except KeyboardInterrupt:
        print()
        return False  # interrupted


def notify(message):
    print(f"\n  {c('✓', 'bold', 'yellow')} {message}")
    # macOS notification if available
    os.system(f'osascript -e \'display notification "{message}" with title "Focus Timer"\' 2>/dev/null')


# ── Stats ─────────────────────────────────────────────────────────────────────
def show_stats():
    sessions = load_log()
    today = date.today().isoformat()
    today_sessions = [s for s in sessions if s["date"] == today and s["type"] == "work"]

    total_min = sum(s["minutes"] for s in today_sessions)
    pomodoros = len(today_sessions)

    header = c("── Today's focus ──────────────────────", "cyan")
    print(f"\n  {header}")
    if not today_sessions:
        print("  No sessions logged yet today.")
    else:
        print(f"  {c(str(pomodoros), 'bold')} pomodoro{'s' if pomodoros != 1 else ''}  ·  "
              f"{c(str(total_min), 'bold')} minutes total\n")
        for s in today_sessions:
            label_str = f"  {s['time']}  {c(s['label'] or '(no label)', 'yellow')}"
            print(f"  {label_str}  — {s['minutes']} min")
    print()


def show_all_stats():
    sessions = load_log()
    work = [s for s in sessions if s["type"] == "work"]
    if not work:
        print("\n  No sessions logged yet.\n")
        return

    by_date = {}
    for s in work:
        by_date.setdefault(s["date"], []).append(s)

    header = c("── All-time stats ─────────────────────", "cyan")
    print(f"\n  {header}")
    total_min = sum(s["minutes"] for s in work)
    print(f"  {c(str(len(work)), 'bold')} total pomodoros  ·  "
          f"{c(str(total_min), 'bold')} total minutes\n")

    for d in sorted(by_date.keys(), reverse=True)[:7]:
        day_sessions = by_date[d]
        day_min = sum(s["minutes"] for s in day_sessions)
        print(f"  {d}  {len(day_sessions)} sessions  {day_min} min")
    print()


# ── Main flow ─────────────────────────────────────────────────────────────────
def ask(prompt, default=""):
    try:
        val = input(prompt).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)


def run_session(pomodoro_count):
    label = ask(f"\n  {c('What are you working on?', 'bold')} (Enter to skip) › ")
    print()

    print(c("  ── Work session ──────────────────────────", "cyan"))
    completed = countdown(WORK_MIN, "Work", "green")

    if completed:
        record_session(label, WORK_MIN, "work")
        notify(f"Work session done! ({label or 'unlabeled'})")
        pomodoro_count += 1

        if pomodoro_count % LONG_BREAK_AFTER == 0:
            print(c("  ── Long break ────────────────────────────", "cyan"))
            countdown(LONG_BREAK_MIN, "Long break", "yellow")
            notify("Long break over — ready for the next round!")
        else:
            print(c("  ── Short break ───────────────────────────", "cyan"))
            countdown(SHORT_BREAK_MIN, "Short break", "yellow")
            notify("Break over — back to work!")
    else:
        # partial session — ask whether to log it
        elapsed_prompt = ask(f"\n  Session interrupted. Log it? (y/N) › ", "n")
        if elapsed_prompt.lower() == "y":
            partial = ask("  Minutes completed › ", "0")
            try:
                mins = int(partial)
                if mins > 0:
                    record_session(label, mins, "work")
                    print(f"  Logged {mins} min.\n")
            except ValueError:
                pass

    return completed, pomodoro_count


def main():
    print(f"\n  {c('Focus Timer', 'bold', 'cyan')}  ·  {WORK_MIN}m work / {SHORT_BREAK_MIN}m short / {LONG_BREAK_MIN}m long")
    print(f"  {c('Ctrl+C', 'yellow')} interrupts a session  ·  sessions auto-saved to {LOG_FILE.name}\n")

    while True:
        show_stats()
        choice = ask(
            f"  {c('[s]', 'green')}tart  {c('[v]', 'cyan')}iew all  {c('[q]', 'red')}uit  › "
        ).lower()

        if choice in ("q", "quit", "exit"):
            print(f"\n  {c('Goodbye!', 'bold')} Great work today.\n")
            sys.exit(0)
        elif choice in ("v", "view"):
            show_all_stats()
        elif choice in ("s", "start", ""):
            pomodoro_count = 0
            while True:
                _, pomodoro_count = run_session(pomodoro_count)
                again = ask(f"\n  {c('[s]', 'green')}tart another  {c('[m]', 'cyan')}enu  › ").lower()
                if again not in ("s", "start", ""):
                    break
        else:
            print("  Type s, v, or q.\n")


if __name__ == "__main__":
    main()
