""" figure set for the full-length article: 16 figures + graphical abstract, one publication style.

Style: DejaVu Sans 8.5 pt, no titles inside figures (captions carry the message), panel letters (a), (b), project palette,
double-column width 17.4 cm. Every figure is drawn from result files (no hand editing); Fig. 7 is a composite of two
FlexSim window captures (raster by nature). Each figure is saved as PNG (400 dpi), TIFF (400 dpi, LZW) and vector PDF
(except the screenshot composite). Captions live here (single source) and are written to paper_full/figures/FIGSET.csv,
which the manuscript builder reads.
Usage: python scripts/full_paper_figures.py --project .     (no randomness)
"""
import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch  # noqa: E402

BLUE, ORANGE, GREEN, PURPLE, GREY, LBLUE = "#1F4E78", "#C55A11", "#548235", "#7030A0", "#7F7F7F", "#5B9BD5"
BANDC = ["#1F4E78", "#5B9BD5", "#548235", "#C55A11", "#7030A0", "#7F7F7F"]
OPTC = {"A0": "#7F7F7F", "A1": "#5B9BD5", "A2": "#1F4E78", "A3": "#C55A11", "A4": "#548235", "A5": "#7030A0"}
W2 = 17.4 / 2.54          # double-column width, inches
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 8.5, "axes.labelsize": 8.5,
                     "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "axes.linewidth": 0.7,
                     "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.4, "pdf.fonttype": 42})
FIG = []                   # (number, stem, sources, caption)


def save(f, out, stem):
    f.savefig(out / f"{stem}.png", dpi=400, bbox_inches="tight")
    f.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    Image.open(out / f"{stem}.png").convert("RGB").save(out / f"{stem}.tif", compression="tiff_lzw", dpi=(400, 400))
    plt.close(f)


def panel(ax, s):
    ax.text(-0.11, 1.04, s, transform=ax.transAxes, fontsize=9.5, fontweight="bold", va="bottom")


def box(ax, xy, w, h, text, fc, ec=BLUE, fs=7.5):
    ax.add_patch(FancyBboxPatch((xy[0] - w / 2, xy[1] - h / 2), w, h, boxstyle="square,pad=0.0", fc=fc, ec=ec, lw=1.1))
    ax.text(xy[0], xy[1], text, ha="center", va="center", fontsize=fs)


def arrow(ax, a, b, color="k", rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, color=color, lw=1.1, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))


def load_ev(root):
    spec = importlib.util.spec_from_file_location("ev", root / "engine" / "ev_des_engine.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    ev.DATA = str(root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json")
    return ev


# ----------------------------------------------------------------------------------------------------- figures
def f01(root, out):
    f, ax = plt.subplots(figsize=(W2, 3.6))
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0.3, 5.3)
    ax.set_aspect("equal")
    ax.axis("off")
    for xy, t in [((1.0, 3.4), "Outside\n(off site)"), ((4.0, 3.4), "Queue\n(waiting car)"), ((8.7, 3.4), "Left\nsite")]:
        ax.add_patch(Circle(xy, 0.62, fc="#EEF3F8", ec=BLUE, lw=1.1))
        ax.text(*xy, t, ha="center", va="center", fontsize=6.3)
    box(ax, (2.5, 3.4), 1.1, 0.65, "Arrive\n(NHPP)", "#FFF2CC", fs=6.5)
    box(ax, (6.35, 3.4), 2.3, 1.0, "Plugged in =\ncharging + idle\n(stay drawn from\nthe arrival band)", "#E2EFDA", fs=6.3)
    arrow(ax, (1.62, 3.4), (1.95, 3.4))
    arrow(ax, (3.05, 3.4), (3.38, 3.4))
    arrow(ax, (4.62, 3.4), (5.2, 3.4))
    arrow(ax, (7.5, 3.4), (8.08, 3.4))
    arrow(ax, (8.7, 4.0), (1.0, 4.0), rad=0.2, ls="--", color=GREY)
    ax.text(4.85, 5.0, "car cycle (next visit)", fontsize=6.3, color=GREY, ha="center")
    ax.add_patch(Circle((6.35, 1.2), 0.62, fc="#EEF3F8", ec=ORANGE, lw=1.1))
    ax.text(6.35, 1.2, "Free\ncharger", ha="center", va="center", fontsize=6.3)
    arrow(ax, (5.82, 1.58), (5.6, 2.9), color=ORANGE, rad=-0.3)
    arrow(ax, (7.0, 2.9), (6.78, 1.58), color=ORANGE, rad=-0.3)
    ax.text(7.2, 1.2, "charger cycle: c identical\nLevel-2 chargers, capacity 1", fontsize=6.3, color=ORANGE, va="center")
    ax.text(4.0, 2.4, "wait W = plug-in - arrival\nrisk: P(W > 15 min)", fontsize=6.3, ha="center", color=BLUE)
    ax.text(1.4, 1.2, "circles: states (queues)\nrectangles: activities\nFIFO, no balking", fontsize=6.3, ha="center", color=GREY)
    save(f, out, "Fig01_activity_cycle")
    FIG.append((1, "Fig01_activity_cycle", "drawn (model definition)",
                "Conceptual model as an activity cycle diagram. Cars alternate between being off site, waiting in one "
                "first-in-first-out queue and being plugged in; chargers alternate between free and occupied. The occupancy "
                "time is the whole plug-in stay (charging plus idle), which is why idle-time rules can replace chargers."))


