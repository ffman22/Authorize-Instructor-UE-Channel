#!/usr/bin/env python3
"""Project kit: install, update and check the session layout of a Claude Code project.

The kit has three kinds of files:
  managed  kit machinery (hooks, tools/kit/*): updated in place when the local copy was not edited;
           an edited copy is kept and the new version is written beside it as <file>.kit-new.
  seed     project documents (CLAUDE.md, README.md, handoff, decisions...): written once at install
           and never overwritten; a later kit version only adds seed files that are missing.
  blocks   a marked block inside .gitignore and .gitattributes, replaced in place; the rest of the
           file is the project's own. .claude/settings.json gets the kit hooks, the kit marketplace and
           the kit plugins merged in.
  plugins  the mods (session-reset, model-router, task-tracker, kit-agents) are not copied: they are
           plugins of the kit repository's marketplace "project-kit", enabled in .claude/settings.json
           and installed by .claude/hooks/install-mods.mjs; project settings for them live in
           .claude/kit.json (a profile seeds its "sessionReset" block).

What is installed is recorded in .claude/kit.lock.json (kit version and a hash per managed file), so
an update is a patch: only files that changed in the kit are written.

Usage (from the project root):
  python3 tools/kit/kit.py init   --source <kit> --profile <name> [--name "..."] [--chat-language ...]
  python3 tools/kit/kit.py update [--source <kit>] [--dry-run]
  python3 tools/kit/kit.py status [--source <kit>]
  python3 tools/kit/kit.py profiles --source <kit>
  python3 tools/kit/kit.py propose --title "..." [--why "..."] [--source <kit>]

propose writes a proposal file for the kit (docs/pipeline/kit_proposals/<date>-<slug>.md) with the diff
of every managed file this project edited against the kit version, plus the reason. It goes to the kit
repository's proposals/ folder (CONTRIBUTING.md there); once merged into the kit, the next update of
each project receives it without a conflict.

<kit> is a local folder of the kit repository, a git URL (cloned shallow into a temporary folder) or
an https URL of a .zip of it. update and status default to "kitSource" in .claude/kit.json.
Only the Python standard library is used.
"""

import argparse
import datetime
import fnmatch
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

KIT_JSON = ".claude/kit.json"
LOCK = ".claude/kit.lock.json"
PLUGIN = Path("plugins") / "project-kit"
BLOCK_BEGIN = "# >>> project-kit (managed block: tools/kit/kit.py update rewrites it)"
BLOCK_END = "# <<< project-kit"
BLOCK_FILES = {"gitignore": ".gitignore", "gitattributes": ".gitattributes"}
TEXT_SUFFIXES = {".md", ".json", ".mjs", ".js", ".ts", ".py", ".sh", ".ps1", ".bat", ".txt", ".yml", ".yaml", ""}


# ---------- kit source ----------

def fetch_source(source, tmp):
    """Return the kit root folder for a local path, a git URL or a zip URL."""
    p = Path(source).expanduser()
    if p.exists():
        root = p.resolve()
    elif source.endswith(".zip") and source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=60) as r:
            data = r.read()
        zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        inner = [d for d in Path(tmp).iterdir() if d.is_dir()]
        root = inner[0] if len(inner) == 1 else Path(tmp)
    else:
        dest = Path(tmp) / "kit"
        subprocess.run(["git", "clone", "-q", "--depth", "1", source, str(dest)], check=True)
        root = dest
    # Accept the kit root or the plugin folder itself.
    if (root / PLUGIN / "templates").is_dir():
        return root / PLUGIN
    if (root / "templates").is_dir():
        return root
    sys.exit(f"kit: no templates/ folder found in {source}")


def kit_version(plugin_dir):
    try:
        return json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "0.0.0"


def load_manifest(plugin_dir):
    return json.loads((plugin_dir / "templates" / "manifest.json").read_text(encoding="utf-8"))


def profiles(plugin_dir):
    base = plugin_dir / "templates" / "profiles"
    return sorted(d.name for d in base.iterdir() if (d / "profile.json").exists())


