""" final consistency pass: every key number is recomputed from its result file, formatted the way the documents
quote it, and searched in the report (report/IE3753_EV_DES_Report.docx), the slides (presentation/IE3753_EV_DES.pptx,
slide text and tables) and the paper (paper/manuscript.docx). A check passes when the expected text is present in every
document that is required to state it. Text is read from the .docx XML (no extra packages) and with python-pptx.
Usage: python scripts/check_consistency_report.py --project .
Output: report/CONSISTENCY_CHECK.csv (check, value, expected_text, source, document, required, found, status).
"""
import argparse
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation


def docx_text(p):
    xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    out = ["".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, flags=re.S)) for para in paras]
    t = "\n".join(out)
    return t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def pptx_text(p):
    out = []
    for sl in Presentation(p).slides:
        for sh in sl.shapes:
            if sh.has_text_frame:
                out.append(sh.text_frame.text)
            if sh.has_table:
                out += [" | ".join(c.text for c in r.cells) for r in sh.table.rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    R = root / "results"
    docs = {"report": docx_text(root / "report" / "IE3753_EV_DES_Report.docx"),
            "slides": pptx_text(root / "presentation" / "IE3753_EV_DES.pptx"),
            "paper": docx_text(root / "paper" / "manuscript.docx")}
    raw = json.loads((root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json").read_text())
    FR = pd.read_csv(R / "phase3" / "p3_frontier.csv")
    GL = pd.read_csv(R / "phase1r" / "r6_growth_limit.csv")
    S5 = pd.read_csv(R / "phase5" / "p5_summary.csv")
    FE = pd.read_csv(R / "phase5" / "p5_feasibility.csv")
    FS_CMP = pd.read_csv(R / "flexsim" / "flexsim_key_cells_comparison.csv")
    PS = pd.read_csv(R / "phase3" / "p3_policy_savings.csv")
    PA = json.loads((R / "phase3" / "p3_policy_assumptions.json").read_text())
    BO = json.loads((R / "phase3" / "p3_boot_decomposition.json").read_text())
    LJ = json.loads((R / "phase6" / "p6_lenses.json").read_text())
    AH = json.loads((R / "phase6" / "p6_ahp.json").read_text())
    PAY = pd.read_csv(R / "phase6" / "p6_payoff.csv")
    VA = pd.read_csv(R / "phase1r" / "validation_v2.csv")
    FG = pd.read_csv(R / "phase1r" / "fit_gaps.csv")
    MOL = pd.read_csv(R / "phase4" / "p4_mol_vs_des.csv")
    MM = pd.read_csv(R / "phase6" / "vv_v2_mmc.csv")
    PN = json.loads((root / "paper" / "paper_numbers.json").read_text())
    IJ = json.loads((R / "phase6" / "p6_inputs.json").read_text())

    def fr(arr, m):
        return int(FR[(FR.arrivals == arr) & np.isclose(FR.m, m)].c_star.iloc[0])

    def p5(g, c, col):
        return float(S5[(S5.group == g) & (S5.scenario == "P0") & (S5.c == c)][col].iloc[0])

    def sav(m, pol):
        return int(PS[np.isclose(PS.m, m) & (PS.policy == pol)].chargers_saved_vs_P0.iloc[0])
    gl_p = GL[(GL.arrivals == "pooled") & GL.feasible].m.max()
    gl_d = GL[(GL.arrivals == "designday") & GL.feasible].m.max()
    va = VA[(VA.service == "band_long") & (VA.metric == "mean_occ")].iloc[0]
    g1 = FG[FG.model == "expon_rate1"].iloc[0]
    d5 = FS_CMP[(FS_CMP.iloc[:, 0] == "front") & np.isclose(FS_CMP.m, 1.3) & (FS_CMP.c == 45)].iloc[0]
    f44 = FE[(FE.arrivals == "pooled") & (FE.c == 44)].iloc[0]
    Mp = PAY.pivot(index="option", columns="m", values="total")
    ev = LJ["emv_values"]
    hz = {o: x for x, o in LJ["hurwicz_envelope"]}
    fl = [fr("pooled", round(1 + 0.1 * i, 1)) for i in range(11)]
    ALL = ["report", "slides", "paper"]
    checks = [  # name, value, expected text (regex), source, documents required
        ("sessions in the data", raw["count"], r"2,953", "data/raw (count)", ALL),
        ("weekdays used", 65, r"65 weekdays", "engine NDAYS / r5_daily_counts.csv", ALL),
        ("c* pooled at +30%", fr("pooled", 1.3), rf"\b{fr('pooled', 1.3)} chargers", "phase3/p3_frontier.csv", ALL),
        ("c* design day at +30%", fr("designday", 1.3), rf"\b{fr('designday', 1.3)}\b", "phase3/p3_frontier.csv", ALL),
        ("growth limit pooled", gl_p, rf"(\+{round((gl_p - 1) * 100)}%|{gl_p:.2f})", "phase1r/r6_growth_limit.csv", ALL),
        ("growth limit design day", gl_d, rf"({round((gl_d - 1) * 100)}%|{gl_d:.2f})", "phase1r/r6_growth_limit.csv", ALL),
        ("P15 at 45 (n = 200)", p5("pooled", 45, "P15_mean"), re.escape(f"{100 * p5('pooled', 45, 'P15_mean'):.3f}%"), "phase5/p5_summary.csv", ALL),
        ("upper 95% at 45", p5("pooled", 45, "P15_hi"), re.escape(f"{100 * p5('pooled', 45, 'P15_hi'):.3f}%"), "phase5/p5_summary.csv", ALL),
        ("P15 at 44", p5("pooled", 44, "P15_mean"), re.escape(f"{100 * p5('pooled', 44, 'P15_mean'):.3f}%"), "phase5/p5_summary.csv", ALL),
        ("FlexSim upper at 45 (+30%)", d5.P15_upper_flexsim, re.escape(f"{100 * d5.P15_upper_flexsim:.3f}%"), "flexsim/flexsim_key_cells_comparison.csv", ALL),
        ("stage-2 replications for 44", int(f44.stage2_n), re.escape(f"{int(f44.stage2_n):,}"), "phase5/p5_feasibility.csv", ALL),
        ("stage-2 lower bound for 44", f44.stage2_lower, re.escape(f"{100 * f44.stage2_lower:.3f}%"), "phase5/p5_feasibility.csv", ["report", "paper"]),
        ("frontier 1.0..2.0", fl, re.escape(", ".join(map(str, fl[:-1])) + f" and {fl[-1]}"), "phase3/p3_frontier.csv", ["paper"]),
        ("frontier key cells", fl, rf"{fl[0]} today, {fl[3]} at \+30%, {fl[6]} at \+60%, {fl[10]} at \+100%", "phase3/p3_frontier.csv", ["report", "slides"]),
        ("saving P1-60 full compliance", sav(1.3, "P1-60"), rf"\b{sav(1.3, 'P1-60')}\b", "phase3/p3_policy_savings.csv", ALL),
        ("saving P1-60 at 50% compliance", sav(1.3, "P3-p0.50"), rf"\b{sav(1.3, 'P3-p0.50')} (if half|with half|chargers are saved)", "phase3/p3_policy_savings.csv", ["report", "paper"]),
        ("saving P1-30", sav(1.3, "P1-30"), rf"\b{sav(1.3, 'P1-30')} \[", "phase3/p3_policy_savings.csv", ALL),
        ("idle share (v2 pairs)", PA["idle_share"], re.escape(f"{100 * PA['idle_share']:.1f}%"), "phase3/p3_policy_assumptions.json", ALL),
        ("rescaled gaps K-S p", g1.KS_boot_p, re.escape(f"{g1.KS_boot_p:.3f}"), "phase1r/fit_gaps.csv", ALL),
        ("rescaled gaps AD p", g1.AD_boot_p, re.escape(f"{g1.AD_boot_p:.3f}"), "phase1r/fit_gaps.csv", ALL),
        ("validation mean occupancy", va["diff"], re.escape(f"+{va['diff']:.2f} [{va.lo:.2f}, {va.hi:.2f}]"), "phase1r/validation_v2.csv", ALL),
        ("M/M/c Wq (rho 0.85)", MM.Wq_sim.iloc[0], re.escape(f"{MM.Wq_sim.iloc[0]:.1f} +/- {MM.Wq_hw.iloc[0]:.1f}"), "phase6/vv_v2_mmc.csv", ["report", "paper"]),
        ("value of time", IJ["INPUTS"]["value_of_time_per_h"], r"38\.80", "phase6/p6_inputs.json (USDOT Table A-2)", ALL),
        ("EMV best (A2)", ev[LJ["emv"]], re.escape(f"{ev[LJ['emv']] / 1000:,.1f}k"), "phase6/p6_lenses.json", ALL),
        ("minimax regret value", LJ["max_regret"][LJ["minimax_regret"]], re.escape(f"{LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k"), "phase6/p6_lenses.json", ALL),
        ("minimax cost worst case", max(Mp.loc[LJ["minimax_cost"]]), re.escape(f"{max(Mp.loc[LJ['minimax_cost']]) / 1000:,.1f}k"), "phase6/p6_payoff.csv", ALL),
        ("EVPI", LJ["evpi"], re.escape(f"{LJ['evpi'] / 1000:,.1f}k"), "phase6/p6_lenses.json", ALL),
        ("AHP CR", AH["CR"], re.escape(f"{AH['CR']:.3f}"), "phase6/p6_ahp.json", ALL),
        ("AHP best score", AH["total"][AH["best"]], re.escape(f"{AH['total'][AH['best']]:.3f}"), "phase6/p6_ahp.json", ALL),
        ("Hurwicz switch A3/A4", hz["A4"], re.escape(f"{hz['A4']:.3f}"), "phase6/p6_lenses.json", ["report", "paper"]),
        ("VoT switch A4/A2", LJ["vot_envelope"][1][0], re.escape(f"{LJ['vot_envelope'][1][0]:.2f}"), "phase6/p6_lenses.json", ["report", "paper"]),
        ("A0 cost at +100%", Mp.loc["A0", 2.0], re.escape(f"{Mp.loc['A0', 2.0] / 1000:,.0f}k"), "phase6/p6_payoff.csv", ["report", "paper"]),
        ("Erlang-C matches DES", int((MOL.err_EC == 0).sum()), rf"{int((MOL.err_EC == 0).sum())} of {len(MOL)}", "phase4/p4_mol_vs_des.csv", ["paper"]),
        ("MOL 1% over-sizing range", (MOL.err_MOL01.min(), MOL.err_MOL01.max()), rf"{int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())} chargers", "phase4/p4_mol_vs_des.csv", ["paper"]),
        ("bootstrap input share", BO["share_input_of_total_per_rep"], re.escape(f"{100 * BO['share_input_of_total_per_rep']:.1f}%"), "phase3/p3_boot_decomposition.json", ["paper"]),
        ("bootstrap c* set", sorted(BO["cstar_distribution"]), r"44, 45 or 46", "phase3/p3_boot_decomposition.json", ["report", "paper"]),
        ("max observed occupancy", PN["max_occupancy_all_sessions"], rf"{PN['max_occupancy_all_sessions']} of 52", "paper/paper_numbers.json", ["paper"]),
        ("median session idle share", PN["median_session_idle_share"], re.escape(f"{100 * PN['median_session_idle_share']:.1f}%"), "paper/paper_numbers.json", ["paper"]),
    ]
    rows = []
    for name, val, pat, src, req in checks:
        for d in ALL:
            found = bool(re.search(pat, docs[d]))
            required = d in req
            status = ("PASS" if found else "FAIL") if required else ("PASS (also stated)" if found else "n/a")
            rows.append(dict(check=name, value=val if not isinstance(val, (list, tuple)) else str(val), expected_text=pat,
                             source=src, document=d, required=required, found=found, status=status))
    # : no author placeholders may remain anywhere (incl. slide notes)
    notes_txt = "\n".join(sl.notes_slide.notes_text_frame.text for sl in Presentation(root / "presentation" / "IE3753_EV_DES.pptx").slides
                          if sl.has_notes_slide)
    for d in ALL:
        txt = docs[d] + ("\n" + notes_txt if d == "slides" else "")
        bad = [p for p in ("[ID]", "[email]", "[Department, University]", "[names]") if p in txt]
        rows.append(dict(check="no author placeholders", value=0, expected_text="none of [ID], [email], [Department, University], [names]",
                         source="report/authors.json ", document=d, required=True, found=not bad,
                         status="PASS" if not bad else "FAIL: " + ", ".join(bad)))
    T = pd.DataFrame(rows)
    T.to_csv(root / "report" / "CONSISTENCY_CHECK.csv", index=False, encoding="utf-8")
    req = T[T.required]
    print(f"checks: {len(checks)}, required document checks: {len(req)}, PASS: {(req.status == 'PASS').sum()}, "
          f"FAIL: {(req.status == 'FAIL').sum()}")
    print(req[req.status == "FAIL"][["check", "document", "expected_text"]].to_string(index=False))


if __name__ == "__main__":
    main()
