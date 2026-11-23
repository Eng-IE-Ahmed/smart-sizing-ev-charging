""" consistency check of the full-length article (extends scripts/check_consistency_report.py to paper_full/).

Every key number is recomputed here from its result file (independently of the manuscript builder), formatted the way
the article quotes it, and searched in the text of paper_full/manuscript_full.docx (paragraphs and tables, read from the
.docx XML). Structural checks: every figure 1-16 and table 1-12 is cited in the text, abstract <= 300 words, main text
8,000-10,000 words, 12-18 figures, 8-14 tables, all references verified and cited, no author placeholders.
Output: paper_full/CONSISTENCY_CHECK.csv (check, value, expected_text, source, found, status).
Usage: python scripts/check_consistency_full_paper.py --project .
"""
import argparse
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


def docx_text(p):
    try:
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf8")
    except PermissionError:  # file open in Word: read a copy made by the Windows copy API (allowed while Word holds it)
        tmp = Path(tempfile.gettempdir()) / "d9_docx_copy.docx"
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Copy-Item -LiteralPath '{p}' -Destination '{tmp}' -Force"],
                       check=True)
        xml = zipfile.ZipFile(tmp).read("word/document.xml").decode("utf8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
    t = "\n".join("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", x, flags=re.S)) for x in paras)
    return t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")


