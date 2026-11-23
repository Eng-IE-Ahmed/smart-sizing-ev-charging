""" A3 build-time guard: no unresolved template placeholder may survive in a built document.

check_docx(path) reads the text of a built .docx (paragraphs and tables, from the XML) and raises SystemExit with the
offending line if it finds a Python format placeholder such as {N['dow_ac1']:.3f}, {D[...]}, {R[...]}, {:...} or any
{name...} expression. Called at the end of scripts/build_full_paper.py (full paper), build_short_paper.py (short paper)
and build_report.py (course report).
"""
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

PATTERNS = [
    re.compile(r"\{[A-Za-z_][A-Za-z_0-9\[\]'\". ]*\}"),      # {name}, {N['x']}, {D["x"]}
    re.compile(r"\{[ NDR]\["),                               # {N[ ... , {D[ ... , {R[ ...
    re.compile(r"\{[^{}]{0,40}:[.,0-9]*[dfe%]\}"),           # {...:.3f}, {...:,} style specs
    re.compile(r"\{:"),                                      # bare format field
]


def docx_lines(path):
    path = Path(path)
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    except PermissionError:  # open in Word: read a copy made by the Windows copy API
        tmp = Path(tempfile.gettempdir()) / "check_placeholders_copy.docx"
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath '{path}' -Destination '{tmp}' -Force"],
                       check=True)
        xml = zipfile.ZipFile(tmp).read("word/document.xml").decode("utf8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    return ["".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, flags=re.S)) for p in paras]


def find_placeholders(lines):
    hits = []
    for i, ln in enumerate(lines, 1):
        for pat in PATTERNS:
            m = pat.search(ln)
            if m:
                hits.append((i, m.group(0), ln[:200]))
                break
    return hits


def check_docx(path):
    hits = find_placeholders(docx_lines(path))
    if hits:
        msg = "\n".join(f"  paragraph {i}: {tok!r} in: {ln}" for i, tok, ln in hits)
        raise SystemExit(f"BUILD GUARD: unresolved placeholder(s) in {Path(path).name}:\n{msg}")
    print(f"build guard: no unresolved placeholders in {Path(path).name}")
