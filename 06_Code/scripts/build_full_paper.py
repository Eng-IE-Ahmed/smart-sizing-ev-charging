""" full-length research article (journal-neutral IMRaD), built with Microsoft Word (COM, scripts/word_builder.py).

Inputs : results/** (all numbers), paper_full/data/d9_*.{json,csv} (scripts/descriptive_numbers.py), paper_full/figures/FIGSET.csv
         (scripts/full_paper_figures.py), paper_full/references_verified.csv (scripts/verify_references.py), paper_full/LITERATURE_MATRIX.csv,
         report/authors.json, 04_FlexSim_Models/outputs/code_*.txt (FlexScript excerpts).
Text   : scripts/full_paper_text.py (sections 1-9). Citations are written as [@key] / [@!key] (narrative) and resolved here to
         APA 7 in-text form; every cited key must be in references_verified.csv and every listed reference must be cited.
Outputs: paper_full/manuscript_full.docx + .pdf, paper_full/pages/page_*.png, paper_full/highlights.docx,
         paper_full/d9_ms_stats.json (word counts, figure/table counts).
Usage  : python scripts/build_full_paper.py --project .      (no randomness)
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from word_builder import WordDoc  # noqa: E402
import full_paper_text  # noqa: E402

ORG = {  # in-text names for organisational / ambiguous references
    "usdot2024": ("U.S. Department of Transportation", "2024"),
    "afdc_proc": ("U.S. Department of Energy, Alternative Fuels Data Center", "n.d.-a"),
    "afdc_om": ("U.S. Department of Energy, Alternative Fuels Data Center", "n.d.-b"),
    "cec2026": ("California Energy Commission", "2026"),
    "acn_site": ("Caltech", "n.d."),
    "lee2021acn": ("Lee, Lee, et al.", "2021"),
    "lee2021sim": ("Lee, Sharma, et al.", "2021"),
    "asensio2021data": ("Asensio, Lawson, et al.", "2021"),
    "asensio2021jie": ("Asensio, Apablaza, et al.", "2021"),
}
HIGHLIGHTS = [
    "Open data from 2,953 workplace charging sessions drive a validated simulation",
    "Python, Excel and FlexSim versions agree car by car; validation uses occupancy",
    "45 chargers meet a 1% wait-risk target at +30% demand; 52 hold to +56%",
    "Over half of plug-in time is idle; a move-after-charging rule saves 7-11 chargers",
    "Decision lenses agree on no purchase now and split under high growth",
]


def pct(x, d=3):
    return f"{100 * x:.{d}f}%"


def pv(p):
    return "< 0.002" if p <= 0.0021 else f"{p:.3f}"


# ------------------------------------------------------------------------------------------------ numbers
def load_numbers(root):
    R = root / "results"
    N = {"root": root}
    D = json.loads((root / "paper_full/data/descriptive_numbers.json").read_text())
    N.update({f"D_{k}": v for k, v in D.items()})
    FG = pd.read_csv(R / "phase1r/fit_gaps.csv").set_index("model")
    N["FG"] = FG
    N["gap_n"] = int(FG.loc["expon_rate1", "n"])
    N["gap_KSp"], N["gap_ADp"], N["gap_chip"] = FG.loc["expon_rate1", ["KS_boot_p", "AD_boot_p", "chi2_p"]]
    N["gap_weib_ADp"], N["gap_gamma_ADp"] = FG.loc["weibull", "AD_boot_p"], FG.loc["gamma", "AD_boot_p"]
    DW = pd.read_csv(R / "phase1r/r5_dow_tests.csv").set_index("test")
    N["dow_F"], N["dow_p"] = DW.loc["one-way ANOVA F", ["value", "p"]]
    N["dow_KW"], N["dow_KWp"] = DW.loc["Kruskal-Wallis H", ["value", "p"]]
    N["dow_Lev"], N["dow_Levp"] = DW.loc["Levene (median) W", ["value", "p"]]
    N["dow_fri"], N["dow_tue"] = DW.loc["mean Fri (n = 14)", "value"], DW.loc["mean Tue (n = 13)", "value"]
    N["dow_wed"] = DW.loc["mean Wed (n = 13)", "value"]
    N["dow_disp"] = DW.loc["index of dispersion s2/mean", "value"]
    N["dow_disp_p"] = DW.loc["dispersion chi2 (df = n-1), lower-tail p", "p"]
    N["dow_ac1"] = DW.loc["lag-1 autocorrelation of daily counts", "value"]
    PT = pd.read_csv(R / "phase1r/r2_partition.csv")
    aw = PT[PT.pool == "all_weekday"].set_index("partition")
    N["R2_chosen"], N["R2_opt6"], N["R2_AB"], N["R2_24"] = (aw.loc["chosen 6 bands", "R2"], aw.loc["optimal k=6", "R2"],
                                                            aw.loc["A/B classes (v1)", "R2"], aw.loc["24 single hours", "R2"])
    S = pd.read_csv(R / "phase1r/fit_service_band_long.csv")
    S["band"] = S.input.str.replace("band_long_", "", regex=False)
    N["S"] = S
    N["svc_single_maxp"] = S[~S.model.str.startswith("mix")].AD_boot_p.max()
    N["svc_n_models"] = S.model.nunique()
    VA = pd.read_csv(R / "phase1r/validation_v2.csv")
    N["VA"] = VA
    for k in ("cars", "mean_occ", "occ_1200", "peak_occ"):
        r = VA[(VA.service == "band_long") & (VA.metric == k)].iloc[0]
        N[f"val_{k}"] = (r["diff"], r.lo, r.hi)
    N["val_KSp"] = VA[(VA.service == "band_long") & (VA.test == "KS 2-sample (primary)")].p.iloc[0]
    N["val_rmse"] = VA[(VA.service == "band_long") & (VA.test == "profile")].stat.iloc[0]
    r = VA[(VA.service == "AB") & (VA.metric == "mean_occ")].iloc[0]
    N["valAB_occ"] = (r["diff"], r.lo, r.hi)
    N["valAB_KSp"] = VA[(VA.service == "AB") & (VA.test == "KS 2-sample (primary)")].p.iloc[0]
    DD = pd.read_csv(R / "phase1/p1_2_drop_day1_crn-r1-60_v2.csv")
    N["drop_all"], N["drop_d1"] = DD.P15_all.mean(), DD.P15_drop_day1.mean()
    CR = pd.read_csv(R / "phase1r/r6_crn_efficiency.csv").set_index("metric")
    N["crn_ratio"] = CR.loc["P15", "variance_reduction_ratio"]
    S5 = pd.read_csv(R / "phase5/p5_summary.csv")
    N["S5"] = S5[S5.scenario == "P0"]
    N["p5"] = lambda g, c, col: float(S5[(S5.group == g) & (S5.scenario == "P0") & (S5.c == c)][col].iloc[0])
    FE = pd.read_csv(R / "phase5/p5_feasibility.csv")
    N["FE"] = FE
    f44 = FE[(FE.arrivals == "pooled") & (FE.c == 44)].iloc[0]
    N["s2_n"], N["s2_lower"] = int(f44.stage2_n), f44.stage2_lower
    N["f45_upper1"] = FE[(FE.arrivals == "pooled") & (FE.c == 45)].one_sided_upper.iloc[0]
    N["f46dd_lower1"] = FE[(FE.arrivals == "designday") & (FE.c == 46)].one_sided_lower.iloc[0]
    P5J = json.loads((R / "phase5/p5_summary.json").read_text())
    N["n_reps"], N["bonf_K"] = P5J["n_reps"], P5J["bonferroni_intervals"]
    N["feas_systems"], N["alpha_each"] = P5J["feasibility_systems"], P5J["alpha_each_one_sided"]
    N["PD"] = pd.read_csv(R / "phase5/p5_paired.csv").set_index("comparison")
    assert len(N["PD"]) * 2 == N["bonf_K"] and N["PD"].iloc[:7][["dP15_sig", "dWq_sig"]].all().all(), "26-interval text"
    FR = pd.read_csv(R / "phase3/p3_frontier.csv")
    N["FR"] = FR
    N["front"] = [int(x) for x in FR[FR.arrivals == "pooled"].sort_values("m").c_star]
    N["front_dd"] = [int(x) for x in FR[(FR.arrivals == "designday") & FR.c_star.notna()].sort_values("m").c_star]
    N["P15up52_16"] = FR[(FR.arrivals == "pooled") & np.isclose(FR.m, 1.6)].P15_upper_at_52.iloc[0]
    GL = pd.read_csv(R / "phase1r/r6_growth_limit.csv")
    N["gl_p"] = GL[(GL.arrivals == "pooled") & GL.feasible].m.max()
    N["gl_d"] = GL[(GL.arrivals == "designday") & GL.feasible].m.max()
    N["c45"] = int(FR[(FR.arrivals == "pooled") & np.isclose(FR.m, 1.3)].c_star.iloc[0])
    N["c47"] = int(FR[(FR.arrivals == "designday") & np.isclose(FR.m, 1.3)].c_star.iloc[0])
    N["BO"] = json.loads((R / "phase3/p3_boot_decomposition.json").read_text())
    N["IMS"] = pd.read_csv(R / "phase3/p3_input_model_sensitivity.csv")
    N["SH"] = pd.read_csv(R / "phase3/p3_shape_cstar.csv")
    N["OU"] = pd.read_csv(R / "phase3/p3_outage_cstar.csv")
    RN = pd.read_csv(R / "phase3/p3_renege_summary.csv")
    N["ren"] = {(m, p): RN[np.isclose(RN.m, m) & (RN.patience_min == p) & (RN.c == 45)].lost_share_mean.iloc[0]
                for m in (1.3, 1.6) for p in (30, 60)}
    PK = pd.read_csv(R / "phase3/p3_peak_summary.csv")
    N["peak_a_45"] = PK[np.isclose(PK.m, 1.3) & (PK.variant == "a") & (PK.c == 45)].P15_mean.iloc[0]
    SC = pd.read_csv(R / "phase1r/r6_smallest_c.csv")
    N["base_45_n60"] = SC[(SC.service == "band_long") & (SC.arrivals == "pooled")].P15_mean_at_cstar.iloc[0]
    N["PKS"] = pd.read_csv(R / "phase3/p3_peak_savings.csv")
    SC1 = pd.read_csv(R / "phase1/station_count.csv")                     #  C1
    st = SC1[SC1.kind == "stationID"]
    N["stations"], N["st_min"], N["st_max"] = len(st), int(st.sessions.min()), int(st.sessions.max())
    E1 = pd.read_csv(R / "phase6/ahp_weight_sensitivity.csv")             #  E1
    assert (E1.best == "A3").all(), "AHP service-weight sweep: A3 no longer first everywhere - revise the text"
    Sx = E1[[c for c in E1 if c.startswith("S_")]]
    marg = Sx.apply(lambda r: r.max() - r.drop(r.idxmax()).max(), axis=1)
    N["ahp_m10"] = float(marg[E1.service_weight.round(2) == 0.10].iloc[0])
    N["ahp_m70"] = float(marg[E1.service_weight.round(2) == 0.70].iloc[0])
    V = pd.read_csv(R / "phase6/ahp_capital_only_sensitivity.csv")        #  1c
    own = V[V.variant == "ownership"]
    assert set(own.best) == {"A1", "A3"}, "ownership-cost variant changed - revise the text"
    N["own_A1_to"] = float(own[own.best == "A1"].service_weight.max())
    N["own_base_margin"] = float(own.iloc[(own.service_weight - 0.423).abs().argmin()].margin)
    capv = V[V.variant == "capital_linear"]
    assert "A3" not in set(capv.best), "capital-only variant: A3 wins somewhere - revise the text"
    seq = list(dict.fromkeys(capv.sort_values("service_weight").best))
    N["cap_seq"] = ", then ".join(seq[:-1]) + " and then " + seq[-1] if len(seq) > 1 else seq[0]
    DM = pd.read_csv(R / "phase6/ahp_dominance.csv")                      #  1d
    gap = eval(DM.A3_gap_to_column_max.iloc[0])  # dict written by supplementary_computations.py
    flips = eval(DM.first_flip_one_way.iloc[0])
    N["ahp_gap_max"] = max(gap.values())
    N["ahp_flip_cost"], N["ahp_flip_flex"] = flips["cost"][0], flips["flexibility"][0]
    assert set(DM[DM.A3_dominates].option) == {"A0", "A1"}
    LJ0 = json.loads((R / "phase6/p6_lenses.json").read_text())
    N["emvA2"] = LJ0["emv_values"]["A2"] / 1000
    N["emv_gap"] = (LJ0["emv_values"]["A3"] - LJ0["emv_values"]["A2"]) / 1000
    GL0 = pd.read_csv(R / "phase1r/r6_growth_limit.csv")
    gp, gd = GL0[(GL0.arrivals == "pooled") & GL0.feasible].m.max(), GL0[(GL0.arrivals == "designday") & GL0.feasible].m.max()
    N["lead_dd"] = 12 * np.log(gd / 1.4) / np.log(1.1)   # months at an illustrative 10%/yr growth, trigger +40%
    N["lead_avg"] = 12 * np.log(gp / 1.4) / np.log(1.1)
    F1 = pd.read_csv(R / "phase5/p1_60_compliance_breakeven.csv")         #  F1
    N["F1"] = {round(r.m, 1): r._asdict() for r in F1.itertuples()}
    R7 = pd.read_csv(R / "phase1r/r7_outputs.csv")
    N["r7"] = {(int(r.c), r.metric): r.mean for r in R7.itertuples()}
    R7h = pd.read_csv(R / "phase1r/r7_p15_by_hour.csv")
    N["r7h"] = {(int(r.c), int(r.hour)): r.P15_pooled for r in R7h.itertuples()}
    PS = pd.read_csv(R / "phase3/p3_policy_savings.csv")
    N["PS"] = PS
    N["sav"] = lambda m, p: int(PS[np.isclose(PS.m, m) & (PS.policy == p)].chargers_saved_vs_P0.iloc[0])
    N["cst"] = lambda m, p: int(PS[np.isclose(PS.m, m) & (PS.policy == p)].c_star.iloc[0])
    N["PA"] = json.loads((R / "phase3/p3_policy_assumptions.json").read_text())
    N["MOL"] = pd.read_csv(R / "phase4/p4_mol_vs_des.csv")
    N["P4"] = json.loads((R / "phase4/p4_summary.json").read_text())
    N["MM"] = pd.read_csv(R / "phase6/vv_v2_mmc.csv")
    N["VV"] = json.loads((R / "phase6/vv_v2_summary.json").read_text())
    N["MM3"] = pd.read_csv(root / "04_FlexSim_Models/outputs/mm3_compare_49.csv").set_index("measure")
    N["B3"] = pd.read_csv(R / "flexsim/flexsim_trace_check.csv").set_index("c")
    N["B4"] = pd.read_csv(R / "flexsim/flexsim_vs_engine_own_streams.csv")
    FS_CMP = pd.read_csv(R / "flexsim/flexsim_key_cells_comparison.csv")
    N["FS_CMP"] = FS_CMP
    N["d5_up45"] = FS_CMP[(FS_CMP.set == "front") & np.isclose(FS_CMP.m, 1.3) & (FS_CMP.c == 45)].P15_upper_flexsim.iloc[0]
    N["d5_up44"] = FS_CMP[(FS_CMP.set == "front") & np.isclose(FS_CMP.m, 1.3) & (FS_CMP.c == 44)].P15_upper_flexsim.iloc[0]
    XC = pd.read_csv(R / "phase6/excel_decision_check.csv")
    XS = XC[XC.cell == "(sheet)"]  # one row per sheet (other rows are self-check cells)
    N["xl_formulas"] = int(XS.value.str.extract(r"formulas=(\d+)")[0].astype(int).sum())
    N["xl_errors"] = int(XS.value.str.extract(r"errors=(\d+)")[0].astype(int).sum())
    N["xl_wq_rel"] = XC[(XC.sheet == "10b_Replica_band_long") & (XC.cell == "I5")].value.iloc[0]
    N["IJ"] = json.loads((R / "phase6/p6_inputs.json").read_text())
    N["LJ"] = json.loads((R / "phase6/p6_lenses.json").read_text())
    N["AH"] = json.loads((R / "phase6/p6_ahp.json").read_text())
    VS = pd.read_csv(R / "phase6/p6_vot_sens.csv")
    N["vot_n"] = len(VS)
    assert not (VS[["emv_best", "minimax_regret_best", "minimax_cost_best"]] == "A5").any().any(), "A5 wins somewhere: revise text"
    AS = pd.read_csv(R / "phase6/p6_ahp_sens.csv")
    N["ahp_A2_w"] = AS[(AS.criterion == "cost") & (AS.best == "A2")].weight.min()
    PAY = pd.read_csv(R / "phase6/p6_payoff.csv")
    N["PAY"] = PAY
    N["Mp"] = PAY.pivot(index="option", columns="m", values="total")
    return N


# ------------------------------------------------------------------------------------------------ citations
class Cite:
    def __init__(self, REF):
        self.REF = REF.set_index("key")
        self.used = []

    def name_year(self, key):
        if key not in self.REF.index:
            raise KeyError(f"citation key not verified: {key}")
        if key not in self.used:
            self.used.append(key)
        if key in ORG:
            return ORG[key]
        apa = self.REF.loc[key, "apa"]
        m = re.match(r"^(.*?) \((\d{4}|n\.d\.[-a-z]*)\)\.", apa)
        auth, yr = m.group(1), m.group(2)
        fams = re.findall(r"(?:^|, (?:& )?)([^,]+?), (?:II, )?(?:\w{1,2}\.[- ]?)+(?=,|$)", auth)
        if not fams:
            fams = [auth.split(",")[0]]
        if len(fams) == 1:
            nm = fams[0]
        elif len(fams) == 2:
            nm = f"{fams[0]} & {fams[1]}"
        else:
            nm = f"{fams[0]} et al."
        return nm, yr

    def sub(self, text):
        def paren(m):
            parts = []
            for k in [x.strip().lstrip("@") for x in m.group(1).split(";")]:
                nm, yr = self.name_year(k)
                parts.append(f"{nm}, {yr}")
            return "(" + "; ".join(parts) + ")"

        def narr(m):
            nm, yr = self.name_year(m.group(1))
            return f"{nm.replace(' & ', ' and ')} ({yr})"
        text = re.sub(r"\[@!(\w+)\]", narr, text)
        return re.sub(r"\[(@\w+(?:;\s*@\w+)*)\]", paren, text)


# ------------------------------------------------------------------------------------------------ tables
ARCH = {  #  I3: re-checked 19 Nov 2026 (scripts/check_sources.py); fresh Internet Archive snapshots
    "afdc_proc": "https://web.archive.org/web/20261119142457/https://afdc.energy.gov/fuels/electricity-infrastructure-development",
    "afdc_om": "https://web.archive.org/web/20261119142522/https://afdc.energy.gov/fuels/electricity-infrastructure-maintenance-and-operation",
    "cec2026": "https://web.archive.org/web/20261119142634/https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-vehicle-charging-infrastructure-assessment",
    "acn_site": "https://web.archive.org/web/20261119142702/https://ev.caltech.edu/dataset",
}


def apa_override(key, apa):
    """ I1-I3 corrections applied to the verified APA strings (see paper_full/RESPONSE_TO_REVIEW.md)."""
    if key == "kinay2023":  # Crossref: no volume/issue/pages, article number only, online 16 June 2023
        new = apa.replace("*Transportation Science*, trsc.2021.0494.",
                          "*Transportation Science*. Advance online publication, 16 June 2023, Article trsc.2021.0494.")
        assert new != apa, "Kinay APA pattern changed"
        apa = new
    if key == "komarina2026":  # year convention: Crossref issue year for every reference
        apa += " [Crossref issue year 2027; article identifier dated 2026.]"
    if key in ARCH:
        apa = apa.replace("Retrieved November 17, 2026", "Retrieved November 19, 2026") + f" Archived at {ARCH[key]}"
    return apa


def apa_sort_key(apa):
    """APA 7 order: by author string letter by letter (diacritics folded), so a sole-author work precedes multi-author
    works with the same first author; then by year."""
    m = re.match(r"^(.*?) \((.*?)\)\.", apa)
    auth, yr = (m.group(1), m.group(2)) if m else (apa, "")
    fold = "".join(ch for ch in unicodedata.normalize("NFKD", auth) if not unicodedata.combining(ch)).lower()
    return (fold, yr)


def short(x):
    x = str(x)
    return x.split(" (")[0] if len(x) > 28 else x


def tables(N, LM, C):
    T = {}
    pick = ["kiraly2026", "uribe2023", "celik2024", "pruckner2017", "uimonen2020", "komarina2026", "bayram2021", "kinay2023",
            "khaksari2021", "zeng2019", "bayram2022sg", "ju2023", "lahariya2020", "ferguson2018", "hlalele2025"]
    rows = [["Study", "Method", "Data", "Decision", "Growth", "Idle", "V&V", "Decision analysis"]]
    L = LM.set_index("key")
    for k in pick:
        r = L.loc[k]
        nm, yr = C.name_year(k)
        rows.append([f"{nm} ({yr})", short(r.method), short(r.data), short(r.decision_variable), short(r.demand_growth),
                     short(r.idle_overstay), short(r.vv_reported), short(r.decision_analysis)])
    rows.append(["This study", "DES in 3 tools + Mt/G/inf, Erlang C", "ACN-Data, 2,953 sessions", "chargers; idle rules",
                 "yes (m 1.0-2.0)", "yes (rules, compliance)", "yes (exact 3-way; data)", "payoff, 5 lenses, EVPI, AHP"])
    T["t1"] = dict(rows=rows, cap="Comparison of this study with selected studies from the literature matrix (coded from the "
                   "abstract or full text; n.s. = not stated in what was read). The full matrix of 50 sources is in the "
                   "supplementary file LITERATURE_MATRIX.csv.", widths=(2.6, 2.6, 2.3, 2.0, 1.6, 1.6, 1.8, 1.7), fs=7)

    B = pd.read_csv(N["root"] / "paper_full/data/d9_band_stats.csv")
    rows = [["Arrival band", "Sessions (share)", "Stay mean / median (h)", "Stay P90 (h)", "Stays > 24 h", "Charging (h)",
             "Idle (h)", "Idle share", "Energy (kWh)"]]
    for r in B.itertuples():
        rows.append([f"{r.band} h", f"{r.sessions:,} ({100 * r.share_of_arrivals:.1f}%)", f"{r.stay_mean_h:.2f} / {r.stay_median_h:.2f}",
                     f"{r.stay_p90_h:.1f}", r.stays_gt24h, f"{r.charge_mean_h:.2f}", f"{r.idle_mean_h:.2f}",
                     pct(r.idle_share_agg, 1), f"{r.kwh_mean:.1f}"])
    D = {k[2:]: v for k, v in N.items() if k.startswith("D_")}
    rows.append(["All weekdays", f"{D['weekday_sessions']:,} (100%)", f"{D['stay_mean_h']:.2f} / {D['stay_median_h']:.2f}", "-",
                 D["stays_gt24h"], f"{D['charge_mean_h']:.2f}", f"{D['idle_mean_h']:.2f}", pct(D["aggregate_idle_share"], 1),
                 f"{D['kwh_mean']:.1f}"])
    T["t2"] = dict(rows=rows, cap=f"Weekday sessions by arrival band (Pacific local time; {D['weekdays']} weekdays). Charging and "
                   f"idle hours use the {D['valid_pairs']:,} sessions with a valid charge-completion time; the idle share is idle "
                   "hours divided by plug-in hours.", widths=(2.0, 2.2, 2.4, 1.4, 1.3, 1.5, 1.3, 1.4, 1.4), fs=7.5)

    FG = N["FG"]
    nm = {"expon_rate1": "Rescaled gaps vs Exp(1)", "expon": "Exponential, fitted rate", "weibull": "Weibull",
          "gamma": "Gamma", "burr12": "Burr XII", "loglogistic": "Log-logistic", "lognorm": "Log-normal",
          "invgauss": "Inverse Gaussian", "exponweib": "Exponentiated Weibull", "gengamma": "Generalised gamma"}
    rows = [["Test or model", "Statistic", "p-value", "Verdict"]]
    for k in ["expon_rate1", "expon", "weibull", "gamma", "exponweib", "gengamma", "burr12", "loglogistic", "lognorm", "invgauss"]:
        r = FG.loc[k]
        rows.append([f"{nm[k]} ({int(r.n_par)} par.)", f"K-S {r.KS:.3f}; A-D {r.AD:.3f}", f"K-S {pv(r.KS_boot_p)}; A-D {pv(r.AD_boot_p)}",
                     r.verdict])
    rows += [["Day of week: one-way ANOVA (65 days)", f"F = {N['dow_F']:.2f}", f"{N['dow_p']:.4f}", "days differ"],
             ["Day of week: Kruskal-Wallis", f"H = {N['dow_KW']:.1f}", f"{N['dow_KWp']:.4f}", "days differ"],
             ["Equal variances across weekdays (Levene)", f"W = {N['dow_Lev']:.3f}", f"{N['dow_Levp']:.3f}", "not rejected"],
             ["Index of dispersion of daily counts", f"{N['dow_disp']:.3f}", f"{N['dow_disp_p']:.3f} (lower tail)", "under-dispersed"],
             ["Lag-1 autocorrelation of daily counts", f"{N['dow_ac1']:.3f}", "-", "no serial dependence"]]
    T["t3"] = dict(rows=rows, cap=f"Arrival-process tests. Rows 1-10: goodness of fit of the {N['gap_n']:,} time-rescaled "
                   "inter-arrival gaps (parametric bootstrap p-values, B = 500 resamples; p < 0.002 marks the floor 1/(B+1)). Under the "
                   "NHPP the rescaled gaps are Exp(1); a fitted model is accepted only if all tests pass. Rows 11-15: day-of-week "
                   "and dispersion tests of the daily counts.", widths=(6.0, 3.6, 4.2, 2.6), fs=7.5)

    S = N["S"]
    rows = [["Band", "n", "Best single family (A-D p)", "Best mixture (A-D p)", "Single families rejected", "Accepted models"]]
    for b in ["05-07", "08-09", "10-11", "12-15", "16-20", "21-04"]:
        d = S[S.band == b]
        sg = d[~d.model.str.startswith("mix")].sort_values("AD")
        mx = d[d.model.str.startswith("mix")].sort_values("AD")
        acc = ", ".join(d[d.verdict == "accepted"].model) or "none"
        rows.append([f"{b} h", int(d.n.iloc[0]), f"{sg.model.iloc[0]} ({pv(sg.AD_boot_p.iloc[0])})",
                     f"{mx.model.iloc[0]} ({pv(mx.AD_boot_p.iloc[0])})", f"{int((sg.verdict == 'rejected').sum())} of {len(sg)}", acc])
    T["t4"] = dict(rows=rows, cap="Stay (service-time) model by arrival band, weekdays including stays over 24 h: best single "
                   "parametric family and best log-normal mixture (mixLNk = k components) by Anderson-Darling statistic, with "
                   "parametric-bootstrap p. A model is accepted when the K-S, A-D and chi-square tests all pass. Because no single "
                   "family passes, the simulation samples each band's empirical pool.", widths=(1.6, 1.0, 3.8, 3.6, 2.6, 3.8), fs=7.5)

    IJ = N["IJ"]["INPUTS"]
    rows = [["Element", "Setting"],
            ["Run type", "Terminating: 65 weekdays back to back (1,560 h), empty start, all cars served"],
            ["Arrivals", "NHPP, 48 half-hour rates x growth factor m; inversion of the cumulative rate"],
            ["Stays", "Empirical pool of the car's arrival band (6 bands), including stays over 24 h"],
            ["Queue", "One FIFO queue, no balking (reneging only in the robustness experiment); c identical chargers"],
            ["Outputs per replication", "P15 = share of cars waiting > 15 min; Wq (mean wait); W95 (95th percentile wait); utilisation"],
            ["Random numbers", "Replication r: stream [r,1] arrivals, [r,2] stays, [r,3] policy compliance (common random numbers)"],
            ["Decision rule (fixed in advance)", "Smallest c with upper 95% t-bound of P15 <= 1%"],
            ["Replications", "60, then +20 while the bound is within 0.15 pp of 1%, up to 200; 200 in the output analysis"],
            ["Statistical guarantee", f"One-sided Bonferroni over {N['feas_systems']} systems (each at {100 * (1 - N['alpha_each']):.2f}%); "
                                      f"stage 2 with {N['s2_n']:,} fresh replications for undetermined systems"],
            ["Factors", "c (34-66); m (1.0-2.0); pooled weekdays or Tue-Wed design day; policies P1-P3; growth shape; "
                        "outages; reneging; bootstrap inputs"],
            ["Variance reduction", f"CRN: variance of paired P15 differences reduced {N['crn_ratio']:.1f}-fold (c = 45 vs 43)"]]
    T["t5"] = dict(rows=rows, cap="Simulation and experimental design.", widths=(4.2, 12.2), fs=7.5)

    rows = [["Input", "Value", "Source / status"],
            ["Hardware per Level-2 connector", f"USD {IJ['hardware_per_connector']:,.0f}", "[@afdc_proc]; based on [@borlaug2020]"],
            ["Installation per connector", f"USD {IJ['installation_per_connector']:,.0f}", "[@afdc_proc]"],
            ["Capital recovery", f"{100 * IJ['interest']:.0f}%, {IJ['life_years']} years (CRF {N['IJ']['crf']:.4f})", "assumption, varied"],
            ["Maintenance per charger-year", f"USD {IJ['maintenance_per_charger_yr']:,.0f}", "[@afdc_om]"],
            ["Network fee per port-year", f"USD {IJ['network_fee_per_port_yr']:,.0f}", "assumption, varied (0-600)"],
            ["Value of waiting and walking time", f"USD {IJ['value_of_time_per_h']:.2f} per hour", "[@usdot2024], Table A-2, 2023 dollars"],
            ["Time to move a car (policy)", f"{IJ['move_minutes_per_moved_car']:.0f} min per moved car", "assumption, varied (2-10)"],
            ["Policy administration", f"USD {IJ['admin_soft_rule_yr']:,.0f} (voluntary) / {IJ['admin_fee_rule_yr']:,.0f} (fee) per year", "assumption"],
            ["Operating days", f"{IJ['weekdays_per_year']} weekdays per year", "assumption"],
            ["Probabilities of m = 1.0 / 1.3 / 1.6 / 2.0", " / ".join(f"{v:.2f}" for v in IJ["prob"].values()), "judgement, varied (q)"]]
    T["t6"] = dict(rows=rows, cap="Cost inputs of the decision analysis (annual basis).", widths=(5.4, 5.0, 6.0), fs=7.5)

    MM, B3, MM3, VV = N["MM"], N["B3"], N["MM3"], N["VV"]
    rows = [["Check", "Result", "Verdict"],
            ["Hand simulation of the first cars; extreme case with very few arrivals", "same event times; nobody waits", "pass"],
            ["Excel workbook = Python (replication 1, m = 1.3, c = 42)", f"3,254 cars; Wq relative difference {N['xl_wq_rel']}", "pass"],
            ["FlexSim = Python, trace mode (same arrivals and stays)", f"3,254 cars; max |wait difference| {B3.loc[42, 'max_abs_wait_diff_min']:.1e} min "
             f"(c = 42), {B3.loc[45, 'max_abs_wait_diff_min']:.1e} min (c = 45); Wq, P15 identical", "pass"],
            ["FlexSim own streams vs Python (12 key cells, 30 reps each)", "every Welch CI of the difference in Wq, P15 and W95 contains 0", "pass"],
            ["FlexSim known answer M/M/3 (49 reps)", f"Wq {MM3.loc['Wq_min', 'flexsim_mean']:.2f} [{MM3.loc['Wq_min', 'lo']:.2f}, "
             f"{MM3.loc['Wq_min', 'hi']:.2f}] vs exact {MM3.loc['Wq_min', 'exact']:.2f} min", "pass"],
            ["Python known answer M/M/c (Erlang C)", "; ".join(f"rho {r.rho:.2f}: {r.Wq_sim:.1f} +/- {r.Wq_hw:.1f} vs {r.Wq_exact_min:.1f} min"
                                                                for r in MM.itertuples()), "pass"],
            ["Flow balance (120 replications)", f"imbalance {VV['V7a_flow_imbalance_total']}", "pass"],
            ["Overload (c = 12)", f"Wq {VV['V6_overload_Wq_min']['12']['1']:,.0f} min -> {VV['V6_overload_Wq_min']['12']['2']:,.0f} min "
             "when the run is doubled", "pass (unstable as expected)"],
            ["Start-up bias (drop day 1)", f"P15 {pct(N['drop_all'])} -> {pct(N['drop_d1'])}", "negligible"],
            ["Model - data: cars per weekday", "{:+.2f} [{:.2f}, {:.2f}]".format(*N["val_cars"]), "CI contains 0"],
            ["Model - data: mean occupied chargers", "{:+.2f} [{:.2f}, {:.2f}]".format(*N["val_mean_occ"]), "CI contains 0"],
            ["Model - data: occupancy at 12:00", "{:+.2f} [{:.2f}, {:.2f}]".format(*N["val_occ_1200"]), "CI contains 0"],
            ["Model - data: daily peak occupancy", "{:+.2f} [{:.2f}, {:.2f}]; K-S p = {:.3f}".format(*N["val_peak_occ"], N["val_KSp"]),
             "CI contains 0"],
            ["Occupancy profile (48 half-hours)", f"RMSE {N['val_rmse']:.2f} cars", "close"],
            ["Occupancy dispersion (variance/mean)", f"model {VV['V11_dispersion']['model_mean_ratio']:.2f} vs data "
             f"{VV['V11_dispersion']['data_mean_ratio']:.2f}", "model conservative"],
            ["Input uncertainty (50 bootstrap inputs x 20 reps)", f"input share of P15 variance {pct(N['BO']['share_input_of_total_per_rep'], 1)}",
             "small"]]
    T["t7"] = dict(rows=rows, cap="Verification and validation (structure after Sargent, 2013). Model - data rows: 95% Welch "
                   "intervals at current demand with 52 chargers (60 replications vs 65 observed weekdays).",
                   widths=(6.2, 7.6, 2.6), fs=7.5)

    rows = [["Arrivals", "c", "Wq (min)", "P15 mean [two-sided 95% CI]", "One-sided bounds (Bonferroni)", "Classification"]]
    FE = N["FE"].set_index(["arrivals", "c"])
    for g, cs in (("pooled", range(44, 49)), ("designday", range(46, 50))):
        for c in cs:
            d = N["S5"][(N["S5"].group == g) & (N["S5"].c == c)].iloc[0]
            f = FE.loc[(g, c)]
            cl = f.classification + (f" -> {f.stage2_classification} (stage 2: n = {int(f.stage2_n):,}, lower {pct(f.stage2_lower)})"
                                     if isinstance(f.stage2_classification, str) else "")
            rows.append(["weekdays" if g == "pooled" else "Tue-Wed", c, f"{d.Wq_mean:.3f}",
                         f"{pct(d.P15_mean)} [{pct(d.P15_lo)}, {pct(d.P15_hi)}]", f"[{pct(f.one_sided_lower)}, {pct(f.one_sided_upper)}]", cl])
    T["t8"] = dict(rows=rows, cap=f"Charger options at +30% demand (m = 1.3), {N['n_reps']} CRN replications each. Feasible means "
                   "the one-sided upper bound is at most 1%; infeasible means the one-sided lower bound exceeds 1% (joint "
                   "confidence of at least 95% over the nine systems).", widths=(1.9, 0.8, 1.6, 4.2, 3.6, 4.3), fs=7.5)

    IMS, SH, OU, BO = N["IMS"], N["SH"], N["OU"], N["BO"]
    rows = [["Factor", "Setting", "c* at m = 1.3", "Note"],
            ["Base case", "pooled weekdays, band_long stays", N["c45"], "validated input model"],
            ["Arrival pattern", "Tue-Wed design day", N["c47"], "validated"]]
    lab = {"band_long_opt": "6 optimised bands", "band": "6 bands, stays <= 24 h", "AB": "2 classes (A/B)",
           "mixA_lnB": "mixture A / log-normal B", "jointGMM": "joint Gaussian mixture (K = 10)"}
    for r in IMS[(IMS.arrivals == "pooled") & (IMS.service != "band_long")].itertuples():
        rows.append(["Stay model", lab.get(r.service, r.service), int(r.c_star), f"validation {r.validation}"])
    for r in SH[SH["shape"] != "uniform"].itertuples():
        base = int(SH[(SH["shape"] == "uniform") & np.isclose(SH.m, r.m)].c_star.iloc[0])
        rows.append(["Growth shape", f"growth only in 07:00-10:00 (m = {r.m:g})", int(r.c_star), f"uniform growth: {base}"])
    for r in OU.itertuples():
        rows.append(["Outages", r.case, int(r.c_star), f"margin {int(r.margin)}"])
    rows.append(["Input uncertainty", "50 bootstrap samples of the 65 days", "44 / 45 / 46",
                 " / ".join(str(v) for v in BO["cstar_distribution"].values()) + " samples"])
    rows.append(["Reneging (at c = 45)", "patience 30 / 60 min", "-", f"{pct(N['ren'][(1.3, 30)], 2)} / {pct(N['ren'][(1.3, 60)], 2)} of drivers leave"])
    T["t9"] = dict(rows=rows, cap="Robustness of the charger requirement at +30% demand. Stay models that fail validation (Section 5) "
                   "under-size by one or two chargers; outages and concentrated growth raise the requirement.",
                   widths=(2.8, 6.2, 2.2, 5.2), fs=7.5)

    PS = N["PS"]
    lab = {"P1-30": "Move within 30 min after charging ends", "P1-60": "Move within 60 min", "P1-120": "Move within 120 min",
           "P2-cap4h": "4-hour stay cap", "P3-p0.25": "60-min rule, 25% comply", "P3-p0.50": "60-min rule, 50% comply",
           "P3-p0.75": "60-min rule, 75% comply"}
    rows = [["Policy", "c* (m = 1.3)", "Saved [95% CI]", "c* (m = 1.6)", "Saved [95% CI]"]]
    for k, t in lab.items():
        a = PS[np.isclose(PS.m, 1.3) & (PS.policy == k)].iloc[0]
        b = PS[np.isclose(PS.m, 1.6) & (PS.policy == k)].iloc[0]
        rows.append([t, int(a.c_star), f"{int(a.chargers_saved_vs_P0)} [{a.saved_CI95_lo:.0f}, {a.saved_CI95_hi:.0f}]", int(b.c_star),
                     f"{int(b.chargers_saved_vs_P0)} [{b.saved_CI95_lo:.0f}, {b.saved_CI95_hi:.0f}]"])
    T["t10"] = dict(rows=rows, cap=f"Chargers saved by idle-time policies (no policy: {N['cst'](1.3, 'P0')} at m = 1.3 and "
                    f"{N['cst'](1.6, 'P0')} at m = 1.6; paired bootstrap 95% CI). Behaviour under each policy is assumed.",
                    widths=(5.6, 2.2, 2.6, 2.2, 2.6), fs=7.5)

    Mp, LJ = N["Mp"], N["LJ"]
    ms = list(Mp.columns)
    reg = Mp - Mp.min(axis=0)
    names = {o[0]: o[1] for o in N["IJ"]["options"]}
    rows = [["Option"] + [f"m = {m:g}" for m in ms] + ["Expected", "Worst case", "Max regret"]]
    for o in Mp.index:
        rows.append([f"{o} {names[o]}"] + [f"{Mp.loc[o, m] / 1000:,.1f}" for m in ms] +
                    [f"{LJ['emv_values'][o] / 1000:,.1f}", f"{Mp.loc[o].max() / 1000:,.1f}", f"{reg.loc[o].max() / 1000:,.1f}"])
    T["t11"] = dict(rows=rows, cap="Payoff table: annual cost (USD thousand) of each option in each growth future, with the "
                    "expected cost (probabilities in Table 6), the worst case and the maximum regret. Waiting costs come from "
                    f"{N['n_reps']} CRN replications per cell.", widths=(5.6, 1.4, 1.4, 1.4, 1.4, 1.6, 1.6, 1.6), fs=7.5)

    ev, AH = LJ["emv_values"], N["AH"]
    hz = LJ["hurwicz_envelope"]
    rows = [["Lens", "Choice", "Key number"],
            ["Simulation rule at m = 1.3", "A0 keep 52", f"c* = {N['c45']} (design day {N['c47']})"],
            ["Pessimistic (minimax cost)", LJ["minimax_cost"], f"worst case USD {Mp.loc[LJ['minimax_cost']].max() / 1000:,.1f}k"],
            ["Optimistic (minimin cost)", LJ["minimin_cost"], f"USD {Mp.loc[LJ['minimin_cost']].min() / 1000:,.1f}k"],
            ["Hurwicz", " / ".join(o for _, o in hz), "alpha switch points " + " / ".join(f"{a:.3f}" for a, _ in hz[1:])],
            ["Minimax regret", LJ["minimax_regret"], f"max regret USD {LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k"],
            ["Expected cost (EMV)", LJ["emv"], f"USD {ev[LJ['emv']] / 1000:,.1f}k (A4 {ev['A4'] / 1000:,.1f}k)"],
            ["Expected value of perfect information", "-", f"USD {LJ['evpi'] / 1000:,.1f}k per year"],
            [f"AHP (CR {AH['CR']:.3f})", AH["best"], f"score {AH['total'][AH['best']]:.3f}; A2 when the total-cost weight >= {N['ahp_A2_w']:.2f}; waiting counted twice"]]
    T["t12"] = dict(rows=rows, cap="Choice under each decision lens (A0 keep 52; A1-A3 buy 2, 6 or 13; A4 keep 52 + voluntary "
                    "60-min rule; A5 rule enforced by a fee).", widths=(5.4, 3.4, 7.6), fs=7.5)
    return T


def appendix_tables(N, root):
    A = {}
    R = pd.read_csv(root / "data/derived/rates_designday.csv")
    rows = [["Slot start", "Pooled", "Design day", "Slot start", "Pooled", "Design day"]]
    for i in range(24):
        j = i + 24
        rows.append([f"{i // 2:02d}:{30 * (i % 2):02d}", f"{R.rate_pooled[i]:.3f}", f"{R.rate_designday[i]:.3f}",
                     f"{j // 2:02d}:{30 * (j % 2):02d}", f"{R.rate_pooled[j]:.3f}", f"{R.rate_designday[j]:.3f}"])
    A["A1"] = dict(rows=rows, cap="Table A1. NHPP arrival rates (cars per half hour) for pooled weekdays and the Tue-Wed design "
                   "day (multiply by m for growth). Source: data/derived/rates_designday.csv.", widths=(2.2, 2.2, 2.4, 2.2, 2.2, 2.4), fs=7)
    rows = [["Experiment", "Replications", "Streams", "Result file"],
            ["Validation (6 stay models)", "60 per model", "[r,1], [r,2], r = 1-60", "results/phase1r/validation_v2*.csv"],
            ["Decision at m = 1.3 (rule)", "60-200 adaptive", "[r,1], [r,2]", "results/phase1r/r6_decision*.csv"],
            ["Sizing grid (2 arrival patterns x 11 m, c 34-66)", "60-200 adaptive", "[r,1], [r,2]", "results/phase3/p3_grid_*.csv"],
            ["Policies P1-P3", "60-200 adaptive", "[r,1], [r,2], [r,3]", "results/phase3/p3_policy_*.csv"],
            ["Peak spreading; growth shape; outages; reneging", "60", "[r,1], [r,2] (+ failure stream)", "results/phase3/p3_*_summary.csv"],
            ["Input bootstrap", "50 inputs x 20", "bootstrap seed + [r,1], [r,2]", "results/phase3/p3_boot_*.csv"],
            ["Output analysis (paired, feasibility)", "200 (+1,400 stage 2)", "[r,1], [r,2], [r,3]", "results/phase5/p5_*.csv"],
            ["Decision-analysis cells", "200 per cell", "[r,1], [r,2], [r,3]", "results/phase6/p6_cells*.csv"],
            ["FlexSim own streams (B4, FS_CMP)", "30 per cell", "FlexSim streams 2r-1, 2r", "results/flexsim/flexsim_vs_engine_own_streams.csv, flexsim_key_cells_comparison.csv"]]
    A["A2"] = dict(rows=rows, cap="Table A2. Replications, random-number streams and result files of each experiment (Python "
                   "engine: numpy default_rng([r, s]); every script is seeded).", widths=(5.0, 2.8, 3.8, 4.8), fs=7)
    VA = N["VA"]
    rows = [["Stay model", "Mean occupancy diff [CI]", "Daily peak diff [CI]", "K-S p (daily peak)", "Profile RMSE", "Overall"]]
    for s in ["band_long", "band_long_opt", "band", "jointGMM", "AB", "mixA_lnB"]:
        d = VA[VA.service == s]
        mo = d[d.metric == "mean_occ"].iloc[0]
        pk = d[d.metric == "peak_occ"].iloc[0]
        ks = d[d.test == "KS 2-sample (primary)"].iloc[0]
        rm = d[d.test == "profile"].iloc[0]
        ov = d[d.test == "OVERALL"].iloc[0]
        rows.append([s, f"{mo['diff']:+.2f} [{mo.lo:.2f}, {mo.hi:.2f}]", f"{pk['diff']:+.2f} [{pk.lo:.2f}, {pk.hi:.2f}]", f"{ks.p:.3f}",
                     f"{rm.stat:.2f}", "PASS" if bool(ov.ok) else "FAIL"])
    A["A3"] = dict(rows=rows, cap="Table A3. Validation of the candidate stay models at current demand (model - data, 95% Welch "
                   "intervals; pass = every interval contains 0 and K-S p > 0.05). Source: results/phase1r/validation_v2.csv.",
                   widths=(2.8, 3.4, 3.4, 2.2, 2.0, 1.6), fs=7)
    IJ, AH = N["IJ"]["INPUTS"], N["AH"]
    crit = IJ["ahp_criteria"]
    lab = {"cost": "total annualised cost"}  # : capital + maintenance/fees + waiting + moving + administration
    rows = [["Criterion"] + [lab.get(c, c) for c in crit] + ["Weight"]]
    for i, c in enumerate(crit):
        rows.append([lab.get(c, c)] + [f"{x:.3g}" for x in IJ["ahp_matrix"][i]] + [f"{AH['weights_gm'][c]:.3f}"])
    rows.append(["Option scores", "", "", "", "", "Total"])
    for o, sc in AH["scores"].items():
        rows.append([o] + [f"{sc[c]:.3f}" for c in crit] + [f"{AH['total'][o]:.3f}"])
    A["A4"] = dict(rows=rows, cap=f"Table A4. AHP pairwise comparison matrix (Saaty scale) with weights (geometric mean; the "
                   f"eigenvector gives the same order), consistency ratio CR = {AH['CR']:.3f}, and option scores (0-1, higher is "
                   "better). The total-annualised-cost criterion is the expected annual cost including capital, maintenance and fees, waiting "
                   "and moving time and administration, so waiting time also enters the service criterion. Source: "
                   "results/phase6/p6_ahp.json.", widths=(3.0, 2.2, 2.2, 2.6, 2.4, 2.6), fs=7)
    PAY = N["PAY"]
    rows = [["Option", "Capital", "Maintenance + network", "Waiting time", "Moving cars", "Administration", "Total"]]
    for r in PAY[np.isclose(PAY.m, 1.3)].itertuples():
        rows.append([r.option] + [f"{x / 1000:,.2f}" for x in (r.capital, r.om, r.delay, r.move, r.admin, r.total)])
    A["A5"] = dict(rows=rows, cap="Table A5. Cost components at m = 1.3 (USD thousand per year). Source: results/phase6/p6_payoff.csv.",
                   widths=(1.6, 2.2, 3.0, 2.2, 2.2, 2.4, 2.0), fs=7)
    return A


# ------------------------------------------------------------------------------------------------ build
class Ctx:
    def __init__(self, w, N, C, T, FIGS, root):
        self.w, self.N, self.C, self.T, self.FIGS, self.root = w, N, C, T, FIGS, root
        self.words = 0
        self.order_fig, self.order_tab = [], []

    def p(self, text):
        t = self.C.sub(text)
        self.words += len(t.replace("**", "").split())
        self.w.para(t, align=3)

    def h(self, text, level=1):
        self.w.heading(text, level)

    def bullets(self, items):
        its = [self.C.sub(x) for x in items]
        self.words += sum(len(x.split()) for x in its)
        self.w.bullets(its)

    def fig(self, num, width=16.5):
        r = self.FIGS[self.FIGS.number == num].iloc[0]
        n = self.w.figure(self.root / "paper_full/figures" / f"{r.stem}.png", width, self.C.sub(r.caption), label="Fig.")
        assert n == num, (n, num)
        self.order_fig.append(num)

    def tab(self, key):
        t = self.T[key]
        rows = [[self.C.sub(str(c)) for c in row] for row in t["rows"]]
        n = self.w.table(rows, caption=self.C.sub(t["cap"]), font_size=t["fs"], col_widths_cm=t["widths"], label="Table")
        assert f"t{n}" == key, (n, key)
        if len(rows) <= 13:  # keep short tables on one page
            tb = self.w.doc.Tables(self.w.doc.Tables.Count)
            tb.Range.ParagraphFormat.KeepWithNext = True
            tb.Rows(tb.Rows.Count).Range.ParagraphFormat.KeepWithNext = False
        self.order_tab.append(key)

    def atab(self, t):
        self.w.para(self.C.sub(t["cap"]), style="caption", align=0, keep_next=True, space_after=2)
        self.w.table([[str(c) for c in row] for row in t["rows"]], caption=None, font_size=t["fs"], col_widths_cm=t["widths"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    root = Path(ap.parse_args().project).resolve()
    P = root / "paper_full"
    # Word saves inside the OneDrive folder go through the cloud path and lock the local files, so the documents are
    # built in a local temporary folder and copied into paper_full/ at the end.
    BUILD = Path(tempfile.gettempdir()) / "d9_manuscript_build"
    BUILD.mkdir(exist_ok=True)
    N = load_numbers(root)
    REF = pd.read_csv(P / "references_verified.csv")
    assert REF.verified.all(), "unverified reference"
    LM = pd.read_csv(P / "LITERATURE_MATRIX.csv")
    yes = lambda col: LM[col].astype(str).str.startswith("yes")  # noqa: E731  (same coding as scripts/literature_matrix.py)
    sizing = LM.theme.isin(["DES", "Queueing", "Simulation (workplace)"])
    real = LM.data.str.contains("Real|real|ACN|transactions|trial|trajector|survey|travel data", regex=True)
    N["GAP"] = dict(n=len(LM), sizing=int(sizing.sum()), sizing_real=int((sizing & real).sum()), vv=int(yes("vv_reported").sum()),
                    idle=int(yes("idle_overstay").sum()),
                    idle_size=int((yes("idle_overstay") & LM.decision_variable.str.contains("chargers|capacity", case=False)).sum()),
                    ymin=int(LM.year.min()), ymax=int(LM.year.max()))
    FIGS = pd.read_csv(P / "figures/FIGSET.csv")
    AU = json.loads((root / "report/authors.json").read_text(encoding="utf-8"))
    C = Cite(REF)
    abstract = full_paper_text.abstract(N)
    n_abs = len(abstract.replace("**", "").split())
    assert n_abs <= 300, n_abs
    T = tables(N, LM, C)
    A = appendix_tables(N, root)
    for h in HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    w = WordDoc(font="Times New Roman", size=12)
    try:
        w.para("Highlights", bold=True, size=14)
        w.bullets(HIGHLIGHTS)
        w.save(BUILD / "highlights.docx")
    finally:
        w.close()

    w = WordDoc(font="Times New Roman", size=11, margins_cm=(2.5, 2.5, 2.5, 2.5), heading_font="Times New Roman",
                space_after=6, line_rule=1)
    ctx = Ctx(w, N, C, T, FIGS, root)
    try:
        w.para(full_paper_text.TITLE, align=1, size=16, bold=True, space_after=10)
        names = [s["name"] for s in AU["students"]] + [AU["supervisor"]["paper_name"]]
        w.para(", ".join(f"{n} (a)" for n in names), align=1, size=12)
        w.para(f"(a) {AU['affiliation']}", align=1, size=10, space_after=2)
        w.para(f"Corresponding author: {AU['corresponding_author']} ([university e-mail to be added])", align=1, size=10,
               space_after=12)
        w.heading("Abstract", 1)
        for part in abstract.split("\n"):
            w.para(C.sub(part), align=3)
        w.para("**Keywords:** discrete-event simulation; electric-vehicle charging; workplace charging; capacity planning; "
               "non-homogeneous Poisson process; idle time; verification and validation; decision analysis", align=0)
        full_paper_text.body(ctx)
        main_words = ctx.words
        w.heading("CRediT authorship contribution statement (draft; to be confirmed by the authors)", 2)
        w.para(" ".join(f"**{s['name']}:** {s['credit']}." for s in AU["students"]) + f" **{AU['supervisor']['paper_name']}:** "
               f"{AU['supervisor']['credit']}.", align=3)
        for head, txt in full_paper_text.back_matter(N):
            w.heading(head, 2)
            w.para(C.sub(txt), align=3)
        w.page_break()
        full_paper_text.appendix(ctx, A, root)
        w.heading("References", 1)
        unused = [k for k in REF.key if k not in C.used]
        refs = [apa_override(k, REF.set_index("key").loc[k, "apa"]) for k in C.used]
        for s_ in sorted(refs, key=apa_sort_key):
            w.para(s_, size=10, align=0, space_after=3)
        w.footer_page_numbers()
        # page PNGs are rendered from the PDF by scripts/render_pages.py (Word's page-EMF export proved fragile)
        pages, _ = w.save(BUILD / "manuscript_full.docx", BUILD / "manuscript_full.pdf", None)
        total_words = w.doc.ComputeStatistics(0)
    finally:
        w.close()
    from check_placeholders import check_docx  #  A3: stop the build on any unresolved template placeholder
    check_docx(BUILD / "manuscript_full.docx")
    locked = []
    for fn in ("highlights.docx", "manuscript_full.docx", "manuscript_full.pdf"):  # local build -> paper_full/
        try:
            shutil.copyfile(BUILD / fn, P / fn)
        except PermissionError:
            locked.append(fn)
    if locked:
        print(f"WARNING: {locked} open in Word, not replaced; the new build is in {BUILD}. Close the file and rerun.")
    stats = dict(abstract_words=n_abs, main_text_words=main_words, total_words_word_count=total_words, pages=pages,
                 figures=len(ctx.order_fig), tables_main=len(ctx.order_tab), references_cited=len(C.used),
                 references_verified_not_cited=unused, figure_order=ctx.order_fig, table_order=ctx.order_tab, build_dir=str(BUILD), not_copied=locked)
    (P / "d9_ms_stats.json").write_text(json.dumps(stats, indent=1))
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
