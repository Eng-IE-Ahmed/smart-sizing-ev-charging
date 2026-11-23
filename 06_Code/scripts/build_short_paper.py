""" journal-neutral research manuscript (IMRaD), built with Microsoft Word (COM, scripts/word_builder.py).
Outputs: paper/manuscript.docx + .pdf (+ paper/pages/*.png for the visual check), paper/highlights.docx,
paper/figures/ (PNG 300 dpi, TIFF, and vector PDF where the figure was drawn by report_figures.py), paper/paper_numbers.json
(numbers computed here: maximum observed occupancy, idle shares). paper/README.md is written separately.
References: APA 7 strings from paper/references_verified.csv (scripts/d7_refs.py, all verified by DOI/ISBN/URL).
Authors: report/authors.json. Usage: python scripts/build_short_paper.py --project .
"""
import argparse
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from word_builder import WordDoc  # noqa: E402

FIGS = [  # (paper file stem, source in figures/report)
    ("Fig1_process_flow", "Fig02_process_flow"),
    ("Fig2_nhpp_rates", "Fig05_nhpp_rates"),
    ("Fig3_stay_ecdf", "Fig07_stay_ecdf"),
    ("Fig4_flexsim_model", "Fig03c_flexsim_clear"),
    ("Fig5_validation_profile", "Fig09_validation_profile"),
    ("Fig6_frontier", "Fig12_frontier"),
    ("Fig7_policy_savings", "Fig13_policy_savings"),
    ("Fig8_analytic_vs_des", "FigS4_mol_vs_des"),
    ("Fig9_prob_sensitivity", "FigS5_prob_sens"),
]
HIGHLIGHTS = [
    "Validated DES of 2,953 workplace EV charging sessions; three tools agree exactly",
    "45 chargers meet a 1% wait-risk target at +30% demand; 52 hold to +56%",
    "Over half of plug-in time is idle; a 60-min move rule saves 7-11 chargers",
    "An Erlang-C rule matches the simulated charger frontier at 10 of 11 levels",
    "Decision lenses agree on no purchase now but split under high demand growth",
]


