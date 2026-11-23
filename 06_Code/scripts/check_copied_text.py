""" plagiarism-style self-check of the full-length article.

Rule: no sentence may contain more than 12 consecutive words copied from a source that was read. The manuscript text
(everything before the reference list, appendix code excluded) is tokenised into lower-case words; every run of 13 words
is compared with every run of 13 words in the source texts. Sources: the extracted full texts and the abstracts that were
read for  (kept outside the repository because of copyright; pass their folder with --sources). Also reports, per
source, the longest run of consecutive shared words.
Outputs: paper_full/INTEGRITY_CHECK.md and paper_full/integrity_overlaps.csv (empty when there is no 13-word overlap).
Usage: python scripts/check_copied_text.py --project . --sources <folder with *.txt and *.json source texts>
"""
import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

N = 13  # more than 12 consecutive words


def words(t):
    return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*", t.lower())


def docx_text(p):
    try:
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf8")
    except PermissionError:  # file open in Word: read a copy made by the Windows copy API
        tmp = Path(tempfile.gettempdir()) / "d9_docx_copy.docx"
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath '{p}' -Destination '{tmp}' -Force"], check=True)
        xml = zipfile.ZipFile(tmp).read("word/document.xml").decode("utf8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    return "\n".join("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", x, flags=re.S)) for x in paras)


def load_sources(folder):
    S = {}
    skip = {"list.txt", "tq.txt", "tq2.txt", "dois.txt", "dois2.txt", "dois3.txt", "oapairs.txt", "heads.txt", "heads2.txt"}
    for p in sorted(folder.rglob("*.txt")):
        if p.name.endswith("_titles.txt") or p.name in skip:
            continue
        S[p.relative_to(folder).as_posix()] = p.read_text(encoding="utf-8", errors="ignore")
    for p in sorted(folder.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        items = []
        if isinstance(d, dict):
            for v in d.values():
                items += v if isinstance(v, list) else [v]
        elif isinstance(d, list):
            items = d
        for i, it in enumerate(items):
            if isinstance(it, dict) and it.get("abstract"):
                S[f"{p.name}#{(it.get('doi') or i)}"] = it["abstract"]
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--docx", default=None, help="manuscript to check (default paper_full/manuscript_full.docx)")
    ap.add_argument("--sources", required=True)
    a = ap.parse_args()
    root = Path(a.project).resolve()
    PF = root / "paper_full"
    T = docx_text(Path(a.docx) if a.docx else PF / "manuscript_full.docx").split("\nReferences\n")[0]
    T = T.split("Source CarArrivals - inter-arrival time:")[0] + T.split("Appendix E. AHP matrices")[-1]  # drop FlexScript code
    mw = words(T)
    mgrams = {}
    for i in range(len(mw) - N + 1):
        mgrams.setdefault(" ".join(mw[i:i + N]), i)
    mby = {k: {" ".join(mw[i:i + k]) for i in range(len(mw) - k + 1)} for k in range(5, N)}
    S = load_sources(Path(a.sources))
    hits, longest = [], []
    for name, txt in S.items():
        sw = words(txt)
        common = set(mgrams) & {" ".join(sw[i:i + N]) for i in range(len(sw) - N + 1)}
        for g in common:
            i = mgrams[g]
            hits.append(dict(source=name, words=g, manuscript_context=" ".join(mw[max(0, i - 5):i + N + 5])))
        L = f">= {N}" if common else 0
        if not common:
            for k in range(N - 1, 4, -1):
                if mby[k] & {" ".join(sw[i:i + k]) for i in range(len(sw) - k + 1)}:
                    L = k
                    break
        longest.append(dict(source=name, source_words=len(sw), longest_shared_run=L))
    H = pd.DataFrame(hits, columns=["source", "words", "manuscript_context"])
    H.to_csv(PF / "integrity_overlaps.csv", index=False, encoding="utf-8")
    Lg = pd.DataFrame(longest)
    full = Lg[~Lg.source.str.contains("#")]
    absn = Lg[Lg.source.str.contains("#")]
    top = Lg.assign(n=pd.to_numeric(Lg.longest_shared_run, errors="coerce").fillna(99)).sort_values("n", ascending=False).head(10)
    md = ["# Integrity check (): copied-text self-check", "",
          f"Rule: no passage of more than 12 consecutive words copied from any source that was read. Method: every run of {N} "
          "consecutive words of the manuscript (text before the reference list, captions and tables included, FlexScript code "
          f"excluded; {len(mw):,} words) was compared with every {N}-word run of each source text (`scripts/check_copied_text.py`).", "",
          f"Sources compared: {len(full)} extracted texts (full papers and abstract dumps) and {len(absn)} abstracts (all "
          "abstracts retrieved during the literature search, including those of the cited papers). The source texts are kept outside "
          "the repository (copyright).", "",
          f"**Result: {len(H)} passages of {N} or more consecutive words shared with any source.**", ""]
    if len(H):
        md += ["| Source | Shared words |", "|---|---|"] + [f"| {r.source} | {r.words} |" for r in H.itertuples()]
    md += ["", "Longest run of consecutive shared words, top 10 sources:", "",
           "| Source | Words in source | Longest shared run |", "|---|---|---|"]
    md += [f"| {r.source} | {r.source_words:,} | {r.longest_shared_run} |" for r in top.itertuples()]
    md += ["", "Extracted texts compared: " + ", ".join(full.source), ""]
    (PF / "INTEGRITY_CHECK.md").write_text("\n".join(md), encoding="utf-8")
    print(f"manuscript words {len(mw):,}; sources {len(S)}; {N}-word overlaps: {len(H)}")
    print(top.to_string(index=False))


if __name__ == "__main__":
    main()
