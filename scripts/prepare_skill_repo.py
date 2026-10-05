#!/usr/bin/env python3
"""Prepare agent-skill repos for publishing: copy + desensitize + README/LICENSE + git commit.

Usage:
    python prepare_skill_repo.py --skill mkvtoolnix --skill officecli \
        --dest D:/WorkBuddy_WorkSpace/repos --template D:/WorkBuddy_WorkSpace/repos/file-organizer

Options:
    --skill NAME      skill folder name under ~/.workbuddy/skills (repeatable)
    --dest DIR        output root, one git repo per skill
    --template DIR    dir that holds LICENSE and .gitignore to copy
    --owner NAME      GitHub owner, used in README clone URL
    --scan-only       print sensitive hits without writing anything
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

DEFAULT_SRC = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills")

# Patterns/replacements are assembled from fragments on purpose: this file is
# itself copied through these rules when the skill gets published, and a literal
# user-path prefix written out in full on a definition line would be rewritten
# into a broken regex.
# The char classes exclude the backtick so markdown examples like
# `C:\Users\<you>` survive desensitization with their backticks intact.
_SLASH = "/"
_WIN_USER_RX = r"C:\\Users\\[^\\\s\"'\`]+"
_WIN_USER_REP = r"C:\\Users\\<you>"
_POSIX_USER_RX = "C:" + _SLASH + "Users" + _SLASH + r"[^/\s\"'\`]+"
_POSIX_USER_REP = "C:" + _SLASH + "Users" + _SLASH + "<you>"

RULES = [
    (re.compile(_WIN_USER_RX, re.I), _WIN_USER_REP),
    (re.compile(_POSIX_USER_RX), _POSIX_USER_REP),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<ip>"),
]
SENS = re.compile(
    r"C:\\Users\\Windows|wechat|xwechat|token|api[_-]?key|password|secret", re.I
)
TEXT_EXT = {
    ".md", ".py", ".ps1", ".json", ".txt", ".yml", ".yaml",
    ".bat", ".sh", ".html", ".css", ".js", ".ts", ".toml", ".ini",
}
SKIP_NAMES = {"__pycache__", ".git", ".DS_Store", "Thumbs.db", "node_modules"}


def parse_frontmatter(path):
    """Return (description, meta). Handles YAML folded blocks (>-)."""
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return "", {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return "", {}
    block = m.group(1).splitlines()
    meta = {}
    i = 0
    while i < len(block):
        line = block[i]
        mm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if not mm:
            i += 1
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val in (">-", ">", "|", "|-"):
            parts = []
            i += 1
            while i < len(block) and (block[i].startswith((" ", "\t")) or not block[i].strip()):
                parts.append(block[i].strip())
                i += 1
            val = "".join(parts)
            meta[key] = val
            continue
        meta[key] = val.strip(">- ")
        i += 1
    return meta.get("description", ""), meta


def build_readme(name, desc, tree, owner):
    return "\n".join([
        "# {}".format(name),
        "",
        desc or "(no description in SKILL.md frontmatter)",
        "",
        "## Install",
        "",
        "```bash",
        "git clone https://github.com/{}/{}.git ~/.workbuddy/skills/{}".format(owner, name, name),
        "```",
        "",
        "## Contents",
        "",
        "```",
        *tree,
        "```",
        "",
        "## Usage",
        "",
        "See [`SKILL.md`](SKILL.md) - that file is the entry point the agent reads.",
        "",
        "## License",
        "",
        "MIT",
        "",
    ])


def tree_lines(root):
    out = [os.path.basename(root) + "/"]
    for cur, dirs, fs in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        rel = os.path.relpath(cur, root)
        level = 0 if rel == "." else rel.count(os.sep) + 1
        if rel != ".":
            out.append("  " * level + os.path.basename(cur) + "/")
        for f in sorted(fs):
            out.append("  " * (level + 1) + f)
    return out


def git(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def prepare(skill, src_root, dest_root, template, owner, scan_only):
    src = os.path.join(src_root, skill)
    if not os.path.isdir(src):
        print("SKIP  {:<40} not found".format(skill))
        return None
    if not os.path.exists(os.path.join(src, "SKILL.md")):
        print("SKIP  {:<40} no SKILL.md".format(skill))
        return None

    desc, meta = parse_frontmatter(os.path.join(src, "SKILL.md"))
    hits = []
    for cur, dirs, fs in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_NAMES]
        for f in fs:
            if f in SKIP_NAMES or f.endswith(".pyc"):
                continue
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            try:
                t = open(os.path.join(cur, f), encoding="utf-8").read()
            except Exception:
                continue
            n = len(SENS.findall(t))
            if n:
                hits.append((os.path.relpath(os.path.join(cur, f), src), n))

    if scan_only:
        print("{:<40} sensitive={}".format(skill, hits or "none"))
        return None

    dst = os.path.join(dest_root, skill)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)

    for cur, dirs, fs in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_NAMES]
        rel = os.path.relpath(cur, src)
        for f in fs:
            if f in SKIP_NAMES or f.endswith(".pyc"):
                continue
            sp = os.path.join(cur, f)
            rp = os.path.join(dst, "" if rel == "." else rel, f)
            os.makedirs(os.path.dirname(rp), exist_ok=True)
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                try:
                    t = open(sp, encoding="utf-8").read()
                except Exception:
                    shutil.copy2(sp, rp)
                    continue
                for rx, rep in RULES:
                    t = rx.sub(rep, t)
                open(rp, "w", encoding="utf-8", newline="\n").write(t)
            else:
                shutil.copy2(sp, rp)

    desc, _ = parse_frontmatter(os.path.join(dst, "SKILL.md"))
    with open(os.path.join(dst, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(build_readme(skill, desc, tree_lines(dst), owner))
    for extra in ("LICENSE", ".gitignore"):
        tpl = os.path.join(template, extra) if template else ""
        if tpl and os.path.exists(tpl):
            shutil.copy2(tpl, os.path.join(dst, extra))

    git(["git", "init", "-q"], dst)
    git(["git", "add", "-A"], dst)
    git(["git", "-c", "user.name=" + owner,
         "-c", "user.email=" + owner + "@users.noreply.github.com",
         "commit", "-q", "-m", "feat: {} agent skill".format(skill)], dst)
    n = git(["git", "ls-files"], dst).stdout.count("\n")
    print("{:<40} files={:<4} sensitive={}".format(skill, n, hits or "none"))
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", action="append", default=[], required=True)
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--template", default="")
    ap.add_argument("--owner", default="longhai-lanxin")
    ap.add_argument("--scan-only", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.dest, exist_ok=True)
    for s in args.skill:
        prepare(s, args.src, args.dest, args.template or args.dest, args.owner, args.scan_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
