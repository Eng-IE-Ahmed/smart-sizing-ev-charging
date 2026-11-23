""" figure set (PROJECT_PLAN Phase 8.2, items 1-14) in figures/report/, 300 dpi, one style (matplotlib defaults,
project palette #1F4E78 / #C55A11 / #70AD47 / #7030A0).
New figures: Fig01 conceptual model (activity cycle diagram), Fig02 process flow with the points where the idle policies
act, Fig03 FlexSim 3D view (composite of two window captures), Fig04 daily arrivals over time, Fig05 NHPP rate profile,
Fig07 stay ECDF by arrival band. The others are copies of existing 300-dpi figures (source listed in FIGSET.csv).
Usage: python scripts/report_figures.py --project .
Output: figures/report/Fig01..Fig14 (+ FigS* extras used by the paper), figures/report/FIGSET.csv. No randomness.
"""
import argparse
import importlib.util
import shutil
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch  # noqa: E402

BLUE, ORANGE, GREEN, PURPLE, GREY = "#1F4E78", "#C55A11", "#70AD47", "#7030A0", "#7F7F7F"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11})

COPIES = [  # (target, source, caption)
    ("Fig06_rescaled_gaps.png", "figures/phase1r/r1_fit_gaps.png", "Arrival process: rescaled inter-arrival gaps vs Exp(1) (NHPP check)"),
    ("Fig08_idle_time.png", "figures/phase1/p1_6_idle_hist.png", "Idle time after charging ends (v1 pool; 56.9% of plug-in hours, 56.7% in the v2 pool)"),
    ("Fig09_validation_profile.png", "figures/phase4/p4_offered_load.png", "Validation: occupancy by time of day, data vs DES vs Mt/G/inf"),
    ("Fig10_P15_vs_c.png", "figures/phase1r/r6_p15_vs_c.png", "P(wait > 15 min) vs chargers at +30%, mean and upper 95% bound"),
    ("Fig11_heatmap_P15.png", "figures/phase3/p3_heat_P15upper.png", "Sizing heat-map: upper 95% bound of P(wait > 15 min)"),
    ("Fig12_frontier.png", "figures/phase3/p3_frontier.png", "Feasibility frontier c*(m) with 95% band"),
    ("Fig13_policy_savings.png", "figures/phase3/p3_policy_savings.png", "Chargers saved by idle-management policies"),
    ("Fig14a_payoff_regret.png", "figures/phase6/p6_payoff_regret.png", "Payoff (annual cost) and regret tables"),
    ("Fig14b_ahp.png", "figures/phase6/p6_ahp.png", "AHP weights and weight sensitivity"),
    ("FigS1_trace_check.png", "figures/flexsim/fig_b3_trace_check.png", "FlexSim = engine, car by car (trace mode)"),
    ("FigS2_flexsim_vs_engine.png", "figures/flexsim/fig_d5_flexsim_vs_engine.png", "FlexSim confirmation of the key cells"),
    ("FigS3_feasibility.png", "figures/phase5/p5_feasibility.png", "Feasibility check with Bonferroni bounds"),
    ("FigS4_mol_vs_des.png", "figures/phase4/p4_mol_vs_des.png", "Analytic sizing rules vs the DES frontier"),
    ("FigS5_prob_sens.png", "figures/phase6/p6_prob_sens.png", "EMV vs the probability of high growth"),
    ("FigS6_decision_tree.png", "figures/phase6/decision_analysis_tree.png", "Decision tree"),
    ("FigS7_paired_diffs.png", "figures/phase5/p5_paired_diffs.png", "Paired CRN differences"),
]


def box(ax, xy, w, h, text, fc, ec=BLUE, fs=9, rounded=True):
    p = FancyBboxPatch((xy[0] - w / 2, xy[1] - h / 2), w, h, boxstyle="round,pad=0.02" if rounded else "square,pad=0.0",
                       fc=fc, ec=ec, lw=1.4)
    ax.add_patch(p)
    ax.text(xy[0], xy[1], text, ha="center", va="center", fontsize=fs)


