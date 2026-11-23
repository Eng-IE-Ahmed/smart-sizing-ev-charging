""" - extend the course workbook with the Phase 1R /  (v2) results.

Builds new sheets 04b, 07b, 08b, 10b, 12b, 13b, 14b, 15b, 16b and updates 00, 03, 07, 08, 11, 17, 18.
Conventions of the workbook: Arial; blue text on yellow = input; black = formula; purple = value from the
engine/raw data/results CSV; green = link to another sheet; red bold on green = key result; comment box =
dark-blue text on light-blue fill (merged range).  English only.  Every purple number comes from a results CSV
named in the sheet.  The workbook is NOT recalculated here (openpyxl writes no cached values): run
scripts/excel_recalc.py afterwards (Microsoft Excel via COM).
The workbook is always rebuilt from the untouched v1 backup, so the script can be re-run.

Usage (from the project root):
  python scripts/excel_update.py --xlsx excel/EV_Charging_DES_Caltech_2019.xlsx \
      --backup excel/EV_Charging_DES_Caltech_2019_v1_backup.xlsx --res results/phase1r \
      --json data/raw/acn_caltech_2019-03-01_2019-05-31.json --engine engine/ev_des_engine.py
No randomness except the engine replication used for the 10b check (CRN streams default_rng([1,1]) / ([1,2])).
"""
import argparse
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.chart import BarChart, LineChart, Reference, ScatterChart, Series
from openpyxl.chart.data_source import NumDataSource, NumRef
from openpyxl.chart.error_bar import ErrorBars
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Font, PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1r_common import load_engine  # noqa: E402

F_BODY = Font(name="Arial", size=10)
F_BOLD = Font(name="Arial", size=10, bold=True)
F_TITLE = Font(name="Arial", size=14, bold=True, color="FF1F4E78")
F_HDR = Font(name="Arial", size=10, bold=True, color="FFFFFFFF")
F_PURPLE = Font(name="Arial", size=10, color="FF7030A0")
F_GREEN = Font(name="Arial", size=10, color="FF008000")
F_BLUE = Font(name="Arial", size=10, color="FF0000FF")
F_KEY = Font(name="Arial", size=11, bold=True, color="FFC00000")
F_BOX = Font(name="Arial", size=10, color="FF1F3864")
F_RED = Font(name="Arial", size=10, bold=True, color="FFC00000")
FILL_HDR = PatternFill("solid", fgColor="FF1F4E78")
FILL_IN = PatternFill("solid", fgColor="FFFFF2CC")
FILL_KEY = PatternFill("solid", fgColor="FFE2EFDA")
FILL_BOX = PatternFill("solid", fgColor="FFEEF3F8")
FILL_SUB = PatternFill("solid", fgColor="FFD9E1F2")
WRAP = Alignment(wrap_text=True, vertical="top")
D = "'02_Data'!"


def RNG(c):
    return f"{D}${c}$2:${c}$2954"


def q(name):
    return f"'{name}'!"


def put(ws, ref, val, kind="f", nf=None):
    c = ws[ref]
    c.value = None if (isinstance(val, float) and math.isnan(val)) else val
    c.font = {"f": F_BODY, "b": F_BOLD, "p": F_PURPLE, "g": F_GREEN, "i": F_BLUE, "k": F_KEY, "r": F_RED}[kind]
    if kind == "i":
        c.fill = FILL_IN
    if kind == "k":
        c.fill = FILL_KEY
    if nf:
        c.number_format = nf
    return c


def title(ws, text):
    ws["A1"] = text
    ws["A1"].font = F_TITLE


def hdr(ws, row, col0, labels):
    for j, lab in enumerate(labels):
        c = ws.cell(row, col0 + j, lab)
        c.font, c.fill = F_HDR, FILL_HDR
        c.alignment = Alignment(wrap_text=True, vertical="center")


def box(ws, rng, text):
    ws.merge_cells(rng)
    c = ws[rng.split(":")[0]]
    c.value, c.font, c.fill, c.alignment = text, F_BOX, FILL_BOX, WRAP


def widths(ws, d):
    for k, v in d.items():
        ws.column_dimensions[k].width = v


PALETTE = ["1F4E78", "C00000", "70AD47", "ED7D31", "7030A0", "808080", "00B0F0"]


def fix_chart(ch, axes=True):
    """Explicit line/fill properties on every series (without them Excel draws line/scatter series invisible)."""
    ch.roundedCorners = False
    for i, s in enumerate(ch.series):
        clr = PALETTE[i % len(PALETTE)]
        if isinstance(ch, (LineChart, ScatterChart)):
            s.graphicalProperties = GraphicalProperties(ln=LineProperties(solidFill=clr, w=19050))
            s.marker.symbol = "none"
            s.smooth = False
        else:
            s.graphicalProperties = GraphicalProperties(solidFill=clr, ln=LineProperties(solidFill=clr))
    if ch.legend is not None:
        ch.legend.overlay = False
        ch.legend.position = "b"
    if axes:
        ch.x_axis.delete = False
        ch.y_axis.delete = False
    return ch


def col(n):
    return openpyxl.utils.get_column_letter(n)


def errbars(ref_f):
    ref = NumDataSource(numRef=NumRef(f=ref_f))
    return ErrorBars(errDir="y", errBarType="both", errValType="cust", plus=ref, minus=ref, noEndCap=False,
                     spPr=GraphicalProperties(ln=LineProperties(solidFill="000000", w=12700)))


# ======================================================================================= sheets
def sheet_03(wb):
    ws = wb["03_Cleaning"]
    put(ws, "B33", "v2 update (Phase 1R, plan decision D5): long stays now ENTER the service pool", "b")
    hdr(ws, 34, 2, ["Check (v2)", "Count", "Rule applied (v2)", "Reason"])
    rows = [
        ("Weekday stays longer than max (> 24 h)", "=C19", "INCLUDED in the band pools (band_long)",
         "Validation (15b_Validation_v2): without them mean occupancy is under-stated (A/B model -0.50 cars, CI excludes 0; "
         "daily-peak KS p = 0.044); with them every pre-written criterion passes. Decision D5."),
        ("v2 service pool = all weekday sessions", "=C17", "USED for service times (v2)",
         "Empirical stay by arrival band (6 bands); see 08b_Service_Bands."),
        ("   band 05-07", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=5\",{RNG('J')},\"<8\")", "08b", ""),
        ("   band 08-09", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=8\",{RNG('J')},\"<10\")", "08b", ""),
        ("   band 10-11", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=10\",{RNG('J')},\"<12\")", "08b", ""),
        ("   band 12-15", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=12\",{RNG('J')},\"<16\")", "08b", ""),
        ("   band 16-20", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=16\",{RNG('J')},\"<21\")", "08b", ""),
        ("   band 21-04", f"=COUNTIFS({RNG('M')},1,{RNG('J')},\">=21\")+COUNTIFS({RNG('M')},1,{RNG('J')},\"<5\")", "08b", ""),
        ("Check: bands add up to the v2 pool", "=IF(SUM(C37:C42)=C36,\"OK ✓\",\"CHECK ✗\")", "", ""),
    ]
    for i, (a, b, c, d) in enumerate(rows):
        r = 35 + i
        put(ws, f"B{r}", a)
        put(ws, f"C{r}", b, nf="#,##0")
        put(ws, f"D{r}", c)
        put(ws, f"E{r}", d)
        ws[f"E{r}"].alignment = WRAP
    for r in (35, 36):
        for cc in "BCDE":
            ws[f"{cc}{r}"].fill = FILL_KEY
    ws["D19"].value = "Exclude from v1 pool; INCLUDED in v2 (row 35)"