def f02(root, out):
    f, ax = plt.subplots(figsize=(W2, 3.0))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 4.3)
    ax.axis("off")
    y = 3.0
    steps = [(1.0, "Car arrives\n(NHPP, 48\nhalf-hour rates\nx growth m)", "#FFF2CC"), (3.2, "Free\ncharger?\n(c chargers)", "#EEF3F8"),
             (5.4, "Plug in;\nstay drawn\nfrom the\narrival band", "#E2EFDA"), (7.6, "Charging\n(energy\ndelivered)", "#E2EFDA"),
             (9.8, "Idle but\nplugged in\n(until driver\nreturns)", "#F8CBAD")]
    for x, t, fc in steps:
        box(ax, (x, y), 1.7, 1.3, t, fc, fs=6.3)
    for k in range(4):
        arrow(ax, (steps[k][0] + 0.86, y), (steps[k + 1][0] - 0.86, y))
    arrow(ax, (10.66, y), (11.2, y))
    ax.text(11.25, y, "Leaves;\ncharger\nfree", fontsize=6.3, va="center")
    box(ax, (3.2, 1.0), 1.7, 0.7, "FIFO queue\n(no balking)", "#EEF3F8", fs=6.3)
    arrow(ax, (3.2, y - 0.66), (3.2, 1.36))
    ax.text(3.3, 1.85, "no", fontsize=6.3)
    arrow(ax, (4.06, 1.0), (5.4, y - 0.66), rad=0.25)
    ax.text(4.12, y + 0.12, "yes", fontsize=6.3)
    ax.text(3.2, 0.2, "outputs: W, P(W > 15 min), Wq, W95", fontsize=6.3, ha="center", color=BLUE)
    ax.add_patch(FancyBboxPatch((7.45, 0.1), 4.7, 1.35, boxstyle="round,pad=0.03", fc="white", ec=ORANGE, lw=1.1, ls="--"))
    ax.text(9.8, 0.78, "Idle-time policies act here\nP1: move within g min after charging ends\nP2: maximum stay 4 h\n"
            "P3: only a share p complies with P1", fontsize=6.3, ha="center", va="center", color=ORANGE)
    arrow(ax, (9.8, 1.5), (9.8, y - 0.66), color=ORANGE)
    save(f, out, "Fig02_process_flow")
    FIG.append((2, "Fig02_process_flow", "drawn (model definition)",
                "Process flow of one car in the simulation. A car takes a free charger or joins the queue; once plugged in it "
                "occupies the charger for its whole stay. The idle-time policies (P1-P3) shorten only the idle part that "
                "follows the end of charging."))


def f03(root, out):
    D = pd.read_csv(root / "results/phase1r/r5_daily_counts.csv", parse_dates=["date"])
    H = pd.read_csv(root / "paper_full/data/d9_hour_stats.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.5), gridspec_kw=dict(width_ratios=[1.35, 1]))
    col = D.dow.map(lambda d: ORANGE if d in ("Tue", "Wed") else BLUE)
    a.bar(D.date, D.arrivals, color=col, width=0.8)
    a.axhline(D.arrivals.mean(), color="k", ls="--", lw=0.8)
    from matplotlib.patches import Patch
    a.set(ylabel="arrivals per weekday", ylim=(0, 62))
    a.legend(handles=[Patch(color=BLUE, label="Mon, Thu, Fri"), Patch(color=ORANGE, label="Tue, Wed")], loc="upper left",
             frameon=False, ncol=2)
    a.tick_params(axis="x", rotation=30)
    panel(a, "(a)")
    b.bar(H.hr, H.arrivals_per_weekday, color="#BDD7EE", width=0.85, label="arrivals per weekday")
    b.set(xlabel="arrival hour (Pacific local time)", ylabel="arrivals per weekday", xticks=range(0, 24, 3))
    b2 = b.twinx()
    H = H[H.sessions >= 10]
    b2.plot(H.hr, H.stay_mean_h, color=ORANGE, marker="o", ms=2.5, label="mean stay (h)")
    b2.plot(H.hr, H.stay_median_h, color=ORANGE, ls="--", lw=1, label="median stay (h)")
    b2.set_ylabel("stay (h)", color=ORANGE)
    b2.spines["right"].set_visible(True)
    b2.set_ylim(0, 22)
    b.set_ylim(0, 12)
    h1, l1 = b.get_legend_handles_labels()
    h2, l2 = b2.get_legend_handles_labels()
    b.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=6.3)
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig03_data_overview")
    FIG.append((3, "Fig03_data_overview", "results/phase1r/r5_daily_counts.csv; paper_full/data/d9_hour_stats.csv",
                "Weekday sessions at the Caltech garage, 1 March to 31 May 2019. (a) Arrivals per weekday (65 days; "
                "dashed line = mean); Tuesdays and Wednesdays are the busiest days. (b) Arrivals by hour (bars) and the mean "
                "and median stay of cars arriving in that hour (lines; hours with at least 10 sessions): morning arrivals stay longest."))


