"""Phase 4.4: workbook sheet "Analytic_MtGinf" - a planner types a growth factor m and reads the chargers needed.

Formulas only (legacy POISSON() so no _xlfn prefix is needed): a(t) = m * m(t) on a 15-minute grid (m(t) purple, from
results/phase4/p4_offered_load_15min.csv); block 1: P(N >= c) = 1 - POISSON(c - 1, a, TRUE) for c = 30..75 and every t,
max over t; c_MOL = MINIFS(c, max, "<=" eps). Block 2: Erlang-C P(wait > tau) = C(c, a) exp(-(c - a) tau / E[S]) (1 if
c <= a), arrival-weighted over t; c_EC = MINIFS(c, P15, "<=" threshold). Also the DES frontier c*(m) and the same rules
computed in Python on the same 15-min grid (purple) as a check. Loads the CURRENT workbook (keeps every sheet), adds or
replaces this sheet, saves; then run scripts/excel_recalc.py (Excel COM) for cached values and the 0-error check.
NOTE: scripts/excel_update.py rebuilds the workbook from the v1 backup - if it is re-run, re-run this script after it.
Usage: python scripts/excel_analytic.py --project . --xlsx excel/EV_Charging_DES_Caltech_2019.xlsx
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.chart import LineChart, Reference, ScatterChart, Series
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Font, PatternFill
from scipy import stats

F_BODY = Font(name="Arial", size=10)
F_BOLD = Font(name="Arial", size=10, bold=True)
F_TITLE = Font(name="Arial", size=14, bold=True, color="FF1F4E78")
F_HDR = Font(name="Arial", size=10, bold=True, color="FFFFFFFF")
F_PURPLE = Font(name="Arial", size=10, color="FF7030A0")
F_GREEN = Font(name="Arial", size=10, color="FF008000")
F_BLUE = Font(name="Arial", size=10, color="FF0000FF")
F_KEY = Font(name="Arial", size=11, bold=True, color="FFC00000")
F_BOX = Font(name="Arial", size=10, color="FF1F3864")
FILL_HDR = PatternFill("solid", fgColor="FF1F4E78")
FILL_IN = PatternFill("solid", fgColor="FFFFF2CC")
FILL_KEY = PatternFill("solid", fgColor="FFE2EFDA")
FILL_BOX = PatternFill("solid", fgColor="FFEEF3F8")
CS = list(range(30, 76))
R0 = 22            # first data row of block 1
R1 = R0 + 96 + 6   # first data row of block 2


def put(ws, ref, v, kind="f", nf=None):
    c = ws[ref]
    c.value = v
    c.font = {"f": F_BODY, "b": F_BOLD, "p": F_PURPLE, "g": F_GREEN, "i": F_BLUE, "k": F_KEY}[kind]
    if kind == "i":
        c.fill = FILL_IN
    if kind == "k":
        c.fill = FILL_KEY
    if nf:
        c.number_format = nf


def col(n):
    return openpyxl.utils.get_column_letter(n)


def erlang_c(c, a):
    if c <= a:
        return 1.0
    tail = stats.poisson.pmf(c, a) * c / (c - a)
    return tail / (stats.poisson.cdf(c - 1, a) + tail)


def py_rules(m15, lam15, ES, mult, eps=0.01, tau=0.25, thr=0.01):
    a = mult * m15
    cmol = next(c for c in CS if stats.poisson.sf(c - 1, a).max() <= eps)
    w = lam15 / lam15.sum()
    cec = next(c for c in CS if (w * np.array([erlang_c(c, ai) * (math.exp(-(c - ai) * tau / ES) if c > ai else 1.0)
                                               for ai in a])).sum() <= thr)
    return cmol, cec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--xlsx", default="excel/EV_Charging_DES_Caltech_2019.xlsx")
    a = ap.parse_args()
    root = Path(a.project)
    Q = pd.read_csv(root / "results" / "phase4" / "p4_offered_load_15min.csv")
    T = pd.read_csv(root / "results" / "phase4" / "p4_mol_vs_des.csv")
    S = json.loads((root / "results" / "phase4" / "p4_summary.json").read_text())
    ES = S["ES_hours"]
    wb = openpyxl.load_workbook(root / a.xlsx)
    if "Analytic_MtGinf" in wb.sheetnames:
        del wb["Analytic_MtGinf"]
    ws = wb.create_sheet("Analytic_MtGinf", wb.sheetnames.index("17_Decision"))
    ws["A1"] = "Step 6b - Analytic benchmark (Mt/G/inf): type a growth factor and read the chargers needed"
    ws["A1"].font = F_TITLE
    ws.merge_cells("A3:N6")
    ws["A3"] = ("Without blocking, the number of charging cars at time t is Poisson with mean m x m(t), where m(t) is the offered load "
                "(cars arriving earlier and still plugged in; computed from the 48 arrival rates and the stay distribution of each "
                "arrival band, results/phase4). Modified offered load (MOL) rule: the smallest c with max over the day of "
                "P(N >= c) <= eps. Erlang-C rule: the smallest c whose arrival-weighted Erlang-C approximation of P(wait > 15 min) "
                "is <= the 1% threshold. Change m (C8) or eps (C9): all formulas update. The DES frontier (phase 3) is shown beside "
                "it - the analytic rules are a quick screen, the DES is the decision tool.")
    ws["A3"].font, ws["A3"].fill, ws["A3"].alignment = F_BOX, FILL_BOX, Alignment(wrap_text=True, vertical="top")
    rows = [("Growth factor m", 1.3, "i", "0.00"), ("eps for the MOL rule", 0.01, "i", "0.0%"),
            ("Wait target tau (h)", "='01_Plan'!$C$11/60", "g", "0.000"), ("Risk threshold", "='01_Plan'!$C$12", "g", "0.0%"),
            ("Mean stay E[S] (h, arrival-weighted, phase 4)", ES, "p", "0.000")]
    for i, (lab, v, k, nf) in enumerate(rows):
        put(ws, f"B{8 + i}", lab, "b")
        put(ws, f"C{8 + i}", v, k, nf)
    last = col(5 + len(CS))
    put(ws, "B14", "c_MOL: smallest c with max_t P(N >= c) <= eps", "b")
    put(ws, "C14", f"=_xlfn.MINIFS($F${R0 - 1}:${last}${R0 - 1},$F${R0 + 97}:${last}${R0 + 97},\"<=\"&$C$9)", "k", "0")
    put(ws, "B15", "c_EC: smallest c with Erlang-C P(wait > tau) <= threshold", "b")
    put(ws, "C15", f"=_xlfn.MINIFS($F${R1 - 1}:${last}${R1 - 1},$F${R1 + 97}:${last}${R1 + 97},\"<=\"&$C$11)", "k", "0")
    put(ws, "B16", "DES c* (phase 3 frontier) at this m", "b")
    put(ws, "C16", "=IFERROR(INDEX($R$9:$R$19,MATCH(ROUND($C$8,1),$Q$9:$Q$19,0)),\"(m not on the 0.1 grid)\")", "g", "0")
    hdr = ["m", "DES c*", "c_MOL eps 1% (1-min, Python)", "c_EC (1-min, Python)", "c_MOL eps 1% (15-min, Python)",
           "c_EC (15-min, Python)", "Check: sheet = Python at m = C8"]
    for j, h in enumerate(hdr):
        c = ws.cell(8, 17 + j, h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, Alignment(wrap_text=True)
    m15, lam15 = Q.m_t_mean15.to_numpy(float), Q.arrivals_per_15min.to_numpy(float)
    for i in range(len(T)):
        rr = 9 + i
        mult = float(T.loc[i, "m"])
        cm15, ce15 = py_rules(m15, lam15, ES, mult)
        vals = [mult, T.loc[i, "DES_c_star"], T.loc[i, "c_MOL_eps0.01"], T.loc[i, "c_EC"], cm15, ce15]
        for j, v in enumerate(vals):
            put(ws, f"{col(17 + j)}{rr}", v if j == 0 else (int(v) if not pd.isna(v) else None), "p", "0.0" if j == 0 else "0")
    ws["Q20"] = "1-min columns: results/phase4/p4_mol_vs_des.csv; 15-min columns use exactly the sheet's grid."
    ws["Q20"].font = F_BODY
    put(ws, "W9", "=IF(ISNA(MATCH(ROUND($C$8,1),$Q$9:$Q$19,0)),\"m not on grid\",IF(AND($C$9=0.01,$C$14=INDEX($U$9:$U$19,MATCH(ROUND($C$8,1),$Q$9:$Q$19,0)),"
        "$C$15=INDEX($V$9:$V$19,MATCH(ROUND($C$8,1),$Q$9:$Q$19,0))),\"MATCH ✓\",\"CHECK ✗\"))", "b")
    put(ws, f"A{R0 - 3}", "Block 1 - P(N >= c) at each quarter hour (Poisson with mean a = m x m(t))", "b")
    for j, h in enumerate(["q", "time", "arrivals / 15 min", "m(t) (15-min mean)", "a(t) = m x m(t)"]):
        c = ws.cell(R0 - 1, 1 + j, h)
        c.font, c.fill = F_HDR, FILL_HDR
    for j, cc in enumerate(CS):
        for rr in (R0 - 1, R1 - 1):
            c = ws.cell(rr, 6 + j, cc)
            c.font, c.fill = F_HDR, FILL_HDR
    for i in range(len(Q)):
        rr = R0 + i
        put(ws, f"A{rr}", int(Q.loc[i, "q"]))
        put(ws, f"B{rr}", str(Q.loc[i, "time"]))
        put(ws, f"C{rr}", float(Q.loc[i, "arrivals_per_15min"]), "p", "0.000")
        put(ws, f"D{rr}", float(Q.loc[i, "m_t_mean15"]), "p", "0.000")
        put(ws, f"E{rr}", f"=$C$8*D{rr}", nf="0.000")
        rb = R1 + i
        for j in range(len(CS)):
            cl = col(6 + j)
            ws[f"{cl}{rr}"] = f"=1-POISSON({cl}${R0 - 1}-1,$E{rr},TRUE)"
            ws[f"{cl}{rr}"].number_format = "0.0000"
            k = f"{cl}${R1 - 1}"
            ws[f"{cl}{rb}"] = (f"=IF({k}>$E{rr},(POISSON({k},$E{rr},FALSE)*{k}/({k}-$E{rr}))/"
                               f"(POISSON({k}-1,$E{rr},TRUE)+POISSON({k},$E{rr},FALSE)*{k}/({k}-$E{rr}))"
                               f"*EXP(-({k}-$E{rr})*$C$10/$C$12),1)")
            ws[f"{cl}{rb}"].number_format = "0.0000"
    put(ws, f"E{R0 + 97}", "max over t", "b")
    put(ws, f"A{R1 - 3}", "Block 2 - Erlang-C approximation of P(wait > tau) at each quarter hour (1 if c <= a)", "b")
    put(ws, f"E{R1 + 97}", "arrival-weighted", "b")
    for j in range(len(CS)):
        cl = col(6 + j)
        put(ws, f"{cl}{R0 + 97}", f"=MAX({cl}{R0}:{cl}{R0 + 95})", nf="0.0000")
        put(ws, f"{cl}{R1 + 97}", f"=SUMPRODUCT($C${R0}:$C${R0 + 95},{cl}{R1}:{cl}{R1 + 95})/SUM($C${R0}:$C${R0 + 95})", nf="0.0000")
    for k, w in {"A": 6, "B": 46, "C": 12, "D": 12, "E": 12, "Q": 8, "R": 9, "S": 13, "T": 13, "U": 13, "V": 13, "W": 16}.items():
        ws.column_dimensions[k].width = w
    ch = LineChart()
    ch.title = "Offered load m(t) and a(t) = m x m(t), by quarter hour"
    ch.add_data(Reference(ws, min_col=4, min_row=R0 - 1, max_row=R0 + 95), titles_from_data=True)
    ch.add_data(Reference(ws, min_col=5, min_row=R0 - 1, max_row=R0 + 95), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=R0, max_row=R0 + 95))
    for i, s in enumerate(ch.series):
        s.graphicalProperties = GraphicalProperties(ln=LineProperties(solidFill=["1F4E78", "C00000"][i], w=19050))
        s.marker.symbol = "none"
        s.smooth = False
    ch.roundedCorners = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.legend.position = "b"
    ch.height, ch.width = 8, 18
    ws.add_chart(ch, "F8")
    sc = ScatterChart()
    sc.title = "Chargers needed vs growth: DES c* and analytic rules"
    xs = Reference(ws, min_col=17, min_row=9, max_row=19)
    for j, (nm, clr) in enumerate([("DES c*", "1F4E78"), ("MOL eps 1%", "C55A11"), ("Erlang-C", "7030A0")]):
        s = Series(Reference(ws, min_col=18 + j, min_row=9, max_row=19), xs, title=nm)
        s.graphicalProperties = GraphicalProperties(ln=LineProperties(solidFill=clr, w=19050))
        sc.series.append(s)
    sc.roundedCorners = False
    sc.x_axis.delete = False
    sc.y_axis.delete = False
    sc.x_axis.title = "growth factor m"
    sc.y_axis.title = "chargers"
    sc.legend.position = "b"
    sc.height, sc.width = 8, 14
    ws.add_chart(sc, "Q22")
    wb.save(root / a.xlsx)
    print("sheet Analytic_MtGinf written:", 96 * len(CS) * 2 + 96 + 2 * len(CS), "formulas in the blocks")


if __name__ == "__main__":
    main()