def sheet_04b(wb, res, wd):
    ws = wb.create_sheet("04b_DayOfWeek", wb.sheetnames.index("04_Stationarity") + 1)
    title(ws, "Step 3b - Day-of-week effect, dispersion of daily counts and the design-day rate table (v2, task R5)")
    box(ws, "A3:M6", "Do weekdays differ? Daily weekday arrivals are counted by formula from 02_Data and grouped by day of week. "
        "The ANOVA table is computed by formula (F.DIST.RT); Kruskal-Wallis and Levene come from Python (purple, results/phase1r/"
        "r5_dow_tests.csv). Fridays are clearly lighter (p < 0.01), so the base case uses pooled weekday rates and a DESIGN DAY "
        "(Tue + Wed rates) is reported beside it (plan D6). The daily counts are UNDER-dispersed (variance < mean, also within "
        "day of week): a Poisson-day NHPP therefore produces more day-to-day variation than observed, i.e. it is conservative.")
    hdr(ws, 9, 1, ["Date", "Day of week (1=Mon)", "Weekday arrivals"])
    for i, d in enumerate(wd):
        r = 10 + i
        put(ws, f"A{r}", d.to_pydatetime(), "p", "yyyy-mm-dd")
        put(ws, f"B{r}", f"=WEEKDAY(A{r},2)")
        put(ws, f"C{r}", f"=COUNTIFS({RNG('H')},A{r},{RNG('M')},1)", nf="0")
    hdr(ws, 9, 5, ["DOW", "Day", "n days", "Mean arrivals", "Variance", "St. dev.", "95% CI half-width", "Lower 95%", "Upper 95%"])
    for k, nm in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        r = 10 + k
        put(ws, f"E{r}", k + 1, "i")
        put(ws, f"F{r}", nm)
        put(ws, f"G{r}", f"=COUNTIF($B$10:$B$74,E{r})", nf="0")
        put(ws, f"H{r}", f"=AVERAGEIF($B$10:$B$74,E{r},$C$10:$C$74)", nf="0.00")
        put(ws, f"I{r}", f"=SUMPRODUCT(($B$10:$B$74=E{r})*($C$10:$C$74-H{r})^2)/(G{r}-1)", nf="0.00")
        put(ws, f"J{r}", f"=SQRT(I{r})", nf="0.00")
        put(ws, f"K{r}", f"=TINV(0.05,G{r}-1)*J{r}/SQRT(G{r})", nf="0.00")
        put(ws, f"L{r}", f"=H{r}-K{r}", nf="0.00")
        put(ws, f"M{r}", f"=H{r}+K{r}", nf="0.00")
    put(ws, "F15", "All", "b")
    put(ws, "G15", "=COUNT(C10:C74)", nf="0")
    put(ws, "H15", "=AVERAGE(C10:C74)", nf="0.00")
    put(ws, "I15", "=VAR(C10:C74)", nf="0.00")
    put(ws, "J15", "=SQRT(I15)", nf="0.00")
    hdr(ws, 18, 5, ["One-way ANOVA (by formula)", "Value"])
    an = [("SS between (SSB)", "=SUMPRODUCT(G10:G14,(H10:H14-H15)^2)", "0.00"),
          ("SS within (SSW)", "=SUMPRODUCT(G10:G14-1,I10:I14)", "0.00"),
          ("df between", "=COUNT(E10:E14)-1", "0"), ("df within", "=G15-COUNT(E10:E14)", "0"),
          ("MS between", "=F19/F21", "0.00"), ("MS within", "=F20/F22", "0.00"), ("F", "=F23/F24", "0.000"),
          ("p-value  F.DIST.RT(F, df1, df2)", "=_xlfn.F.DIST.RT(F25,F21,F22)", "0.0000"),
          ("Check SSB + SSW = (n-1) x total variance", "=IF(ABS(F19+F20-(G15-1)*I15)<1E-6,\"OK ✓\",\"CHECK ✗\")", None),
          ("Verdict (5% level)", "=IF(F26<0.05,\"Days differ - report a design day\",\"No day-of-week effect\")", None)]
    for i, (a, f, nf) in enumerate(an):
        put(ws, f"E{19 + i}", a)
        put(ws, f"F{19 + i}", f, "k" if i in (7, 9) else "f", nf)
    T = pd.read_csv(res / "r5_dow_tests.csv").set_index("test")
    hdr(ws, 31, 5, ["From Python (r5_dow_tests.csv)", "Statistic", "p-value"])
    for i, (lab, key) in enumerate([("Kruskal-Wallis H", "Kruskal-Wallis H"), ("Levene (median) W", "Levene (median) W"),
                                    ("One-way ANOVA F (Python check)", "one-way ANOVA F")]):
        put(ws, f"E{32 + i}", lab)
        put(ws, f"F{32 + i}", float(T.loc[key, "value"]), "p", "0.000")
        put(ws, f"G{32 + i}", float(T.loc[key, "p"]), "p", "0.0000")
    put(ws, "E35", "Check: ANOVA F by formula = Python F")
    put(ws, "F35", "=IF(ABS(F25-F34)<1E-6,\"OK ✓\",\"CHECK ✗\")")
    hdr(ws, 38, 5, ["Dispersion of daily counts (by formula)", "Value"])
    dp = [("Index of dispersion = variance / mean", "=I15/H15", "0.000"),
          ("Chi-square = (n-1) var / mean", "=(G15-1)*I15/H15", "0.00"),
          ("Lower-tail p  CHISQ.DIST(chi2, n-1, TRUE)", "=_xlfn.CHISQ.DIST(F40,G15-1,TRUE)", "0.0000"),
          ("Two-sided p", "=2*MIN(F41,1-F41)", "0.0000"),
          ("Within-DOW index (SSW/df_within)/mean", "=(F20/F22)/H15", "0.000"),
          ("Within-DOW chi-square = SSW / mean", "=F20/H15", "0.00"),
          ("Within-DOW lower-tail p", "=_xlfn.CHISQ.DIST(F44,F22,TRUE)", "0.0000"),
          ("Lag-1 autocorrelation of daily counts", "=CORREL(C10:C73,C11:C74)", "0.000"),
          ("Verdict", "=IF(F41<0.05,\"Under-dispersed: Poisson-day NHPP is conservative\",\"Consistent with Poisson\")", None)]
    for i, (a, f, nf) in enumerate(dp):
        put(ws, f"E{39 + i}", a)
        put(ws, f"F{39 + i}", f, "k" if i in (0, 8) else "f", nf)
    dd = pd.read_csv(res.parent.parent / "data" / "derived" / "rates_designday.csv")
    hdr(ws, 9, 15, ["Slot", "Start (min)", "Pooled rate (arrivals / 30 min)", "Design-day rate (Tue + Wed)",
                    "Ratio design / pooled", "rates_designday.csv (Python)", "Difference"])
    for k in range(48):
        r = 10 + k
        put(ws, f"O{r}", k)
        put(ws, f"P{r}", f"=O{r}*30")
        put(ws, f"Q{r}", f"=COUNTIFS({RNG('K')},O{r},{RNG('M')},1)/'01_Plan'!$C$6", nf="0.0000")
        put(ws, f"R{r}", f"=(COUNTIFS({RNG('K')},O{r},{RNG('M')},1,{RNG('I')},2)+COUNTIFS({RNG('K')},O{r},{RNG('M')},1,{RNG('I')},3))"
                         f"/($G$11+$G$12)", nf="0.0000")
        put(ws, f"S{r}", f"=IF(Q{r}>0,R{r}/Q{r},\"\")", nf="0.00")
        put(ws, f"T{r}", float(dd.rate_designday[k]), "p", "0.0000")
        put(ws, f"U{r}", f"=R{r}-T{r}", nf="0.0E+00")
    put(ws, "O58", "Total per day", "b")
    put(ws, "Q58", "=SUM(Q10:Q57)", "k", "0.00")
    put(ws, "R58", "=SUM(R10:R57)", "k", "0.00")
    put(ws, "S58", "=R58/Q58", "f", "0.000")
    put(ws, "U58", "=IF(MAX(U10:U57)-MIN(U10:U57)<1E-9,\"matches Python ✓\",\"CHECK ✗\")")
    widths(ws, {"A": 12, "B": 10, "C": 10, "E": 40, "F": 22, "G": 12, "H": 12, "I": 10, "J": 9, "K": 11, "L": 10, "M": 10,
                "O": 6, "P": 9, "Q": 13, "R": 13, "S": 10, "T": 14, "U": 12})
    ch = BarChart()
    ch.title = "Mean weekday arrivals by day of week (95% CI)"
    ch.y_axis.title = "arrivals per day"
    ch.add_data(Reference(ws, min_col=8, min_row=9, max_row=14), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=6, min_row=10, max_row=14))
    ch.series[0].errBars = errbars(f"{q(ws.title)}$K$10:$K$14")
    ch.y_axis.scaling.min = 25
    ch.legend = None
    ch.height, ch.width = 7.5, 14
    ws.add_chart(fix_chart(ch), "H18")


def sheet_07b(wb, res):
    ws = wb.create_sheet("07b_Fit_Revised", wb.sheetnames.index("08_Fit_Service_B") + 1)
    title(ws, "Step 3g - Revised fitting (v2, task R1): MLE + parametric-bootstrap goodness of fit")
    box(ws, "A3:N7", "Every input was refitted by maximum likelihood (9 families + lognormal mixtures K = 1-5) and tested with KS and "
        "Anderson-Darling p-values from a PARAMETRIC BOOTSTRAP (500 resamples: simulate from the fit, refit, recompute), plus "
        "chi-square with equiprobable bins and df = k - 1 - p. Purple values: results/phase1r/fit_summary.csv, fit_service_class.csv, "
        "fit_check_mixA4_refit.csv (scripts/fit_input_models.py, seed 20261114). The verdict columns are formulas. Sheets 06-08 (v1) used "
        "moment/regression estimators and the standard tables of critical values; those tables assume known parameters, so with "
        "estimated parameters they are too lenient. 07 and 08 are kept as v1 for transparency and are SUPERSEDED by this sheet. "
        "Result: interarrival gaps are Exp(1) (accepted); NO parametric model is accepted for class A (incl. the 4-component "
        "mixture); class B only a 5-component mixture; so the model uses the EMPIRICAL stay distribution by arrival band (08b).")
    S = pd.read_csv(res / "fit_summary.csv")
    hdr(ws, 9, 1, ["Input", "n", "Best by BIC", "Best single family", "AD (best family)", "AD bootstrap p", "KS bootstrap p",
                   "Chi-square p", "Models accepted (both bootstrap p > 0.05)", "Verdict"])
    for i, r in enumerate(S.itertuples()):
        rr = 10 + i
        for j, (v, nf) in enumerate([(r.input, None), (int(r.n), "0"), (r.best_BIC, None), (r.best_family, None),
                                     (float(r.best_family_AD), "0.000"), (float(r.best_family_AD_p), "0.000"),
                                     (float(r.best_family_KS_p), "0.000"), (float(r.best_family_chi2_p), "0.0E+00"), (r.accepted, None)]):
            put(ws, f"{col(1 + j)}{rr}", v, "p", nf)
        put(ws, f"J{rr}", f"=IF(I{rr}=\"none\",\"no parametric model -> empirical\",\"accepted: \"&I{rr})")
    C = pd.read_csv(res / "fit_service_class.csv")
    r0 = 10 + len(S) + 3
    last = r0 + len(C)
    put(ws, f"A{r0 - 1}", "Class A and class B in detail (fit_service_class.csv)", "b")
    hdr(ws, r0, 1, ["Input", "Model", "Free parameters", "Log-likelihood", "AIC", "BIC", "dBIC (formula)", "KS", "KS bootstrap p",
                    "AD", "AD bootstrap p", "Chi-square p", "Verdict (formula)", "AD bootstrap 95th pct"])
    for i, r in enumerate(C.itertuples()):
        rr = r0 + 1 + i
        for j, (v, nf) in enumerate([(r.input, None), (r.model, None), (int(r.n_par), "0"), (float(r.LL), "0.0"), (float(r.AIC), "0.0"),
                                     (float(r.BIC), "0.0")]):
            put(ws, f"{col(1 + j)}{rr}", v, "p", nf)
        put(ws, f"G{rr}", f"=F{rr}-_xlfn.MINIFS($F${r0 + 1}:$F${last},$A${r0 + 1}:$A${last},A{rr})", nf="0.0")
        for j, (v, nf) in enumerate([(float(r.KS), "0.0000"), (float(r.KS_boot_p), "0.000"), (float(r.AD), "0.000"),
                                     (float(r.AD_boot_p), "0.000"), (float(r.chi2_p), "0.0E+00")]):
            put(ws, f"{col(8 + j)}{rr}", v, "p", nf)
        put(ws, f"M{rr}", f"=IF(AND(I{rr}>0.05,K{rr}>0.05),\"accepted\",\"rejected\")")
        put(ws, f"N{rr}", float(r.AD_boot_q95), "p", "0.000")
    rA = [r0 + 1 + i for i, r in enumerate(C.itertuples()) if r.input == "svc_A"]
    R3 = pd.read_csv(res / "fit_check_mixA4_refit.csv")
    r1 = last + 4
    put(ws, f"A{r1 - 1}", "Why the class-A 4-component mixture was 'accepted' in the first review (fit_check_mixA4_refit.csv)", "b")
    hdr(ws, r1, 1, ["Bootstrap refit rule", "n", "AD (data)", "Mean bootstrap AD", "95th pct bootstrap AD", "AD bootstrap p",
                    "KS bootstrap p", "Verdict (formula)"])
    lab = {"warm+2": "warm start + 2 random starts (used)", "random2": "2 random starts (first review)", "random20": "20 random starts"}
    for i, r in enumerate(R3.itertuples()):
        rr = r1 + 1 + i
        for j, (v, nf) in enumerate([(lab[r.refit], None), (int(r.n), "0"), (float(r.AD), "0.000"), (float(r.AD_boot_mean), "0.000"),
                                     (float(r.AD_boot_q95), "0.000"), (float(r.AD_boot_p), "0.000"), (float(r.KS_boot_p), "0.000")]):
            put(ws, f"{col(1 + j)}{rr}", v, "p", nf)
        put(ws, f"H{rr}", f"=IF(AND(F{rr}>0.05,G{rr}>0.05),\"accepted\",\"rejected\")")
    put(ws, f"A{r1 + 5}", "A weak refit stops in poor local optima, inflates the bootstrap statistics and so the p-value; with an "
        "adequate refit the mixture is rejected.")
    widths(ws, {"A": 34, "B": 10, "C": 14, "D": 16, "E": 12, "F": 12, "G": 12, "H": 12, "I": 34, "J": 30, "K": 12, "L": 12, "M": 14, "N": 14})
    ch = BarChart()
    ch.title = "Class A: Anderson-Darling statistic vs bootstrap 95% critical value (log scale)"
    ch.y_axis.title = "AD"
    ch.series.append(Series(Reference(ws, min_col=10, min_row=rA[0], max_row=rA[-1]), title="AD (data)"))
    ch.series.append(Series(Reference(ws, min_col=14, min_row=rA[0], max_row=rA[-1]), title="bootstrap 95% critical value"))
    ch.set_categories(Reference(ws, min_col=2, min_row=rA[0], max_row=rA[-1]))
    ch.y_axis.scaling.logBase = 10
    ch.height, ch.width = 7.5, 16
    ws.add_chart(fix_chart(ch), f"P{r0}")
    for nm in ("07_Fit_Service_A", "08_Fit_Service_B"):
        put(wb[nm], "A2", "SUPERSEDED (v1): moment/regression estimators with standard critical values. Current fits: 07b_Fit_Revised.", "r")