def f04(root, out):
    R = pd.read_csv(root / "data/derived/rates_designday.csv")
    g = pd.read_csv(root / "results/phase1/p1_1_rescaled_gaps_v1.csv").rescaled_gap.to_numpy()
    FG = pd.read_csv(root / "results/phase1r/fit_gaps.csv")
    e = FG[FG.model == "expon_rate1"].iloc[0]
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.5), gridspec_kw=dict(width_ratios=[1.35, 1]))
    x = np.arange(49) / 2
    a.step(x, np.append(R.rate_pooled, R.rate_pooled.iloc[-1]), where="post", color=BLUE, lw=1.6, label="pooled weekdays (m = 1.0)")
    a.step(x, np.append(R.rate_designday, R.rate_designday.iloc[-1]), where="post", color=ORANGE, lw=1.0, label="Tue-Wed design day")
    a.step(x, 1.3 * np.append(R.rate_pooled, R.rate_pooled.iloc[-1]), where="post", color=BLUE, lw=0.9, ls="--", label="pooled x 1.3")
    a.set(xlabel="time of day (Pacific local time)", ylabel="arrivals per half hour", xticks=range(0, 25, 3), xlim=(0, 24))
    a.legend(frameon=False)
    panel(a, "(a)")
    s = np.sort(g)
    b.step(s, np.arange(1, len(s) + 1) / len(s), where="post", color=BLUE, label=f"rescaled gaps (n = {len(s):,})")
    xx = np.linspace(0, s.max(), 300)
    b.plot(xx, 1 - np.exp(-xx), color=ORANGE, ls="--", label="Exp(1)")
    b.set(xlabel="rescaled inter-arrival gap", ylabel="cumulative share", xlim=(0, 6))
    b.text(2.2, 0.35, f"K-S p = {e.KS_boot_p:.3f}\nA-D p = {e.AD_boot_p:.3f}\nchi-square p = {e.chi2_p:.3f}\n(parametric bootstrap)",
           fontsize=7)
    b.legend(frameon=False, loc="lower right")
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig04_arrival_model")
    FIG.append((4, "Fig04_arrival_model", "data/derived/rates_designday.csv; results/phase1/p1_1_rescaled_gaps_v1.csv; results/phase1r/fit_gaps.csv",
                "Arrival model. (a) Non-homogeneous Poisson rates for 48 half-hour slots (count per slot divided by 65 "
                "weekdays) for pooled weekdays, the Tuesday-Wednesday design day and +30% growth. (b) Time-rescaling check: "
                "the rescaled gaps follow the unit exponential distribution expected under the NHPP."))


