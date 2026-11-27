"""Rotate the session log: keep the newest entries in docs/pipeline/session_log.md, move the rest to
docs/pipeline/session_log_archive.md (newest first, nothing deleted).

Why: every session reads the latest entry; a log that only grows costs more tokens each time it is opened.
The archive is for people and for a session that needs old detail.

  python3 tools/kit/rotate_session_log.py            # keep 3 entries (default)
  python3 tools/kit/rotate_session_log.py --keep 5
  python3 tools/kit/rotate_session_log.py --dry-run  # say what would move

Managed by the project kit (tools/kit/kit.py update).
"""
import argparse
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG = os.path.join(ROOT, "docs", "pipeline", "session_log.md")
ARCHIVE = os.path.join(ROOT, "docs", "pipeline", "session_log_archive.md")
ARCHIVE_HEAD = ("# Session log archive\n\nPart of the [repository map](../../README.md).\n\n"
                "Older entries of [session_log.md](session_log.md), newest first, moved by "
                "`tools/kit/rotate_session_log.py`. Read only when old detail is needed.\n\n")


def split_entries(text):
    """Header (everything before the first '## ' entry) and the list of entries, each starting with '## '."""
    parts = re.split(r"(?m)^(?=## )", text)
    return parts[0], [p if p.endswith("\n") else p + "\n" for p in parts[1:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    head, entries = split_entries(open(LOG, encoding="utf-8").read())
    keep, move = entries[:args.keep], entries[args.keep:]
    if not move:
        print(f"Session log: {len(entries)} entries, nothing to rotate (keep {args.keep}).")
        return
    print(f"Session log: {len(entries)} entries; {len(move)} move to session_log_archive.md.")
    if args.dry_run:
        return
    old_head, old = split_entries(open(ARCHIVE, encoding="utf-8").read()) if os.path.exists(ARCHIVE) else (ARCHIVE_HEAD, [])
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        f.write(old_head + "".join(move + old))
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(head + "".join(keep))


if __name__ == "__main__":
    main()