def sheet_08b(wb, res, ev, df):
    ws = wb.create_sheet("08b_Service_Bands", wb.sheetnames.index("07b_Fit_Revised") + 1)
    title(ws, "Step 3h - Stay depends on arrival time: 6 arrival bands, empirical pools incl. stays > 24 h (v2 base model, D5)")
    box(ws, "A3:R7", "Mean stay changes strongly with the arrival hour (06h 6.1 h, 07h 8.5 h, 13h 3.9 h, 16h 2.2 h). The v2 model draws "
        "a car's stay from the empirical pool of its ARRIVAL BAND (05-07, 08-09, 10-11, 12-15, 16-20, 21-04), weekday sessions "
        "including stays > 24 h: X = x(ceil(U n)). The bands were fixed before validation; they explain R^2 = 0.256 of ln(stay) "
        "vs 0.284 for the best possible 6-band split and 0.204 for the v1 A/B classes (r2_partition.csv). Counts and means by hour are "
        "formulas on 02_Data; medians, R^2 and the sorted pools are purple (Python, results/phase1r). The percentile table and the "
        "BandOfHour24 lookup are the FlexSim input tables (18_FlexSim_Inputs).")
    H = pd.read_csv(res / "r2_dwell_by_hour.csv")
    hdr(ws, 9, 1, ["Hour", "Band", "n weekday", "n > 24 h", "Mean stay (h)", "Median stay (h)", "Mean stay <= 24 h (h)", "Sum of stays (h)"])
    for h in range(24):
        r = 10 + h
        put(ws, f"A{r}", h)
        put(ws, f"B{r}", f"=INDEX($M$10:$M$15,J{r})")
        put(ws, f"C{r}", f"=COUNTIFS({RNG('J')},A{r},{RNG('M')},1)", nf="0")
        put(ws, f"D{r}", f"=COUNTIFS({RNG('J')},A{r},{RNG('M')},1,{RNG('L')},\">24\")", nf="0")
        put(ws, f"E{r}", f"=IF(C{r}>0,AVERAGEIFS({RNG('L')},{RNG('J')},A{r},{RNG('M')},1),\"\")", nf="0.00")
        put(ws, f"F{r}", None if np.isnan(H.median_all[h]) else float(H.median_all[h]), "p", "0.00")
        put(ws, f"G{r}", f"=IF(C{r}-D{r}>0,AVERAGEIFS({RNG('L')},{RNG('J')},A{r},{RNG('M')},1,{RNG('L')},\"<=24\"),\"\")", nf="0.00")
        put(ws, f"H{r}", f"=SUMIFS({RNG('L')},{RNG('J')},A{r},{RNG('M')},1)", nf="0.00")
    put(ws, "A34", "Total", "b")
    put(ws, "C34", "=SUM(C10:C33)", nf="0")
    put(ws, "D34", "=SUM(D10:D33)", nf="0")
    put(ws, "H34", "=SUM(H10:H33)", nf="0.00")
    hdr(ws, 9, 9, ["BandOfHour24: hour", "Band (1-6)", "Band label"])
    bo = ev.band_of(np.arange(24)) + 1
    for h in range(24):
        r = 10 + h
        put(ws, f"I{r}", h)
        put(ws, f"J{r}", int(bo[h]), "p", "0")
        put(ws, f"K{r}", f"=INDEX($M$10:$M$15,J{r})")
    pools = ev.band_pools(df, long_stays=True)
    hdr(ws, 9, 13, ["Band", "Index", "n (by formula)", "Mean stay (h)", "Pool n", "Pool sum (h)", "Check vs 02_Data"])
    for b in range(6):
        r = 10 + b
        pc = col(28 + b)
        put(ws, f"M{r}", ev.BAND_LABELS[b], "p")
        put(ws, f"N{r}", b + 1)
        put(ws, f"O{r}", f"=SUMIF($J$10:$J$33,N{r},$C$10:$C$33)", nf="0")
        put(ws, f"P{r}", f"=SUMIF($J$10:$J$33,N{r},$H$10:$H$33)/O{r}", nf="0.00")
        put(ws, f"Q{r}", f"=COUNT(${pc}$10:${pc}$1044)", nf="0")
        put(ws, f"R{r}", f"=SUM(${pc}$10:${pc}$1044)", nf="0.00")
        put(ws, f"S{r}", f"=IF(AND(Q{r}=O{r},ABS(R{r}-P{r}*O{r})<=1E-9*R{r}),\"MATCH ✓\",\"CHECK ✗\")")
    P = pd.read_csv(res / "r2_partition.csv")
    hdr(ws, 18, 13, ["Partition of the 24 hours (r2_partition.csv)", "Pool", "k", "R^2 of ln(stay)", "Bands"])
    sel = P[P.partition.isin(["A/B classes (v1)", "chosen 6 bands", "optimal k=6", "24 single hours"])]
    for i, r in enumerate(sel.itertuples()):
        rr = 19 + i
        for j, (v, nf) in enumerate([(r.partition, None), (r.pool, None), (int(r.k), "0"), (float(r.R2), "0.000"), (r.bands, None)]):
            put(ws, f"{col(13 + j)}{rr}", v, "p", nf)
    hdr(ws, 9, 20, ["Cumulative prob. p"] + [f"Band {lab} (h)" for lab in ev.BAND_LABELS])
    for i in range(101):
        r = 10 + i
        put(ws, f"T{r}", i / 100, "f", "0.00")
        for b in range(6):
            pc = col(28 + b)
            put(ws, f"{col(21 + b)}{r}", f"=INDEX(${pc}$10:${pc}$1044,MAX(1,CEILING(T{r}*$Q${10 + b},1)))", nf="0.000")
    hdr(ws, 9, 28, [f"Pool {lab} sorted (h)" for lab in ev.BAND_LABELS])
    for b, Pb in enumerate(pools):
        for i, v in enumerate(Pb):
            c = ws.cell(10 + i, 28 + b, float(v))
            c.font, c.number_format = F_PURPLE, "0.0000"
    put(ws, "AB8", "Sorted pools = engine ServiceModel('band_long') (purple); used by 10b and FlexSim", "b")
    widths(ws, {"A": 6, "B": 8, "C": 10, "D": 9, "E": 11, "F": 11, "G": 12, "H": 12, "I": 10, "J": 9, "K": 9, "M": 26, "N": 12, "O": 12,
                "P": 12, "Q": 30, "R": 12, "S": 14, "T": 10})
    ch = LineChart()
    ch.title = "Mean and median stay by arrival hour (weekdays)"
    ch.y_axis.title = "stay (h)"
    ch.x_axis.title = "arrival hour"
    ch.add_data(Reference(ws, min_col=5, min_row=9, max_row=33), titles_from_data=True)
    ch.add_data(Reference(ws, min_col=6, min_row=9, max_row=33), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=10, max_row=33))
    ch.height, ch.width = 7.5, 16
    ws.add_chart(fix_chart(ch), "A37")
    ch2 = ScatterChart()
    ch2.title = "Empirical CDF of stay by arrival band"
    ch2.x_axis.title = "stay (h)"
    ch2.y_axis.title = "cumulative probability"
    yref = Reference(ws, min_col=20, min_row=10, max_row=110)
    for b in range(6):
        s = Series(yref, Reference(ws, min_col=21 + b, min_row=10, max_row=110), title=f"band {ev.BAND_LABELS[b]}")
        s.marker.symbol = "none"
        ch2.series.append(s)
    ch2.x_axis.scaling.min, ch2.x_axis.scaling.max = 0, 24
    ch2.style = 13
    ch2.height, ch2.width = 7.5, 16
    ws.add_chart(fix_chart(ch2), "A53")