def arrow(ax, a, b, color="k", style="-|>", rad=0.0, lw=1.3, ls="-"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=12, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))


def fig01(out):
    f, ax = plt.subplots(figsize=(10, 5.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.0)
    ax.axis("off")
    for xy, t in [((1.0, 3.6), "Outside\n(not on site)"), ((4.0, 3.6), "Queue\n(waiting car)"), ((8.6, 3.6), "Done\n(leaving)")]:
        ax.add_patch(Circle(xy, 0.62, fc="#EEF3F8", ec=BLUE, lw=1.4))
        ax.text(*xy, t, ha="center", va="center", fontsize=8.5)
    box(ax, (2.5, 3.6), 1.3, 0.7, "Arrive\n(NHPP)", "#FFF2CC", rounded=False)
    box(ax, (6.25, 3.6), 2.2, 1.0, "Plugged in\n= charging + idle\n(occupancy time)", "#E2EFDA", rounded=False)
    arrow(ax, (1.62, 3.6), (1.85, 3.6))
    arrow(ax, (3.15, 3.6), (3.38, 3.6))
    arrow(ax, (4.62, 3.6), (5.15, 3.6))
    arrow(ax, (7.35, 3.6), (7.98, 3.6))
    arrow(ax, (8.6, 4.24), (1.0, 4.24), rad=0.22, ls="--", color=GREY)
    ax.text(4.8, 5.55, "car cycle (next visit)", fontsize=8, color=GREY, ha="center")
    ax.add_patch(Circle((6.25, 1.2), 0.62, fc="#EEF3F8", ec=ORANGE, lw=1.4))
    ax.text(6.25, 1.2, "Free\ncharger", ha="center", va="center", fontsize=8.5)
    arrow(ax, (5.75, 1.6), (5.6, 3.1), color=ORANGE, rad=-0.3)
    arrow(ax, (6.9, 3.1), (6.75, 1.6), color=ORANGE, rad=-0.3)
    ax.text(7.5, 1.2, "charger cycle:\nc identical Level-2 chargers", fontsize=8, color=ORANGE, va="center")
    ax.text(4.0, 2.55, "wait W = start - arrival\nrisk: P(W > 15 min)", fontsize=8, ha="center", color=BLUE)
    ax.text(8.6, 2.55, "idle part of the stay is\nthe target of policies P1-P3", fontsize=8, ha="center", color=GREEN)
    ax.set_title("Conceptual model (activity cycle diagram): circles = queues/states, rectangles = activities; FIFO, no balking",
                 fontsize=10)
    f.savefig(out, dpi=300, bbox_inches="tight")
    f.savefig(Path(out).with_suffix(".pdf"), bbox_inches="tight")
    plt.close(f)


def fig02(out):
    f, ax = plt.subplots(figsize=(11, 4.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    y = 3.0
    steps = [(0.9, "Car arrives\nNHPP: 48 half-hour\nrates x growth m", "#FFF2CC"),
             (2.9, "Free charger?\n(c chargers)", "#EEF3F8"),
             (4.9, "Plug in\nstay drawn from\narrival band", "#E2EFDA"),
             (6.9, "Charging\n(energy delivered)", "#E2EFDA"),
             (8.9, "Idle but plugged\n(until the driver\nreturns)", "#F8CBAD")]
    for x, t, fc in steps:
        box(ax, (x, y), 1.6, 1.15, t, fc)
    for k in range(4):
        arrow(ax, (steps[k][0] + 0.82, y), (steps[k + 1][0] - 0.82, y))
    arrow(ax, (9.72, y), (10.6, y))
    ax.text(10.65, y, "Departs:\ncharger\nfree", fontsize=8.5, va="center")
    box(ax, (2.9, 1.2), 1.6, 0.8, "FIFO queue\n(no balking)", "#EEF3F8")
    arrow(ax, (2.9, y - 0.6), (2.9, 1.62))
    ax.text(3.0, 2.05, "no", fontsize=8)
    arrow(ax, (3.72, 1.2), (4.9, y - 0.6), rad=0.25)
    ax.text(3.9, y + 0.12, "yes", fontsize=8)
    ax.text(2.9, 0.3, "measure: wait W, P(W > 15 min), Wq, W95", fontsize=8, ha="center", color=BLUE)
    ax.add_patch(FancyBboxPatch((7.55, 0.2), 3.3, 1.45, boxstyle="round,pad=0.03", fc="white", ec=ORANGE, lw=1.6, ls="--"))
    ax.text(9.2, 0.92, "WHERE THE POLICY ACTS\nP1: move the car within g min\nafter charging ends\n"
            "P2: maximum stay 4 h\nP3: only a share p of drivers complies", fontsize=7.4, ha="center", va="center", color=ORANGE)
    arrow(ax, (8.9, 1.7), (8.9, y - 0.6), color=ORANGE, style="-|>")
    ax.set_title("System process flow (one car); the idle-but-plugged step (56.7% of plug-in hours) is what the policies shorten",
                 fontsize=10)
    f.savefig(out, dpi=300, bbox_inches="tight")
    f.savefig(Path(out).with_suffix(".pdf"), bbox_inches="tight")
    plt.close(f)


def fig03(root, out):
    a = Image.open(root / "flexsim/screenshots/G01_layout_3D.png").convert("RGB")
    b = Image.open(root / "flexsim/screenshots/D5_policy_P1-30_m1.3_c32.png").convert("RGB")
    h = 900
    a = a.resize((int(a.width * h / a.height), h))
    b = b.resize((int(b.width * h / b.height), h))
    pad, top = 30, 90
    W = a.width + b.width + 3 * pad
    canvas = Image.new("RGB", (W, h + top + pad), "white")
    canvas.paste(a, (pad, top))
    canvas.paste(b, (2 * pad + a.width, top))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    d.text((pad, 25), "(a) FlexSim 2027: 52 chargers (Processors), +30% demand, c = 45 (46-52 grey)", fill=(31, 78, 120), font=font)
    d.text((2 * pad + a.width, 25), "(b) best idle policy P1-30 run, c = 32 (33-52 grey)", fill=(31, 78, 120), font=font)
    canvas.save(out, dpi=(300, 300))


def fig03c(root, out):
    """: one clear FlexSim figure - (a) the 3D layout cropped to the model (no library panel or toolbars), with
    numbered markers and a legend strip in large type; (b) one dashboard panel (arrivals/departures per hour)."""
    lay = Image.open(root / "flexsim/screenshots/G01_layout_3D.png").convert("RGB").crop((480, 140, 1440, 770))
    dash = Image.open(root / "flexsim/screenshots/G07b_dashboard_seconds_c45.png").convert("RGB").crop((420, 232, 980, 555))
    try:
        fb = ImageFont.truetype("arialbd.ttf", 26)
        fm = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        fb = fm = ImageFont.load_default()
    d = ImageDraw.Draw(lay)
    marks = [(1, (285, 545)), (2, (455, 562)), (3, (150, 330)), (4, (850, 205)), (5, (838, 79))]
    for n, (x, y) in marks:
        d.ellipse((x - 19, y - 19, x + 19, y + 19), fill=(197, 90, 17), outline="white", width=3)
        d.text((x, y), str(n), fill="white", font=fb, anchor="mm")
    legend = ["1  Source 'CarArrivals' (arrival times from the NHPP)", "2  Queue 'ChargeQueue' (FIFO, no balking)",
              "3  Processor = one charger, capacity 1 (brown box = car plugged in)",
              "4  Chargers 46-52 closed (grey): c = 45 open", "5  Sink 'Departed'"]
    W = lay.width
    strip_h = 36 * len(legend) + 20
    top_h = 50
    canvas = Image.new("RGB", (W, top_h + lay.height + strip_h + top_h + dash.height + 10), "white")
    dc = ImageDraw.Draw(canvas)
    dc.text((10, 12), "(a) FlexSim 2027 3D view, +30% demand, 52 Processors (day 9, 09:30)", fill=(31, 78, 120), font=fb)
    canvas.paste(lay, (0, top_h))
    y0 = top_h + lay.height + 10
    for k, t in enumerate(legend):
        dc.text((14, y0 + 36 * k), t, fill=(30, 30, 30), font=fm)
    y1 = y0 + strip_h
    dc.text((10, y1 + 12), "(b) Dashboard panel after the run: arrivals and departures per hour", fill=(31, 78, 120), font=fb)
    canvas.paste(dash, ((W - dash.width) // 2, y1 + top_h))
    canvas.save(out, dpi=(300, 300))


def fig07b(root, out):
    """ (guideline step 3: histogram + at least two fitted distributions for the service times): the six band_long
    panels of figures/phase1r/r1_fit_service.png (5 x 3 grid of 1300 x 1020 px panels), arranged 3 x 2."""
    src = Image.open(root / "figures/phase1r/r1_fit_service.png").convert("RGB")
    pw, ph = src.width // 3, src.height // 5
    cells = [(2, 2), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1)]
    canvas = Image.new("RGB", (3 * pw, 2 * ph), "white")
    for k, (r, c) in enumerate(cells):
        canvas.paste(src.crop((c * pw, r * ph, (c + 1) * pw, (r + 1) * ph)), ((k % 3) * pw, (k // 3) * ph))
    canvas.save(out, dpi=(300, 300))


def fig04(root, out):
    D = pd.read_csv(root / "results/phase1r/r5_daily_counts.csv", parse_dates=["date"])
    f, ax = plt.subplots(figsize=(10, 3.8))
    col = D.dow.map(lambda d: ORANGE if d in ("Tue", "Wed") else BLUE)
    ax.bar(D.date, D.arrivals, color=col, width=0.8)
    ax.axhline(D.arrivals.mean(), color="k", ls="--", lw=1)
    ax.text(D.date.iloc[-1], D.arrivals.mean() + 1, f"mean {D.arrivals.mean():.1f} per weekday", ha="right", fontsize=9)
    ax.bar([], [], color=BLUE, label="Mon, Thu, Fri")
    ax.bar([], [], color=ORANGE, label="Tue, Wed (design day)")
    ax.set(ylabel="arrivals per weekday",
           title=f"Daily arrivals, Caltech garage, weekdays 1 Mar - 31 May 2019 ({len(D)} days, holiday removed)")
    ax.legend(fontsize=8, loc="lower left")
    f.autofmt_xdate()
    f.tight_layout()
    f.savefig(out, dpi=300)
    f.savefig(Path(out).with_suffix(".pdf"))
    plt.close(f)


def fig05(root, out):
    R = pd.read_csv(root / "data/derived/rates_designday.csv")
    f, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(49) / 2
    ax.step(x, np.append(R.rate_pooled, R.rate_pooled.iloc[-1]), where="post", color=BLUE, lw=2, label="pooled weekdays")
    ax.step(x, np.append(R.rate_designday, R.rate_designday.iloc[-1]), where="post", color=ORANGE, lw=1.4, label="Tue-Wed design day")
    ax.step(x, 1.3 * np.append(R.rate_pooled, R.rate_pooled.iloc[-1]), where="post", color=BLUE, lw=1, ls="--", label="pooled x 1.3 (+30%)")
    ax.set(xlabel="hour of day (local, Pacific)", ylabel="arrivals per half hour", xticks=range(0, 25, 2),
           title="NHPP rate profile: 48 half-hour rates r_k = count_k / 65 weekdays; peak at 08:00 local")
    ax.legend(fontsize=8)
    f.tight_layout()
    f.savefig(out, dpi=300)
    f.savefig(Path(out).with_suffix(".pdf"))
    plt.close(f)


def fig07(root, out):
    spec = importlib.util.spec_from_file_location("ev", root / "engine" / "ev_des_engine.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    ev.DATA = str(root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json")
    df = ev.load()
    pools = ev.band_pools(df, long_stays=True)
    f, ax = plt.subplots(figsize=(8.5, 4.2))
    cols = ["#1F4E78", "#5B9BD5", "#70AD47", "#C55A11", "#7030A0", "#7F7F7F"]
    for b, P in enumerate(pools):
        s = np.sort(P)
        ax.step(s, np.arange(1, len(s) + 1) / len(s), where="post", color=cols[b], lw=1.6,
                label=f"arrivals {ev.BAND_LABELS[b]} h (n = {len(s)}, mean {s.mean():.1f} h)")
    ax.set_xscale("log")
    ax.set(xlabel="stay (plug-in to unplug), hours, log scale", ylabel="cumulative share",
           title="Stay (occupancy) distribution by arrival band - empirical, weekdays, incl. stays > 24 h")
    ax.legend(fontsize=7.5, loc="upper left")
    f.tight_layout()
    f.savefig(out, dpi=300)
    f.savefig(Path(out).with_suffix(".pdf"))
    plt.close(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out = root / "figures" / "report"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    fig01(out / "Fig01_conceptual_model.png")
    rows.append(("Fig01_conceptual_model.png", "new (report_figures.py)", "Conceptual model: activity cycle diagram"))
    fig02(out / "Fig02_process_flow.png")
    rows.append(("Fig02_process_flow.png", "new", "System process flow and where the idle policies act"))
    fig03(root, out / "Fig03_flexsim_3d.png")
    rows.append(("Fig03_flexsim_3d.png", "flexsim/screenshots/G01_layout_3D.png + D5_policy_P1-30_m1.3_c32.png", "FlexSim 3D view"))
    fig07b(root, out / "Fig07b_service_fits.png")
    rows.append(("Fig07b_service_fits.png", "figures/phase1r/r1_fit_service.png (band_long panels)",
                 "Service-time histograms with the two best fitted distributions per arrival band"))
    fig03c(root, out / "Fig03c_flexsim_clear.png")
    rows.append(("Fig03c_flexsim_clear.png", "G01_layout_3D.png (3D view crop) + G07b dashboard (arrivals/departures panel)",
                 "FlexSim model, readable: layout with numbered objects and one dashboard panel"))
    dash = Image.open(root / "flexsim/screenshots/G07b_dashboard_seconds_c45.png").convert("RGB")
    dash.crop((0, 232, dash.width, dash.height)).save(out / "Fig03b_flexsim_dashboard.png", dpi=(300, 300))
    rows.append(("Fig03b_flexsim_dashboard.png", "flexsim/screenshots/G07b_dashboard_seconds_c45.png (bottom row crop)",
                 "FlexSim dashboard: charger utilisation and arrivals/departures per hour"))
    fig04(root, out / "Fig04_daily_arrivals.png")
    rows.append(("Fig04_daily_arrivals.png", "new from results/phase1r/r5_daily_counts.csv", "Daily arrivals over time"))
    fig05(root, out / "Fig05_nhpp_rates.png")
    rows.append(("Fig05_nhpp_rates.png", "new from data/derived/rates_designday.csv", "NHPP rate profile"))
    fig07(root, out / "Fig07_stay_ecdf.png")
    rows.append(("Fig07_stay_ecdf.png", "new from engine band pools", "Stay ECDF by arrival band"))
    for tgt, src, cap in COPIES:
        shutil.copy2(root / src, out / tgt)
        rows.append((tgt, src, cap))
    pd.DataFrame(rows, columns=["file", "source", "caption"]).sort_values("file").to_csv(out / "FIGSET.csv", index=False)
    print(len(rows), "figures in", out)


if __name__ == "__main__":
    main()
