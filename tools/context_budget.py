#!/usr/bin/env python3
"""Check token budgets (chars / 4) of always-loaded files, rules and skills."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUDGETS = {"CLAUDE.md": 1800}
RULE_BUDGET, SKILL_BUDGET, ALWAYS_TOTAL = 500, 700, 3000


def tokens(p: Path) -> int:
    return len(p.read_text(encoding="utf-8")) // 4


def main() -> int:
    strict = "--strict" in sys.argv
    errors, always = [], 0
    for name, budget in BUDGETS.items():
        t = tokens(ROOT / name)
        always += t
        print(f"{name}: {t}/{budget}")
        if t > budget:
            errors.append(f"{name} over budget")
    for p in sorted((ROOT / ".claude/rules").glob("*.md")):
        t = tokens(p)
        always += t
        print(f"{p.relative_to(ROOT)}: {t}/{RULE_BUDGET}")
        if t > RULE_BUDGET:
            errors.append(f"{p.name} over budget")
    for p in sorted((ROOT / ".claude/skills").glob("*/SKILL.md")):
        t = tokens(p)
        print(f"{p.relative_to(ROOT)}: {t}/{SKILL_BUDGET}")
        if t > SKILL_BUDGET:
            errors.append(f"{p.parent.name} skill over budget")
    print(f"always-loaded total: {always}/{ALWAYS_TOTAL}")
    if always > ALWAYS_TOTAL:
        errors.append("always-loaded total over budget")
    for e in errors:
        print("ERROR:", e)
    return 1 if (errors and strict) else 0


if __name__ == "__main__":
    sys.exit(main())