def sheet_10b(wb, res, ev, df):
    src = "10_Replica_Rep1"
    ws = wb.create_sheet("10b_Replica_band_long", wb.sheetnames.index(src) + 1)
    title(ws, "Step 4b - One FULL replication with the v2 service model (stay by arrival band, incl. stays > 24 h), formulas only")
    put(ws, "A3", "Growth m", "b")
    put(ws, "B3", 1.3, "i", "0.00")
    put(ws, "A4", "Chargers c", "b")
    put(ws, "B4", 42, "i", "0")
    put(ws, "A5", "Rows available", "b")
    put(ws, "B5", 4500)
    for c0, lab in (("D3", "Results of this replication"), ("G3", "Engine (band_long, rep 1)"), ("I3", "Relative difference"),
                    ("J3", "Check")):
        put(ws, c0, lab, "b")
        ws[c0].fill = FILL_SUB
    res_rows = [("Cars arriving in 65 weekdays", "=SUM(I12:I4511)", "#,##0", "N"),
                ("Mean wait Wq (min)", "=AVERAGE(O12:O4511)", "0.000000", "Wq"),
                ("P(wait > 0)", "=COUNTIF(O12:O4511,\">1E-9\")/E4", "0.0000%", "P0"),
                ("P(wait > target)", "=COUNTIF(O12:O4511,\">\"&'01_Plan'!$C$11)/E4", "0.0000%", "P15"),
                ("95th percentile wait W95 (min)", "=PERCENTILE(O12:O4511,0.95)", "0.000000", "W95")]
    colmap = {"N": "T", "Wq": "U", "P0": "V", "P15": "W", "W95": "X"}
    for i, (lab, f, nf, k) in enumerate(res_rows):
        r = 4 + i
        put(ws, f"D{r}", lab, "b")
        put(ws, f"E{r}", f, "k", nf)
        put(ws, f"G{r}", f"=IFERROR(INDEX(${colmap[k]}$4:${colmap[k]}$17,MATCH(TEXT($B$4,\"0\")&\"|\"&TEXT($B$3,\"0.00\"),$Q$4:$Q$17,0)),\"n/a\")",
            "p", nf)
        put(ws, f"I{r}", f"=IF(ISNUMBER(G{r}),ABS(E{r}-G{r})/MAX(ABS(G{r}),1E-300),\"n/a\")", nf="0.0E+00")
        if k in ("N", "W95"):
            put(ws, f"J{r}", f"=IF(ISNUMBER(G{r}),IF(E{r}=G{r},\"EXACT ✓\",\"DIFFERENT ✗\"),\"no engine run\")", "b")
        else:
            put(ws, f"J{r}", f"=IF(ISNUMBER(G{r}),IF(I{r}<=1E-12,\"MATCH ✓ (<= 1e-12)\",\"DIFFERENT ✗\"),\"no engine run\")", "b")
    hdr(ws, 3, 17, ["key", "c", "m", "N", "Wq", "P0", "P15", "W95"])
    rates, A, B = ev.inputs(df)
    mod = ev.ServiceModel("band_long", df)
    eng = []
    for c, m in [(c, 1.3) for c in range(40, 53)] + [(52, 1.0)]:
        o = ev.replicate(rates, A, B, c, 1, m, model=mod)[0]
        eng.append(dict(c=c, m=m, **{k: o[k] for k in ("N", "Wq", "P0", "P15", "W95")}))
    E = pd.DataFrame(eng)
    E.to_csv(res / "excel_replica_rep1_engine.csv", index=False)
    for i, r in enumerate(E.itertuples()):
        rr = 4 + i
        put(ws, f"Q{rr}", f"=TEXT(R{rr},\"0\")&\"|\"&TEXT(S{rr},\"0.00\")")
        for j, v in enumerate([r.c, r.m, r.N, r.Wq, r.P0, r.P15, r.W95]):
            put(ws, f"{col(18 + j)}{rr}", float(v), "p")
    put(ws, "Q18", "Engine values: results/phase1r/excel_replica_rep1_engine.csv (engine ServiceModel('band_long'), rep 1)")
    box(ws, "A9:O10", "Same random numbers as 10_Replica_Rep1 (U1, U2 of replication 1, green links) and the same arrival formulas; only the "
        "stay changes: band = BandOfHour24(hour of arrival) and stay = x(ceil(U2 n_band)) from the sorted band pool in 08b_Service_Bands "
        "(incl. stays > 24 h). Pass rule (G0): relative difference <= 1e-12, N and W95 exactly equal. Change c (B4) or m (B3): if the "
        "engine table has that case, the check updates.")
    hdr(ws, 11, 1, ["Car j", "U1 (arrival)", "E = -ln(1-U1)", "L = cumulative E", "Day index", "rem", "Slot k", "Arrival t (h)",
                    "Within horizon?", "Band (1-6)", "U2 (service)", "Stay (h) = x(ceil(U2 n_band))", "Start", "Departure", "Wait (min)"])
    a5 = "'05_Arrivals'!"
    for j in range(1, 4501):
        r = 11 + j
        ws.cell(r, 1, j)
        ws.cell(r, 2, f"='{src}'!B{r}").font = F_GREEN
        ws.cell(r, 3, f"=-LN(1-B{r})")
        ws.cell(r, 4, f"=C{r}" if j == 1 else f"=D{r - 1}+C{r}")
        ws.cell(r, 5, f"=INT(D{r}/({a5}$D$55*$B$3))")
        ws.cell(r, 6, f"=(D{r}-E{r}*{a5}$D$55*$B$3)/$B$3")
        ws.cell(r, 7, f"=MATCH(F{r},{a5}$F$6:$F$53,1)-1")
        ws.cell(r, 8, f"=E{r}*24+G{r}*0.5+(F{r}-INDEX({a5}$F$6:$F$53,G{r}+1))/INDEX({a5}$D$6:$D$53,G{r}+1)*0.5")
        ws.cell(r, 9, f"=IF(H{r}<'01_Plan'!$C$14,1,0)")
        ws.cell(r, 10, f"=INDEX('08b_Service_Bands'!$J$10:$J$33,INT(MOD(H{r},24))+1)")
        ws.cell(r, 11, f"='{src}'!K{r}").font = F_GREEN
        ws.cell(r, 12, f"=INDEX('08b_Service_Bands'!$AB$10:$AG$1044,MAX(1,CEILING(K{r}*INDEX('08b_Service_Bands'!$Q$10:$Q$15,J{r}),1)),J{r})")
        ws.cell(r, 13, f"=H{r}" if j == 1 else f"=IF(A{r}<=$B$4,H{r},MAX(H{r},SMALL(N$12:N{r - 1},A{r}-$B$4)))")
        ws.cell(r, 14, f"=M{r}+L{r}")
        ws.cell(r, 15, f"=IF(I{r}=1,(M{r}-H{r})*60,\"\")")
    widths(ws, {"A": 7, "B": 11, "D": 30, "E": 14, "G": 14, "H": 14, "I": 12, "J": 18, "L": 14, "M": 12, "N": 12, "O": 10, "Q": 10})
    ch = LineChart()
    ch.title = "Waiting time of each car (min), first 3,300 cars"
    ch.add_data(Reference(ws, min_col=15, min_row=11, max_row=3311), titles_from_data=True)
    ch.legend = None
    ch.height, ch.width = 7, 16
    ws.add_chart(fix_chart(ch), "Q20")
    return E


def sheet_11(wb):
    ws = wb["11_Pilot_n"]
    put(ws, "A6", "t(0.975, n0 - 1)  (v2 rule)", "b")
    put(ws, "B6", "=TINV(0.05,COUNT(B8:B17)-1)", nf="0.000")
    ws["A5"].value = "z (v1, superseded by t in B6)"
    ws["A20"].value = "n required = ROUNDUP((t s / h)^2), t from B6"
    for cc in "BCDEFGHI":
        h = "$B$3" if cc in "BCDE" else "$B$4"
        ws[f"{cc}20"].value = f"=ROUNDUP(($B$6*{cc}19/{h})^2,0)"
    ws["A26"].value = ws["A26"].value + (" v2: the formula now uses t(0.975, n0 - 1) (B6) instead of z, because s comes from only n0 = 10 "
                                         "pilot runs. The final v2 runs (12b-13b) also use the boundary-aimed rule at the right.")
    put(ws, "K3", "Boundary-aimed precision rule (v2, D2 item 1)", "b")
    ws["K3"].font = Font(name="Arial", size=11, bold=True, color="FF1F4E78")
    put(ws, "K4", "Start with n0 replications; while the upper 95% bound of P15 lies within +-band of the 1% threshold, add 'step' "
        "replications (CRN r = 61, 62, ...) until it does not or n = max.")
    for r, (lab, v, nf) in enumerate([("Start n0", 60, "0"), ("Band around threshold (+-)", 0.0015, "0.00%"), ("Step", 20, "0"),
                                      ("Maximum n", 200, "0")]):
        put(ws, f"K{5 + r}", lab)
        put(ws, f"L{5 + r}", v, "i", nf)
    hdr(ws, 10, 11, ["c", "n used (13b)", "Upper 95% P15 (13b)", "|upper - threshold|", "Inside band?", "Rule satisfied?"])
    for i, c in enumerate(range(40, 53)):
        r = 11 + i
        put(ws, f"K{r}", c)
        put(ws, f"L{r}", f"=INDEX('13b_Output_CI_v2'!$B$8:$B$20,MATCH(K{r},'13b_Output_CI_v2'!$A$8:$A$20,0))", "g", "0")
        put(ws, f"M{r}", f"=INDEX('13b_Output_CI_v2'!$H$8:$H$20,MATCH(K{r},'13b_Output_CI_v2'!$A$8:$A$20,0))", "g", "0.000%")
        put(ws, f"N{r}", f"=ABS(M{r}-'01_Plan'!$C$12)", nf="0.000%")
        put(ws, f"O{r}", f"=IF(N{r}<=$L$6,\"yes\",\"no\")")
        put(ws, f"P{r}", f"=IF(OR(N{r}>$L$6,L{r}>=$L$8),\"✓\",\"✗ add replications\")")
    widths(ws, {"K": 26, "L": 12, "M": 14, "N": 14, "O": 11, "P": 18})