def f05(root, out):
    ev = load_ev(root)
    pools = ev.band_pools(ev.load(), long_stays=True)
    S = pd.read_csv(root / "results/phase1r/fit_service_band_long.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.7))
    for k, P in enumerate(pools):
        s = np.sort(P)
        a.step(s, np.arange(1, len(s) + 1) / len(s), where="post", color=BANDC[k], lw=1.2,
               label=f"{ev.BAND_LABELS[k]} h (n = {len(s)})")
    a.set_xscale("log")
    a.set(xlabel="stay (h), log scale", ylabel="cumulative share")
    a.legend(frameon=False, title="arrival band", title_fontsize=6.8, loc="lower right", fontsize=6.3)
    panel(a, "(a)")
    S["band"] = S.input.str.replace("band_long_", "", regex=False)
    fam = list(dict.fromkeys(S.model))
    for k, lab in enumerate(ev.BAND_LABELS):
        d = S[S.band == lab].set_index("model").reindex(fam)
        b.scatter(np.arange(len(fam)) + (k - 2.5) * 0.11, d.AD_boot_p.clip(lower=1e-3), color=BANDC[k], s=12, label=lab, zorder=3)
    b.axhline(0.05, color="k", ls="--", lw=0.8)
    b.text(len(fam) - 0.6, 0.06, "0.05", fontsize=7, ha="right")
    b.set_yscale("log")
    b.set_xticks(range(len(fam)))
    b.set_xticklabels(fam, rotation=45, ha="right")
    b.set(ylabel="Anderson-Darling bootstrap p")
    b.legend(frameon=False, fontsize=6.3, ncol=3, loc="upper right", title="arrival band", title_fontsize=6.5)
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig05_stay_model")
    FIG.append((5, "Fig05_stay_model", "engine band pools (ev.band_pools); results/phase1r/fit_service_band_long.csv",
                "Stay (service-time) model. (a) Empirical distribution of the stay by arrival band, including stays over 24 h; "
                "these pools are sampled directly by the simulation. (b) Goodness of fit of the parametric candidates in each "
                "band (Anderson-Darling, parametric bootstrap with B = 500, so p cannot fall below 1/(B+1) = 0.002; mixLNk = mixture of "
                "k log-normals): no single family "
                "passes in any band, and only log-normal mixtures pass, in the 16-20 h and 21-04 h bands."))


def f06(root, out):
    Hh = pd.read_csv(root / "paper_full/data/d9_idle_hist.csv")
    B = pd.read_csv(root / "paper_full/data/d9_band_stats.csv")
    N = json.loads((root / "paper_full/data/descriptive_numbers.json").read_text())
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.5))
    a.bar((Hh.lo + Hh.hi) / 2, Hh.sessions, width=0.048, color=LBLUE)
    a.axvline(N["median_session_idle_share"], color=ORANGE, ls="--", lw=1)
    a.text(N["median_session_idle_share"] + 0.02, Hh.sessions.max() * 0.92, "median", color=ORANGE, fontsize=7)
    a.set(xlabel="idle share of the stay (session)", ylabel="sessions")
    panel(a, "(a)")
    x = np.arange(len(B))
    b.bar(x, B.charge_mean_h, color=BLUE, label="charging")
    b.bar(x, B.idle_mean_h, bottom=B.charge_mean_h, color="#F8CBAD", label="idle (plugged in, not charging)")
    b.set_xticks(x)
    b.set_xticklabels(B.band)
    b.set(xlabel="arrival band (h)", ylabel="mean hours per session")
    b.legend(frameon=False, loc="upper left")
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig06_idle_time")
    FIG.append((6, "Fig06_idle_time", "paper_full/data/d9_idle_hist.csv, d9_band_stats.csv, descriptive_numbers.json (scripts/descriptive_numbers.py)",
                "Idle time in the observed sessions (weekday sessions with a valid charge-completion time). (a) Share of each "
                "stay spent plugged in but not charging; most sessions are idle for more than half of their stay. (b) Mean "
                "charging and idle hours by arrival band."))


def f07(root, out):
    dm = importlib.util.spec_from_file_location("d7f", root / "scripts" / "report_figures.py")
    d7 = importlib.util.module_from_spec(dm)
    dm.loader.exec_module(d7)
    d7.fig03c(root, out / "Fig07_flexsim_model.png")
    Image.open(out / "Fig07_flexsim_model.png").convert("RGB").save(out / "Fig07_flexsim_model.tif", compression="tiff_lzw", dpi=(300, 300))
    FIG.append((7, "Fig07_flexsim_model", "flexsim/screenshots/G01_layout_3D.png, G07b_dashboard_seconds_c45.png (via report_figures.fig03c)",
                "FlexSim 2027 implementation at +30% demand with 45 open chargers. (a) 3D layout cropped to the model, with the "
                "object types numbered (source, queue, 52 single-capacity processors, closed chargers in grey, sink). (b) "
                "Dashboard panel of arrivals and departures per hour after the run (FlexSim default calendar)."))