def load_profile(plugin_dir, name):
    path = plugin_dir / "templates" / "profiles" / name / "profile.json"
    if not path.exists():
        sys.exit(f"kit: unknown profile '{name}'. Profiles: {', '.join(profiles(plugin_dir))}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------- rendering ----------

def table_rows(rows):
    return "".join("| " + " | ".join(r) + " |\n" for r in rows)


def bullets(items):
    return "".join(f"- {i}\n" for i in items)


def values(cfg, prof):
    today = datetime.date.today().isoformat()
    skip = prof.get("budgetSkip", [])
    return {
        "PROJECT_NAME": cfg.get("projectName", "Project"),
        "PROJECT_INTENT": cfg.get("intent", "What the project is, who it serves and why it exists now."),
        "OWNER_PROFILE": cfg.get("ownerProfile", "Who owns the project and how they work (skills, tools, time)."),
        "CHAT_LANGUAGE": cfg.get("chatLanguage", "English"),
        "DOCS_LANGUAGE": cfg.get("docsLanguage", "English"),
        "PROFILE": cfg.get("profile", "generic"),
        "PROFILE_LABEL": prof.get("label", "generic project"),
        "KIT_SOURCE": cfg.get("kitSource", ""),
        "DATE": today,
        "ARCH_ROWS": table_rows(prof.get("archRows", [])),
        "FOLDER_ROWS": table_rows(prof.get("folderRows", [])),
        "TOPIC_ROWS": table_rows(prof.get("topicRows", [])),
        "TOOL_ROWS": table_rows(prof.get("toolRows", [])),
        "NAMING_ROWS": table_rows(prof.get("namingRows", [])),
        "DOCS_ARCH_ROWS": table_rows(prof.get("docsArchRows", [])),
        "DOCS_INTENT": prof.get("docsIntent", ""),
        "PROFILE_RULES": bullets(prof.get("rules", [])),
        "PROFILE_CONSTRAINTS": bullets(prof.get("constraints", [])),
        "PROFILE_GOTCHAS": bullets(prof.get("gotchas", [])),
        "BUDGET_SKIP": "".join(f', "{s}"' for s in skip),
    }


def render(raw, vals):
    for k, v in vals.items():
        raw = raw.replace("{{" + k + "}}", v)
    return raw


def read_template(path, vals):
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        return render(data.decode("utf-8"), vals).encode("utf-8")
    return data


def template_files(plugin_dir, profile_name, vals):
    """{relative path: bytes} for core + profile files, rendered."""
    out = {}
    for base in (plugin_dir / "templates" / "core", plugin_dir / "templates" / "profiles" / profile_name / "files"):
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file():
                out[f.relative_to(base).as_posix()] = read_template(f, vals)
    return out


def is_managed(rel, manifest):
    return any(fnmatch.fnmatch(rel, g) for g in manifest["managed"])


def norm(data):
    """Line endings ignored, so a Windows checkout (CRLF) does not read as a local edit."""
    return data.replace(b"\r\n", b"\n")


def sha(data):
    return hashlib.sha256(norm(data)).hexdigest()


# ---------- blocks and settings ----------

def block_text(plugin_dir, kind, prof):
    lines = (plugin_dir / "templates" / "blocks" / kind).read_text(encoding="utf-8").rstrip("\n").splitlines()
    lines += prof.get(kind, [])
    return "\n".join([BLOCK_BEGIN, *lines, BLOCK_END]) + "\n"


def apply_block(text, block):
    if BLOCK_BEGIN in text and BLOCK_END in text:
        a = text.index(BLOCK_BEGIN)
        b = text.index(BLOCK_END) + len(BLOCK_END)
        rest = text[b:]
        return text[:a] + block.rstrip("\n") + (rest if rest.startswith("\n") else "\n" + rest)
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return text + sep + block


def merge_settings(local, kit):
    """Add the kit's hook commands, marketplace and plugins to the project settings; never remove or
    change the project's own (a plugin the project turned off stays off)."""
    out = json.loads(json.dumps(local))
    for key in ("extraKnownMarketplaces", "enabledPlugins"):
        for name, value in kit.get(key, {}).items():
            out.setdefault(key, {}).setdefault(name, value)
    hooks = out.setdefault("hooks", {})
    for event, groups in kit.get("hooks", {}).items():
        have = hooks.setdefault(event, [])
        commands = {h.get("command") for g in have for h in g.get("hooks", [])}
        for g in groups:
            missing = [h for h in g.get("hooks", []) if h.get("command") not in commands]
            if missing:
                have.append({**g, "hooks": missing})
    return out


# ---------- plan and apply ----------

def plan(project, plugin_dir, cfg, lock, fresh):
    manifest = load_manifest(plugin_dir)
    prof = load_profile(plugin_dir, cfg.get("profile", "generic"))
    vals = values(cfg, prof)
    files = template_files(plugin_dir, cfg.get("profile", "generic"), vals)
    old = lock.get("files", {})
    actions = []  # (kind, rel, data)
    new_lock = {}
    for rel, data in files.items():
        if rel in (KIT_JSON, ".claude/settings.json"):
            continue
        dest = project / rel
        if is_managed(rel, manifest):
            new_lock[rel] = sha(data)
            if not dest.exists():
                actions.append(("create", rel, data))
                continue
            cur = dest.read_bytes()
            if norm(cur) == norm(data):
                continue
            if fresh or sha(cur) == old.get(rel):
                actions.append(("update", rel, data))
            else:
                actions.append(("conflict", rel + ".kit-new", data))
                new_lock[rel] = old.get(rel, sha(cur))
        elif not dest.exists():
            actions.append(("create", rel, data))
    for rel, h in old.items():
        if rel not in files and (project / rel).exists() and sha((project / rel).read_bytes()) == h:
            actions.append(("remove", rel, b""))
    for kind, target in BLOCK_FILES.items():
        dest = project / target
        cur = dest.read_text(encoding="utf-8") if dest.exists() else ""
        new = apply_block(cur, block_text(plugin_dir, kind, prof))
        if new != cur:
            actions.append(("block", target, new.encode("utf-8")))
    kit_settings = json.loads(render((plugin_dir / "templates" / "core" / ".claude" / "settings.json").read_text(encoding="utf-8"), vals))
    sp = project / ".claude" / "settings.json"
    local = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    merged = merge_settings(local, kit_settings)
    if merged != local:
        actions.append(("settings", ".claude/settings.json", (json.dumps(merged, indent=2) + "\n").encode("utf-8")))
    return actions, new_lock, vals


def apply(project, actions):
    for kind, rel, data in actions:
        dest = project / rel
        if kind == "remove":
            dest.unlink()
            parent = dest.parent
            while parent != project and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()  # a folder the kit emptied leaves with it
                parent = parent.parent
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        if rel.endswith((".sh", ".py", ".mjs", ".command")):
            dest.chmod(dest.stat().st_mode | 0o111)


def report(actions, dry):
    if not actions:
        print("kit: everything is up to date.")
        return
    labels = {"create": "new", "update": "updated", "remove": "removed", "block": "block", "settings": "merged",
              "conflict": "EDITED LOCALLY, new version beside it"}
    for kind, rel, _ in actions:
        print(f"  {labels[kind]:<40} {rel}")
    n = sum(1 for a in actions if a[0] == "conflict")
    print(f"kit: {len(actions)} change(s){' (dry run, nothing written)' if dry else ''}.")
    if n:
        print(f"kit: {n} file(s) were edited in this project: compare each <file>.kit-new with the file, "
              "merge what is needed, then delete the .kit-new file.")


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------- commands ----------

def cmd_init(args, project):
    cfg = read_json(project / KIT_JSON)
    if cfg and not args.force:
        sys.exit("kit: this project already has .claude/kit.json; use 'update' (or init --force).")
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = fetch_source(args.source, tmp)
        prof = load_profile(plugin_dir, args.profile)
        cfg = {
            "projectName": args.name or project.name,
            "profile": args.profile,
            "chatLanguage": args.chat_language,
            "docsLanguage": args.docs_language,
            "kitSource": args.kit_source or args.source,
            "mainBranch": args.main_branch,
            "sessionLogKeep": 3,
            "budgetSkip": ["node_modules/", ".claude/skills/", *prof.get("budgetSkip", [])],
        }
        if args.intent:
            cfg["intent"] = args.intent
        if args.owner_profile:
            cfg["ownerProfile"] = args.owner_profile
        if prof.get("sessionReset"):
            cfg["sessionReset"] = prof["sessionReset"]
        actions, new_lock, _ = plan(project, plugin_dir, cfg, {}, fresh=False)
        report(actions, args.dry_run)
        if args.dry_run:
            return
        apply(project, actions)
        write_json(project / KIT_JSON, cfg)
        write_json(project / LOCK, {"version": kit_version(plugin_dir), "files": new_lock})
        print(f"kit: installed version {kit_version(plugin_dir)} with profile '{args.profile}'.")


def cmd_update(args, project, dry=None):
    cfg = read_json(project / KIT_JSON)
    if not cfg:
        sys.exit("kit: no .claude/kit.json here; run 'init' first (from the project root).")
    source = args.source or cfg.get("kitSource")
    if not source:
        sys.exit("kit: no kit source: pass --source or set kitSource in .claude/kit.json.")
    lock = read_json(project / LOCK)
    dry = args.dry_run if dry is None else dry
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = fetch_source(source, tmp)
        new, old = kit_version(plugin_dir), lock.get("version", "none")
        print(f"kit: installed {old}, available {new}.")
        actions, new_lock, _ = plan(project, plugin_dir, cfg, lock, fresh=False)
        prof = load_profile(plugin_dir, cfg.get("profile", "generic"))
        seed_reset = prof.get("sessionReset") and "sessionReset" not in cfg
        if seed_reset:
            print(f"  {'seeded':<40} {KIT_JSON} (sessionReset of profile '{cfg.get('profile', 'generic')}')")
        report(actions, dry)
        if dry:
            return
        apply(project, actions)
        if seed_reset:
            write_json(project / KIT_JSON, {**cfg, "sessionReset": prof["sessionReset"]})
        write_json(project / LOCK, {"version": new, "files": new_lock})


def cmd_propose(args, project):
    import difflib
    import re
    cfg = read_json(project / KIT_JSON)
    if not cfg:
        sys.exit("kit: no .claude/kit.json here.")
    source = args.source or cfg.get("kitSource")
    with tempfile.TemporaryDirectory() as tmp:
        plugin_dir = fetch_source(source, tmp)
        manifest = load_manifest(plugin_dir)
        prof = load_profile(plugin_dir, cfg.get("profile", "generic"))
        files = template_files(plugin_dir, cfg.get("profile", "generic"), values(cfg, prof))
        version = kit_version(plugin_dir)
    diffs = []
    for rel, data in files.items():
        dest = project / rel
        if is_managed(rel, manifest) and dest.exists() and norm(dest.read_bytes()) != norm(data):
            a = data.decode("utf-8", "replace").splitlines(keepends=True)
            b = dest.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
            diffs.append("".join(difflib.unified_diff(a, b, f"kit/{rel}", f"project/{rel}")))
    slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")[:50] or "proposal"
    out = project / "docs" / "pipeline" / "kit_proposals" / f"{datetime.date.today().isoformat()}-{slug}.md"
    body = [
        f"# Kit proposal: {args.title}", "",
        f"- From project: {cfg.get('projectName', project.name)} (profile {cfg.get('profile', 'generic')})",
        f"- Kit version installed: {read_json(project / LOCK).get('version', 'none')}; compared with: {version}",
        f"- Why: {args.why or '(fill in: the problem seen and why the change helps every project)'}",
        "- Scope: ◇ every project / ◇ only this profile (choose one)", "",
        "## Seed or document changes", "",
        "(Changes to seed files such as CLAUDE.md sections, rules or page templates: describe them here,",
        "with the text to add. Seed files are never updated automatically, so the kit templates change and",
        "each project adopts the change at its next recap.)", "",
        "## Managed file diffs", "",
    ]
    body += [f"```diff\n{d}```\n" for d in diffs] if diffs else ["(none: no managed file differs from the kit)", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"kit: proposal written to {out.relative_to(project).as_posix()} ({len(diffs)} managed file diff(s)).")
    print("kit: next: copy it to the kit repository's proposals/ folder on a branch proposal/<project>-<slug> (CONTRIBUTING.md).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="project root (default: current folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="install the kit in this project")
    i.add_argument("--source", required=True)
    i.add_argument("--kit-source", help="source recorded for later updates (default: --source)")
    i.add_argument("--profile", default="generic")
    i.add_argument("--name")
    i.add_argument("--intent")
    i.add_argument("--owner-profile")
    i.add_argument("--chat-language", default="English")
    i.add_argument("--docs-language", default="English")
    i.add_argument("--main-branch", default="main")
    i.add_argument("--force", action="store_true")
    i.add_argument("--dry-run", action="store_true")
    u = sub.add_parser("update", help="apply the kit changes since the installed version")
    u.add_argument("--source")
    u.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("status", help="what an update would change (same as update --dry-run)")
    s.add_argument("--source")
    p = sub.add_parser("profiles", help="list the profiles of a kit source")
    p.add_argument("--source", required=True)
    pr = sub.add_parser("propose", help="write a proposal for the kit from this project's edits")
    pr.add_argument("--title", required=True)
    pr.add_argument("--why")
    pr.add_argument("--source")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    if args.cmd == "init":
        cmd_init(args, project)
    elif args.cmd == "update":
        cmd_update(args, project)
    elif args.cmd == "status":
        args.dry_run = True
        cmd_update(args, project, dry=True)
    elif args.cmd == "propose":
        cmd_propose(args, project)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            plugin_dir = fetch_source(args.source, tmp)
            for name in profiles(plugin_dir):
                print(f"  {name:<14} {load_profile(plugin_dir, name).get('label', '')}")


if __name__ == "__main__":
    main()