def sheet_12b_13b_14b(wb, res):
    R = pd.read_csv(res / "r6_decision_reps.csv")
    R = R[(R.tag == "grid") & (R.service == "band_long") & (R.arrivals == "pooled")]
    cs = list(range(40, 53))
    i12 = wb.sheetnames.index("14_Paired") + 1
    ws = wb.create_sheet("12b_Replications_v2", i12)
    title(ws, "Step 5 (v2) - Replications at +30% demand, c = 40...52, base model band_long (CRN), from the engine")
    box(ws, "A3:AA5", "Per-replication P(wait > 15 min) and mean wait Wq for every c (purple = results/phase1r/r6_decision_reps.csv, "
        "scripts/decision_rule.py; CRN: replication r uses streams [r,1] and [r,2] for every c). 60 replications each; c values whose upper "
        "95% bound fell within +-0.15 pp of 1% received extra replications (r = 61...) up to 200 (boundary-aimed rule, 11_Pilot_n). "
        "Blank = not run.")
    put(ws, "A6", "c ->", "b")
    hdr(ws, 7, 1, ["Rep"] + [f"P15 c={c}" for c in cs] + [f"Wq c={c}" for c in cs])
    for j, c in enumerate(cs):
        put(ws, f"{col(2 + j)}6", c)
        put(ws, f"{col(15 + j)}6", c)
    for r in range(1, 201):
        ws.cell(7 + r, 1, r)
    for j, c in enumerate(cs):
        g = R[R.c == c].set_index("rep")
        for rep, row in g.iterrows():
            a = ws.cell(7 + rep, 2 + j, float(row.P15))
            a.font, a.number_format = F_PURPLE, "0.000%"
            b = ws.cell(7 + rep, 15 + j, float(row.Wq))
            b.font, b.number_format = F_PURPLE, "0.000"
    for j in range(1, 28):
        ws.column_dimensions[col(j)].width = 10
    ch = LineChart()
    ch.title = "P15 per replication: c = 44, 45, 46 (CRN keeps the lines together)"
    for j in (4, 5, 6):
        ch.add_data(Reference(ws, min_col=2 + j, min_row=7, max_row=67), titles_from_data=True)
    ch.y_axis.title = "P15"
    ch.x_axis.title = "replication"
    ch.height, ch.width = 7, 16
    ws.add_chart(fix_chart(ch), "AC7")

    ws = wb.create_sheet("13b_Output_CI_v2", i12 + 1)
    title(ws, "Step 5b (v2) - t-based 95% CI of P(wait > 15) and Wq for every c = 40...52; decision rule by formula")
    box(ws, "A3:P5", "Rule (01_Plan, fixed before simulating): the smallest c whose upper 95% bound of P(wait > 15 min) is <= 1%, at +30% "
        "demand. Here c* is the smallest c such that it AND every larger c pass. All statistics are formulas on 12b; P(wait > 0), W95 and "
        "utilisation are purple means from results/phase1r/r6_decision.csv.")
    hdr(ws, 7, 1, ["c", "n", "Mean P15", "s P15", "t(0.975, n-1)", "Half-width", "Lower 95%", "Upper 95%", "Rule met?",
                   "It and all larger c pass?", "Mean Wq (min)", "s Wq", "Upper 95% Wq", "Mean P(wait>0)", "Mean W95 (min)",
                   "Mean utilisation", "Threshold"])
    Dd = pd.read_csv(res / "r6_decision.csv")
    Dd = Dd[(Dd.service == "band_long") & (Dd.arrivals == "pooled")].set_index("c")
    P15c = "'12b_Replications_v2'!$B$8:$N$207"
    WQc = "'12b_Replications_v2'!$O$8:$AA$207"
    for i, c in enumerate(cs):
        r = 8 + i
        cp = f"INDEX({P15c},0,MATCH($A{r},'12b_Replications_v2'!$B$6:$N$6,0))"
        cw = f"INDEX({WQc},0,MATCH($A{r},'12b_Replications_v2'!$O$6:$AA$6,0))"
        put(ws, f"A{r}", c)
        put(ws, f"B{r}", f"=COUNT({cp})", nf="0")
        put(ws, f"C{r}", f"=AVERAGE({cp})", nf="0.000%")
        put(ws, f"D{r}", f"=STDEV({cp})", nf="0.000%")
        put(ws, f"E{r}", f"=TINV(0.05,B{r}-1)", nf="0.000")
        put(ws, f"F{r}", f"=E{r}*D{r}/SQRT(B{r})", nf="0.000%")
        put(ws, f"G{r}", f"=C{r}-F{r}", nf="0.000%")
        put(ws, f"H{r}", f"=C{r}+F{r}", nf="0.000%")
        put(ws, f"I{r}", f"=IF(H{r}<='01_Plan'!$C$12,\"PASS\",\"FAIL\")")
        put(ws, f"J{r}", f"=I{r}=\"PASS\"" if c == 52 else f"=AND(I{r}=\"PASS\",J{r + 1})")
        put(ws, f"K{r}", f"=AVERAGE({cw})", nf="0.000")
        put(ws, f"L{r}", f"=STDEV({cw})", nf="0.000")
        put(ws, f"M{r}", f"=K{r}+TINV(0.05,COUNT({cw})-1)*L{r}/SQRT(COUNT({cw}))", nf="0.000")
        put(ws, f"N{r}", float(Dd.P0_mean[c]), "p", "0.00%")
        put(ws, f"O{r}", float(Dd.W95_mean[c]), "p", "0.000")
        put(ws, f"P{r}", float(Dd.Util_mean[c]), "p", "0.0%")
        put(ws, f"Q{r}", "='01_Plan'!$C$12", "g", "0.0%")
        put(ws, f"S{r}", float(Dd.P15_upper[c]), "p", "0.0000%")
        put(ws, f"T{r}", f"=ABS(H{r}-S{r})", nf="0.0E+00")
    put(ws, "S7", "Upper (Python)", "b")
    put(ws, "T7", "|diff|", "b")
    put(ws, "A23", "Smallest feasible c* (rule, by formula)", "b")
    put(ws, "D23", "=_xlfn.MINIFS(A8:A20,J8:J20,TRUE)", "k", "0")
    SM = pd.read_csv(res / "r6_smallest_c.csv").set_index(["service", "arrivals"])
    put(ws, "A24", "Engine result (r6_smallest_c.csv)", "b")
    put(ws, "D24", int(SM.loc[("band_long", "pooled"), "c_star"]), "p", "0")
    put(ws, "A25", "Check", "b")
    put(ws, "D25", "=IF(D23=D24,\"MATCH ✓\",\"CHECK ✗\")", "b")
    put(ws, "A26", "Upper bounds vs r6_decision.csv (max |diff|)", "b")
    put(ws, "D26", "=MAX(T8:T20)", nf="0.0E+00")
    put(ws, "E26", "=IF(D26<1E-12,\"MATCH ✓\",\"CHECK ✗\")", "b")
    widths(ws, {"A": 10, "B": 8, "C": 11, "D": 11, "E": 11, "F": 11, "G": 11, "H": 11, "I": 10, "J": 14, "K": 11, "L": 9, "M": 12,
                "N": 12, "O": 11, "P": 11, "Q": 10, "S": 13})
    ch = LineChart()
    ch.title = "P(wait > 15 min) vs chargers, m = 1.3 (band_long, CRN)"
    for cc in (3, 8, 17):
        ch.add_data(Reference(ws, min_col=cc, min_row=7, max_row=20), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=8, max_row=20))
    ch.y_axis.title = "P15"
    ch.x_axis.title = "chargers c"
    ch.y_axis.number_format = "0.0%"
    ch.height, ch.width = 8, 16
    ws.add_chart(fix_chart(ch), "A29")

    ws = wb.create_sheet("14b_Paired_v2", i12 + 2)
    title(ws, "Step 5c (v2) - Paired CRN differences vs the recommended c, Bonferroni-adjusted, and the CRN variance reduction")
    box(ws, "A3:P4", "For every other c, the P15 difference (recommended c* minus c) is computed replication by replication (reps 1-60, the "
        "same random numbers). With k comparisons the familywise level 5% is split Bonferroni-style: each CI uses alpha = 0.05 / k. "
        "CRN efficiency: Var(c*) + Var(c* - 2) (what independent runs would give) divided by Var(paired difference).")
    rows = [("Recommended c* (13b)", "='13b_Output_CI_v2'!D23", "g", "0"),
            ("Number of comparisons k", "=COUNT(B12:N12)-1", "f", "0"),
            ("Familywise alpha", 0.05, "i", "0.00"),
            ("Per-comparison alpha = alpha / k", "=B8/B7", "f", "0.0000"),
            ("Common replications n", 60, "i", "0"),
            ("t(1 - alpha_k / 2, n - 1)", "=TINV(B9,B10-1)", "f", "0.000")]
    for i, (lab, f, k, nf) in enumerate(rows):
        put(ws, f"A{6 + i}", lab, "b")
        put(ws, f"B{6 + i}", f, k, nf)
    put(ws, "A12", "Rep \\ c", "b")
    ws["A12"].font, ws["A12"].fill = F_HDR, FILL_HDR
    for j, c in enumerate(cs):
        cell = ws.cell(12, 2 + j, c)
        cell.font, cell.fill = F_HDR, FILL_HDR
    for rep in range(1, 61):
        r, src_r = 12 + rep, 7 + rep
        ws.cell(r, 1, rep)
        for j in range(13):
            cc = col(2 + j)
            ws.cell(r, 2 + j, f"=INDEX('12b_Replications_v2'!$B{src_r}:$N{src_r},1,MATCH($B$6,'12b_Replications_v2'!$B$6:$N$6,0))"
                              f"-'12b_Replications_v2'!{cc}{src_r}").number_format = "0.000%"
    for i, l in enumerate(["Mean difference (c* - c)", "s of difference", "Bonferroni half-width", "Lower", "Upper", "Significant?"]):
        put(ws, f"A{75 + i}", l, "b")
    for j in range(13):
        cc = col(2 + j)
        put(ws, f"{cc}75", f"=AVERAGE({cc}13:{cc}72)", nf="0.000%")
        put(ws, f"{cc}76", f"=STDEV({cc}13:{cc}72)", nf="0.000%")
        put(ws, f"{cc}77", f"=$B$11*{cc}76/SQRT($B$10)", nf="0.000%")
        put(ws, f"{cc}78", f"={cc}75-{cc}77", nf="0.000%")
        put(ws, f"{cc}79", f"={cc}75+{cc}77", nf="0.000%")
        put(ws, f"{cc}80", f"=IF({cc}12=$B$6,\"(c*)\",IF(OR({cc}78>0,{cc}79<0),\"yes\",\"no\"))")
    put(ws, "A83", "CRN efficiency for (c*, c* - 2), P15, reps 1-60", "b")
    C = pd.read_csv(res / "r6_crn_efficiency.csv").set_index("metric")
    crn = [("Var P15 at c*", "=VAR(INDEX('12b_Replications_v2'!$B$8:$N$67,0,MATCH($B$6,'12b_Replications_v2'!$B$6:$N$6,0)))", "f", "0.0E+00"),
           ("Var P15 at c* - 2", "=VAR(INDEX('12b_Replications_v2'!$B$8:$N$67,0,MATCH($B$6-2,'12b_Replications_v2'!$B$6:$N$6,0)))", "f", "0.0E+00"),
           ("Var of paired difference", "=VAR(INDEX($B$13:$N$72,0,MATCH($B$6-2,$B$12:$N$12,0)))", "f", "0.0E+00"),
           ("Variance-reduction ratio (independent / paired)", "=(B84+B85)/B86", "k", "0.00"),
           ("Python (r6_crn_efficiency.csv)", float(C.loc["P15", "variance_reduction_ratio"]), "p", "0.00"),
           ("Check", "=IF(ABS(B87-B88)<1E-9,\"MATCH ✓\",\"CHECK ✗\")", "f", None),
           ("Wq: variance-reduction ratio (Python)", float(C.loc["Wq", "variance_reduction_ratio"]), "p", "0.00")]
    for i, (lab, f, k, nf) in enumerate(crn):
        put(ws, f"A{84 + i}", lab)
        put(ws, f"B{84 + i}", f, k, nf)
    ws.column_dimensions["A"].width = 44
    ch = BarChart()
    ch.title = "Mean paired difference in P15 (c* minus c), Bonferroni 95%"
    ch.add_data(Reference(ws, min_col=1, max_col=14, min_row=75), from_rows=True, titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, max_col=14, min_row=12))
    ch.series[0].errBars = errbars(f"{q(ws.title)}$B$77:$N$77")
    ch.y_axis.number_format = "0.0%"
    ch.legend = None
    ch.height, ch.width = 7.5, 16
    ws.add_chart(fix_chart(ch), "D83")


