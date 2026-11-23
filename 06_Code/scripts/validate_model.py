"""Phase 1R / R4 - operational validation with pre-written criteria, for all 5 service models.

At m = 1.0, c = 52, replications r = 1..R (CRN streams of the engine), data = ALL sessions (any day, any length)
present on the 65 weekdays:
  * Welch 95% CI of (model - data) for: cars per weekday, mean occupancy (exact time integral / 24 h),
    occupancy at 12:00, daily peak occupancy (exact, event based). Model unit = replication mean over its 65 days;
    data unit = one weekday.
  * Two-sample KS on the daily peak: all model days (R x 65) vs the 65 data days (primary, exact peak);
    also the reviewer's definition (peak over the 48 half-hour points, reps 1..20) for reproduction.
  * Occupancy profile at the 48 half-hour points with 95% t-bands (data: over days; model: over replications).
  PASS = every Welch CI contains 0 AND primary KS p > 0.05.

Usage (from the project root):
  python scripts/validate_model.py --json data/raw/acn_caltech_2019-03-01_2019-05-31.json --engine engine/ev_des_engine.py \
      --out results/phase1r --fig figures/phase1r --reps 60
Seeds: engine CRN default_rng([r,1]) / ([r,2]); fitted service models random_state = 20261114 (engine SEED).
Output: validation_v2.csv, validation_v2_profile.csv, validation_v2_model_reps.csv, validation_v2_data_days.csv,
        figure r4_validation_profile.png.
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from p1r_common import T0, fifo, load_engine, plt, savefig, weekdays, welch  # noqa: E402


def day_metrics(s, e, days):
    """Per day [D, D+24h): mean occupancy (exact integral / 24), occupancy at 12:00, exact peak occupancy."""
    rows = []
    for D in days:
        ov = np.clip(np.minimum(e, D + 24) - np.maximum(s, D), 0, None).sum() / 24
        noon = int(((s <= D + 12) & (e > D + 12)).sum())
        n0 = int(((s <= D) & (e > D)).sum())
        ins, outs = (s > D) & (s < D + 24), (e > D) & (e < D + 24)
        ts = np.concatenate([s[ins], e[outs]])
        dl = np.concatenate([np.ones(ins.sum()), -np.ones(outs.sum())])
        order = np.lexsort((dl, ts))            # departures (-1) before arrivals at equal times
        peak = max(n0, int(n0 + np.cumsum(dl[order]).max())) if len(ts) else n0
        rows.append((ov, noon, peak))
    return np.array(rows)


def slot_counts(s, e, days):
    """Occupancy N(t) at the 48 half-hour slot starts of each day -> (ndays, 48)."""
    tau = np.array(days)[:, None] + np.arange(48)[None, :] * 0.5
    return ((s[None, None, :] <= tau[..., None]) & (e[None, None, :] > tau[..., None])).sum(-1)


def main():
    ap = argparse.ArgumentParser()
    for k in ["json", "engine", "out", "fig"]:
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--reps", type=int, default=60)
    a = ap.parse_args()
    out, fig = Path(a.out), Path(a.fig)
    out.mkdir(parents=True, exist_ok=True), fig.mkdir(parents=True, exist_ok=True)
    ev = load_engine(a.engine, a.json)
    df = ev.load()
    rates, A, B = ev.inputs(df)
    wd = weekdays(ev)
    D = [(d - T0).total_seconds() / 3600 for d in wd]
    s_h = ((df.conn - T0).dt.total_seconds() / 3600).values
    e_h = ((df.disc - T0).dt.total_seconds() / 3600).values
    dm = day_metrics(s_h, e_h, D)
    cars = df[df.weekday].groupby("date").size().reindex([d.date() for d in wd], fill_value=0).values
    sc = slot_counts(s_h, e_h, D)
    data = pd.DataFrame({"date": [d.date() for d in wd], "cars": cars, "mean_occ": dm[:, 0], "occ_1200": dm[:, 1],
                         "peak_occ": dm[:, 2], "peak_halfhour": sc.max(1)})
    data.to_csv(out / "validation_v2_data_days.csv", index=False)

    rows, rep_rows = [], []
    dmean, dhw = sc.mean(0), stats.t.ppf(0.975, 64) * sc.std(0, ddof=1) / np.sqrt(65)
    prof = {"data": (dmean, dhw)}
    mdays = [24 * d for d in range(65)]
    for name in ev.SERVICES:
        t0 = time.time()
        model = ev.ServiceModel(name, df)
        reps, peaks, peaks_hh20, P = [], [], [], []
        for r in range(1, a.reps + 1):
            o, arr, svc, _ = ev.replicate(rates, A, B, 52, r, 1.0, model=model)
            st = fifo(arr, svc, 52)
            m3 = day_metrics(st, st + svc, mdays)
            scm = slot_counts(st, st + svc, mdays)
            reps.append((r, len(arr) / 65, *m3.mean(0)))
            peaks.append(m3[:, 2])
            if r <= 20:
                peaks_hh20.append(scm.max(1))
            P.append(scm.mean(0))
        R = pd.DataFrame(reps, columns=["rep", "cars", "mean_occ", "occ_1200", "peak_occ"]).assign(service=name)
        rep_rows.append(R)
        res = {}
        for met in ["cars", "mean_occ", "occ_1200", "peak_occ"]:
            w = welch(R[met], data[met])
            res[met] = w["contains0"]
            rows.append(dict(service=name, test="Welch CI model-data", metric=met, model_mean=R[met].mean(),
                             data_mean=data[met].mean(), diff=w["diff"], lo=w["lo"], hi=w["hi"], ok=w["contains0"]))
        pk, pk20 = np.concatenate(peaks), np.concatenate(peaks_hh20)
        ks = stats.ks_2samp(pk, data.peak_occ)
        ks2 = stats.ks_2samp(pk20, data.peak_halfhour)
        rows.append(dict(service=name, test="KS 2-sample (primary)", metric=f"daily peak exact, {a.reps} reps x 65 days",
                         model_mean=pk.mean(), data_mean=data.peak_occ.mean(), stat=ks.statistic, p=ks.pvalue,
                         ok=ks.pvalue > 0.05))
        rows.append(dict(service=name, test="KS 2-sample (reviewer def.)", metric="daily peak half-hour, 20 reps x 65 days",
                         model_mean=pk20.mean(), data_mean=data.peak_halfhour.mean(), stat=ks2.statistic, p=ks2.pvalue,
                         ok=ks2.pvalue > 0.05))
        P = np.array(P)
        pm, phw = P.mean(0), stats.t.ppf(0.975, a.reps - 1) * P.std(0, ddof=1) / np.sqrt(a.reps)
        prof[name] = (pm, phw)
        rmse = float(np.sqrt(np.mean((pm - dmean) ** 2)))
        rows.append(dict(service=name, test="profile", metric="RMSE of 48 half-hour means (model_mean/data_mean = max)",
                         model_mean=pm.max(), data_mean=dmean.max(), stat=rmse))
        passed = bool(all(res.values()) and ks.pvalue > 0.05)
        rows.append(dict(service=name, test="OVERALL", metric="all Welch CIs contain 0 and primary KS p > 0.05", ok=passed))
        print(f"{name:9s} {'PASS' if passed else 'FAIL'}  KS p={ks.pvalue:.3f} (rev. def. {ks2.pvalue:.3f}) "
              f"Welch {res}  RMSE {rmse:.2f}  {time.time() - t0:.0f}s", flush=True)
    V = pd.DataFrame(rows)
    V.to_csv(out / "validation_v2.csv", index=False)
    pd.concat(rep_rows).to_csv(out / "validation_v2_model_reps.csv", index=False)
    pr = pd.DataFrame({"slot": range(48), "time": [f"{k // 2:02d}:{30 * (k % 2):02d}" for k in range(48)]})
    for k, (m, h) in prof.items():
        pr[f"{k}_mean"], pr[f"{k}_hw95"] = m, h
    pr.to_csv(out / "validation_v2_profile.csv", index=False)
    pd.set_option("display.width", 250)
    print(V[V.test != "OVERALL"].round(4).to_string(index=False))

    f, axs = plt.subplots(1, 5, figsize=(20, 3.8), sharey=True)
    x = np.arange(48) / 2
    for axi, name in zip(axs, ev.SERVICES):
        axi.fill_between(x, dmean - dhw, dmean + dhw, color="#BDBDBD", alpha=0.7, label="data 95% CI")
        axi.plot(x, dmean, "k-", lw=1, label="data mean (65 weekdays)")
        m, h = prof[name]
        axi.fill_between(x, m - h, m + h, color="#9DC3E6", alpha=0.7)
        axi.plot(x, m, "-", color="#1F4E78", lw=1, label=f"model ({a.reps} reps) 95% CI")
        ok = V[(V.service == name) & (V.test == "OVERALL")].ok.iloc[0]
        axi.set(title=f"{name}: {'PASS' if ok else 'FAIL'}", xlabel="hour of day", xticks=range(0, 25, 4))
    axs[0].set_ylabel("chargers occupied")
    axs[0].legend(fontsize=7)
    savefig(f, fig / "r4_validation_profile.png")


if __name__ == "__main__":
    main()