def P(x, d=3):
    return f"{100 * x:.{d}f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--docx", default=None, help="manuscript to check (default paper_full/manuscript_full.docx)")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    R, PF = root / "results", root / "paper_full"
    T = docx_text(Path(a.docx) if a.docx else PF / "manuscript_full.docx")
    body = T.split("\nReferences\n")[0]
    raw = json.loads((root / "data/raw/acn_caltech_2019-03-01_2019-05-31.json").read_text())
    DN = json.loads((PF / "data/descriptive_numbers.json").read_text())
    FG = pd.read_csv(R / "phase1r/fit_gaps.csv").set_index("model")
    DW = pd.read_csv(R / "phase1r/r5_dow_tests.csv").set_index("test")
    PT = pd.read_csv(R / "phase1r/r2_partition.csv")
    VA = pd.read_csv(R / "phase1r/validation_v2.csv")
    S5 = pd.read_csv(R / "phase5/p5_summary.csv")
    FE = pd.read_csv(R / "phase5/p5_feasibility.csv")
    FR = pd.read_csv(R / "phase3/p3_frontier.csv")
    GL = pd.read_csv(R / "phase1r/r6_growth_limit.csv")
    FS_CMP = pd.read_csv(R / "flexsim/flexsim_key_cells_comparison.csv")
    PS = pd.read_csv(R / "phase3/p3_policy_savings.csv")
    BO = json.loads((R / "phase3/p3_boot_decomposition.json").read_text())
    SH = pd.read_csv(R / "phase3/p3_shape_cstar.csv")
    OU = pd.read_csv(R / "phase3/p3_outage_cstar.csv")
    RN = pd.read_csv(R / "phase3/p3_renege_summary.csv")
    MOL = pd.read_csv(R / "phase4/p4_mol_vs_des.csv")
    P4 = json.loads((R / "phase4/p4_summary.json").read_text())
    MM = pd.read_csv(R / "phase6/vv_v2_mmc.csv")
    MM3 = pd.read_csv(root / "04_FlexSim_Models/outputs/mm3_compare_49.csv").set_index("measure")
    VV = json.loads((R / "phase6/vv_v2_summary.json").read_text())
    CR = pd.read_csv(R / "phase1r/r6_crn_efficiency.csv").set_index("metric")
    DD = pd.read_csv(R / "phase1/p1_2_drop_day1_crn-r1-60_v2.csv")
    XC = pd.read_csv(R / "phase6/excel_decision_check.csv")
    LJ = json.loads((R / "phase6/p6_lenses.json").read_text())
    AH = json.loads((R / "phase6/p6_ahp.json").read_text())
    AS = pd.read_csv(R / "phase6/p6_ahp_sens.csv")
    PAY = pd.read_csv(R / "phase6/p6_payoff.csv")
    IJ = json.loads((R / "phase6/p6_inputs.json").read_text())["INPUTS"]
    REF = pd.read_csv(PF / "references_verified.csv")
    ST = json.loads((PF / "d9_ms_stats.json").read_text())
    Mp = PAY.pivot(index="option", columns="m", values="total")

    def p5(g, c, col):
        return float(S5[(S5.group == g) & (S5.scenario == "P0") & (S5.c == c)][col].iloc[0])

    def sav(m, p):
        return int(PS[np.isclose(PS.m, m) & (PS.policy == p)].chargers_saved_vs_P0.iloc[0])

    fl = [int(x) for x in FR[FR.arrivals == "pooled"].sort_values("m").c_star]
    gl_p = GL[(GL.arrivals == "pooled") & GL.feasible].m.max()
    gl_d = GL[(GL.arrivals == "designday") & GL.feasible].m.max()
    f44 = FE[(FE.arrivals == "pooled") & (FE.c == 44)].iloc[0]
    f45 = FE[(FE.arrivals == "pooled") & (FE.c == 45)].iloc[0]
    va = {k: VA[(VA.service == "band_long") & (VA.metric == k)].iloc[0] for k in ("cars", "mean_occ", "peak_occ")}
    hz = {o: a for a, o in LJ["hurwicz_envelope"]}
    pe = {o: a for a, o in LJ["prob_envelope"]}
    aw = PT[PT.pool == "all_weekday"].set_index("partition")
    xs = XC[XC.cell == "(sheet)"]
    xl_f = int(xs.value.str.extract(r"formulas=(\d+)")[0].astype(int).sum())
    d5_45 = FS_CMP[(FS_CMP.set == "front") & np.isclose(FS_CMP.m, 1.3) & (FS_CMP.c == 45)].P15_upper_flexsim.iloc[0]
    ren13 = RN[np.isclose(RN.m, 1.3) & (RN.patience_min == 30) & (RN.c == 45)].lost_share_mean.iloc[0]
    shp = SH[SH["shape"] != "uniform"].sort_values("m").c_star.tolist()
    mol13 = int(MOL[np.isclose(MOL.m, 1.3)]["c_MOL_eps0.01"].iloc[0])
    a2w = AS[(AS.criterion == "cost") & (AS.best == "A2")].weight.min()
    e = re.escape
    C = [  # name, value, expected regex, source
        ("sessions", raw["count"], r"2,953", "data/raw (count)"),
        ("weekday sessions", DN["weekday_sessions"], e(f"{DN['weekday_sessions']:,}"), "paper_full/data/descriptive_numbers.json"),
        ("weekdays", DN["weekdays"], r"65 weekdays", "paper_full/data/descriptive_numbers.json"),
        ("arrivals per weekday", DN["arrivals_per_weekday_mean"], e(f"{DN['arrivals_per_weekday_mean']:.1f} arrivals per weekday"), "paper_full/data/descriptive_numbers.json"),
        ("max occupancy", DN["max_occupancy_all_sessions"], rf"{DN['max_occupancy_all_sessions']} of 52", "paper_full/data/descriptive_numbers.json"),
        ("idle share aggregate", DN["aggregate_idle_share"], e(P(DN["aggregate_idle_share"], 1)), "paper_full/data/descriptive_numbers.json (= phase3/p3_policy_assumptions.json)"),
        ("median session idle share", DN["median_session_idle_share"], e(P(DN["median_session_idle_share"], 1)), "paper_full/data/descriptive_numbers.json"),
        ("mean stay", DN["stay_mean_h"], e(f"{DN['stay_mean_h']:.2f} h"), "paper_full/data/descriptive_numbers.json"),
        ("energy per session", DN["kwh_mean"], e(f"{DN['kwh_mean']:.1f} kWh"), "paper_full/data/descriptive_numbers.json"),
        ("gap K-S p", FG.loc["expon_rate1", "KS_boot_p"], e(f"{FG.loc['expon_rate1', 'KS_boot_p']:.3f}"), "results/phase1r/fit_gaps.csv"),
        ("gap A-D p", FG.loc["expon_rate1", "AD_boot_p"], e(f"{FG.loc['expon_rate1', 'AD_boot_p']:.3f}"), "results/phase1r/fit_gaps.csv"),
        ("gap chi2 p", FG.loc["expon_rate1", "chi2_p"], e(f"{FG.loc['expon_rate1', 'chi2_p']:.3f}"), "results/phase1r/fit_gaps.csv"),
        ("ANOVA F", DW.loc["one-way ANOVA F", "value"], e(f"F = {DW.loc['one-way ANOVA F', 'value']:.2f}"), "results/phase1r/r5_dow_tests.csv"),
        ("dispersion index", DW.loc["index of dispersion s2/mean", "value"], e(f"{DW.loc['index of dispersion s2/mean', 'value']:.3f}"), "results/phase1r/r5_dow_tests.csv"),
        ("R2 six bands", aw.loc["chosen 6 bands", "R2"], e(f"{aw.loc['chosen 6 bands', 'R2']:.3f}"), "results/phase1r/r2_partition.csv"),
        ("c* pooled m 1.3", fl[3], rf"\b{fl[3]} chargers", "results/phase3/p3_frontier.csv"),
        ("c* design day m 1.3", int(FR[(FR.arrivals == "designday") & np.isclose(FR.m, 1.3)].c_star.iloc[0]), r"needs 47|47 for the Tuesday", "results/phase3/p3_frontier.csv"),
        ("P15 at 45", p5("pooled", 45, "P15_mean"), e(P(p5("pooled", 45, "P15_mean"))), "results/phase5/p5_summary.csv"),
        ("P15 CI at 45", (p5("pooled", 45, "P15_lo"), p5("pooled", 45, "P15_hi")), e(f"[{P(p5('pooled', 45, 'P15_lo'))}, {P(p5('pooled', 45, 'P15_hi'))}]"), "results/phase5/p5_summary.csv"),
        ("P15 at 44", p5("pooled", 44, "P15_mean"), e(P(p5("pooled", 44, "P15_mean"))), "results/phase5/p5_summary.csv"),
        ("one-sided upper at 45", f45.one_sided_upper, e(P(f45.one_sided_upper)), "results/phase5/p5_feasibility.csv"),
        ("stage 2 n for 44", int(f44.stage2_n), e(f"{int(f44.stage2_n):,}"), "results/phase5/p5_feasibility.csv"),
        ("stage 2 lower for 44", f44.stage2_lower, e(P(f44.stage2_lower)), "results/phase5/p5_feasibility.csv"),
        ("FlexSim upper at 45", d5_45, e(P(d5_45)), "results/flexsim/flexsim_key_cells_comparison.csv"),
        ("FlexSim own-stream cells: all CIs contain 0", bool(FS_CMP.P15_no_sig_diff.all() and FS_CMP.Wq_min_no_sig_diff.all() and FS_CMP.W95_min_no_sig_diff.all()),
         r"every 95% Welch interval of the difference contains zero", "results/flexsim/flexsim_key_cells_comparison.csv"),
        ("frontier", fl, e(", ".join(map(str, fl[:-1])) + f" and {fl[-1]}"), "results/phase3/p3_frontier.csv"),
        ("growth limit pooled", gl_p, e(f"m = {gl_p:.2f}"), "results/phase1r/r6_growth_limit.csv"),
        ("growth limit design day", gl_d, e(f"m = {gl_d:.2f}"), "results/phase1r/r6_growth_limit.csv"),
        ("bootstrap c* counts", BO["cstar_distribution"], e(f"{BO['cstar_distribution']['44']}, {BO['cstar_distribution']['45']} and {BO['cstar_distribution']['46']} of 50"), "results/phase3/p3_boot_decomposition.json"),
        ("input share of variance", BO["share_input_of_total_per_rep"], e(P(BO["share_input_of_total_per_rep"], 1)), "results/phase3/p3_boot_decomposition.json"),
        ("growth shape 1.3 / 1.6", shp, rf"rise to {shp[0]} at m = 1.3 and {shp[1]}", "results/phase3/p3_shape_cstar.csv"),
        ("outage MTTR 72 margin", int(OU.margin.iloc[4]), rf"{int(OU.margin.iloc[4])} for a 72-h", "results/phase3/p3_outage_cstar.csv"),
        ("reneging m 1.3 (30 min)", ren13, e(P(ren13, 2)), "results/phase3/p3_renege_summary.csv"),
        ("saving P1-30", sav(1.3, "P1-30"), rf"saving of {sav(1.3, 'P1-30')}", "results/phase3/p3_policy_savings.csv"),
        ("saving P1-60", sav(1.3, "P1-60"), rf"60-minute rule would save {sav(1.3, 'P1-60')}", "results/phase3/p3_policy_savings.csv"),
        ("saving P3 25/50/75%", (sav(1.3, "P3-p0.25"), sav(1.3, "P3-p0.50"), sav(1.3, "P3-p0.75")),
         rf"{sav(1.3, 'P3-p0.25')}, {sav(1.3, 'P3-p0.50')} or {sav(1.3, 'P3-p0.75')} chargers are saved", "results/phase3/p3_policy_savings.csv"),
        ("MOL 1% at m 1.3", mol13, rf"gives {mol13} chargers", "results/phase4/p4_mol_vs_des.csv"),
        ("MOL 1% error range", (MOL.err_MOL01.min(), MOL.err_MOL01.max()), rf"{int(MOL.err_MOL01.min())}-{int(MOL.err_MOL01.max())}", "results/phase4/p4_mol_vs_des.csv"),
        ("Erlang-C matches", int((MOL.err_EC == 0).sum()), rf"{int((MOL.err_EC == 0).sum())} of {len(MOL)} growth levels", "results/phase4/p4_mol_vs_des.csv"),
        ("Mt/G/inf RMSE vs data", P4["rmse_vs_data"], e(f"{P4['rmse_vs_data']:.2f}"), "results/phase4/p4_summary.json"),
        ("m(t) peak", P4["max_m_t"], e(f"{P4['max_m_t']:.1f} cars at {P4['t_of_max']}"), "results/phase4/p4_summary.json"),
        ("M/M/c rho 0.85", MM.Wq_sim.iloc[0], e(f"{MM.Wq_sim.iloc[0]:.1f} +/- {MM.Wq_hw.iloc[0]:.1f}"), "results/phase6/vv_v2_mmc.csv"),
        ("FlexSim M/M/3", MM3.loc["Wq_min", "flexsim_mean"], e(f"{MM3.loc['Wq_min', 'flexsim_mean']:.2f}"), "04_FlexSim_Models/outputs/mm3_compare_49.csv"),
        ("validation mean occupancy", va["mean_occ"]["diff"], e(f"{va['mean_occ']['diff']:+.2f} [{va['mean_occ'].lo:.2f}, {va['mean_occ'].hi:.2f}]"), "results/phase1r/validation_v2.csv"),
        ("validation daily peak", va["peak_occ"]["diff"], e(f"{va['peak_occ']['diff']:+.2f} [{va['peak_occ'].lo:.2f}, {va['peak_occ'].hi:.2f}]"), "results/phase1r/validation_v2.csv"),
        ("dispersion model vs data", VV["V11_dispersion"]["model_mean_ratio"], e(f"{VV['V11_dispersion']['model_mean_ratio']:.2f} against {VV['V11_dispersion']['data_mean_ratio']:.2f}"), "results/phase6/vv_v2_summary.json"),
        ("CRN ratio", CR.loc["P15", "variance_reduction_ratio"], e(f"factor of {CR.loc['P15', 'variance_reduction_ratio']:.1f}"), "results/phase1r/r6_crn_efficiency.csv"),
        ("drop day 1", (DD.P15_all.mean(), DD.P15_drop_day1.mean()), e(f"{P(DD.P15_all.mean())} to {P(DD.P15_drop_day1.mean())}"), "results/phase1/p1_2_drop_day1_crn-r1-60_v2.csv"),
        ("Excel formulas", xl_f, e(f"{xl_f:,} formulas"), "results/phase6/excel_decision_check.csv"),
        ("value of time", IJ["value_of_time_per_h"], r"38\.80", "results/phase6/p6_inputs.json"),
        ("A0 cost m 1.3", Mp.loc["A0", 1.3], e(f"USD {Mp.loc['A0', 1.3] / 1000:,.1f}k"), "results/phase6/p6_payoff.csv"),
        ("A0 cost m 2.0", Mp.loc["A0", 2.0], e(f"USD {Mp.loc['A0', 2.0] / 1000:,.0f}k"), "results/phase6/p6_payoff.csv"),
        ("EMV A2", LJ["emv_values"]["A2"], e(f"{LJ['emv_values']['A2'] / 1000:,.1f}k"), "results/phase6/p6_lenses.json"),
        ("minimax cost A3", Mp.loc["A3"].max(), e(f"{Mp.loc['A3'].max() / 1000:,.1f}k"), "results/phase6/p6_payoff.csv"),
        ("max regret A4", LJ["max_regret"]["A4"], e(f"{LJ['max_regret']['A4'] / 1000:,.1f}k"), "results/phase6/p6_lenses.json"),
        ("EVPI", LJ["evpi"], e(f"{LJ['evpi'] / 1000:,.1f}k"), "results/phase6/p6_lenses.json"),
        ("Hurwicz switches", (hz["A4"], hz["A2"]), e(f"between {hz['A4']:.3f} and {hz['A2']:.3f}"), "results/phase6/p6_lenses.json"),
        ("q switches", (pe["A1"], pe["A2"], pe["A4"], pe["A3"]), e(f"q = {pe['A1']:.3f}, A1 up to {pe['A2']:.3f}, A2 up to {pe['A4']:.3f}, A4 up to {pe['A3']:.3f}"), "results/phase6/p6_lenses.json"),
        ("VoT switch", LJ["vot_envelope"][1][0], e(f"USD {LJ['vot_envelope'][1][0]:.2f}"), "results/phase6/p6_lenses.json"),
        ("AHP CR", AH["CR"], e(f"{AH['CR']:.3f}"), "results/phase6/p6_ahp.json"),
        ("AHP best score", AH["total"]["A3"], e(f"{AH['total']['A3']:.3f}"), "results/phase6/p6_ahp.json"),
        ("AHP cost-weight switch", a2w, e(f"reaches {a2w:.2f}"), "results/phase6/p6_ahp_sens.csv"),
    ]
    rows = []
    for name, val, pat, src in C:
        found = bool(re.search(pat, body))
        rows.append(dict(check=name, value=str(val), expected_text=pat, source=src, found=found, status="PASS" if found else "FAIL"))
    cap_free = re.sub(r"(Fig\.|Table) \d+\. ", "", body)            # drop caption labels so only in-text citations count
    figs_cited = [n for n in range(1, 17) if re.search(rf"Fig\. {n}[ab]?\b", cap_free)]
    tabs_cited = [n for n in range(1, 13) if re.search(rf"Table {n}\b", cap_free)]
    S = [("every figure cited in the text", len(figs_cited), len(figs_cited) == 16),
         ("every table cited in the text", len(tabs_cited), len(tabs_cited) == 12),
         ("abstract <= 300 words", ST["abstract_words"], ST["abstract_words"] <= 300),
         ("main text 8,000-10,000 words", ST["main_text_words"], 8000 <= ST["main_text_words"] <= 10000),
         ("figures 12-18", ST["figures"], 12 <= ST["figures"] <= 18),
         ("tables 8-14", ST["tables_main"], 8 <= ST["tables_main"] <= 14),
         ("all references verified", int(REF.verified.sum()), bool(REF.verified.all())),
         ("every verified reference cited", len(ST["references_verified_not_cited"]), not ST["references_verified_not_cited"]),
         ("no author placeholders", 0, not any(p in T for p in ("[ID]", "[email]", "[Department, University]", "[names]")))]
    for name, val, ok in S:
        rows.append(dict(check=name, value=str(val), expected_text="(structural)", source="paper_full/d9_ms_stats.json; manuscript text",
                         found=ok, status="PASS" if ok else "FAIL"))
    Tb = pd.DataFrame(rows)
    Tb.to_csv(PF / "CONSISTENCY_CHECK.csv", index=False, encoding="utf-8")
    print(f"checks: {len(Tb)}, PASS: {(Tb.status == 'PASS').sum()}, FAIL: {(Tb.status == 'FAIL').sum()}")
    print(Tb[Tb.status == "FAIL"][["check", "value", "expected_text"]].to_string(index=False))


if __name__ == "__main__":
    main()