def sheet_15b(wb, res):
    ws = wb.create_sheet("15b_Validation_v2", wb.sheetnames.index("15_Validation") + 1)
    title(ws, "Step 5d (v2) - Validation with pre-written criteria (task R4): 6 service models vs the data, m = 1.0, c = 52")
    box(ws, "A3:N6", "Criteria written BEFORE looking at the results: for cars per weekday, mean occupancy, occupancy at 12:00 and the daily "
        "peak, the 95% Welch CI of (model - data) must contain 0, AND the two-sample KS test of the daily peak must give p > 0.05. "
        "Model unit = one replication (mean of its 65 days, 60 replications); data unit = one weekday (all sessions present). "
        "Welch CIs are formulas on the purple per-replication / per-day values (results/phase1r/validation_v2_model_reps.csv, "
        "validation_v2_data_days.csv); Excel's TINV truncates the Welch df to an integer, so the bounds can differ from Python in the "
        "4th digit (Python bounds shown beside). KS p-values are purple (validation_v2.csv).")
    MR = pd.read_csv(res / "validation_v2_model_reps.csv")
    DD = pd.read_csv(res / "validation_v2_data_days.csv")
    V = pd.read_csv(res / "validation_v2.csv")
    PR = pd.read_csv(res / "validation_v2_profile.csv")
    models = list(MR.service.unique())
    mets = [("cars", "Cars per weekday"), ("mean_occ", "Mean occupancy"), ("occ_1200", "Occupancy at 12:00"), ("peak_occ", "Daily peak")]
    c0 = 27
    put(ws, f"{col(c0)}7", "Model per-replication means (purple, validation_v2_model_reps.csv)", "b")
    mcol = {}
    for i, mdl in enumerate(models):
        g = MR[MR.service == mdl].sort_values("rep")
        for j, (k, lab) in enumerate(mets):
            cn = c0 + i * 4 + j
            mcol[(mdl, k)] = col(cn)
            hc = ws.cell(8, cn, f"{mdl} | {lab}")
            hc.font, hc.fill = F_HDR, FILL_HDR
            for t, v in enumerate(g[k].values):
                ws.cell(9 + t, cn, float(v)).font = F_PURPLE
    d0 = c0 + 4 * len(models) + 1
    put(ws, f"{col(d0)}7", "Data per weekday (purple, validation_v2_data_days.csv)", "b")
    dcol = {}
    for j, (k, lab) in enumerate([("date", "Date")] + mets):
        cn = d0 + j
        dcol[k] = col(cn)
        hc = ws.cell(8, cn, lab)
        hc.font, hc.fill = F_HDR, FILL_HDR
        for t, v in enumerate(DD[k].values):
            ws.cell(9 + t, cn, str(v) if k == "date" else float(v)).font = F_PURPLE
    put(ws, "A8", "Summary", "b")
    hdr(ws, 9, 1, ["Service model"] + [lab + " CI contains 0?" for _, lab in mets] + ["KS p (daily peak)", "KS pass?", "OVERALL",
                                                                                     "KS p (half-hour peak, 20 reps)", "Profile RMSE"])
    hdr(ws, 18, 1, ["Service model", "Metric", "Model mean", "Data mean", "Difference", "Var/n model", "Var/n data", "Welch df", "t",
                    "Lower 95%", "Upper 95%", "Contains 0?", "Python lower", "Python upper"])
    r = 19
    for i, mdl in enumerate(models):
        sr = 10 + i
        put(ws, f"A{sr}", mdl, "b")
        for j, (k, lab) in enumerate(mets):
            mc, dc = mcol[(mdl, k)], dcol[k]
            mr_, dr_ = f"${mc}$9:${mc}$68", f"${dc}$9:${dc}$73"
            put(ws, f"A{r}", mdl)
            put(ws, f"B{r}", lab)
            put(ws, f"C{r}", f"=AVERAGE({mr_})", nf="0.000")
            put(ws, f"D{r}", f"=AVERAGE({dr_})", nf="0.000")
            put(ws, f"E{r}", f"=C{r}-D{r}", nf="0.000")
            put(ws, f"F{r}", f"=VAR({mr_})/COUNT({mr_})", nf="0.0000")
            put(ws, f"G{r}", f"=VAR({dr_})/COUNT({dr_})", nf="0.0000")
            put(ws, f"H{r}", f"=(F{r}+G{r})^2/(F{r}^2/(COUNT({mr_})-1)+G{r}^2/(COUNT({dr_})-1))", nf="0.0")
            put(ws, f"I{r}", f"=TINV(0.05,H{r})", nf="0.000")
            put(ws, f"J{r}", f"=E{r}-I{r}*SQRT(F{r}+G{r})", nf="0.000")
            put(ws, f"K{r}", f"=E{r}+I{r}*SQRT(F{r}+G{r})", nf="0.000")
            put(ws, f"L{r}", f"=IF(AND(J{r}<=0,K{r}>=0),\"yes\",\"NO\")")
            vr = V[(V.service == mdl) & (V.test == "Welch CI model-data") & (V.metric == k)].iloc[0]
            put(ws, f"M{r}", float(vr.lo), "p", "0.000")
            put(ws, f"N{r}", float(vr.hi), "p", "0.000")
            put(ws, f"{col(2 + j)}{sr}", f"=L{r}")
            r += 1
        ks = V[(V.service == mdl) & (V.test == "KS 2-sample (primary)")].iloc[0]
        ks2 = V[(V.service == mdl) & (V.test == "KS 2-sample (reviewer def.)")].iloc[0]
        rm = V[(V.service == mdl) & (V.test == "profile")].iloc[0]
        put(ws, f"F{sr}", float(ks.p), "p", "0.000")
        put(ws, f"G{sr}", f"=IF(F{sr}>0.05,\"yes\",\"NO\")")
        put(ws, f"H{sr}", f"=IF(AND(B{sr}=\"yes\",C{sr}=\"yes\",D{sr}=\"yes\",E{sr}=\"yes\",G{sr}=\"yes\"),\"PASS\",\"FAIL\")", "k")
        put(ws, f"I{sr}", float(ks2.p), "p", "0.000")
        put(ws, f"J{sr}", float(rm.stat), "p", "0.00")
    p0 = d0 + len(mets) + 2
    labs = ["Time", "Data mean", "Data half-width", "Data lower", "Data upper", "band_long mean", "band_long half-width",
            "band_long lower", "band_long upper", "AB (v1) mean"]
    for j, lab in enumerate(labs):
        hc = ws.cell(8, p0 + j, lab)
        hc.font, hc.fill = F_HDR, FILL_HDR
    for t in range(48):
        rr = 9 + t
        vals = [PR.time[t], PR.data_mean[t], PR.data_hw95[t], None, None, PR.band_long_mean[t], PR.band_long_hw95[t], None, None,
                PR.AB_mean[t]]
        for j, v in enumerate(vals):
            cl = col(p0 + j)
            if j in (3, 7):
                ws[f"{cl}{rr}"] = f"={col(p0 + j - 2)}{rr}-{col(p0 + j - 1)}{rr}"
            elif j in (4, 8):
                ws[f"{cl}{rr}"] = f"={col(p0 + j - 3)}{rr}+{col(p0 + j - 2)}{rr}"
            else:
                ws[f"{cl}{rr}"] = str(v) if j == 0 else float(v)
                ws[f"{cl}{rr}"].font = F_PURPLE
            if j:
                ws[f"{cl}{rr}"].number_format = "0.00"
    widths(ws, {"A": 16, "B": 18, "C": 12, "D": 12, "E": 12, "F": 12, "G": 10, "H": 10, "I": 14, "J": 12, "K": 12, "L": 11, "M": 12, "N": 12})
    ch = LineChart()
    ch.title = "Chargers occupied by half hour: data (95% band) vs band_long and AB, m = 1.0, c = 52"
    for j in (1, 3, 4, 5, 9):
        ch.add_data(Reference(ws, min_col=p0 + j, min_row=8, max_row=56), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=p0, min_row=9, max_row=56))
    ch.y_axis.title = "chargers occupied"
    ch.x_axis.title = "time of day"
    ch.height, ch.width = 9, 20
    ws.add_chart(fix_chart(ch), "A45")


