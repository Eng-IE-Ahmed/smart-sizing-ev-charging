"""Phase 6: decision-analysis sheets in the workbook, all computed by formulas.

Sheets (inserted after Analytic_MtGinf, before 17_Decision):
  DA1_Costs          inputs with sources/assumptions, CRF, options, engine results (purple = data from
                     results/phase6/p6_cells.csv), annual cost of every (option, future) by formula
  DA2_Uncertainty    payoff table, minimax cost (pessimistic), minimin cost (optimistic), regret table + minimax regret,
                     Hurwicz with an alpha input and an alpha sweep (+ chart)
  DA3_Risk           growth probabilities (expert judgement), EMV (expected annual cost), EVPI, decision-tree roll-back
                     table, probability sensitivity (+ chart, breakeven), value-of-time sensitivity
  DA4_AHP            pairwise matrix + rationale, geometric-mean weights, lambda_max, CI, CR, ideal-mode scores of the
                     options, overall scores, weight sensitivity for each criterion (+ charts)
  DA5_Recommendation recommendation under each lens + explanation
Python reference values (results/phase6/p6_*.json/csv from scripts/decision_analysis.py) are written in purple next to check
cells ("MATCH ✓"). Loads the CURRENT workbook (keeps every sheet), replaces these sheets, saves; then run
scripts/excel_recalc.py (Excel COM) for cached values and the 0-error check.
Usage: python scripts/excel_decision.py --project . [--xlsx excel/EV_Charging_DES_Caltech_2019.xlsx]
"""
import argparse
import json
from pathlib import Path

import openpyxl
import pandas as pd
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill

F_BODY = Font(name="Arial", size=10)
F_BOLD = Font(name="Arial", size=10, bold=True)
F_TITLE = Font(name="Arial", size=14, bold=True, color="FF1F4E78")
F_HDR = Font(name="Arial", size=10, bold=True, color="FFFFFFFF")
F_PURPLE = Font(name="Arial", size=10, color="FF7030A0")
F_GREEN = Font(name="Arial", size=10, color="FF008000")
F_BLUE = Font(name="Arial", size=10, color="FF0000FF")
F_KEY = Font(name="Arial", size=11, bold=True, color="FFC00000")
F_BOX = Font(name="Arial", size=10, color="FF1F3864")
F_SMALL = Font(name="Arial", size=9, color="FF595959")
FILL_HDR = PatternFill("solid", fgColor="FF1F4E78")
FILL_IN = PatternFill("solid", fgColor="FFFFF2CC")
FILL_KEY = PatternFill("solid", fgColor="FFE2EFDA")
FILL_BOX = PatternFill("solid", fgColor="FFEEF3F8")
USD = '"$"#,##0'
FUT = [1.0, 1.3, 1.6, 2.0]
SHEETS = ["DA1_Costs", "DA2_Uncertainty", "DA3_Risk", "DA4_AHP", "DA5_Recommendation"]
TOL = "0.5"   # $ tolerance of the Excel = Python cost checks


def put(ws, ref, v, kind="f", nf=None, wrap=False):
    c = ws[ref]
    c.value = v
    c.font = {"f": F_BODY, "b": F_BOLD, "p": F_PURPLE, "g": F_GREEN, "i": F_BLUE, "k": F_KEY, "s": F_SMALL}[kind]
    if kind == "i":
        c.fill = FILL_IN
    if kind == "k":
        c.fill = FILL_KEY
    if nf:
        c.number_format = nf
    if wrap:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    return c


def hdr(ws, row, col0, labels):
    for j, h in enumerate(labels):
        c = ws.cell(row, col0 + j, h)
        c.font, c.fill, c.alignment = F_HDR, FILL_HDR, Alignment(wrap_text=True, vertical="center")


def L(n):
    return openpyxl.utils.get_column_letter(n)


def box(ws, rng, text):
    ws.merge_cells(rng)
    c = ws[rng.split(":")[0]]
    c.value, c.font, c.fill, c.alignment = text, F_BOX, FILL_BOX, Alignment(wrap_text=True, vertical="top")


def title(ws, text):
    ws["A1"] = text
    ws["A1"].font = F_TITLE
    ws.column_dimensions["A"].width = 3


