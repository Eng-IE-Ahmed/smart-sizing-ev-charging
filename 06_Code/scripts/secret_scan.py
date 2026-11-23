""" secret scan before any push: walks the files git would track (git ls-files when inside a repo, else the whole
tree) and fails (exit 1) on anything that looks like a secret. Matches are reported with file and line only and the value
MASKED - a secret is never printed.
Checks: token files (acn_token.txt, .env, *.pem, *.key), ACN_API_TOKEN assignments with a value, GitHub/AWS/Slack/OpenAI/
Anthropic key formats, private-key blocks, 'password='/'secret='/'api_key=' with a quoted value; plus long opaque strings
(>= 32 chars of [A-Za-z0-9_-] with letters and digits) listed for a manual check (they do not fail the scan).
Usage: python scripts/secret_scan.py --project .   Output: report/SECRET_SCAN.txt
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

TEXT = {".py", ".md", ".txt", ".csv", ".json", ".fs", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".ps1", ".sh", ".bat",
        ".html", ".xml", ".fsx", ".log", ".gitignore"}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}
PATTERNS = [
    ("github token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}")),
    ("github fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{40,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}")),
    ("OpenAI/Anthropic key", re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("ACN token assignment", re.compile(r"ACN_API_TOKEN\s*[=:]\s*['\"]?[A-Za-z0-9_-]{8,}")),
    ("password/secret assignment", re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key)\s*[=:]\s*['\"][^'\"\s]{6,}['\"]")),
]
OPAQUE = re.compile(r"(?<![A-Za-z0-9_./-])[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_./-])")
ALLOW = {"8cb3624fefb4abd14fe243ad843a5982f1b609d5e5f23140d33f16a9a9757567"}   # SHA-256 of the raw data file


def tracked(root):
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "-co", "--exclude-standard"], cwd=root,
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        return [root / p for p in out.splitlines() if p]
    except Exception:  # noqa: BLE001
        return [p for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS)]


def mask(s):
    return s[:3] + "...(" + str(len(s)) + " chars)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    files = tracked(root)
    hits = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        if f.name.lower() in ("acn_token.txt", ".env") or f.suffix.lower() in (".pem", ".key"):
            hits.append((rel, 0, "secret file", "(file present)"))
            continue
        if f.suffix.lower() not in TEXT or f.stat().st_size > 20_000_000:
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        big_data = f.suffix.lower() in (".csv", ".json") and f.stat().st_size > 200_000
        for i, ln in enumerate(lines, 1):
            for name, pat in PATTERNS:
                m = pat.search(ln)
                if m:
                    hits.append((rel, i, name, mask(m.group(0))))
            if big_data:
                continue
            for m in OPAQUE.finditer(ln):
                s = m.group(0)
                if s in ALLOW or not (re.search(r"[A-Za-z]", s) and re.search(r"\d", s)):
                    continue
                if re.fullmatch(r"[0-9a-f]{32,}", s):
                    continue                              # hex digests (hashes)
                hits.append((rel, i, "opaque string (check)", mask(s)))
    strict = [h for h in hits if h[2] != "opaque string (check)"]
    rep = [f"files scanned: {len(files)}", f"secret findings (fail): {len(strict)}",
           f"opaque strings for manual check: {len(hits) - len(strict)}"] + [f"{r}:{i}  {n}  {m}" for r, i, n, m in hits]
    (root / "report" / "SECRET_SCAN.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep[:80]))
    sys.exit(1 if strict else 0)


if __name__ == "__main__":
    main()