def sheet_16b(wb, res):
    ws = wb.create_sheet("16b_Sensitivity_v2", wb.sheetnames.index("16_Sensitivity") + 1)
    title(ws, "Step 6a (v2) - Growth limit of the existing 52 chargers and input-model sensitivity (tasks R6, D6, D7)")
    box(ws, "A3:P6", "Left: P15 at c = 52 for growth m = 1.0...2.0 (step 0.1, refined to 0.02 near the limit), base model band_long, pooled "
        "weekday rates and the design day (Tue + Wed). Right: the smallest feasible c for every service model x arrival profile. Means, "
        "standard deviations and n are purple (results/phase1r/r6_growth_limit.csv, r6_decision.csv); upper bounds, PASS/FAIL, the growth "
        "limit and c* are formulas. The last column shows the 15b validation verdict of each service model.")
    G = pd.read_csv(res / "r6_growth_limit.csv").sort_values(["arrivals", "m"], ascending=[False, True])
    hdr(ws, 8, 1, ["Arrivals", "m", "n", "Mean P15", "s", "Upper 95%", "Rule met?", "All m' <= m pass?"])
    first = {}
    for i, r in enumerate(G.itertuples()):
        rr = 9 + i
        put(ws, f"A{rr}", r.arrivals, "p")
        put(ws, f"B{rr}", float(r.m), "p", "0.00")
        put(ws, f"C{rr}", int(r.n), "p", "0")
        put(ws, f"D{rr}", float(r.P15_mean), "p", "0.000%")
        put(ws, f"E{rr}", float(r.P15_s), "p", "0.000%")
        put(ws, f"F{rr}", f"=D{rr}+TINV(0.05,C{rr}-1)*E{rr}/SQRT(C{rr})", nf="0.000%")
        put(ws, f"G{rr}", f"=IF(F{rr}<='01_Plan'!$C$12,\"PASS\",\"FAIL\")")
        if r.arrivals not in first:
            first[r.arrivals] = rr
            put(ws, f"H{rr}", f"=G{rr}=\"PASS\"")
        else:
            put(ws, f"H{rr}", f"=AND(G{rr}=\"PASS\",H{rr - 1})")
    last = 8 + len(G)
    put(ws, f"A{last + 2}", "Growth limit of 52 chargers (largest m with all smaller m passing)", "b")
    for i, ar in enumerate(["pooled", "designday"]):
        put(ws, f"A{last + 3 + i}", ar)
        put(ws, f"B{last + 3 + i}", f"=_xlfn.MAXIFS($B$9:$B${last},$A$9:$A${last},A{last + 3 + i},$H$9:$H${last},TRUE)", "k", "0.00")
    glim = {"pooled": f"B{last + 3}", "designday": f"B{last + 4}"}
    Dd = pd.read_csv(res / "r6_decision.csv")
    order = [("band_long", "pooled"), ("band_long_opt", "pooled"), ("band", "pooled"), ("AB", "pooled"), ("mixA_lnB", "pooled"),
             ("jointGMM", "pooled"), ("band_long", "designday"), ("band_long_opt", "designday")]
    hdr(ws, 8, 11, ["Service", "Arrivals", "c", "n", "Mean P15", "s", "Upper 95%", "Rule met?", "It and all larger pass?"])
    rr = 9
    for s, ar in order:
        g = Dd[(Dd.service == s) & (Dd.arrivals == ar)].sort_values("c")
        for t, r in enumerate(g.itertuples()):
            put(ws, f"K{rr}", s, "p")
            put(ws, f"L{rr}", ar, "p")
            put(ws, f"M{rr}", int(r.c), "p", "0")
            put(ws, f"N{rr}", int(r.n), "p", "0")
            put(ws, f"O{rr}", float(r.P15_mean), "p", "0.000%")
            put(ws, f"P{rr}", float(r.P15_s), "p", "0.000%")
            put(ws, f"Q{rr}", f"=O{rr}+TINV(0.05,N{rr}-1)*P{rr}/SQRT(N{rr})", nf="0.000%")
            put(ws, f"R{rr}", f"=IF(Q{rr}<='01_Plan'!$C$12,\"PASS\",\"FAIL\")")
            put(ws, f"S{rr}", f"=R{rr}=\"PASS\"" if t == len(g) - 1 else f"=AND(R{rr}=\"PASS\",S{rr + 1})")
            rr += 1
    lastd = rr - 1
    SM = pd.read_csv(res / "r6_smallest_c.csv").set_index(["service", "arrivals"])
    hdr(ws, 8, 21, ["Service model", "Arrivals", "Smallest feasible c* (formula)", "Engine (r6_smallest_c.csv)", "Check",
                    "Validation (15b)"])
    cstar = {}
    for i, (s, ar) in enumerate(order):
        r = 9 + i
        put(ws, f"U{r}", s, "b")
        put(ws, f"V{r}", ar)
        put(ws, f"W{r}", f"=_xlfn.MINIFS($M$9:$M${lastd},$K$9:$K${lastd},U{r},$L$9:$L${lastd},V{r},$S$9:$S${lastd},TRUE)", "k", "0")
        put(ws, f"X{r}", int(SM.loc[(s, ar), "c_star"]), "p", "0")
        put(ws, f"Y{r}", f"=IF(W{r}=X{r},\"MATCH ✓\",\"CHECK ✗\")")
        put(ws, f"Z{r}", f"=IFERROR(INDEX('15b_Validation_v2'!$H$10:$H$15,MATCH(U{r},'15b_Validation_v2'!$A$10:$A$15,0)),\"n/a\")")
        cstar[(s, ar)] = f"W{r}"
    widths(ws, {"A": 12, "B": 8, "C": 6, "D": 10, "E": 10, "F": 10, "G": 10, "H": 14, "K": 14, "L": 11, "M": 6, "N": 6, "O": 10, "P": 10,
                "Q": 10, "R": 10, "S": 13, "U": 16, "V": 11, "W": 16, "X": 16, "Y": 11, "Z": 14})
    ch = ScatterChart()
    ch.title = "Growth limit of 52 chargers: P15 upper bound vs growth factor m (band_long)"
    ch.x_axis.title = "growth factor m"
    ch.y_axis.title = "P15 (upper 95%)"
    for ar in ("pooled", "designday"):
        a, b = first[ar], first[ar] + int((G.arrivals == ar).sum()) - 1
        ch.series.append(Series(Reference(ws, min_col=6, min_row=a, max_row=b), Reference(ws, min_col=2, min_row=a, max_row=b), title=ar))
    ch.y_axis.number_format = "0%"
    ch.x_axis.scaling.min, ch.x_axis.scaling.max = 1.0, 2.0
    ch.style = 13
    ch.height, ch.width = 8, 16
    ws.add_chart(fix_chart(ch), f"A{last + 7}")
    return cstar, glim


