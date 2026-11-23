""" - recalculate the workbook in Microsoft Excel (COM), save the cached values, count formula errors and read the
check cells of the v2 sheets.  (LibreOffice is not installed on this PC; Excel 16 is used instead.)

Usage (from the project root):
  python scripts/excel_recalc.py --xlsx excel/EV_Charging_DES_Caltech_2019.xlsx --out results/phase1r/excel_check.csv
Output: per-sheet formula / error counts and the check cells (CSV) + printed summary.  No randomness.
"""
import argparse
import time
from pathlib import Path

import pandas as pd
import win32com.client as win32

XL_FORMULAS, XL_ERRORS = -4123, 16
CHECKS = {
    "03_Cleaning": ["C35", "C36", "C43"],
    "04b_DayOfWeek": ["H10", "H14", "F25", "F26", "F27", "F35", "F39", "F41", "F45", "U58"],
    "08b_Service_Bands": ["S10", "S11", "S12", "S13", "S14", "S15", "O10", "Q10"],
    "10b_Replica_band_long": ["E4", "G4", "I4", "J4", "E5", "G5", "I5", "J5", "E6", "G6", "I6", "J6", "E7", "G7", "I7", "J7",
                              "E8", "G8", "I8", "J8"],
    "11_Pilot_n": ["B6", "B22", "B24", "P14"],
    "13b_Output_CI_v2": ["H12", "H13", "D23", "D25", "D26", "E26"],
    "14b_Paired_v2": ["B6", "B7", "B11", "B87", "B88", "B89"],
    "15b_Validation_v2": ["H10", "H11", "H12", "H13", "H14", "H15"],
    "16b_Sensitivity_v2": [f"{c}{r}" for r in range(9, 17) for c in "UVWXYZ"],
    "17_Decision": [f"F{r}" for r in range(41, 52)] + ["A53", "A54", "A55", "A56"],
    #  / Phase 4 sheet (added by scripts/excel_analytic.py); skipped if the sheet is absent
    "Analytic_MtGinf": ["C8", "C12", "C14", "C15", "C16", "W9"] + [f"{c}{r}" for r in range(9, 20) for c in "QRSTUV"],
    #  / Phase 6 sheets (scripts/excel_decision.py)
    "DA1_Costs": ["C12", "C20", "C21", "R59"],
    "DA2_Uncertainty": ["G15", "H16", "G27", "C41"] + [f"E{r}" for r in range(45, 49)],
    "DA3_Risk": ["C12", "C13", "C14", "C15", "C16", "C17", "C19", "C23", "C78"] + [f"E{r}" for r in range(80, 84)] + ["E101"],
    "DA4_AHP": ["H8", "H9", "H10", "H11", "C14", "C17", "D17", "I17", "G30", "J30"] + [f"G{r}" for r in range(23, 29)]
               + [f"K{r}" for r in range(23, 29)],
    "DA5_Recommendation": [f"C{r}" for r in range(5, 13)] + [f"D{r}" for r in range(5, 13)],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    path = str(Path(a.xlsx).resolve())
    xl = win32.DispatchEx("Excel.Application")
    xl.Visible, xl.DisplayAlerts = False, False
    rows = []
    try:
        wb = xl.Workbooks.Open(path)
        t0 = time.time()
        xl.CalculateFullRebuild()
        while xl.CalculationState != 0:          # xlDone
            time.sleep(1)
        print(f"full recalculation {time.time() - t0:.0f} s")
        tot_f = tot_e = 0
        for ws in wb.Worksheets:
            try:
                nf = ws.UsedRange.SpecialCells(XL_FORMULAS).Count
            except Exception:  # noqa: BLE001  (no formulas on the sheet)
                nf = 0
            errs = []
            try:
                rng = ws.UsedRange.SpecialCells(XL_FORMULAS, XL_ERRORS)
                ne = rng.Count
                for area in rng.Areas:
                    for c in area.Cells:
                        errs.append(c.Address(False, False))
                        if len(errs) >= 30:
                            break
                    if len(errs) >= 30:
                        break
            except Exception:  # noqa: BLE001  (no error cells)
                ne = 0
            tot_f, tot_e = tot_f + nf, tot_e + ne
            rows.append(dict(sheet=ws.Name, cell="(sheet)", value=f"formulas={nf}; errors={ne}", errors_at=";".join(errs)))
        names = [wb.Worksheets(i).Name for i in range(1, wb.Worksheets.Count + 1)]
        for s, cells in CHECKS.items():
            if s not in names:
                continue
            ws = wb.Worksheets(s)
            for c in cells:
                rows.append(dict(sheet=s, cell=c, value=ws.Range(c).Text, errors_at=""))
        # every self-check cell ("MATCH ✓" / "CHECK ✗") of the analytic and decision sheets, wherever it sits
        for s in names:
            if not (s.startswith("DA") or s == "Analytic_MtGinf"):
                continue
            ur = wb.Worksheets(s).UsedRange
            vals = ur.Value
            for i, row in enumerate(vals or ()):
                for j, v in enumerate(row):
                    if isinstance(v, str) and ("MATCH ✓" in v or "CHECK ✗" in v):
                        addr = wb.Worksheets(s).Cells(ur.Row + i, ur.Column + j).Address.replace("$", "")
                        rows.append(dict(sheet=s, cell=f"check {addr}", value=v, errors_at=""))
        rows.append(dict(sheet="(total)", cell="", value=f"formulas={tot_f}; errors={tot_e}", errors_at=""))
        wb.Save()
        wb.Close(SaveChanges=False)
    finally:
        xl.Quit()
    R = pd.DataFrame(rows)
    R.to_csv(a.out, index=False, encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 140)
    pd.set_option("display.max_rows", 500)
    print(R.to_string(index=False))


if __name__ == "__main__":
    main()
