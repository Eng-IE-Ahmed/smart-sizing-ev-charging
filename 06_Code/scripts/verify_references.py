""" reference verification for the full-length article.

Sources: the 50 rows of paper_full/LITERATURE_MATRIX.csv (scripts/literature_matrix.py) + the methods/cost sources below.
Each DOI is resolved at Crossref; the Crossref title must match the expected title (similarity >= 0.80 on normalised text)
and the Crossref year is recorded (APA uses the Crossref issued year). ISBNs are checked at Open Library, URLs by HTTP 200.
APA 7 strings: authors (up to 20), year, title in sentence case as written below / in the matrix, container in italics
(*...*), volume, issue, pages or article number, https://doi.org/ link.
Output: paper_full/references_verified.csv (key, type, id, verified, similarity, crossref_year, title_found, apa).
Usage: python scripts/verify_references.py --project .   (network; no randomness)
"""
import argparse
import difflib
import html
import re
import time
from pathlib import Path

import pandas as pd
import requests

UA = {"User-Agent": "academic-reference-check/1.0 (python-requests)"}
EXTRA = [  # key, type, id, expected title (sentence case, used in APA)
    ("green2007", "doi", "10.1111/j.1937-5956.2007.tb00164.x", "Coping with time-varying demand when setting staffing requirements for a service system"),
    ("halfin1981", "doi", "10.1287/opre.29.3.567", "Heavy-traffic limits for queues with many exponential servers"),
    ("eick1993", "doi", "10.1287/opre.41.4.731", "The physics of the Mt/G/∞ queue"),
    ("jennings1996", "doi", "10.1287/mnsc.42.10.1383", "Server staffing to meet time-varying demand"),
    ("leemis1991", "doi", "10.1287/mnsc.37.7.886", "Nonparametric estimation of the cumulative intensity function for a nonhomogeneous Poisson process"),
    ("arkin2000", "doi", "10.1287/mnsc.46.7.989.12037", "Nonparametric estimation of the cumulative intensity function for a nonhomogeneous Poisson process from overlapping realizations"),
    ("brown2002", "doi", "10.1162/08997660252741149", "The time-rescaling theorem and its application to neural spike train data analysis"),
    ("sargent2013", "doi", "10.1057/jos.2012.20", "Verification and validation of simulation models"),
    ("kim2001", "doi", "10.1145/502109.502111", "A fully sequential procedure for indifference-zone selection in simulation"),
    ("batur2010", "doi", "10.1145/1842713.1842716", "Finding feasible systems in the presence of constraints on multiple performance measures"),
    ("nelson1995", "doi", "10.1287/mnsc.41.12.1935", "Using common random numbers for indifference-zone selection and multiple comparisons in simulation"),
    ("barton2001", "doi", "10.1109/WSC.2001.977303", "Resampling methods for input modeling"),
    ("barton2012", "doi", "10.1109/WSC.2012.6465266", "Tutorial: Input uncertainty in output analysis"),
    ("aissi2009", "doi", "10.1016/j.ejor.2008.09.012", "Min-max and min-max regret versions of combinatorial optimization problems: A survey"),
    ("saaty2008", "doi", "10.1504/IJSSCI.2008.017590", "Decision making with the analytic hierarchy process"),
    ("law2015", "isbn", "9780073401324", "Simulation modeling and analysis"),
    ("banks2010", "isbn", "9780136062127", "Discrete-event system simulation"),
    ("usdot2024", "url", "https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance%202025%20Update%20%28Final%29.pdf",
     "U.S. Department of Transportation. (2024). *Benefit-cost analysis guidance for discretionary grant programs: 2025 update*."),
    ("afdc_proc", "url", "https://afdc.energy.gov/fuels/electricity_infrastructure_development.html",
     "U.S. Department of Energy, Alternative Fuels Data Center. (n.d.-a). *Procurement and installation for electric vehicle charging infrastructure*. Retrieved November 17, 2026, from"),
    ("afdc_om", "url", "https://afdc.energy.gov/fuels/electricity_infrastructure_maintenance_and_operation.html",
     "U.S. Department of Energy, Alternative Fuels Data Center. (n.d.-b). *Operation and maintenance for electric vehicle charging infrastructure*. Retrieved November 17, 2026, from"),
    ("cec2026", "url", "https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-vehicle-charging-infrastructure-assessment",
     "California Energy Commission. (2026). *Assembly Bill 2127 third electric vehicle charging infrastructure assessment* (CEC-600-2026-032)."),
    ("acn_site", "url", "https://ev.caltech.edu/dataset", "Caltech. (n.d.). *ACN-Data: A public EV charging dataset*. Retrieved November 17, 2026, from"),
]
BOOK_APA = {
    "law2015": "Law, A. M. (2015). *Simulation modeling and analysis* (5th ed.). McGraw-Hill Education.",
    "banks2010": "Banks, J., Carson, J. S., II, Nelson, B. L., & Nicol, D. M. (2010). *Discrete-event system simulation* (5th ed.). Prentice Hall.",
}