def sheet_17(wb, res, cstar, glim):
    ws = wb["17_Decision"]
    put(ws, "A2", "SUPERSEDED (v1): rows 3-34 are the v1 decision (A/B service model, option grid 38/42/46/52). Current v2 decision: rows 40-88 (values in column F).", "r")
    box(ws, "A36:I38", "Superseded v1 result: 'recommend 46 chargers' and 'the existing 52 chargers keep meeting the rule up to about +60% "
        "more cars'. Reasons it is superseded: (1) the coarse option grid {38, 42, 46, 52} could not see c = 45; (2) the A/B service model "
        "fails validation (15b_Validation_v2: mean occupancy -0.50 cars, daily-peak KS p = 0.044) and under-states peak occupancy, so it "
        "under-sizes; with the validated model 52 chargers hold only up to +56% (pooled) / +46% (design day).")
    ws.row_dimensions[36].height = 30
    put(ws, "A40", "v2 DECISION (current) - base model band_long (validated), pooled weekdays, +30% demand, rule from 01_Plan", "b")
    ws["A40"].font = Font(name="Arial", size=12, bold=True, color="FF1F4E78")
    sv = "'16b_Sensitivity_v2'!"
    rows = [("RECOMMENDED number of chargers (base)", "='13b_Output_CI_v2'!D23", "k", "0"),
            ("Planning value for the busiest weekdays (design day Tue-Wed)", f"={sv}{cstar[('band_long', 'designday')]}", "k", "0"),
            ("Existing chargers", "=ROUND('01_Plan'!$C$15,0)", "g", "0"),
            ("Chargers that can be released (base / design day)", "=(B43-B41)&\" / \"&(B43-B42)", "k", None),
            ("New chargers to buy", "=MAX(0,B42-B43)", "f", "0"),
            ("P15 at recommended c: mean", "=INDEX('13b_Output_CI_v2'!$C$8:$C$20,MATCH(B41,'13b_Output_CI_v2'!$A$8:$A$20,0))", "g", "0.00%"),
            ("P15 at recommended c: upper 95%", "=INDEX('13b_Output_CI_v2'!$H$8:$H$20,MATCH(B41,'13b_Output_CI_v2'!$A$8:$A$20,0))", "g", "0.00%"),
            ("Growth limit of 52 chargers (pooled weekdays), m", f"={sv}{glim['pooled']}", "k", "0.00"),
            ("Growth limit of 52 chargers (design day), m", f"={sv}{glim['designday']}", "k", "0.00"),
            ("Bad-day rate at recommended c (days with >= 1 wait > 15 min)", "=INDEX($B$64:$B$69,MATCH(B41,$A$64:$A$69,0))", "f", "0.0%"),
            ("Busiest arrival hour for waits at recommended c", "=INDEX($K$64:$K$87,MATCH(MAX($L$64:$L$87),$L$64:$L$87,0))&\":00\"", "f", None)]
    # values in column F (labels merged over A:E so they are readable); B41..B51 references -> F41..F51
    import re
    tof = lambda s: re.sub(r"(?<![$A-Z!])B(4[1-9]|5[01])(?!\d)", r"F\1", s)  # noqa: E731
    for i, (lab, f, k, nf) in enumerate(rows):
        put(ws, f"A{41 + i}", lab, "b")
        ws.merge_cells(f"A{41 + i}:E{41 + i}")
        put(ws, f"F{41 + i}", tof(f) if isinstance(f, str) else f, k, nf)
    sens = (f"=\"Input-model sensitivity (16b): validated models band_long \"&{sv}{cstar[('band_long', 'pooled')]}&\" and band_long_opt \"&"
            f"{sv}{cstar[('band_long_opt', 'pooled')]}&\"; models that fail validation: band \"&{sv}{cstar[('band', 'pooled')]}&\", jointGMM \"&"
            f"{sv}{cstar[('jointGMM', 'pooled')]}&\", AB \"&{sv}{cstar[('AB', 'pooled')]}&\", mixA_lnB \"&{sv}{cstar[('mixA_lnB', 'pooled')]}&"
            f"\" - the invalid models under-size.\"")
    put(ws, "A53", sens)
    put(ws, "A54", "=\"With \"&B41&\" chargers and 30% more cars, about 1 driver in \"&TEXT(1/MAX(B46,1E-9),\"#,##0\")&\" waits more than \"&"
        "'01_Plan'!$C$11&\" min (upper 95% bound \"&TEXT(B47,\"0.00%\")&\" <= 1%).\"")
    put(ws, "A55", "=\"On about \"&TEXT(B50,\"0%\")&\" of weekdays at least one driver waits more than \"&'01_Plan'!$C$11&\" min; waits "
        "concentrate on cars arriving around \"&B51&\" (midday, while the morning cars still occupy the chargers).\"")
    put(ws, "A56", "=\"The existing \"&B43&\" chargers meet the rule up to about +\"&TEXT(B48-1,\"0%\")&\" more cars (+\"&TEXT(B49-1,\"0%\")&"
        "\" on Tue-Wed); \"&(B43-B41)&\" chargers could be released or repurposed at +30%.\"")
    for r in (54, 55, 56):
        ws[f"A{r}"].value = tof(ws[f"A{r}"].value)
    for r in (53, 54, 55, 56):
        ws.merge_cells(f"A{r}:I{r}")
        ws[f"A{r}"].alignment = WRAP
        ws.row_dimensions[r].height = 28
    R7 = pd.read_csv(res / "r7_outputs.csv")
    put(ws, "A62", "R7 outputs, band_long, m = 1.3, 60 reps (results/phase1r/r7_outputs.csv)", "b")
    hdr(ws, 63, 1, ["c", "Bad-day rate", "lower 95%", "upper 95%", "Share of time all busy", "Mean max queue", "Max queue (all reps)",
                    "Wq 12-15 band (min)"])
    for i, c in enumerate(sorted(R7.c.unique())):
        r = 64 + i
        g = R7[R7.c == c].set_index("metric")
        put(ws, f"A{r}", int(c), "p", "0")
        for j, (k, fld, nf) in enumerate([("bad_day_rate", "mean", "0.0%"), ("bad_day_rate", "lo", "0.0%"), ("bad_day_rate", "hi", "0.0%"),
                                          ("share_all_busy", "mean", "0.00%"), ("max_queue", "mean", "0.0"),
                                          ("max_queue_overall_max", "mean", "0"), ("Wq_min_band_12-15", "mean", "0.00")]):
            put(ws, f"{col(2 + j)}{r}", float(g.loc[k, fld]), "p", nf)
    H7 = pd.read_csv(res / "r7_p15_by_hour.csv")
    put(ws, "K62", "P15 by arrival hour at c = 45 (r7_p15_by_hour.csv)", "b")
    hdr(ws, 63, 11, ["Hour", "P15 at c = 45", "Arrivals (60 reps)"])
    g = H7[H7.c == 45].sort_values("hour")
    for i, r in enumerate(g.itertuples()):
        put(ws, f"K{64 + i}", int(r.hour), "p", "0")
        put(ws, f"L{64 + i}", float(r.P15_pooled), "p", "0.00%")
        put(ws, f"M{64 + i}", int(r.arrivals), "p", "#,##0")
    ch = BarChart()
    ch.title = "P(wait > 15 min) by arrival hour, c = 45, m = 1.3"
    ch.add_data(Reference(ws, min_col=12, min_row=63, max_row=87), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=11, min_row=64, max_row=87))
    ch.y_axis.number_format = "0%"
    ch.legend = None
    ch.height, ch.width = 7, 14
    ws.add_chart(fix_chart(ch), "O62")


def sheet_18(wb, ev):
    ws = wb["18_FlexSim_Inputs"]
    ws.unmerge_cells("H13:L13")
    ws["B11"].value = "Band label on arrival = BandOfHour24[hour of arrival] (table P14:R38); v1 A/B rule superseded"
    ws["H13"].value = "Empirical stay by ARRIVAL BAND (minutes; v2 incl. stays > 24 h) - percentile table for FlexSim (from 08b)"
    ws["H13"].font = F_BOLD
    ws["H14"].value = "Cumulative prob."
    for b in range(6):
        ws.cell(14, 9 + b, f"Band {ev.BAND_LABELS[b]} (min)").font = F_BOLD
    for i in range(101):
        r, src = 15 + i, 10 + i
        put(ws, f"H{r}", f"='08b_Service_Bands'!T{src}", "g", "0.00")
        for b in range(6):
            put(ws, f"{col(9 + b)}{r}", f"='08b_Service_Bands'!{col(21 + b)}{src}*60", "g", "0.0")
    put(ws, "P13", "BandOfHour24 lookup (from 08b)", "b")
    hdr(ws, 14, 16, ["Hour", "Band (1-6)", "Band label"])
    for h in range(24):
        r = 15 + h
        put(ws, f"P{r}", f"='08b_Service_Bands'!I{10 + h}", "g", "0")
        put(ws, f"Q{r}", f"='08b_Service_Bands'!J{10 + h}", "g", "0")
        put(ws, f"R{r}", f"='08b_Service_Bands'!K{10 + h}", "g")
    put(ws, "P40", "For an exact match with the engine use the full sorted pools in 08b_Service_Bands!AB10:AG1044 "
        "(stay = x(ceil(U n_band))); the 101-point percentile table is for display.")
    widths(ws, {"M": 14, "N": 14, "P": 8, "Q": 10, "R": 10})


def sheet_00(wb):
    ws = wb["00_Guide"]
    put(ws, "A42", "v2 sheets (Phase 1R, decisions D5-D7) - CURRENT results", "b")
    ws["A42"].font = Font(name="Arial", size=12, bold=True, color="FF1F4E78")
    hdr(ws, 43, 1, ["Sheet", "Guideline step", "Marks", "What it contains"])
    rows = [("04b_DayOfWeek", "Step 3", "20", "Day-of-week ANOVA (formula), Kruskal-Wallis, dispersion test, design-day (Tue-Wed) rate table."),
            ("07b_Fit_Revised", "Step 3", "20", "MLE + parametric-bootstrap KS/AD for all inputs; supersedes the v1 fits in 07/08."),
            ("08b_Service_Bands", "Step 3", "20", "Stay by arrival hour, the 6 arrival bands, R^2 table, sorted band pools and percentile tables (FlexSim inputs)."),
            ("10b_Replica_band_long", "Step 4", "20", "Full replication with the v2 band model by formulas; matches the engine (rel. diff <= 1e-12, N and W95 exact)."),
            ("12b_Replications_v2", "Step 5", "25", "Per-replication P15 and Wq for c = 40...52 (base model, CRN, boundary-aimed n)."),
            ("13b_Output_CI_v2", "Step 5", "25", "t-based CIs for every c and the decision rule by formula: c* = 45."),
            ("14b_Paired_v2", "Step 5", "25", "Paired CRN differences vs c*, Bonferroni-adjusted; CRN variance-reduction ratio."),
            ("15b_Validation_v2", "Step 5", "25", "Pre-written validation criteria for 6 service models (Welch CIs by formula, KS); occupancy profile."),
            ("16b_Sensitivity_v2", "Step 6", "10", "Growth limit of 52 chargers (pooled / design day) and smallest c per input model."),
            ("17_Decision (rows 40+)", "Step 6", "10", "v2 decision: 45 chargers (47 on Tue-Wed); v1 decision kept as superseded.")]
    for i, vals in enumerate(rows):
        for j, v in enumerate(vals):
            put(ws, f"{col(1 + j)}{44 + i}", v)
    box(ws, "A55:D58", "v1 vs v2: v1 sheets (07, 08 fits; 10 replica; 11-17 decision with the A/B service model) are kept unchanged for "
        "transparency. v2 replaces the A/B service model by stay-by-arrival-band including stays > 24 h (it passes validation, A/B does "
        "not), evaluates every c from 40 to 52, and changes the recommendation from 46 to 45 chargers (47 for Tue-Wed). 11_Pilot_n now "
        "uses t instead of z; 18_FlexSim_Inputs now holds the band tables. Engine: engine/ev_des_engine.py --service band_long.")


def main():
    ap = argparse.ArgumentParser()
    for k in ["xlsx", "backup", "res", "json", "engine"]:
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    xlsx, backup, res = Path(a.xlsx), Path(a.backup), Path(a.res)
    if not backup.exists():
        shutil.copy2(xlsx, backup)
    ev = load_engine(a.engine, a.json)
    df = ev.load()
    wd = [d for d in pd.date_range("2019-03-01", "2019-05-31") if d.dayofweek < 5 and d.date() != ev.HOLIDAY]
    wb = openpyxl.load_workbook(backup)          # always build from the untouched v1 workbook
    sheet_03(wb)
    sheet_04b(wb, res, wd)
    sheet_07b(wb, res)
    sheet_08b(wb, res, ev, df)
    E = sheet_10b(wb, res, ev, df)
    sheet_12b_13b_14b(wb, res)
    sheet_15b(wb, res)
    cstar, glim = sheet_16b(wb, res)
    sheet_17(wb, res, cstar, glim)
    sheet_18(wb, ev)
    sheet_11(wb)
    sheet_00(wb)
    wb.save(xlsx)
    print("saved", xlsx)
    print(wb.sheetnames)
    print(E.to_string(index=False))


if __name__ == "__main__":
    main()
