""" I1-I3 source checks (network): Crossref metadata of two references and the cost-critical web sources.

I1/I2: Crossref fields volume, issue, page, article-number, published-print, published-online, issued for
       10.1287/trsc.2021.0494 (Kinay et al.) and 10.32604/ee.2026.087166 (Komarina et al.).
I3:    HTTP status of the AFDC (2 pages), California Energy Commission and Caltech ACN-Data pages; whether the figures
       used are still on the page; latest archived snapshot from the Internet Archive availability API.
Output: paper_full/source_check.json. Usage: python scripts/check_sources.py --project .
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

import requests

UA = {"User-Agent": "academic-reference-check/1.0 (python-requests)"}
WEB = {
    "afdc_proc": ("https://afdc.energy.gov/fuels/electricity_infrastructure_development.html", [r"3,500", r"2,500"]),
    "afdc_om": ("https://afdc.energy.gov/fuels/electricity_infrastructure_maintenance_and_operation.html", [r"\$?400"]),
    "cec2026": ("https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-vehicle-charging-infrastructure-assessment",
                [r"6\.8 million", r"2030"]),
    "acn_site": ("https://ev.caltech.edu/dataset", [r"54 EVSEs", r"Caltech"]),
}


def saaty1990(root):
    """ item 3: verify Saaty (1990) at Crossref (publisher deposit), try Semantic Scholar for the abstract, and add the
    verified APA entry to paper_full/references_verified.csv if it is not there yet."""
    import pandas as pd
    doi = "10.1016/0377-2217(90)90057-I"
    m = requests.get(f"https://api.crossref.org/works/{doi}", headers=UA, timeout=40).json()["message"]
    meta = dict(title=(m.get("title") or [""])[0], container=(m.get("container-title") or [""])[0], volume=m.get("volume"),
                issue=m.get("issue"), page=m.get("page"), issued=(m.get("issued", {}).get("date-parts") or [[None]])[0],
                authors=[f"{a.get('family')}, {a.get('given')}" for a in m.get("author", [])])
    try:
        s2 = requests.get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}", params={"fields": "abstract"},
                          headers=UA, timeout=40).json()
        meta["abstract_semantic_scholar"] = bool(s2.get("abstract"))
    except Exception as e:  # noqa: BLE001
        meta["abstract_semantic_scholar"] = f"error: {e}"
    assert meta["volume"] == "48" and meta["issue"] == "1" and meta["page"] == "9-26", meta
    apa = ("Saaty, T. L. (1990). How to make a decision: The analytic hierarchy process. *European Journal of Operational "
           "Research*, *48*(1), 9–26. https://doi.org/10.1016/0377-2217(90)90057-i")
    p = root / "paper_full/references_verified.csv"
    R = pd.read_csv(p)
    if "saaty1990" not in set(R.key):
        R = pd.concat([R, pd.DataFrame([dict(key="saaty1990", type="doi", id=doi, verified=True, similarity=1.0,
                                             crossref_year=1990, matrix_year="", title_found=meta["title"], apa=apa)])])
        R.to_csv(p, index=False, encoding="utf-8")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--saaty-only", action="store_true")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    if a.saaty_only:
        meta = saaty1990(root)
        f = root / "paper_full/source_check.json"
        d = json.loads(f.read_text())
        d["saaty1990_crossref_D10_1"] = meta
        f.write_text(json.dumps(d, indent=1))
        print(json.dumps(meta, indent=1))
        return
    out = {"checked_on": date.today().isoformat(), "crossref": {}, "web": {}}
    for doi in ("10.1287/trsc.2021.0494", "10.32604/ee.2026.087166"):
        m = requests.get(f"https://api.crossref.org/works/{doi}", headers=UA, timeout=40).json()["message"]
        dp = lambda f: (m.get(f, {}).get("date-parts") or [[None]])[0]  # noqa: E731
        out["crossref"][doi] = dict(volume=m.get("volume"), issue=m.get("issue"), page=m.get("page"),
                                    article_number=m.get("article-number"), published_print=dp("published-print"),
                                    published_online=dp("published-online"), issued=dp("issued"),
                                    container=(m.get("container-title") or [""])[0])
    for k, (url, pats) in WEB.items():
        row = dict(url=url)
        try:
            r = requests.get(url, headers=UA, timeout=40)
            txt = re.sub(r"<[^>]+>", " ", r.text)
            row.update(status=r.status_code, figures_found={p: bool(re.search(p, txt)) for p in pats})
        except Exception as e:  # noqa: BLE001
            row.update(status=f"error: {e}")
        try:
            a = requests.get("https://archive.org/wayback/available", params={"url": url}, headers=UA, timeout=40).json()
            snap = a.get("archived_snapshots", {}).get("closest") or {}
            row.update(archive_url=snap.get("url"), archive_timestamp=snap.get("timestamp"))
        except Exception as e:  # noqa: BLE001
            row.update(archive_url=None, archive_error=str(e))
        out["web"][k] = row
    (root / "paper_full/source_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