def extra_numbers(root):
    spec = importlib.util.spec_from_file_location("p3", root / "scripts" / "experiments.py")
    p3 = importlib.util.module_from_spec(spec)
    sys.modules["p3"] = p3
    spec.loader.exec_module(p3)
    p3.setup(str(root))
    df = p3.G["df"]
    t = np.concatenate([df.conn.values.astype("datetime64[s]").astype(float), df.disc.values.astype("datetime64[s]").astype(float)])
    e = np.concatenate([np.ones(len(df)), -np.ones(len(df))])
    o = np.lexsort((e, t))
    W = df[df.weekday]
    ok = W.done.notna() & (W.charge_h > 0) & (W.done <= W.disc)
    Wp = W[ok]
    idle = 1 - Wp.charge_h / Wp.dur
    return dict(max_occupancy_all_sessions=int(np.cumsum(e[o]).max()), valid_weekday_sessions=int(len(Wp)),
                median_session_idle_share=float(idle.median()), aggregate_idle_share=float(1 - Wp.charge_h.sum() / Wp.dur.sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    R, FR, P = root / "results", root / "figures" / "report", root / "paper"
    (P / "figures").mkdir(parents=True, exist_ok=True)
    AU = json.loads((root / "report" / "authors.json").read_text(encoding="utf-8"))
    REF = pd.read_csv(P / "references_verified.csv")
    assert REF.verified.all(), "unverified reference"
    S5 = pd.read_csv(R / "phase5" / "p5_summary.csv")
    PS = pd.read_csv(R / "phase3" / "p3_policy_savings.csv")
    MOL = pd.read_csv(R / "phase4" / "p4_mol_vs_des.csv")
    LJ = json.loads((R / "phase6" / "p6_lenses.json").read_text())
    AH = json.loads((R / "phase6" / "p6_ahp.json").read_text())
    PAY = pd.read_csv(R / "phase6" / "p6_payoff.csv")
    Mp = PAY.pivot(index="option", columns="m", values="total")
    X = extra_numbers(root)
    (P / "paper_numbers.json").write_text(json.dumps(X, indent=1))

    for stem, src in FIGS:
        shutil.copy2(FR / f"{src}.png", P / "figures" / f"{stem}.png")
        Image.open(FR / f"{src}.png").convert("RGB").save(P / "figures" / f"{stem}.tif", compression="tiff_lzw", dpi=(300, 300))
        if (FR / f"{src}.pdf").exists():
            shutil.copy2(FR / f"{src}.pdf", P / "figures" / f"{stem}.pdf")

    for h in HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    w = WordDoc(font="Times New Roman", size=12)
    try:
        w.para("Highlights", bold=True, size=14)
        w.bullets(HIGHLIGHTS)
        w.save(P / "highlights.docx")
    finally:
        w.close()

    abstract = (
        "**Purpose:** Workplaces must decide how many Level-2 chargers to add as electric-vehicle demand grows, and whether "
        "managing the idle time of plugged-in cars can replace hardware. **Methods:** We built a "
        "discrete-event simulation of the Caltech garage (52 chargers with sessions) from 2,953 ACN-Data sessions (March-May 2019). Arrivals "
        "follow a non-homogeneous Poisson process with 48 half-hour rates, accepted by a time-rescaling test; stays are sampled "
        "from the data by arrival band because every parametric family was rejected. The model was implemented in Python, "
        "Excel and FlexSim with car-by-car agreement and validated against observed occupancy. Charger counts were chosen by "
        "a pre-specified rule: the smallest count whose upper 95% bound of the probability of waiting more than 15 min is at "
        "most 1%. **Results:** At +30% demand 45 chargers meet the rule with at least 95% joint confidence (44 fail on 1,400 "
        "fresh replications); a Tuesday-Wednesday design day needs 47, and the existing 52 suffice to +56% growth. Idle "
        "time is 56.7% of plug-in hours; if drivers complied, a 60-min move rule would save 11 chargers (7 at half "
        "compliance), an assumed effect. An arrival-weighted Erlang-C approximation reproduces the simulated frontier at 10 of 11 "
        "growth levels, whereas the modified-offered-load rule over-sizes by 5-8 chargers. Decision lenses "
        "agree that no purchase is needed now but disagree under high growth (buy 6 or 13, or the rule); staging follows "
        "the lowest expected cost. "
        "**Conclusions:** Staged expansion is the robust choice; an idle-time rule should be piloted and measured "
        "before decisions rest on it.")
    nwords = len(abstract.replace("**", "").split())
    assert nwords <= 250, nwords

    w = WordDoc(font="Times New Roman", size=11, margins_cm=(2.5, 2.5, 2.5, 2.5), heading_font="Times New Roman",
                space_after=6, line_rule=1)
    nfig = {}

    def fig(stem, width, cap):
        nfig[stem] = w.figure(P / "figures" / f"{stem}.png", width, cap, label="Fig.")
    try:
        w.para("Sizing workplace electric-vehicle charging under demand growth: a validated discrete-event simulation of "
               "charger counts, idle-time policies and decision lenses", align=1, size=16, bold=True, space_after=10)
        names = [s["name"] for s in AU["students"]] + [AU["supervisor"]["paper_name"]]
        w.para(", ".join(f"{n} (a)" for n in names), align=1, size=12)
        w.para(f"(a) {AU['affiliation']}", align=1, size=10, space_after=2)
        w.para(f"Corresponding author: {AU['corresponding_author']}", align=1, size=10, space_after=12)
        w.heading("Abstract", 1)
        w.para(abstract, align=3)
        w.para("**Keywords:** discrete-event simulation; electric-vehicle charging; workplace charging; capacity planning; "
               "idle time; decision analysis", align=0)

        w.heading("1. Introduction", 1)
        w.para("Employers, universities and garage operators that installed Level-2 chargers early now face a planning question "
               "that is simple to state and hard to answer: how many chargers are needed when demand grows, and how much of the "
               "need can be met by changing how the existing chargers are used? Two features of workplace charging make the "
               "question harder than a textbook multi-server queue. First, arrivals depend strongly on the time of day, with a "
               "sharp morning peak. Second, the time a car occupies a charger is not the charging time but the whole stay: many "
               "cars remain plugged in long after their battery is full, so a large share of charger time is idle. Capacity "
               "therefore depends on the joint distribution of arrival time and stay, and on behaviour that policies can "
               "change.", align=3)
        w.para("Open session data make this question answerable with evidence. The Adaptive Charging Network dataset "
               "(ACN-Data) records plug-in, charge-completion and unplug times for every session at Caltech and other sites "
               "(Lee et al., 2019). Király et al. (2026) used ACN-Data to plan charging infrastructure with a hierarchical "
               "Bayesian demand model, an agent-based simulation in 5-min steps with a fixed fleet of 500 vehicles, nine slot "
               "configurations and TOPSIS. They reported that their log-normal dwell model was rejected by a Kolmogorov-Smirnov "
               "test, that dwell times were drawn from marginal distributions independent of arrival time, that the arrival "
               "peak was at 14:00, and that full service was not reached within the range studied; they named empirical "
               "resampling of dwell times as future work. Lahariya et al. (2020) modelled the connection time conditional on the "
               "arrival time; Hüttel et al. (2023) showed that charging records can be censored when all chargers are busy. "
               "Discrete-event simulation (DES) has been used to size related systems, for example battery-swapping stations "
               "(Uribe et al., 2023), and analytic designs exist for commercial premises (Bayram et al., 2022). Time-varying "
               "infinite-server theory gives the offered load m(t) and the modified-offered-load staffing rule (Eick et al., "
               "1993; Jennings et al., 1996).", align=3)
        w.para("This paper closes four gaps. (i) Input modelling: we test the arrival process formally and sample stays "
               "conditionally on the arrival band, including stays over 24 h, after every parametric family is rejected. "
               "(ii) A decision rule with a guarantee: charger counts are chosen by a pre-specified risk rule with replication "
               "control, common random numbers and a feasibility check at a stated joint confidence. (iii) Idle-time policies: "
               "we quantify the chargers saved by move-after-charging rules and a stay cap, with compliance sensitivity. "
               "(iv) Decision analysis: we cost the options under growth uncertainty, compare decision lenses, and benchmark "
               "the DES against analytic sizing rules. The model is implemented in three environments (Python, Microsoft Excel "
               "and FlexSim) that agree car by car; because all three were written from one specification with the same AI "
               "assistant, they are not independent in the sense of Sargent (2013), and the independent checks are the "
               "closed-form queueing benchmarks and the validation against observed occupancy.", align=3)

        w.heading("2. Data", 1)
        w.para("We downloaded all 2,953 sessions of the Caltech site from 1 March to 31 May 2019 through the ACN-Data API; "
               "the raw file is kept unchanged with its SHA-256 hash. The ACN-Data documentation lists 54 Level-2 EVSEs at the "
               "Caltech garage (https://ev.caltech.edu/dataset, accessed 19 November 2026); 52 distinct stations recorded at "
               "least one session in this window, the model is sized against these 52, and the difference is attributed to "
               "EVSEs without sessions, not to data loss (Király et al., 2026, report the same 52 stations). Times, which the release gives in UTC, were "
               "converted to Pacific local time. Weekends and Memorial Day were removed, leaving 65 weekdays with 2,577 sessions "
               f"(39.6 arrivals per weekday). The highest number of cars plugged in at the same time was "
               f"{X['max_occupancy_all_sessions']} of 52, so the records are not censored by full occupancy in this period (cf. "
               "Hüttel et al., 2023). Daily counts show no trend; autocorrelations of gaps and of daily counts stay within their "
               "95% bounds and a runs test gives p = 0.94. Days of the week differ (ANOVA F = 5.72, p = 0.0006): Tuesdays and "
               "Wednesdays are busier, so results are also reported for a Tuesday-Wednesday design day. Idle time (plugged in "
               f"but not charging) is {100 * X['aggregate_idle_share']:.1f}% of plug-in hours for the "
               f"{X['valid_weekday_sessions']:,} weekday sessions with a valid charge-completion time; the median session is "
               f"idle for {100 * X['median_session_idle_share']:.1f}% of its stay.", align=3)

        w.heading("3. Model", 1)
        w.heading("3.1 Arrivals", 2)
        w.para("Arrivals form a non-homogeneous Poisson process (NHPP) with 48 half-hour rates r_k = count_k / 65, estimated "
               "nonparametrically (Leemis, 1991) and multiplied by a growth factor m (Fig. 2). Arrivals are generated by "
               "inverting the cumulative rate with unit-rate exponential steps (Arkin & Leemis, 2000). The NHPP was tested by "
               "time rescaling (Brown et al., 2002): the 2,512 rescaled gaps are consistent with Exp(1) (Kolmogorov-Smirnov "
               "p = 0.447, Anderson-Darling p = 0.311, chi-square p = 0.368, parametric bootstrap), whereas fitted gamma and "
               "Weibull models are rejected (Anderson-Darling p = 0.006). The arrival peak is at 08:00 local time.", align=3)
        fig("Fig2_nhpp_rates", 14.5, "NHPP rate profile: 48 half-hour arrival rates for pooled weekdays, the Tuesday-Wednesday design "
            "day and +30% growth.")
        w.heading("3.2 Stays", 2)
        w.para("The occupancy (service) time is the whole stay from plug-in to unplug. Stays depend on the arrival time, so "
               "the day was partitioned into six arrival bands (05-07, 08-09, 10-11, 12-15, 16-20, 21-04 h) by maximising "
               "the explained variance of log stay. In each band we fitted log-normal, gamma, Weibull, generalised gamma, "
               "Burr XII and mixtures of up to five log-normals; every single family is rejected in every band "
               "(Anderson-Darling p <= 0.004) and the mixtures pass in only two bands. Stays are therefore sampled by "
               "inverse transform from the empirical pool of the car's arrival band, including stays over 24 h (Fig. 3). A "
               "simpler two-class model (arrivals 05:00-11:59 versus other times) was rejected at validation because it "
               "under-stated the daily peak occupancy (K-S p = 0.044).", align=3)
        fig("Fig3_stay_ecdf", 13.0, "Empirical stay distribution by arrival band (log scale; weekdays, including stays over 24 h).")
        w.heading("3.3 Queue, run design and decision rule", 2)
        w.para("Cars wait in one first-in-first-out queue without balking for one of c identical chargers (Fig. 1). One "
               "replication covers the 65 weekdays back to back (1,560 h) and starts empty; a Welch plot shows that the empty "
               "start does not bias the result (dropping day 1 moves P15 from 0.452% to 0.458%), so the study is terminating "
               "(Law, 2015). Replication r uses the same random-number streams for every option (common random numbers, CRN), "
               "which reduced the variance of paired differences by a factor of 7.74. The risk measure is P15 = P(wait > 15 "
               "min) per car; the decision rule, fixed before any experiment, selects the smallest c whose upper 95% t-bound "
               "of P15 is at most 1%. Replications start at 60 and grow by 20, up to 200, while the bound is within 0.15 "
               "percentage points of 1%.", align=3)
        fig("Fig1_process_flow", 15.5, "Process flow of one car; the idle-but-plugged step is where the policies of Section 5.3 act.")
        w.para("The same model was implemented three times: a Python engine (the experiment workhorse), a Microsoft Excel "
               "workbook with formulas only, and a FlexSim 2027 model built by script (Source, Queue, 52 Processors with "
               "capacity one, Sink; chargers above c are closed; Fig. 4).", align=3)
        fig("Fig4_flexsim_model", 11.5, "FlexSim model at +30% demand with 45 open chargers: (a) 3D layout with the object types "
            "numbered; (b) dashboard panel of arrivals and departures per hour (FlexSim default calendar).")

        w.heading("4. Verification and validation", 1)
        rows = [["Test", "Result"],
                ["Hand calculation; extreme case (very few arrivals)", "match; nobody waits"],
                ["Excel = Python (replication 1, +30%, c = 42)", "3,254 cars; relative difference <= 5e-14"],
                ["FlexSim = Python, trace mode (c = 42 and 45)", "3,254 waits equal to 1.4e-14 min; Wq and P15 identical"],
                ["FlexSim own streams vs Python (22 cells x 30 replications)", "every Welch CI of the difference contains 0"],
                ["Known answer M/M/c (Erlang C), rho = 0.85 and 0.76", "Wq 69.1 +/- 5.4 vs 70.9 min; 17.1 +/- 1.3 vs 17.7 min"],
                ["Flow balance; overload (c = 12)", "imbalance 0 in 120 replications; wait doubles with run length"],
                ["Validation: cars per weekday, model - data", "-0.10 [-1.37, 1.17]"],
                ["Validation: mean occupied chargers, model - data", "+0.18 [-0.17, 0.54]"],
                ["Validation: daily peak occupancy", "+0.21 [-0.67, 1.08]; K-S p = 0.21"],
                ["Occupancy dispersion (variance/mean), model vs data", "0.99 vs 0.72 (model conservative)"]]
        w.table(rows, caption="Verification and validation (Sargent, 2013); 95% Welch intervals for model - data.", font_size=9,
                col_widths_cm=(8.0, 8.0), label="Table")
        w.para("Waiting times are not in the data, because cars that found all chargers busy are not recorded; validation "
               "therefore uses occupancy (Table 1). With current demand and 52 chargers every 95% Welch interval of model minus "
               "data contains zero, and the occupancy profile is matched within 0.50 chargers (root-mean-square over the 48 "
               "half-hours; Fig. 5). The model's day-to-day variation is larger than the data's, so its risk estimates are on "
               "the safe side.", align=3)
        fig("Fig5_validation_profile", 13.0, "Mean occupancy by time of day: data, DES and the Mt/G/inf offered load.")

        w.heading("5. Experiments and results", 1)
        w.heading("5.1 Charger count at +30% demand", 2)
        rows = [["Arrivals", "c", "Wq (min)", "P15 [95% CI]", "Rule"]]
        for g, cs in (("pooled", range(44, 49)), ("designday", range(46, 50))):
            for c in cs:
                d = S5[(S5.group == g) & (S5.scenario == "P0") & (S5.c == c)].iloc[0]
                rows.append(["weekdays" if g == "pooled" else "Tue-Wed", c, f"{d.Wq_mean:.3f}",
                             f"{100 * d.P15_mean:.3f}% [{100 * d.P15_lo:.3f}, {100 * d.P15_hi:.3f}]",
                             "met" if d.P15_hi <= 0.01 else "not met"])
        w.table(rows, caption="Options at m = 1.3 (200 CRN replications each).", font_size=9, col_widths_cm=(2.6, 1.2, 2.2, 6.0, 2.4),
                label="Table")
        w.para("With 200 CRN replications (Table 2), 45 chargers give P15 = 0.731% (95% CI [0.665%, 0.798%]) and 44 give "
               "1.039%. A one-sided Bonferroni check over nine systems (each at 99.44%) classifies 45-48 (weekdays) and 47-49 "
               "(design day) as feasible and 46 on the design day as infeasible at a joint confidence of at least 95%; 44 was "
               "undetermined and was tested alone on 1,400 fresh replications, where its lower bound is 1.026% > 1% "
               "(infeasible). This two-stage logic follows the spirit of feasibility determination (Batur & Kim, 2010) and "
               "indifference-zone selection (Kim & Nelson, 2001) without their sequential machinery. All paired differences "
               "against 45 are significant under Bonferroni (13 comparisons, each for P15 and the mean wait: 26 intervals).",
               align=3)
        w.heading("5.2 Growth frontier and robustness", 2)
        w.para("Over growth m = 1.0 to 2.0 the smallest feasible count is 36, 39, 42, 45, 48, 51, 54, 56, 59, 62 and 65 "
               "(Fig. 6); the existing 52 chargers hold to m = 1.56 (1.46 on the design day). FlexSim with its own random "
               "streams confirmed the cells at m = 1.3 and 1.6 (at 45 chargers and m = 1.3 its upper bound of P15 is 0.978%; "
               "every Welch interval against the engine contains zero). "
               "Bootstrapping the 65 days (50 inputs x 20 replications) attributes 5.8% of the per-replication variance of "
               "P15 to input uncertainty; the selected count over bootstrap inputs is 44, 45 or 46 (13, 26 and 11 inputs), so 46 "
               "is a robust choice. Growth concentrated in 07:00-10:00 raises the need to 47 at m = 1.3 and 59 at m = 1.6. "
               "Fixed outages of k chargers add k; random failures (assumed mean time between failures 720 h) need a margin of "
               "1 or 5 chargers for repair times of 24 or 72 h. With 30-min patience, 0.30% of drivers would leave at 45 "
               "chargers and m = 1.3.", align=3)
        fig("Fig6_frontier", 12.0, "Feasibility frontier c*(m) with its 95% band for pooled weekdays and the design day.")
        w.heading("5.3 Idle-time policies", 2)
        rows = [["Policy", "c* (m = 1.3)", "Saved [95% CI]", "c* (m = 1.6)", "Saved [95% CI]"]]
        lab = {"P1-30": "Move within 30 min", "P1-60": "Move within 60 min", "P1-120": "Move within 120 min",
               "P2-cap4h": "4-hour stay cap", "P3-p0.25": "60-min rule, 25% comply", "P3-p0.50": "60-min rule, 50% comply",
               "P3-p0.75": "60-min rule, 75% comply"}
        for k, txt in lab.items():
            a13 = PS[(PS.m == 1.3) & (PS.policy == k)].iloc[0]
            a16 = PS[(PS.m == 1.6) & (PS.policy == k)].iloc[0]
            rows.append([txt, int(a13.c_star), f"{int(a13.chargers_saved_vs_P0)} [{a13.saved_CI95_lo:.0f}, {a13.saved_CI95_hi:.0f}]",
                         int(a16.c_star), f"{int(a16.chargers_saved_vs_P0)} [{a16.saved_CI95_lo:.0f}, {a16.saved_CI95_hi:.0f}]"])
        w.table(rows, caption="Chargers saved by idle-time policies (paired bootstrap 95% CI; no policy: 45 and 54).", font_size=9,
                col_widths_cm=(4.6, 2.4, 2.8, 2.4, 2.8), label="Table")
        w.para("Policies sample (charge, stay) pairs of the 2,490 valid sessions. A rule that makes drivers move within 30 "
               "min after charging ends reduces the need from 45 to 32 chargers at +30% demand; within 60 min, to 34; a 4-hour "
               "cap, to 36 (Table 3, Fig. 7). If only half of the drivers follow the 60-min rule, 7 chargers are saved. These "
               "effects rest on assumed behaviour, which the data cannot show. Moving 20% of the 08:00-09:30 arrivals to "
               "09:30-11:00 saves no charger (P15 at 45 chargers 0.644% vs 0.634%), because the binding occupancy occurs at "
               "12:00-15:00, when morning cars are still plugged in.", align=3)
        fig("Fig7_policy_savings", 13.0, "Chargers saved versus no policy at m = 1.3 and 1.6 with paired-bootstrap 95% intervals.")
        w.heading("5.4 Analytic benchmark", 2)
        r13 = MOL[np.isclose(MOL.m, 1.3)].iloc[0]
        w.para("The Mt/G/inf offered load m(t), computed from the 48 rates and the band stay distributions, matches the "
               "observed occupancy (root-mean-square error 0.54) and the DES (0.11) (Eick et al., 1993). The modified-offered-"
               f"load rule (Jennings et al., 1996) with a 1% tail gives {int(r13['c_MOL_eps0.01'])} chargers at m = 1.3 and "
               "over-sizes by 5-8 chargers across m = 1.0-2.0, because it keeps the chance that all chargers are busy below the "
               "tail at every moment, so its planning value is set by the early-afternoon peak, whereas the decision rule bounds "
               "the share of all arrivals of the day that wait more than 15 min; with a 5% tail it is 1-3 chargers high. An arrival-weighted Erlang-C approximation of P15 reproduces "
               "the DES frontier at 10 of 11 growth levels (one charger low at m = 1.6, the boundary cell; Fig. 8). For a "
               "quick estimate under uniform growth the Erlang-C rule is enough; the DES remains necessary for a confidence "
               "statement, for policies that change stays, and for reneging, outages and non-uniform growth.", align=3)
        fig("Fig8_analytic_vs_des", 12.0, "Analytic sizing rules versus the DES frontier.")

        w.heading("6. Decision analysis", 1)
        w.para("Six options were costed in four growth futures (m = 1.0, 1.3, 1.6, 2.0) with the simulated waits: A0 keep 52; "
               "A1, A2, A3 buy 2, 6 or 13 chargers; A4 keep 52 with the voluntary 60-min rule at 50% compliance; A5 the rule "
               "enforced by a fee. Annual cost = new chargers x (USD 3,500 hardware + 2,500 installation) x CRF(7%, 10 years) + "
               "USD 700 per charger-year for maintenance and network fees + waiting and walking time valued at USD 38.80 per "
               "hour + policy administration. Hardware, installation and maintenance costs come from the US DOE Alternative "
               "Fuels Data Center (n.d.-a, n.d.-b), which cites Borlaug et al. (2020); the value of waiting and walking time is "
               "from USDOT (2024, Table A-2, 2023 dollars). Network fees, administration, the time to move a car and the growth "
               "probabilities (0.15/0.40/0.30/0.15) are assumptions and are varied. The California Energy Commission (2026) "
               "projects 6.8 million light-duty electric vehicles in California in 2030, which motivates the high-growth futures. "
               f"Keeping 52 chargers costs USD {Mp.loc['A0', 1.3] / 1000:,.1f}k per year at m = 1.3 but USD "
               f"{Mp.loc['A0', 2.0] / 1000:,.0f}k at m = 2.0.", align=3)
        ev = LJ["emv_values"]
        rows = [["Lens", "Choice", "Key number"],
                ["Simulation rule at m = 1.3", "A0 keep 52", "c* = 45"],
                ["Pessimistic (minimax cost)", LJ["minimax_cost"], f"worst case USD {max(Mp.loc[LJ['minimax_cost']]) / 1000:,.1f}k"],
                ["Optimistic (minimin cost)", LJ["minimin_cost"], f"USD {min(Mp.loc[LJ['minimin_cost']]) / 1000:,.1f}k"],
                ["Hurwicz", "A3 / A4 / A0", "A4 for alpha 0.431-0.900"],
                ["Minimax regret", LJ["minimax_regret"], f"USD {LJ['max_regret'][LJ['minimax_regret']] / 1000:,.1f}k"],
                ["Expected cost (EMV)", LJ["emv"], f"USD {ev[LJ['emv']] / 1000:,.1f}k (A4 {ev['A4'] / 1000:,.1f}k)"],
                ["EVPI", "-", f"USD {LJ['evpi'] / 1000:,.1f}k per year"],
                ["AHP (CR 0.017)", AH["best"], f"score {AH['total'][AH['best']]:.3f}"]]
        w.table(rows, caption="Choice under each decision lens (annual cost; A2 = buy 6, A3 = buy 13, A4 = keep 52 + rule).",
                font_size=9, col_widths_cm=(6.0, 3.6, 6.4), label="Table")
        w.para("The lenses agree that nothing is needed at +30% growth and disagree under high growth (Table 4). Once waiting is "
               "priced, the pessimist buys 13 chargers, whose cost hardly changes with growth; expected cost favours buying 6, "
               "only USD 1.1k per year ahead of the voluntary rule; and minimax regret favours the rule. The expected-cost "
               "choice switches with the probability of high growth q = P(m >= 1.6): A0 below 0.124, A1 to 0.211, A2 to 0.555, "
               "A4 to 0.783 and A3 above (Fig. 9), and between A4 and A2 at a value of time of USD 33.68 per hour. A perfect "
               "growth forecast would be worth USD 11.1k per year, which favours staged decisions. The analytic hierarchy process "
               "(Saaty, 1990), with service weighted 0.42, prefers buying 13 chargers; it moves to buying 6 only when the weight of "
               "the total annualised cost (capital, maintenance and fees, waiting and moving time, administration) reaches 0.70. "
               "Because waiting time enters both that criterion and the service criterion, the AHP counts it twice, which "
               "favours larger purchases: buying 13 is near-dominant (within 0.056 of the best score on every criterion) and "
               "stays first for any service weight from 0.10 to 0.70, but with cost scored on ownership cost only (no waiting) "
               "buying 2 leads for service weights up to 0.34, and with capital alone buying 13 is never first. The weights "
               "are the authors' judgement, not elicited from the site, so the recommendation does not rest on the AHP.",
               align=3)
        fig("Fig9_prob_sensitivity", 12.5, "Expected annual cost of each option versus the probability of high growth.")

        w.heading("7. Discussion", 1)
        w.para("The results show that, for a workplace garage, the binding resource is charger-hours during the midday "
               "plateau, not the morning arrival peak: cars that arrive at 08:00 stay about eight hours. Two consequences follow. "
               "Shifting arrivals by an hour or two does not help, whereas shortening idle stays does; and analytic rules that "
               "treat the stay as a service time work well only when the stay distribution is conditioned on the arrival time. "
               "Király et al. (2026) found large gains from spreading arrivals across the whole day in an overloaded system with "
               "a fixed fleet; our system is sized for a 1% wait risk and the shift tested is realistic, so the two findings "
               "are compatible: both identify concurrency, not daily energy, as the constraint. Their arrival peak at 14:00 "
               "differs from the 08:00 local peak in our window; we note this neutrally, since their corpus and processing "
               "differ and the release gives times in UTC. Their reported idle time (about 40% for the median session) is "
               f"lower than the {100 * X['median_session_idle_share']:.1f}% median we find for weekday sessions in spring "
               "2019.", align=3)
        w.para("**Implications for planners.** Three practical points follow. First, a site that sizes chargers on the "
               "average number of cars plugged in will under-build, while a site that sizes so that the garage is almost never "
               "full, even at its busiest moment, will over-build by several chargers; a wait-based risk target with an explicit "
               "confidence bound sits between the two and can be checked with a short simulation or, as a screen, an "
               "Erlang-C formula with arrival-conditioned stays. Second, because more than half of plug-in time is idle, the "
               "first lever to test is turnover: a voluntary move-after-charging rule costs little to pilot, its savings are a "
               "what-if until compliance is measured (it matches a six-charger purchase only above about 42% compliance), and "
               "its effect can be measured directly from the charge-completion and unplug times that networked chargers already record. Third, "
               "the value of better growth information is large relative to the annual cost differences between options, "
               "so planners should prefer staged purchases triggered by observed growth over one large purchase now. The lenses "
               "that buy 13 now (pessimistic, low-optimism Hurwicz, AHP) commit under an unknown growth path; the purchase is "
               "deferrable, and the staged path follows buy 6, the option with the lowest expected cost (USD 54.7k a year, "
               "USD 3.2k below buying 13). It gives up protection only if growth outruns the purchase lead time: with a +40% "
               "trigger and the rule met to +46% on busy days, chargers must be in service within about 5 months at an "
               "illustrative 10% annual growth, so a slower procurement needs an earlier trigger.", align=3)
        w.para("**Future work.** A pilot of the 60-min rule at the site would replace the assumed compliance by a measured one. "
               "The model can be extended with balking for drivers who see a full garage, with a power limit per circuit, and "
               "with a staged-investment (real-options) formulation in which purchases are decided year by year as growth is "
               "observed. Applying the same pipeline to the other ACN sites and to later years would test how general the "
               "frontier and the policy savings are.", align=3)
        w.para("**Limitations.** The study covers one site and one spring (2019), before the pandemic changed commuting. Cars "
               "that found all chargers busy are not recorded; no censoring was found in this period, but future demand may "
               "include drivers who give up. The policy savings rest on behavioural assumptions (that drivers move within g "
               "minutes, and independent compliance with probability p), which should be measured in a pilot. The three "
               "implementations share one specification and one AI assistant, so their agreement does not rule out a shared "
               "misreading; the AHP weights are the authors' judgement. The cost model "
               "uses published averages for hardware, installation and maintenance (not converted between dollar years), an "
               "assumed network fee and administration cost, and a value of time that, together with the time needed to move a "
               "car, decides between the rule and buying six chargers. The growth probabilities are a judgement. The model "
               "excludes weekends and does not treat energy or power limits.", align=3)

        w.heading("8. Conclusion", 1)
        w.para("A validated discrete-event simulation, built from open session data and implemented in three environments, "
               "shows that the Caltech garage needs 45 chargers for 30% more demand (47 on the busiest days), "
               "that its 52 chargers last until about +56% growth, and that rules shortening idle stays could replace 7 to 13 "
               "chargers if drivers comply as assumed - a what-if until compliance is measured. Analytic Erlang-C sizing is a good screen when stays are conditioned on "
               "arrival time; the simulation adds the statistical guarantee, the policy effects and the risk of high growth. "
               "Planners should defer purchases, pilot an idle-time rule while measuring compliance, and expand in stages "
               "as growth is observed; staging follows the lowest expected cost, whereas the lenses that buy 13 now pay for "
               "protection against high growth.", align=3)

        w.heading("CRediT authorship contribution statement (draft; to be confirmed by the team)", 2)
        w.para(" ".join(f"**{s['name']}:** {s['credit']}." for s in AU["students"])
               + f" **{AU['supervisor']['paper_name']}:** {AU['supervisor']['credit']}.", align=3)
        w.heading("Data availability", 2)
        w.para("The session data are public (ACN-Data, https://ev.caltech.edu/dataset; Lee et al., 2019). The simulation code, "
               "the input-analysis scripts, the Excel workbook and the FlexSim model are held in a private repository and are "
               "available from the corresponding author on reasonable request; a reviewer-access link will be supplied to the "
               "editor on submission. Derived session-level data are not redistributed beyond that access.", align=3)
        w.heading("Declaration of generative AI and AI-assisted technologies", 2)
        w.para("During the preparation of this work the authors used Claude (Anthropic) through Claude Code to write and run "
               "analysis scripts, build spreadsheet formulas and the script that builds the FlexSim model, and draft text. No "
               "data were generated or altered by the tool; every number comes from the public data, seeded scripts, spreadsheet "
               "formulas or saved simulation outputs. Evidence per class of number: text numbers by automated consistency checks "
               "against the result files; the workbook by an Excel recalculation with 0 formula errors; the simulation logic by "
               "the car-by-car trace comparison and closed-form benchmarks. The authors reviewed and edited the content and "
               "take full responsibility for the publication.", align=3)
        w.heading("Funding", 2)
        w.para("This research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit "
               "sectors.")
        w.heading("Declaration of competing interest", 2)
        w.para("The authors declare that they have no known competing financial interests or personal relationships that could "
               "have appeared to influence the work reported in this paper.")
        w.heading("References", 1)
        override = {
            "law2015": "Law, A. M. (2015). *Simulation modeling and analysis* (5th ed.). McGraw-Hill Education. ISBN 9780073401324.",
            "banks2010": "Banks, J., Carson, J. S., Nelson, B. L., & Nicol, D. M. (2010). *Discrete-event system simulation* (5th ed.). "
                         "Prentice Hall. ISBN 9780136062127.",
            "lee2019": "Lee, Z. J., Li, T., & Low, S. H. (2019). ACN-Data: Analysis and applications of an open EV charging dataset. In "
                       "*Proceedings of the Tenth ACM International Conference on Future Energy Systems (e-Energy '19)* (pp. 139-149). "
                       "https://doi.org/10.1145/3307772.3328313",
            "bayram2022": "Bayram, I. S., Devetsikiotis, M., & Jovanovic, R. (2022). Optimal design of electric vehicle charging stations "
                          "for commercial premises. *International Journal of Energy Research*, *46*(8), 10040-10051. "
                          "https://doi.org/10.1002/er.6523",
            "afdc_proc": "U.S. Department of Energy, Alternative Fuels Data Center. (n.d.-a). *Procurement and installation for electric "
                         "vehicle charging infrastructure*. Retrieved November 19, 2026, from "
                         "https://afdc.energy.gov/fuels/electricity_infrastructure_development.html (archived at "
                         "https://web.archive.org/web/20261119142457/https://afdc.energy.gov/fuels/electricity-infrastructure-development)",
            "afdc_om": "U.S. Department of Energy, Alternative Fuels Data Center. (n.d.-b). *Operation and maintenance for electric vehicle "
                       "charging infrastructure*. Retrieved November 19, 2026, from "
                       "https://afdc.energy.gov/fuels/electricity_infrastructure_maintenance_and_operation.html (archived at "
                       "https://web.archive.org/web/20261119142522/https://afdc.energy.gov/fuels/electricity-infrastructure-maintenance-and-operation)",
            "usdot2024": "U.S. Department of Transportation. (2024). *Benefit-cost analysis guidance for discretionary grant programs: "
                         "2025 update*. https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance"
                         "%202025%20Update%20%28Final%29.pdf",
            "cec2026": "California Energy Commission. (2026). *Assembly Bill 2127 third electric vehicle charging infrastructure "
                       "assessment* (CEC-600-2026-032). https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-"
                       "vehicle-charging-infrastructure-assessment (archived at https://web.archive.org/web/20261119142634/"
                       "https://www.energy.ca.gov/publications/2026/assembly-bill-2127-third-electric-vehicle-charging-"
                       "infrastructure-assessment)"}
        used = ["arkin2000", "banks2010", "batur2010", "bayram2022", "borlaug2020", "brown2002", "cec2026", "eick1993", "huttel2023",
                "jennings1996", "kim2001", "kiraly2026", "lahariya2020", "law2015", "lee2019", "leemis1991", "saaty1990",
                "sargent2013", "uribe2023", "usdot2024", "afdc_proc", "afdc_om"]
        refs = [override.get(k) or REF[REF.key == k].iloc[0].apa for k in used]
        for s_ in sorted(refs, key=lambda x: re.sub(r"[^A-Za-z]", "", x).lower()):
            w.para(s_, size=10, align=0, space_after=3)
        w.footer_page_numbers()
        pages, _ = w.save(P / "manuscript.docx", P / "manuscript.pdf", P / "pages")
        wc = w.doc.ComputeStatistics(0)
    finally:
        w.close()
    from check_placeholders import check_docx  #  A3: stop on any unresolved template placeholder
    check_docx(P / "manuscript.docx")
    (P / "references_used.txt").write_text("\n".join(sorted(used)), encoding="utf-8")
    print("abstract words:", nwords, "| pages:", pages, "| words:", wc, "| figures:", len(nfig))


if __name__ == "__main__":
    main()