def f08(root, out):
    FS_CMP = pd.read_csv(root / "results/flexsim/flexsim_key_cells_comparison.csv")
    MM = pd.read_csv(root / "results/phase6/vv_v2_mmc.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    lab = [f"{s} m={m:g} c={int(c)}" for s, m, c in zip(FS_CMP.set, FS_CMP.m, FS_CMP.c)]
    y = np.arange(len(FS_CMP))
    a.errorbar(100 * FS_CMP.P15_diff, y, xerr=[100 * (FS_CMP.P15_diff - FS_CMP.P15_lo), 100 * (FS_CMP.P15_hi - FS_CMP.P15_diff)], fmt="o", ms=3,
               color=BLUE, ecolor=BLUE, capsize=2)
    a.axvline(0, color="k", lw=0.8)
    a.set_yticks(y)
    a.set_yticklabels(lab, fontsize=6.5)
    a.invert_yaxis()
    a.set(xlabel="FlexSim - Python, P(W > 15 min), percentage points (95% Welch CI)")
    panel(a, "(a)")
    x = np.arange(len(MM))
    b.bar(x - 0.18, MM.Wq_exact_min, width=0.34, color=GREY, label="exact (Erlang C)")
    b.bar(x + 0.18, MM.Wq_sim, width=0.34, yerr=MM.Wq_hw, color=BLUE, capsize=3, label="simulation, 95% CI")
    b.set_xticks(x)
    b.set_xticklabels([f"c = {int(c)}\nrho = {r:.2f}" for c, r in zip(MM.c, MM.rho)])
    b.set(ylabel="mean wait Wq (min)", ylim=(0, 95))
    b.legend(frameon=False, loc="upper right")
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig08_verification")
    FIG.append((8, "Fig08_verification", "results/flexsim/flexsim_key_cells_comparison.csv; results/phase6/vv_v2_mmc.csv",
                "Verification. (a) FlexSim with its own random streams versus the Python engine in the 12 key cells (30 "
                "replications each): every 95% Welch interval of the difference in P(W > 15 min) contains zero. (b) Known-answer "
                "test: with exponential stays the simulated M/M/c mean wait matches the exact Erlang-C value."))


def f09(root, out):
    P = pd.read_csv(root / "results/phase1r/validation_v2_profile.csv")
    O = pd.read_csv(root / "results/phase4/p4_offered_load_15min.csv")
    Dp = pd.read_csv(root / "results/phase6/vv_v2_dispersion.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.5), gridspec_kw=dict(width_ratios=[1.4, 1]))
    t = P.slot / 2 + 0.25
    a.fill_between(t, P.data_mean - P.data_hw95, P.data_mean + P.data_hw95, color="#D9D9D9", label="data, 95% CI")
    a.plot(t, P.data_mean, color="k", lw=1, label="data (65 weekdays)")
    a.plot(t, P.band_long_mean, color=BLUE, label="DES (60 replications)")
    a.plot(O.q / 4 + 0.125, O.m_t_mean15, color=ORANGE, ls="--", lw=1.1, label="Mt/G/inf offered load m(t)")
    a.set(xlabel="time of day (Pacific local time)", ylabel="cars plugged in", xticks=range(0, 25, 3), xlim=(0, 24))
    a.legend(frameon=False, loc="center left", fontsize=6.5)
    panel(a, "(a)")
    tt = Dp.slot / 2 + 0.25
    b.plot(tt, Dp.data_var_over_mean, color="k", lw=1, label="data")
    b.plot(tt, Dp.model_var_over_mean, color=BLUE, label="DES")
    b.axhline(1, color=GREY, ls=":", lw=0.8)
    b.set(xlabel="time of day", ylabel="variance / mean of occupancy", xticks=range(0, 25, 6), xlim=(0, 24))
    b.legend(frameon=False)
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig09_validation")
    FIG.append((9, "Fig09_validation", "results/phase1r/validation_v2_profile.csv; results/phase4/p4_offered_load_15min.csv; results/phase6/vv_v2_dispersion.csv",
                "Validation at current demand with 52 chargers. (a) Mean number of cars plugged in by time of day: data with "
                "its 95% interval, the simulation and the analytic Mt/G/inf offered load. (b) Day-to-day dispersion of "
                "occupancy (variance over mean): the model varies more than the data, so its risk estimates are conservative."))


def f10(root, out):
    S = pd.read_csv(root / "results/phase5/p5_summary.csv")
    S = S[S.scenario == "P0"]
    f, ax = plt.subplots(figsize=(W2 * 0.62, 2.6))
    for g, col, lab, dx in (("pooled", BLUE, "pooled weekdays", -0.08), ("designday", ORANGE, "Tue-Wed design day", 0.08)):
        d = S[S.group == g].sort_values("c")
        ax.errorbar(d.c + dx, 100 * d.P15_mean, yerr=[100 * (d.P15_mean - d.P15_lo), 100 * (d.P15_hi - d.P15_mean)], fmt="o-",
                    ms=3.5, color=col, capsize=2.5, label=lab)
    ax.axhline(1.0, color="k", ls="--", lw=0.8)
    ax.text(48.2, 1.03, "target 1%", fontsize=7)
    ax.set(xlabel="number of chargers c", ylabel="P(W > 15 min), % (95% CI)")
    ax.legend(frameon=False)
    f.tight_layout()
    save(f, out, "Fig10_p15_vs_c")
    FIG.append((10, "Fig10_p15_vs_c", "results/phase5/p5_summary.csv",
                "Probability of waiting more than 15 min at +30% demand (m = 1.3) versus the number of chargers, with 95% "
                "confidence intervals from 200 replications with common random numbers. The decision rule selects the smallest "
                "c whose upper bound is at most 1%."))


def f11(root, out):
    G = pd.read_csv(root / "results/phase3/p3_grid_summary.csv")
    G = G[G.arrivals == "pooled"]
    Pv = G.pivot_table(index="c", columns="m", values="P15_upper")
    f, ax = plt.subplots(figsize=(W2 * 0.75, 3.0))
    Z = (100 * Pv.values).clip(1e-3, None)
    im = ax.pcolormesh(np.arange(len(Pv.columns) + 1) - 0.5, np.arange(len(Pv.index) + 1) - 0.5, Z,
                       norm=LogNorm(vmin=1e-3, vmax=max(np.nanmax(Z), 10)), cmap="RdYlBu_r", shading="flat")
    ax.contour(np.arange(len(Pv.columns)), np.arange(len(Pv.index)), Z, levels=[1.0], colors="k", linewidths=1.2)
    ax.set_xticks(range(len(Pv.columns)))
    ax.set_xticklabels([f"{m:g}" for m in Pv.columns])
    step = 5
    ax.set_yticks(range(0, len(Pv.index), step))
    ax.set_yticklabels(Pv.index[::step])
    if 52 in list(Pv.index):
        ax.axhline(list(Pv.index).index(52), color="w", ls="--", lw=1)
        ax.text(0.1, list(Pv.index).index(52) + 0.4, "52 installed", color="w", fontsize=7)
    ax.set(xlabel="demand growth factor m", ylabel="number of chargers c")
    cb = f.colorbar(im, ax=ax)
    cb.set_label("upper 95% bound of P(W > 15 min), %")
    f.tight_layout()
    save(f, out, "Fig11_heatmap")
    FIG.append((11, "Fig11_heatmap", "results/phase3/p3_grid_summary.csv",
                "Sizing grid for pooled weekdays: upper 95% bound of P(W > 15 min) for every combination of growth factor and "
                "charger count (log colour scale). The black contour is the 1% target; the white dashed line marks the 52 "
                "installed chargers."))


def f12(root, out):
    F = pd.read_csv(root / "results/phase3/p3_frontier.csv")
    M = pd.read_csv(root / "results/phase4/p4_mol_vs_des.csv")
    f, ax = plt.subplots(figsize=(W2 * 0.68, 2.8))
    for g, col, lab in (("pooled", BLUE, "DES, pooled weekdays"), ("designday", ORANGE, "DES, Tue-Wed design day")):
        d = F[F.arrivals == g].sort_values("m")
        ax.step(d.m, d.c_star, where="mid", color=col, lw=1.6, label=lab)
    ax.plot(M.m, M["c_MOL_eps0.01"], "v:", color=GREY, ms=3, lw=0.9, label="modified offered load, 1% tail")
    ax.plot(M.m, M["c_MOL_eps0.05"], "^:", color=PURPLE, ms=3, lw=0.9, label="modified offered load, 5% tail")
    ax.plot(M.m, M.c_EC, "o", color=GREEN, ms=3.5, mfc="none", label="arrival-weighted Erlang C")
    ax.axhline(52, color="k", ls="--", lw=0.8)
    ax.text(1.0, 52.6, "52 installed", fontsize=7)
    ax.set(xlabel="demand growth factor m", ylabel="smallest feasible c*")
    ax.legend(frameon=False, loc="upper left", fontsize=6.8)
    f.tight_layout()
    save(f, out, "Fig12_frontier")
    FIG.append((12, "Fig12_frontier", "results/phase3/p3_frontier.csv; results/phase4/p4_mol_vs_des.csv",
                "Feasibility frontier: the smallest charger count that meets the rule at each growth factor, from the "
                "simulation (pooled weekdays and design day) and from three analytic sizing rules. The installed 52 chargers "
                "meet the rule up to the point where the frontier crosses the dashed line."))


def f13(root, out):
    S = pd.read_csv(root / "results/phase3/p3_policy_savings.csv")
    S = S[S.policy != "P0"]
    lab = {"P1-30": "move within 30 min", "P1-60": "move within 60 min", "P1-120": "move within 120 min", "P2-cap4h": "4-h stay cap",
           "P3-p0.25": "60-min rule, 25% comply", "P3-p0.50": "60-min rule, 50% comply", "P3-p0.75": "60-min rule, 75% comply"}
    pols = [p for p in lab if p in set(S.policy)]
    f, ax = plt.subplots(figsize=(W2 * 0.7, 2.6))
    y = np.arange(len(pols))
    for m, col, dy in ((1.3, BLUE, -0.17), (1.6, ORANGE, 0.17)):
        d = S[np.isclose(S.m, m)].set_index("policy").reindex(pols)
        ax.barh(y + dy, d.chargers_saved_vs_P0, height=0.32, color=col, label=f"m = {m:g}",
                xerr=[d.chargers_saved_vs_P0 - d.saved_CI95_lo, d.saved_CI95_hi - d.chargers_saved_vs_P0], capsize=2,
                error_kw=dict(lw=0.8))
    ax.set_yticks(y)
    ax.set_yticklabels([lab[p] for p in pols])
    ax.invert_yaxis()
    ax.set(xlabel="chargers saved vs no policy (95% CI)")
    ax.legend(frameon=False, loc="lower right")
    f.tight_layout()
    save(f, out, "Fig14_policies")
    FIG.append((14, "Fig14_policies", "results/phase3/p3_policy_savings.csv",
                "Chargers saved by idle-time policies at +30% (m = 1.3) and +60% (m = 1.6) demand, relative to the "
                "no-policy requirement at the same growth. Driver behaviour under the policies (moving within g minutes, "
                "compliance share) is assumed, not observed."))


def f14(root, out):
    Bc = pd.read_csv(root / "results/phase3/p3_boot_cstar.csv")
    Rn = pd.read_csv(root / "results/phase3/p3_renege_summary.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.5))
    v = Bc.c_star.value_counts().sort_index()
    a.bar(v.index, v.values, color=LBLUE, width=0.6)
    a.set(xlabel="c* selected with a bootstrap input sample", ylabel="bootstrap inputs (of 50)", xticks=list(v.index))
    panel(a, "(a)")
    for (m, pt), d in Rn.groupby(["m", "patience_min"]):
        d = d.sort_values("c")
        b.plot(d.c, 100 * d.lost_share_mean, color=BLUE if np.isclose(m, 1.3) else ORANGE, ls="-" if pt == 30 else "--",
               label=f"m = {m:g}, patience {pt} min")
    b.set(xlabel="number of chargers c", ylabel="drivers who leave (%)")
    b.legend(frameon=False)
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig13_robustness")
    FIG.append((13, "Fig13_robustness", "results/phase3/p3_boot_cstar.csv; results/phase3/p3_renege_summary.csv",
                "Robustness. (a) Charger count selected when the 65 input days are resampled (50 bootstrap inputs x 20 "
                "replications at m = 1.3). (b) Share of drivers who would leave if they waited longer than their patience, by "
                "charger count."))


def f15(root, out):
    Pq = pd.read_csv(root / "results/phase6/p6_prob_sens.csv")
    Hz = pd.read_csv(root / "results/phase6/p6_hurwicz.csv")
    L = json.loads((root / "results/phase6/p6_lenses.json").read_text())
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.6))
    for o in OPTC:
        a.plot(Pq.q_high, Pq[f"E_{o}"] / 1000, color=OPTC[o], label=o)
        b.plot(Hz.alpha, Hz[f"H_{o}"] / 1000, color=OPTC[o], label=o)
    a.axvline(L["q_judged"], color="k", ls=":", lw=0.8)
    a.text(L["q_judged"] + 0.01, a.get_ylim()[0] + 1, "judged q", fontsize=7, va="bottom")
    a.set(xlabel="probability of high growth q = P(m >= 1.6)", ylabel="expected annual cost (USD thousand)")
    f.legend(*a.get_legend_handles_labels(), frameon=False, ncol=6, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    panel(a, "(a)")
    b.set(xlabel="Hurwicz optimism coefficient alpha", ylabel="Hurwicz value (USD thousand)", ylim=(0, 150))
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig15_decision_sensitivity")
    FIG.append((15, "Fig15_decision_sensitivity", "results/phase6/p6_prob_sens.csv; results/phase6/p6_hurwicz.csv; results/phase6/p6_lenses.json",
                "Decision analysis under growth uncertainty (A0 keep 52; A1, A2, A3 buy 2, 6 or 13; A4 keep 52 with a voluntary "
                "60-min rule; A5 the rule enforced by a fee). (a) Expected annual cost versus the probability of high growth. "
                "(b) Hurwicz criterion versus the optimism coefficient (lower is better)."))


def f16(root, out):
    Pay = pd.read_csv(root / "results/phase6/p6_payoff.csv")
    As = pd.read_csv(root / "results/phase6/p6_ahp_sens.csv")
    f, (a, b) = plt.subplots(1, 2, figsize=(W2, 2.6))
    ms = sorted(Pay.m.unique())
    w = 0.13
    for k, o in enumerate(OPTC):
        d = Pay[Pay.option == o].set_index("m").reindex(ms)
        a.bar(np.arange(len(ms)) + (k - 2.5) * w, d.total / 1000, width=w, color=OPTC[o], label=o)
    a.set_xticks(range(len(ms)))
    a.set_xticklabels([f"m = {m:g}" for m in ms])
    a.set(ylabel="annual cost (USD thousand)")
    a.legend(frameon=False, ncol=3, fontsize=6.8)
    panel(a, "(a)")
    d = As[As.criterion == "cost"]
    for o in OPTC:
        b.plot(d.weight, d[f"S_{o}"], color=OPTC[o], label=o)
    b.set(xlabel="weight of the total-annualised-cost criterion (others rescaled)", ylabel="AHP overall score")
    panel(b, "(b)")
    f.tight_layout()
    save(f, out, "Fig16_payoff_ahp")
    FIG.append((16, "Fig16_payoff_ahp", "results/phase6/p6_payoff.csv; results/phase6/p6_ahp_sens.csv",
                "(a) Annual cost of each option in each growth future (capital, maintenance and network fees, waiting and "
                "walking time, and policy administration). (b) AHP overall score of each option as the weight of the "
                "total-annualised-cost criterion changes (higher is better); this criterion includes the monetised waiting "
                "time, which also enters the service criterion."))


def graphical_abstract(root, out):
    F = pd.read_csv(root / "results/phase3/p3_frontier.csv")
    S = pd.read_csv(root / "results/phase3/p3_policy_savings.csv")
    N = json.loads((root / "paper_full/data/descriptive_numbers.json").read_text())
    f, (a, b, c) = plt.subplots(1, 3, figsize=(W2, 2.4), gridspec_kw=dict(width_ratios=[0.85, 1.1, 1.25], wspace=0.55))
    _, _, pct = a.pie([1 - N["aggregate_idle_share"], N["aggregate_idle_share"]], colors=[BLUE, "#F8CBAD"], startangle=90,
                      autopct="%1.0f%%", pctdistance=0.78, textprops=dict(fontsize=7.5), wedgeprops=dict(width=0.45))
    pct[0].set_color("white")
    a.legend(["charging", "idle (plugged in)"], loc="upper center", bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=7, ncol=1)
    a.set_title("Plug-in hours (weekday sessions)", fontsize=8)
    d = F[F.arrivals == "pooled"].sort_values("m")
    b.step(d.m, d.c_star, where="mid", color=BLUE, lw=1.8, label="needed (1% rule)")
    b.axhline(52, color="k", ls="--", lw=0.8, label="52 installed")
    b.set(xlabel="demand growth factor m", ylabel="chargers")
    b.legend(frameon=False, fontsize=6.5, loc="upper left")
    b.set_title("Chargers needed vs growth", fontsize=8)
    s = S[np.isclose(S.m, 1.3) & S.policy.isin(["P1-30", "P1-60", "P3-p0.50"])].set_index("policy").reindex(["P1-30", "P1-60", "P3-p0.50"])
    names = ["move within 30 min", "move within 60 min", "60-min rule, 50% comply"]
    c.barh(range(3), s.chargers_saved_vs_P0, color="#A9D18E")
    for k, (nm, v) in enumerate(zip(names, s.chargers_saved_vs_P0)):
        c.text(0.3, k, f"{nm}: {int(v)}", va="center", fontsize=7)
    c.set_yticks([])
    c.invert_yaxis()
    c.set(xlabel="chargers saved at +30%")
    c.set_title("Idle-time rules", fontsize=8)
    f.savefig(out / "graphical_abstract.png", dpi=400, bbox_inches="tight")
    f.savefig(out / "graphical_abstract.pdf", bbox_inches="tight")
    plt.close(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    root = Path(ap.parse_args().project).resolve()
    out = root / "paper_full" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    for fn in (f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13, f14, f15, f16):
        fn(root, out)
        print("done", fn.__name__)
    graphical_abstract(root, root / "paper_full")
    pd.DataFrame(FIG, columns=["number", "stem", "sources", "caption"]).sort_values("number").to_csv(out / "FIGSET.csv", index=False)
    print(len(FIG), "figures")


if __name__ == "__main__":
    main()
