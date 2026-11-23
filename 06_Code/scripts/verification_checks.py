"""V&V re-checks on the v2 engine (Directive , PROJECT_PLAN §7): the Phase-1 verification tasks 1.8a-c were run with the
v1 (A/B) service model; the queue logic is unchanged in v2 (results/phase1r/r3_engine_v2_AB_vs_v1.csv), but they are
repeated here with the v2 base model band_long so that every §7 entry has v2 evidence. Also the model side of V11.

V7a flow balance: m = 1.3, c = 45 and 38, reps 1..60: arrived = completed + in service at the end + queued at the end.
V6  overload:     m = 1.3, c = 20 and 12, run length x1 (65 weekdays) and x2 (130), reps 1..20: Wq must grow with run
                  length when the system is overloaded (c = 12: offered load ~14.4 > 12) and stay stable when it is not.
V5  known answer: constant arrival rate lambda = 1.3 x (weekday arrivals / 24 h), exponential stays with the arrival-weighted
                  band_long mean E[S] (deterministic quantile set of 200,000 points), c with rho ~ 0.9 and ~ 0.8,
                  horizon x10, reps 1..20: Wq and P(wait > 0) vs the exact M/M/c (Erlang C) values; 95% t-CI.
V11 model side:   occupancy N(t) at the 48 half-hour points of each day, DES band_long, m = 1.0, c = 52, reps 1..60:
                  variance/mean across the 65 days (per rep, then averaged) vs the data's ratio (results/phase1/
                  p1_4_dispersion_all_sessions_v1.csv). The NHPP model gives ~Poisson (ratio ~1); the data are under-dispersed.
Usage: python scripts/verification_checks.py --project .
Output: results/phase6/vv_v2_flow_balance.csv, vv_v2_overload.csv, vv_v2_mmc.csv, vv_v2_dispersion.csv, vv_v2_summary.json
Seeds: engine CRN streams default_rng([r,1]) / [r,2].
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def tci(x):
    x = np.asarray(x, float)
    return x.mean(), stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / math.sqrt(len(x))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project).resolve()
    out = root / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("ev", root / "engine" / "ev_des_engine.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    ev.DATA = str(root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json")
    df = ev.load()
    rates, A, B = ev.inputs(df)
    mod = ev.ServiceModel("band_long", df)
    H0 = ev.HORIZON
    S = {}

    fb = []
    for c in (45, 38):
        for r in range(1, 61):
            arr, svc, _ = ev.draw(rates, A, B, r, 1.3, mod)
            st = ev.run_queue(arr, svc, c)[1]
            e = st + svc
            comp, ins, que = int((e <= H0).sum()), int(((st < H0) & (e > H0)).sum()), int((st >= H0).sum())
            fb.append(dict(c=c, rep=r, arrived=len(arr), completed=comp, in_service_end=ins, queued_end=que,
                           imbalance=len(arr) - comp - ins - que))
    fb = pd.DataFrame(fb)
    fb.to_csv(out / "vv_v2_flow_balance.csv", index=False)
    S["V7a_flow_imbalance_total"] = int(fb.imbalance.abs().sum())

    ov = []
    for c in (20, 12):
        for mult_h in (1, 2):
            ev.HORIZON = H0 * mult_h
            for r in range(1, 21):
                arr, svc, _ = ev.draw(rates, A, B, r, 1.3, mod)
                o = ev.run_queue(arr, svc, c)[0]
                ov.append(dict(c=c, run_length_x=mult_h, rep=r, Wq=o["Wq"], Util=o["Util"]))
    ev.HORIZON = H0
    ov = pd.DataFrame(ov)
    ov.to_csv(out / "vv_v2_overload.csv", index=False)
    g = ov.groupby(["c", "run_length_x"]).Wq.mean().unstack()
    S["V6_overload_Wq_min"] = {int(c): {int(k): float(v) for k, v in row.items()} for c, row in g.iterrows()}

    lam_h = 1.3 * rates.sum() / 24
    ES = float(sum(rates[k] * mod.pools[ev.band_of(k // 2)].mean() for k in range(48)) / rates.sum())
    N = 200000
    expo = np.sort(-ES * np.log(1 - (np.arange(1, N + 1) - 0.5) / N))
    flat = np.full(48, rates.sum() / 48)
    aE = lam_h * expo.mean()
    mm = []
    ev.HORIZON = H0 * 10
    for c in (math.ceil(aE / 0.9), math.ceil(aE / 0.8)):
        terms = sum(aE ** k / math.factorial(k) for k in range(c))
        last = aE ** c / math.factorial(c) * c / (c - aE)
        Pw = last / (terms + last)
        Wq_exact = Pw * expo.mean() / (c - aE) * 60
        sims = [ev.replicate(flat, expo, expo, c, r, 1.3)[0] for r in range(1, 21)]
        wq, hw = tci([q["Wq"] for q in sims])
        p0, hp = tci([q["P0"] for q in sims])
        mm.append(dict(c=c, lam_per_h=lam_h, ES_h=float(expo.mean()), a=aE, rho=aE / c, Pw_exact=Pw, Wq_exact_min=Wq_exact,
                       Wq_sim=wq, Wq_hw=hw, Wq_in_CI=bool(abs(wq - Wq_exact) <= hw), P0_sim=p0, P0_hw=hp,
                       P0_in_CI=bool(abs(p0 - Pw) <= hp), rel_hw=hw / wq))
    ev.HORIZON = H0
    mm = pd.DataFrame(mm)
    mm.to_csv(out / "vv_v2_mmc.csv", index=False)
    S["V5_mmc"] = mm[["c", "rho", "Wq_exact_min", "Wq_sim", "Wq_hw", "Wq_in_CI", "Pw_exact", "P0_sim", "P0_in_CI"]].to_dict("records")

    taus = (np.arange(ev.NDAYS)[:, None] * 24 + np.arange(48)[None, :] * 0.5)        # 65 x 48 observation times
    ratios = []
    for r in range(1, 61):
        arr, svc, _ = ev.draw(rates, A, B, r, 1.0, mod)
        st = ev.run_queue(arr, svc, 52)[1]
        s_sorted, e_sorted = np.sort(st), np.sort(st + svc)
        Nt = np.searchsorted(s_sorted, taus, side="right") - np.searchsorted(e_sorted, taus, side="right")
        mu, var = Nt.mean(axis=0), Nt.var(axis=0, ddof=1)
        ratios.append(np.where(mu > 0, var / np.where(mu > 0, mu, 1), np.nan))
    Rm = np.nanmean(np.array(ratios), axis=0)
    D = pd.read_csv(root / "results" / "phase1" / "p1_4_dispersion_all_sessions_v1.csv")
    disp = pd.DataFrame({"slot": range(48), "time": [f"{k // 2:02d}:{30 * (k % 2):02d}" for k in range(48)],
                         "model_var_over_mean": Rm, "data_var_over_mean": D.var_over_mean.values})
    disp.to_csv(out / "vv_v2_dispersion.csv", index=False)
    S["V11_dispersion"] = dict(model_mean_ratio=float(np.nanmean(Rm)), model_range=[float(np.nanmin(Rm)), float(np.nanmax(Rm))],
                               data_mean_ratio=float(D.var_over_mean.mean()),
                               data_range=[float(D.var_over_mean.min()), float(D.var_over_mean.max())],
                               data_slots_under_bonferroni=7, data_slots_under_5pct=19)
    (out / "vv_v2_summary.json").write_text(json.dumps(S, indent=1, default=float))
    print(json.dumps(S, indent=1, default=float))


if __name__ == "__main__":
    main()