def line_chart(ws, anchor, title_, ytitle, xtitle, data_ref, cats_ref, w=18, h=9):
    ch = LineChart()
    ch.title, ch.y_axis.title, ch.x_axis.title = title_, ytitle, xtitle
    ch.add_data(data_ref, titles_from_data=True)
    ch.set_categories(cats_ref)
    ch.width, ch.height = w, h
    ch.roundedCorners = False
    ch.legend.position = "r"
    ch.legend.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ws.add_chart(ch, anchor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--xlsx", default="excel/EV_Charging_DES_Caltech_2019.xlsx")
    a = ap.parse_args()
    root = Path(a.project)
    rd = root / "results" / "phase6"
    IJ = json.loads((rd / "p6_inputs.json").read_text())
    I = IJ["INPUTS"]
    OPT = IJ["options"]                      # [name, label, new, c, admin key]
    C = pd.read_csv(rd / "p6_cells.csv")
    PAY = pd.read_csv(rd / "p6_payoff.csv")
    FL = pd.read_csv(rd / "p6_flex.csv").set_index("option")
    LJ = json.loads((rd / "p6_lenses.json").read_text())
    AH = json.loads((rd / "p6_ahp.json").read_text())
    nopt = len(OPT)
    names = [o[0] for o in OPT]

    wb = openpyxl.load_workbook(root / a.xlsx)
    for s in SHEETS:
        if s in wb.sheetnames:
            del wb[s]
    ws_ = {}
    for s in SHEETS:
        ws_[s] = wb.create_sheet(s, wb.sheetnames.index("17_Decision"))

    # ------------------------------------------------------------------ DA1_Costs
    ws = ws_["DA1_Costs"]
    title(ws, "Step 7a - Decision analysis: cost model (annual cost of each option in each growth future)")
    box(ws, "B3:R5", "Blue cells on yellow = inputs you may change; purple = data (engine output, results/phase6/p6_cells.csv, "
        "200 CRN replications per cell, scripts/decision_analysis.py); black = formulas; green = links to other sheets. Annual cost = "
        "new chargers x (hardware + installation) x CRF + chargers x (maintenance + network fee) + waiting hours x value of time "
        "+ hours spent moving cars x value of time + policy administration. Electricity is the same in every option and is left "
        "out. The 52 existing chargers are sunk (no capital cost). Every source or assumption is listed in columns E-G and in "
        "report/SOURCES.md.")
    hdr(ws, 7, 2, ["Input", "Value", "Unit", "Type", "Source / basis", "Accessed"])
    afdc1 = ("AFDC (US DOE), Procurement and Installation for EV Charging Infrastructure, citing the NLR/INL report 'Levelized "
             "Cost of Charging EVs in the United States' (Borlaug et al., Joule 2020): https://afdc.energy.gov/fuels/"
             "electricity_infrastructure_development.html")
    afdc2 = ("AFDC (US DOE), Operation and Maintenance for EV Charging Infrastructure ('up to $400 annually, per charger'): "
             "https://afdc.energy.gov/fuels/electricity_infrastructure_maintenance_and_operation.html")
    inp = [  # row, label, value, unit, type, source, nf
        (8, "Hardware per Level 2 connector", I["hardware_per_connector"], "$", "source", afdc1 + " - '$3,500 per connector for Level 2'", USD),
        (9, "Installation per connector (public/workplace)", I["installation_per_connector"], "$", "source", afdc1 + " - '$2,500 per connector for Level 2'", USD),
        (10, "Discount rate i", I["interest"], "per year", "assumption", "Plan 6.1 (i = 7%)", "0.0%"),
        (11, "Life N", I["life_years"], "years", "assumption", "Plan 6.1 (10 years)", "0"),
        (13, "Maintenance per charger-year", I["maintenance_per_charger_yr"], "$/yr", "source", afdc2, USD),
        (14, "Network fee per port-year", I["network_fee_per_port_yr"], "$/yr", "assumption", "AFDC mentions network fees without an amount; assumption, tested 0-600 (results/phase6/p6_vot_sens.csv)", USD),
        (15, "Value of time (waiting / walking back to move the car)", I["value_of_time_per_h"], "$/h (2023 $)", "source",
         "USDOT, Benefit-Cost Analysis Guidance for Discretionary Grant Programs, 2025 Update (Nov 2024), Appendix A, Table A-2 "
         "(2023 $ per person-hour): walking, cycling, waiting, standing and transfer time $38.80 (used); all purposes $21.10 (low case); "
         "personal $19.40; business $33.50. https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance"
         "%202025%20Update%20%28Final%29.pdf (value supplied by the reviewer, 15 Nov 2026). Dollar years: VoT 2023 $; AFDC costs are "
         "undated (study 2020) and not converted - a x1.2 capital price level is tested in results/phase6/p6_vot_sens.csv. "
         "Sensitivity 10-50 $/h in DA3_Risk", '"$"#,##0.00'),
        (16, "Weekdays per year", I["weekdays_per_year"], "days", "assumption", "260 weekdays - 10 holidays; the model covers weekdays only", "0"),
        (17, "Minutes to move a car after charging", I["move_minutes_per_moved_car"], "min", "assumption", "Behavioural assumption (walk to the garage and re-park); tested 2-10 min", "0.0"),
        (18, "Administration of the soft P1-60 rule", I["admin_soft_rule_yr"], "$/yr", "assumption", "Notifications / signage / staff time; assumption", USD),
        (19, "Administration of the enforced fee rule", I["admin_fee_rule_yr"], "$/yr", "assumption", "Idle-fee set-up, enforcement and complaints; assumption (fee revenue is a transfer, not counted)", USD),
    ]
    for r, lab, v, unit, typ, src, nf in inp:
        put(ws, f"B{r}", lab, "b")
        put(ws, f"C{r}", v, "i", nf)
        put(ws, f"D{r}", unit)
        put(ws, f"E{r}", typ, "f")
        put(ws, f"F{r}", src, "s")
        put(ws, f"G{r}", "2026-11-15" if typ == "source" else "")
    put(ws, "B12", "Capital recovery factor CRF(i, N)", "b")
    put(ws, "C12", "=C10*(1+C10)^C11/((1+C10)^C11-1)", "f", "0.00000")
    put(ws, "D12", "per year")
    put(ws, "F12", f"check: Python CRF = {IJ['crf']:.6f}", "s")
    put(ws, "B20", "Annualised capital per new connector", "b")
    put(ws, "C20", "=(C8+C9)*C12", "f", USD)
    put(ws, "B21", "O&M per charger-year", "b")
    put(ws, "C21", "=C13+C14", "f", USD)
    put(ws, "B22", "Risk threshold for the service rule (P15 upper bound)", "b")
    put(ws, "C22", "='01_Plan'!$C$12", "g", "0.0%")

    hdr(ws, 24, 2, ["Option", "Description", "New chargers", "Chargers c", "Policy administration ($/yr)",
                    "Driver acceptance rating (0-1)", "Basis of the rating"])
    acc_basis = {"none": "no change for drivers",
                 "soft": "a request to move within 60 min after charging; half of drivers comply (P3, behavioural assumption)",
                 "fee": "an enforced idle fee after 60 min; unpopular (expert judgement)"}
    for i, (n_, lab, new, c, ak) in enumerate(OPT):
        r = 25 + i
        put(ws, f"B{r}", n_, "b")
        put(ws, f"C{r}", lab)
        put(ws, f"D{r}", new, "i", "0")
        put(ws, f"E{r}", c, "i", "0")
        put(ws, f"F{r}", {"none": "=0", "soft": "=$C$18", "fee": "=$C$19"}[ak], "f", USD)
        put(ws, f"G{r}", I["acceptance_rating"][ak], "i", "0.00")
        put(ws, f"H{r}", acc_basis[ak], "s")
    OR = (25, 24 + nopt)
    ob = f"$B${OR[0]}:$B${OR[1]}"

    R0 = 34
    cols = ["Option", "Growth m", "Chargers c", "Cars in 65 weekdays (engine)", "Mean wait Wq (min, engine)",
            "P(wait>15) mean (engine)", "P(wait>15) upper 95% (engine)", "Share of cars moved (engine)", "Cars per year",
            "Capital ($/yr)", "O&M ($/yr)", "Waiting hours per year", "Moving hours per year", "Waiting cost ($/yr)",
            "Moving cost ($/yr)", "Policy admin ($/yr)", "TOTAL annual cost ($/yr)", "Cost without time ($/yr)",
            "Time hours per year", "Meets the service rule (1/0)", "Probability of this future", "Python total (check)",
            "Excel - Python ($)"]
    hdr(ws, R0 - 1, 2, cols)
    ws.row_dimensions[R0 - 1].height = 54
    rows = [(n_, m) for n_ in names for m in FUT]
    for k, (n_, m) in enumerate(rows):
        r = R0 + k
        d = C[(C.option == n_) & ((C.m - m).abs() < 1e-9)].iloc[0]
        py = PAY[(PAY.option == n_) & ((PAY.m - m).abs() < 1e-9)].iloc[0]
        put(ws, f"B{r}", n_, "b")
        put(ws, f"C{r}", m, "f", "0.0")
        put(ws, f"D{r}", f"=INDEX($E${OR[0]}:$E${OR[1]},MATCH(B{r},{ob},0))", "f", "0")
        put(ws, f"E{r}", float(d.N_mean), "p", "#,##0.0")
        put(ws, f"F{r}", float(d.Wq_mean), "p", "0.00000")
        put(ws, f"G{r}", float(d.P15_mean), "p", "0.000%")
        put(ws, f"H{r}", float(d.P15_upper), "p", "0.000%")
        put(ws, f"I{r}", float(d.moved_share_mean), "p", "0.0000")
        put(ws, f"J{r}", f"=E{r}/65*$C$16", "f", "#,##0")
        put(ws, f"K{r}", f"=INDEX($D${OR[0]}:$D${OR[1]},MATCH(B{r},{ob},0))*$C$20", "f", USD)
        put(ws, f"L{r}", f"=D{r}*$C$21", "f", USD)
        put(ws, f"M{r}", f"=F{r}/60*J{r}", "f", "#,##0.0")
        put(ws, f"N{r}", f"=I{r}*J{r}*$C$17/60", "f", "#,##0.0")
        put(ws, f"O{r}", f"=M{r}*$C$15", "f", USD)
        put(ws, f"P{r}", f"=N{r}*$C$15", "f", USD)
        put(ws, f"Q{r}", f"=INDEX($F${OR[0]}:$F${OR[1]},MATCH(B{r},{ob},0))", "f", USD)
        put(ws, f"R{r}", f"=K{r}+L{r}+O{r}+P{r}+Q{r}", "b", USD)
        put(ws, f"S{r}", f"=K{r}+L{r}+Q{r}", "f", USD)
        put(ws, f"T{r}", f"=M{r}+N{r}", "f", "#,##0.0")
        put(ws, f"U{r}", f"=IF(H{r}<=$C$22,1,0)", "f", "0")
        put(ws, f"V{r}", f"=INDEX(DA3_Risk!$C$8:$F$8,MATCH(C{r},DA3_Risk!$C$7:$F$7,0))", "g", "0.00")
        put(ws, f"W{r}", float(py.total), "p", USD)
        put(ws, f"X{r}", f"=R{r}-W{r}", "f", "0.000")
    RL = R0 + len(rows) - 1
    put(ws, f"B{RL + 2}", "Check: every Excel total equals the Python total (|diff| <= $0.50)", "b")
    put(ws, f"R{RL + 2}", f"=IF(SUMPRODUCT(--(ABS(X{R0}:X{RL})>{TOL}))=0,\"MATCH ✓\",\"CHECK ✗\")", "k")
    for colw, wdt in zip("BCDEFGH", (34, 34, 12, 14, 26, 16, 60)):
        ws.column_dimensions[colw].width = wdt
    for j in range(9, 25):
        ws.column_dimensions[L(j)].width = 13
    RNG = dict(ob=f"DA1_Costs!$B${R0}:$B${RL}", m=f"DA1_Costs!$C${R0}:$C${RL}", tot=f"DA1_Costs!$R${R0}:$R${RL}",
              S=f"DA1_Costs!$S${R0}:$S${RL}", T=f"DA1_Costs!$T${R0}:$T${RL}", U=f"DA1_Costs!$U${R0}:$U${RL}",
              V=f"DA1_Costs!$V${R0}:$V${RL}")

    # ------------------------------------------------------------------ DA2_Uncertainty
    ws = ws_["DA2_Uncertainty"]
    title(ws, "Step 7b - Decision under strict uncertainty: payoff (annual cost), minimax, minimin, Hurwicz, minimax regret")
    box(ws, "B3:N5", "Payoff = annual cost (lower is better) from DA1_Costs. Pessimistic (Wald) = minimise the worst cost; optimistic = "
        "minimise the best cost; Hurwicz = minimise alpha x best + (1 - alpha) x worst (alpha = optimism, input in C40); regret = cost "
        "- the lowest cost in that future; minimax regret = minimise the largest regret. Futures = demand growth m.")
    hdr(ws, 7, 2, ["Option \\ growth m"] + FUT + ["Worst (max cost)", "Best (min cost)"])
    for j in range(4):
        ws.cell(7, 3 + j).number_format = "0.0"
    for i, n_ in enumerate(names):
        r = 8 + i
        put(ws, f"B{r}", n_, "b")
        for j in range(4):
            cl = L(3 + j)
            put(ws, f"{cl}{r}", f"=SUMIFS({RNG['tot']},{RNG['ob']},$B{r},{RNG['m']},{cl}$7)", "f", USD)
        put(ws, f"G{r}", f"=MAX(C{r}:F{r})", "f", USD)
        put(ws, f"H{r}", f"=MIN(C{r}:F{r})", "f", USD)
    PR = (8, 7 + nopt)
    put(ws, "B15", "Pessimistic (minimax cost) choice", "b")
    put(ws, "G15", f"=INDEX($B$8:$B${PR[1]},MATCH(MIN(G8:G{PR[1]}),G8:G{PR[1]},0))", "k")
    put(ws, "B16", "Optimistic (minimin cost) choice", "b")
    put(ws, "H16", f"=INDEX($B$8:$B${PR[1]},MATCH(MIN(H8:H{PR[1]}),H8:H{PR[1]},0))", "k")
    put(ws, "I14", "Python", "b")
    put(ws, "I15", LJ["minimax_cost"], "p")
    put(ws, "J15", "=IF(G15=I15,\"MATCH ✓\",\"CHECK ✗\")", "f")
    put(ws, "I16", LJ["minimin_cost"], "p")
    put(ws, "J16", "=IF(H16=I16,\"MATCH ✓\",\"CHECK ✗\")", "f")
    hdr(ws, 19, 2, ["Regret \\ growth m"] + FUT + ["Max regret"])
    for j in range(4):
        ws.cell(19, 3 + j).number_format = "0.0"
    for i, n_ in enumerate(names):
        r = 20 + i
        put(ws, f"B{r}", n_, "b")
        for j in range(4):
            cl = L(3 + j)
            put(ws, f"{cl}{r}", f"={cl}{8 + i}-MIN({cl}$8:{cl}${PR[1]})", "f", USD)
        put(ws, f"G{r}", f"=MAX(C{r}:F{r})", "f", USD)
        put(ws, f"I{r}", LJ["max_regret"][n_], "p", USD)
        put(ws, f"J{r}", f"=IF(ABS(G{r}-I{r})<={TOL},\"MATCH ✓\",\"CHECK ✗\")", "f")
    put(ws, "I19", "Python max regret", "b")
    RR = (20, 19 + nopt)
    put(ws, "B27", "Minimax regret choice", "b")
    put(ws, "G27", f"=INDEX($B$20:$B${RR[1]},MATCH(MIN(G20:G{RR[1]}),G20:G{RR[1]},0))", "k")
    put(ws, "I27", LJ["minimax_regret"], "p")
    put(ws, "J27", "=IF(G27=I27,\"MATCH ✓\",\"CHECK ✗\")", "f")
    hdr(ws, 31, 2, ["Option", "Hurwicz value at alpha (C40)"])
    for i, n_ in enumerate(names):
        r = 32 + i
        put(ws, f"B{r}", n_, "b")
        put(ws, f"C{r}", f"=$C$40*H{8 + i}+(1-$C$40)*G{8 + i}", "f", USD)
    put(ws, "B40", "Hurwicz optimism alpha", "b")
    put(ws, "C40", 0.5, "i", "0.00")
    put(ws, "B41", "Hurwicz choice at alpha (C40)", "b")
    put(ws, "C41", f"=INDEX($B$32:$B${31 + nopt},MATCH(MIN(C32:C{31 + nopt}),C32:C{31 + nopt},0))", "k")
    hz = LJ["hurwicz_envelope"]
    put(ws, "B43", "Exact alpha where two options tie (edit the names; pairs on the optimal path shown)", "b")
    hdr(ws, 44, 2, ["Switch", "Option X", "Option Y", "alpha* (X = Y)", "Python alpha*", "Check"])
    pr = f"$B$8:$B${PR[1]}"
    for k in range(len(hz) - 1):
        r = 45 + k
        X, Y = hz[k][1], hz[k + 1][1]
        gx, gy = f"INDEX($G$8:$G${PR[1]},MATCH(C{r},{pr},0))", f"INDEX($G$8:$G${PR[1]},MATCH(D{r},{pr},0))"
        hx, hy = f"INDEX($H$8:$H${PR[1]},MATCH(C{r},{pr},0))", f"INDEX($H$8:$H${PR[1]},MATCH(D{r},{pr},0))"
        put(ws, f"B{r}", f"switch {k + 1}", "b")
        put(ws, f"C{r}", X, "i")
        put(ws, f"D{r}", Y, "i")
        put(ws, f"E{r}", f"=({gy}-{gx})/(({hx}-{gx})-({hy}-{gy}))", "k", "0.000")
        put(ws, f"F{r}", hz[k + 1][0], "p", "0.000")
        put(ws, f"G{r}", f"=IF(ABS(E{r}-F{r})<1E-9,\"MATCH ✓\",\"CHECK ✗\")", "f")
    SW0 = 45 + len(hz) + 3
    put(ws, f"B{SW0 - 2}", "Hurwicz alpha sweep", "b")
    hdr(ws, SW0 - 1, 2, ["alpha"] + names + ["Best option"])
    for k in range(21):
        r = SW0 + k
        put(ws, f"B{r}", round(0.05 * k, 2), "f", "0.00")
        for i in range(nopt):
            put(ws, f"{L(3 + i)}{r}", f"=$B{r}*$H${8 + i}+(1-$B{r})*$G${8 + i}", "f", USD)
        put(ws, f"{L(3 + nopt)}{r}", f"=INDEX($C${SW0 - 1}:${L(2 + nopt)}${SW0 - 1},MATCH(MIN(C{r}:{L(2 + nopt)}{r}),C{r}:{L(2 + nopt)}{r},0))", "b")
    line_chart(ws, "L30", "Hurwicz value vs optimism alpha", "annual cost ($)", "alpha",
               Reference(ws, min_col=3, max_col=2 + nopt, min_row=SW0 - 1, max_row=SW0 + 20),
               Reference(ws, min_col=2, min_row=SW0, max_row=SW0 + 20))
    ws.column_dimensions["B"].width = 34
    for j in range(3, 12):
        ws.column_dimensions[L(j)].width = 14

    # ------------------------------------------------------------------ DA3_Risk
    ws = ws_["DA3_Risk"]
    title(ws, "Step 7c - Decision under risk: expected annual cost (EMV), EVPI, decision tree and sensitivity")
    box(ws, "B3:N5", "Growth probabilities are an EXPERT JUDGEMENT of the team (no forecast exists for this garage). Anchor: the "
        "California Energy Commission projects 6.8 million light-duty electric vehicles in California in 2030 (AB 2127 Third EV "
        "Charging Infrastructure Assessment, CEC-600-2026-032, Oct 2026), i.e. strong statewide growth; a single workplace garage "
        "grows less because its commuter base is fixed. Change C8:F8 (they must sum to 1) or use the sensitivity tables.")
    hdr(ws, 7, 2, ["Growth m"] + FUT + ["Sum"])
    for j in range(4):
        ws.cell(7, 3 + j).number_format = "0.0"
    put(ws, "B8", "Probability (expert judgement)", "b")
    for j, m in enumerate(FUT):
        put(ws, f"{L(3 + j)}8", I["prob"][f"{m:.1f}"], "i", "0.00")
    put(ws, "G8", "=SUM(C8:F8)", "f", "0.00")
    put(ws, "H8", "=IF(ABS(G8-1)<1E-9,\"OK\",\"must sum to 1\")", "f")
    hdr(ws, 11, 2, ["Option", "EMV = expected annual cost", "Python EMV", "Check"])
    for i, n_ in enumerate(names):
        r = 12 + i
        put(ws, f"B{r}", n_, "b")
        put(ws, f"C{r}", f"=SUMPRODUCT(DA2_Uncertainty!C{8 + i}:F{8 + i},$C$8:$F$8)", "f", USD)
        put(ws, f"D{r}", LJ["emv_values"][n_], "p", USD)
        put(ws, f"E{r}", f"=IF(ABS(C{r}-D{r})<={TOL},\"MATCH ✓\",\"CHECK ✗\")", "f")
    ER = (12, 11 + nopt)
    put(ws, "B19", "Best option by EMV (lowest expected cost)", "b")
    put(ws, "C19", f"=INDEX($B$12:$B${ER[1]},MATCH(MIN(C12:C{ER[1]}),C12:C{ER[1]},0))", "k")
    put(ws, "D19", LJ["emv"], "p")
    put(ws, "E19", "=IF(C19=D19,\"MATCH ✓\",\"CHECK ✗\")", "f")
    put(ws, "B21", "Lowest cost in each future (perfect information)", "b")
    for j in range(4):
        put(ws, f"{L(3 + j)}21", f"=MIN(DA2_Uncertainty!{L(3 + j)}8:{L(3 + j)}{7 + nopt})", "f", USD)
    put(ws, "B22", "Expected cost with perfect information", "b")
    put(ws, "C22", "=SUMPRODUCT(C21:F21,C8:F8)", "f", USD)
    put(ws, "B23", "EVPI = min EMV - expected cost with perfect information", "b")
    put(ws, "C23", f"=MIN(C12:C{ER[1]})-C22", "k", USD)
    put(ws, "D23", LJ["evpi"], "p", USD)
    put(ws, "E23", f"=IF(ABS(C23-D23)<={TOL},\"MATCH ✓\",\"CHECK ✗\")", "f")
    put(ws, "F23", "= the most a perfect growth forecast is worth per year", "s")
    T0 = 27
    put(ws, f"B{T0 - 1}", "Decision tree (roll-back): decision node -> option -> chance node (growth) -> annual cost", "b")
    hdr(ws, T0, 2, ["Option", "Growth m", "Probability", "Annual cost", "p x cost", "EMV of the chance node"])
    r = T0 + 1
    for i, n_ in enumerate(names):
        r_first = r
        for j, m in enumerate(FUT):
            put(ws, f"B{r}", n_, "b" if j == 0 else "f")
            put(ws, f"C{r}", m, "f", "0.0")
            put(ws, f"D{r}", f"={L(3 + j)}$8", "f", "0.00")
            put(ws, f"E{r}", f"=DA2_Uncertainty!{L(3 + j)}{8 + i}", "g", USD)
            put(ws, f"F{r}", f"=D{r}*E{r}", "f", USD)
            r += 1
        put(ws, f"G{r_first}", f"=SUM(F{r_first}:F{r - 1})", "b", USD)
    TL = r - 1
    put(ws, f"B{TL + 1}", "Decision node: choose the option with the lowest EMV", "b")
    put(ws, f"G{TL + 1}", f"=MIN(G{T0 + 1}:G{TL})", "k", USD)
    PS0 = TL + 5
    put(ws, f"B{PS0 - 2}", "Probability sensitivity: q = P(high growth, m = 1.6 or 2.0); shares within the low and high groups as in C8:F8", "b")
    hdr(ws, PS0 - 1, 2, ["q", "p(1.0)", "p(1.3)", "p(1.6)", "p(2.0)"] + names + ["Best option"])
    for k in range(21):
        r = PS0 + k
        put(ws, f"B{r}", round(0.05 * k, 2), "f", "0.00")
        put(ws, f"C{r}", f"=(1-$B{r})*$C$8/($C$8+$D$8)", "f", "0.000")
        put(ws, f"D{r}", f"=(1-$B{r})*$D$8/($C$8+$D$8)", "f", "0.000")
        put(ws, f"E{r}", f"=$B{r}*$E$8/($E$8+$F$8)", "f", "0.000")
        put(ws, f"F{r}", f"=$B{r}*$F$8/($E$8+$F$8)", "f", "0.000")
        for i in range(nopt):
            put(ws, f"{L(7 + i)}{r}", f"=SUMPRODUCT(DA2_Uncertainty!$C${8 + i}:$F${8 + i},$C{r}:$F{r})", "f", USD)
        put(ws, f"{L(7 + nopt)}{r}", f"=INDEX($G${PS0 - 1}:${L(6 + nopt)}${PS0 - 1},MATCH(MIN(G{r}:{L(6 + nopt)}{r}),G{r}:{L(6 + nopt)}{r},0))", "b")
    PSL = PS0 + 20
    put(ws, f"B{PSL + 2}", "Current q (E8 + F8)", "b")
    put(ws, f"C{PSL + 2}", "=E8+F8", "f", "0.00")
    pq = LJ["prob_envelope"]
    hdr(ws, PSL + 3, 2, ["Exact switch q (X = Y; edit the names)", "Option X", "Option Y", "q* (X = Y)", "Python q*", "Check"])
    da2o = f"DA2_Uncertainty!$B$8:$B${PR[1]}"
    for k in range(len(pq) - 1):
        r = PSL + 4 + k
        X, Y = pq[k][1], pq[k + 1][1]

        def lo(cell):
            return (f"(SUMPRODUCT(INDEX(DA2_Uncertainty!$C$8:$D${PR[1]},MATCH({cell},{da2o},0),0),$C$8:$D$8)/($C$8+$D$8))")

        def hi(cell):
            return (f"(SUMPRODUCT(INDEX(DA2_Uncertainty!$E$8:$F${PR[1]},MATCH({cell},{da2o},0),0),$E$8:$F$8)/($E$8+$F$8))")
        put(ws, f"B{r}", f"switch {k + 1} (cheapest below q*: X, above: Y)", "b")
        put(ws, f"C{r}", X, "i")
        put(ws, f"D{r}", Y, "i")
        put(ws, f"E{r}", f"=({lo(f'D{r}')}-{lo(f'C{r}')})/(({lo(f'D{r}')}-{lo(f'C{r}')})-({hi(f'D{r}')}-{hi(f'C{r}')}))", "k", "0.000")
        put(ws, f"F{r}", pq[k + 1][0], "p", "0.000")
        put(ws, f"G{r}", f"=IF(ABS(E{r}-F{r})<1E-9,\"MATCH ✓\",\"CHECK ✗\")", "f")
    PQL = PSL + 4 + len(pq) - 2
    line_chart(ws, "P26", "Expected annual cost vs P(high growth)", "expected annual cost ($)", "q = P(m = 1.6 or 2.0)",
               Reference(ws, min_col=7, max_col=6 + nopt, min_row=PS0 - 1, max_row=PSL),
               Reference(ws, min_col=2, min_row=PS0, max_row=PSL))
    VS0 = PQL + 5
    put(ws, f"B{VS0 - 2}", "Value-of-time sensitivity (probabilities C8:F8; other inputs as in DA1_Costs; USDOT 2023 $: "
        "21.10 all purposes, 38.80 waiting/walking)", "b")
    hdr(ws, VS0 - 1, 2, ["Value of time ($/h)"] + names + ["Best option by EMV"])
    vlist = (10, 14, 18, 21.1, 25, 30, 38.8, 40, 50)
    for k, v in enumerate(vlist):
        r = VS0 + k
        put(ws, f"B{r}", v, "i", '"$"#,##0.00')
        for i in range(nopt):
            put(ws, f"{L(3 + i)}{r}", f"=SUMPRODUCT(({RNG['ob']}={L(3 + i)}${VS0 - 1})*({RNG['S']}+$B{r}*{RNG['T']})*{RNG['V']})", "f", USD)
        put(ws, f"{L(3 + nopt)}{r}", f"=INDEX($C${VS0 - 1}:${L(2 + nopt)}${VS0 - 1},MATCH(MIN(C{r}:{L(2 + nopt)}{r}),C{r}:{L(2 + nopt)}{r},0))", "b")
    VC = VS0 + len(vlist) + 1
    put(ws, f"B{VC}", "Check: the formula at the DA1 value of time reproduces the EMV of A4", "b")
    put(ws, f"C{VC}", f"=IF(ABS(SUMPRODUCT(({RNG['ob']}=\"A4\")*({RNG['S']}+DA1_Costs!$C$15*{RNG['T']})*{RNG['V']})-C{12 + names.index('A4')})<={TOL},\"MATCH ✓\",\"CHECK ✗\")", "f")
    vt = LJ["vot_envelope"]
    hdr(ws, VC + 2, 2, ["Exact value of time where X = Y (edit)", "Option X", "Option Y", "v* ($/h)", "Python v*", "Check"])
    for k in range(len(vt) - 1):
        r = VC + 3 + k
        X, Y = vt[k][1], vt[k + 1][1]
        sx, sy = (f"SUMPRODUCT(({RNG['ob']}={c})*{RNG['S']}*{RNG['V']})" for c in (f"C{r}", f"D{r}"))
        tx, ty = (f"SUMPRODUCT(({RNG['ob']}={c})*{RNG['T']}*{RNG['V']})" for c in (f"C{r}", f"D{r}"))
        put(ws, f"B{r}", f"switch {k + 1} (cheapest below v*: X, above: Y)", "b")
        put(ws, f"C{r}", X, "i")
        put(ws, f"D{r}", Y, "i")
        put(ws, f"E{r}", f"=({sy}-{sx})/({tx}-{ty})", "k", '"$"#,##0.00')
        put(ws, f"F{r}", vt[k + 1][0], "p", '"$"#,##0.00')
        put(ws, f"G{r}", f"=IF(ABS(E{r}-F{r})<1E-6,\"MATCH ✓\",\"CHECK ✗\")", "f")
    ws.column_dimensions["B"].width = 44
    for j in range(3, 15):
        ws.column_dimensions[L(j)].width = 13

    # ------------------------------------------------------------------ DA4_AHP
    ws = ws_["DA4_AHP"]
    crit = I["ahp_criteria"]
    title(ws, "Step 7d - AHP: criteria weights (pairwise comparisons), consistency, and the overall score of each option")
    box(ws, "B3:N5", "Saaty scale 1-9 (1 equal, 3 moderately, 5 strongly more important; reciprocals below the diagonal). Weights by the "
        "geometric-mean method; lambda_max = mean of (A w)_i / w_i; CI = (lambda_max - n)/(n - 1); RI(4) = 0.90 (Saaty); CR = CI/RI must be "
        "<= 0.10. Option scores (ideal mode, best = 1): cost = lowest EMV / EMV; service = probability (DA3_Risk C8:F8) that the option "
        "meets the P15 rule, / best; acceptance = rating / best (DA1_Costs); flexibility = growth limit m_max / best (engine).")
    hdr(ws, 7, 2, ["Criterion"] + crit + ["Geometric mean", "Weight w", "(A w)_i", "(A w)_i / w_i", "Rationale of the judgements in this row"])
    A = I["ahp_matrix"]
    rationale = ["Cost matters, but the amounts are small next to the site budget: half as important as service, twice acceptance and flexibility",
                 "Service (the 1% standard of P(wait > 15 min)) is the project's objective: the most important criterion",
                 "Acceptance matters for the policy options only; equal to flexibility",
                 "Flexibility for future growth: equal to acceptance, half of cost and of service"]
    for i in range(4):
        r = 8 + i
        put(ws, f"B{r}", crit[i], "b")
        for j in range(4):
            cl = L(3 + j)
            if i == j:
                put(ws, f"{cl}{r}", 1, "f", "0.000")
            elif j > i:
                put(ws, f"{cl}{r}", A[i][j], "i", "0.000")
            else:
                put(ws, f"{cl}{r}", f"=1/{L(3 + i)}{8 + j}", "f", "0.000")
        put(ws, f"G{r}", f"=GEOMEAN(C{r}:F{r})", "f", "0.0000")
        put(ws, f"H{r}", f"=G{r}/SUM($G$8:$G$11)", "k", "0.0000")
        put(ws, f"I{r}", f"=SUMPRODUCT(C{r}:F{r},$C$13:$F$13)", "f", "0.0000")
        put(ws, f"J{r}", f"=I{r}/H{r}", "f", "0.0000")
        put(ws, f"K{r}", rationale[i], "s")
    put(ws, "B13", "Weights as a row (for SUMPRODUCT)", "b")
    for j in range(4):
        put(ws, f"{L(3 + j)}13", f"=$H${8 + j}", "f", "0.0000")
    put(ws, "B14", "lambda_max", "b")
    put(ws, "C14", "=AVERAGE(J8:J11)", "f", "0.0000")
    put(ws, "B15", "CI = (lambda_max - 4) / 3", "b")
    put(ws, "C15", "=(C14-4)/3", "f", "0.0000")
    put(ws, "B16", "RI (n = 4, Saaty)", "b")
    put(ws, "C16", 0.90, "f", "0.00")
    put(ws, "B17", "CR = CI / RI", "b")
    put(ws, "C17", "=C15/C16", "k", "0.0000")
    put(ws, "D17", "=IF(C17<=0.1,\"CR <= 0.10 ✓ consistent\",\"CR > 0.10 - revise the judgements\")", "b")
    put(ws, "F14", "Python lambda_max", "s")
    put(ws, "H14", AH["lambda_max_gm"], "p", "0.0000")
    put(ws, "F17", "Python CR", "s")
    put(ws, "H17", AH["CR"], "p", "0.0000")
    put(ws, "I17", "=IF(AND(ABS(C14-H14)<1E-9,ABS(C17-H17)<1E-9),\"MATCH ✓\",\"CHECK ✗\")", "f")
    put(ws, "B18", "Eigenvector weights (Python numpy, method check)", "b")
    for j in range(4):
        put(ws, f"{L(3 + j)}18", AH["weights_eig"][crit[j]], "p", "0.0000")
    S0 = 23
    hdr(ws, S0 - 1, 2, ["Option"] + [f"Score: {c}" for c in crit] + ["OVERALL score", "P(meets rule) (raw)",
                                                                     "Growth limit m_max (engine)", "Python overall", "Check"])
    for i, n_ in enumerate(names):
        r = S0 + i
        put(ws, f"B{r}", n_, "b")
        put(ws, f"C{r}", f"=MIN(DA3_Risk!$C$12:$C${ER[1]})/DA3_Risk!C{12 + i}", "f", "0.000")
        put(ws, f"H{r}", f"=SUMPRODUCT(({RNG['ob']}=B{r})*{RNG['U']}*{RNG['V']})", "f", "0.000")
        put(ws, f"D{r}", f"=H{r}/MAX($H${S0}:$H${S0 + nopt - 1})", "f", "0.000")
        put(ws, f"E{r}", f"=DA1_Costs!G{25 + i}/MAX(DA1_Costs!$G${OR[0]}:$G${OR[1]})", "g", "0.000")
        put(ws, f"I{r}", float(FL.loc[n_, "m_max"]), "p", "0.0")
        put(ws, f"F{r}", f"=I{r}/MAX($I${S0}:$I${S0 + nopt - 1})", "f", "0.000")
        put(ws, f"G{r}", f"=SUMPRODUCT(C{r}:F{r},$C$13:$F$13)", "b", "0.0000")
        put(ws, f"J{r}", AH["total"][n_], "p", "0.0000")
        put(ws, f"K{r}", f"=IF(ABS(G{r}-J{r})<1E-6,\"MATCH ✓\",\"CHECK ✗\")", "f")
    SL = S0 + nopt - 1
    put(ws, f"B{SL + 2}", "Best option by AHP (highest overall score)", "b")
    put(ws, f"G{SL + 2}", f"=INDEX($B${S0}:$B${SL},MATCH(MAX(G{S0}:G{SL}),G{S0}:G{SL},0))", "k")
    put(ws, f"I{SL + 2}", AH["best"], "p")
    put(ws, f"J{SL + 2}", f"=IF(G{SL + 2}=I{SL + 2},\"MATCH ✓\",\"CHECK ✗\")", "f")
    W0 = SL + 6
    put(ws, f"B{W0 - 2}", "Weight sensitivity: the weight of one criterion is set to w*, the other weights keep their ratios", "b")
    blk = 24
    for k_, cname in enumerate(crit):
        b0 = W0 + k_ * blk
        hdr(ws, b0, 2, [f"w*({cname})"] + [f"w({c})" for c in crit] + names + ["Best option"])
        for t in range(21):
            r = b0 + 1 + t
            put(ws, f"B{r}", round(0.05 * t, 2), "f", "0.00")
            for j in range(4):
                if j == k_:
                    put(ws, f"{L(3 + j)}{r}", f"=$B{r}", "f", "0.000")
                else:
                    put(ws, f"{L(3 + j)}{r}", f"=$H${8 + j}*(1-$B{r})/(1-$H${8 + k_})", "f", "0.000")
            for i in range(nopt):
                put(ws, f"{L(7 + i)}{r}", f"=SUMPRODUCT($C${S0 + i}:$F${S0 + i},$C{r}:$F{r})", "f", "0.000")
            put(ws, f"{L(7 + nopt)}{r}", f"=INDEX($G${b0}:${L(6 + nopt)}${b0},MATCH(MAX(G{r}:{L(6 + nopt)}{r}),G{r}:{L(6 + nopt)}{r},0))", "b")
        if k_ in (0, 1):
            line_chart(ws, "P22" if k_ == 0 else "P42", f"AHP overall score vs the weight of {cname.upper()}", "overall score",
                       f"weight of {cname}", Reference(ws, min_col=7, max_col=6 + nopt, min_row=b0, max_row=b0 + 21),
                       Reference(ws, min_col=2, min_row=b0 + 1, max_row=b0 + 21))
    ws.column_dimensions["B"].width = 30
    for j in range(3, 14):
        ws.column_dimensions[L(j)].width = 13
    ws.column_dimensions["K"].width = 60

    # ------------------------------------------------------------------ DA5_Recommendation
    ws = ws_["DA5_Recommendation"]
    title(ws, "Step 7e - Recommendation under each lens")
    hdr(ws, 4, 2, ["Lens", "Recommended option", "Key number", "What it values"])
    lens_rows = [
        ("DES decision rule (smallest c with upper 95% P15 <= 1% at m = 1.3)",
         "=IF(52>=INDEX(Analytic_MtGinf!$R$9:$R$19,4),\"A0 (52 >= c* = \"&INDEX(Analytic_MtGinf!$R$9:$R$19,4)&\")\",\"buy chargers\")",
         "=INDEX(Analytic_MtGinf!$R$9:$R$19,4)", "0", "the service standard at the planning growth only (+30%)"),
        ("Pessimistic: minimax cost", "=DA2_Uncertainty!G15", f"=MIN(DA2_Uncertainty!G8:G{PR[1]})", USD, "protection against the worst future"),
        ("Optimistic: minimin cost", "=DA2_Uncertainty!H16", f"=MIN(DA2_Uncertainty!H8:H{PR[1]})", USD, "the best case only"),
        ("Hurwicz (alpha in DA2_Uncertainty!C40)", "=DA2_Uncertainty!C41", "=DA2_Uncertainty!C40", "0.00", "a mix of best and worst case"),
        ("Minimax regret", "=DA2_Uncertainty!G27", f"=MIN(DA2_Uncertainty!G20:G{RR[1]})", USD, "the largest opportunity loss"),
        ("EMV (expected annual cost)", "=DA3_Risk!C19", f"=MIN(DA3_Risk!C12:C{ER[1]})", USD, "probability-weighted cost"),
        ("EVPI (value of a perfect growth forecast)", "-", "=DA3_Risk!C23", USD, "how much better information is worth per year"),
        ("AHP (cost, service, acceptance, flexibility)", f"=DA4_AHP!G{SL + 2}", f"=MAX(DA4_AHP!G{S0}:G{SL})", "0.000",
         "multi-criteria: service and acceptance weigh more than cost"),
    ]
    for k, (lab, rec, num, nf, what) in enumerate(lens_rows):
        r = 5 + k
        put(ws, f"B{r}", lab, "b")
        put(ws, f"C{r}", rec, "k")
        put(ws, f"D{r}", num, "g", nf)
        put(ws, f"E{r}", what, "s")
    Mp = PAY.pivot(index="option", columns="m", values="total")
    ev_ = LJ["emv_values"]
    best_emv = min(ev_, key=ev_.get)
    second = sorted(ev_, key=ev_.get)[1]
    ASn = pd.read_csv(rd / "p6_ahp_sens.csv")
    cs_ = ASn[(ASn.criterion == "cost") & (ASn.best != AH["best"])]
    cost_sw = f"moves to {cs_.iloc[0].best} only if the cost weight reaches about {cs_.iloc[0].weight:.2f}" if len(cs_) else "does not change with the cost weight"
    pqs = LJ["prob_envelope"]
    ptxt = "; ".join(f"{o} for q {'<' if k == 0 else 'from ' + format(x, '.3f') + ' to'} {pqs[k + 1][0]:.3f}" if k + 1 < len(pqs)
                     else f"{o} above {x:.3f}" for k, (x, o) in enumerate(pqs))
    vts = LJ["vot_envelope"]
    vtxt = (f"{vts[0][1]} is cheapest below a value of time of ${vts[1][0]:.2f}/h and {vts[1][1]} above it" if len(vts) > 1
            else f"{vts[0][1]} is cheapest at every value of time from $10 to $50/h")
    hzs = LJ["hurwicz_envelope"]
    htxt = ", ".join(f"{o} from alpha = {x:.3f}" for x, o in hzs)
    box(ws, "B15:I30", f"Why the lenses disagree (waiting and walking time valued at the USDOT $38.80/h). The DES rule asks only whether "
        f"today's 52 chargers meet the service standard at +30% growth: they do (45 are enough), so it buys nothing (A0). Once "
        f"waiting is priced, a shortage at high growth is expensive: at +100% growth keeping 52 chargers costs about "
        f"${Mp.loc['A0', 2.0] / 1000:,.0f}k per year. The pessimistic lens (minimax cost) picks {LJ['minimax_cost']}, whose cost hardly "
        f"changes with growth; minimax regret picks {LJ['minimax_regret']} (largest regret ${LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k); "
        f"the expected cost (EMV) picks {best_emv} at ${ev_[best_emv] / 1000:,.1f}k per year, with {second} only "
        f"${(ev_[second] - ev_[best_emv]) / 1000:,.1f}k more - the EMV ranking is close and sensitive: {vtxt}; by the probability "
        f"of high growth q: {ptxt} (judged q = {LJ['q_judged']:.2f}). Hurwicz: {htxt}. A perfect growth forecast is worth "
        f"${LJ['evpi'] / 1000:,.1f}k per year (EVPI), so learning the growth before buying has value (a staged decision is not "
        f"modelled here). AHP (service weighted highest) picks {AH['best']} and {cost_sw}. A4 rests on a behavioural assumption "
        f"(half of the drivers move their car within 60 min of the end of charging), which the data cannot confirm. Recommended path: "
        f"keep the 52 chargers now (every lens agrees nothing is needed at +30%), start the soft 60-min rule and measure compliance "
        f"and growth each year, and buy chargers (about 6, A2) when growth passes about +40-50% (the 52 chargers hold to m = 1.56); "
        f"plan for 13 (A3) if growth heads towards +100% while compliance stays low.")
    put(ws, "B32", "Python reference (results/phase6/p6_lenses.json, p6_ahp.json):", "b")
    put(ws, "B33", f"minimax cost {LJ['minimax_cost']}, minimin {LJ['minimin_cost']}, minimax regret {LJ['minimax_regret']}, "
        f"EMV {LJ['emv']}, EVPI {LJ['evpi']:,.0f} $/yr, AHP {AH['best']} (CR {AH['CR']:.4f})", "p")
    ws.column_dimensions["B"].width = 58
    ws.column_dimensions["C"].width = 26
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 50
    wb.save(root / a.xlsx)
    print("sheets written:", SHEETS)


if __name__ == "__main__":
    main()