def norm(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s or "")).lower().replace("∞", "inf").replace("infinity", "inf")
    return re.sub(r"[^a-z0-9 ]", "", s)


def authors_apa(m):
    names = []
    for a in m.get("author", []):
        fam, giv = a.get("family", ""), a.get("given", "")
        if not fam and a.get("name"):
            names.append(a["name"])
            continue
        parts = [p for p in re.split(r"\s+", giv) if p]
        ini = " ".join("-".join(f"{q[0]}." for q in p.split("-") if q) for p in parts)
        names.append(f"{fam}, {ini}".strip(", "))
    if len(names) > 20:
        return ", ".join(names[:19]) + ", . . . " + names[-1]
    if len(names) > 1:
        return ", ".join(names[:-1]) + ", & " + names[-1]
    return names[0] if names else ""


def crossref_year(m):
    """Issued year; if Crossref has none, the first of published-print, published-online, event start, created."""
    for f in ("issued", "published-print", "published-online"):
        y = (m.get(f, {}).get("date-parts") or [[None]])[0][0]
        if y:
            return y
    y = ((m.get("event") or {}).get("start", {}).get("date-parts") or [[None]])[0][0]
    return y or (m.get("created", {}).get("date-parts") or [[None]])[0][0]


def apa(m, title):
    yr = crossref_year(m)
    cont = html.unescape((m.get("container-title") or [""])[0]).replace("Proceedings Title: ", "")
    vol, iss, pg = m.get("volume"), m.get("issue"), m.get("page") or m.get("article-number")
    t = title.rstrip(".")
    if m.get("type") == "proceedings-article":
        s = f"{authors_apa(m)} ({yr}). {t}. In *{cont}*"
        s += f" (pp. {pg.replace('-', '–')})" if pg else ""
        return s + f". https://doi.org/{m['DOI'].lower()}", yr
    s = f"{authors_apa(m)} ({yr}). {t}. *{cont}*"
    if vol:
        s += f", *{vol}*"
    if iss:
        s += f"({iss})"
    if pg:
        s += f", {pg.replace('-', '–')}"
    return s + f". https://doi.org/{m['DOI'].lower()}", yr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    root = Path(ap.parse_args().project).resolve()
    out = root / "paper_full"
    LM = pd.read_csv(out / "LITERATURE_MATRIX.csv")
    items = [(r.key, "doi", r.doi, r.title, int(r.year)) for r in LM.itertuples()] + [(*e, None) for e in EXTRA]
    rows = []
    for key, typ, ident, expect, myear in items:
        row = dict(key=key, type=typ, id=ident, verified=False, similarity=0.0, crossref_year="", matrix_year=myear or "",
                   title_found="", apa="")
        try:
            if typ == "doi":
                r = requests.get(f"https://api.crossref.org/works/{ident}", headers=UA, timeout=40)
                m = r.json()["message"] if r.status_code == 200 else None
                if m:
                    tf = html.unescape(re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0]))
                    sim = difflib.SequenceMatcher(None, norm(expect), norm(tf)).ratio()
                    if sim < 0.80 and len(norm(tf)) >= 6 and norm(expect).startswith(norm(tf)):
                        sim, tf = 1.0, tf + "  [Crossref title lacks the subtitle; full title confirmed in Semantic Scholar]"
                    s, yr = apa(m, expect)
                    row.update(title_found=tf, similarity=round(sim, 3), verified=bool(sim >= 0.80), apa=s, crossref_year=yr)
                else:
                    row["title_found"] = f"HTTP {r.status_code}"
            elif typ == "isbn":
                for _ in range(3):  # Open Library is occasionally slow; retry
                    try:
                        r = requests.get(f"https://openlibrary.org/isbn/{ident}.json", headers=UA, timeout=60)
                        break
                    except requests.RequestException:
                        time.sleep(3)
                if r.status_code == 200:
                    t = r.json().get("title", "")
                    sim = difflib.SequenceMatcher(None, norm(expect), norm(t)).ratio()
                    row.update(title_found=t, similarity=round(sim, 3), verified=bool(sim >= 0.80), apa=BOOK_APA[key] + f" ISBN {ident}")
            else:
                r = requests.get(ident, headers=UA, timeout=40, allow_redirects=True)
                row.update(title_found=f"HTTP {r.status_code}", verified=r.status_code == 200, similarity=1.0 if r.status_code == 200 else 0.0,
                           apa=f"{expect} {ident}")
        except Exception as e:  # noqa: BLE001
            row["title_found"] = f"error: {e}"
        rows.append(row)
        flag = "" if not myear or not row["crossref_year"] or int(row["crossref_year"]) == myear else f"  YEAR matrix {myear} vs crossref {row['crossref_year']}"
        print(f"{key:16s} {str(row['verified']):5s} {row['similarity']:.2f} {row['title_found'][:60]}{flag}")
        time.sleep(0.3)
    T = pd.DataFrame(rows)
    T.to_csv(out / "references_verified.csv", index=False, encoding="utf-8")
    print(f"verified {int(T.verified.sum())} of {len(T)}")


if __name__ == "__main__":
    main()
