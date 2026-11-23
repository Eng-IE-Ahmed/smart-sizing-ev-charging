"""Phase 4 analytic benchmark: Mt/G/inf offered load, modified-offered-load (MOL) sizing, Erlang-C
approximation and comparison with the DES frontier. (4.4, the Excel sheet, is built by scripts/excel_analytic.py.)

4.1 m(t) = sum_b int_0^inf lambda_b(t - x) P(S_b > x) dx, b = the 6 band_long arrival bands (weekday rates of the 48
    half-hour slots, stays incl. > 24 h, empirical survival from the band pools), periodic over the day, 1-minute steps
    (circular convolution of the per-minute arrival rate with the survival function folded onto 1,440 minutes).
    Plotted with the data's mean occupancy (all sessions) and the DES (band_long, m = 1.0, c = 52) by half hour.
4.2 c_MOL(m, eps) = min{c : max_t P(Poisson(m m(t)) >= c) <= eps}, eps = 0.01 and 0.05; Erlang-C approximation:
    P15(t) = C(c, a_t) exp(-(c - a_t) tau / E[S]) for c > a_t (else 1), a_t = m m(t), tau = 0.25 h, E[S] = arrival-weighted
    mean stay; arrival-weighted average over t; c_EC(m) = min{c : P15 <= 1%}.
4.3 table c_MOL / c_EC vs DES c*(m) (results/phase3/p3_frontier.csv), m = 1.0..2.0.
Usage: python scripts/analytic_benchmarks.py --project .
Output: results/phase4/p4_offered_load_1min.csv, p4_offered_load_15min.csv, p4_mol_vs_des.csv, p4_summary.json;
        figures/phase4/p4_offered_load.png, p4_mol_vs_des.png. No randomness.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def load_engine(root):
    spec = importlib.util.spec_from_file_location("ev", root / "engine" / "ev_des_engine.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    ev.DATA = str(root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json")
    return ev


def offered_load(ev, df, rates):
    pools = ev.band_pools(df, long_stays=True)
    lam_min = np.repeat(rates, 30) / 30.0                       # arrivals per minute, minute of day 0..1439
    band_min = ev.band_of(np.arange(1440) // 60)
    xmax = int(math.ceil(max(p.max() for p in pools) * 60)) + 1
    x = np.arange(xmax) + 0.5                                   # minutes since arrival (mid-point)
    m = np.zeros(1440)
    for b, P in enumerate(pools):
        S = 1.0 - np.searchsorted(np.sort(P) * 60, x, side="right") / len(P)   # P(S_b > x)
        fold = np.zeros(1440)
        np.add.at(fold, np.arange(xmax) % 1440, S)
        lb = np.where(band_min == b, lam_min, 0.0)
        m += np.real(np.fft.ifft(np.fft.fft(lb) * np.fft.fft(fold)))         # circular convolution
    ES = float(sum(rates[k] * pools[ev.band_of(k // 2)].mean() for k in range(48)) / rates.sum())   # hours
    return np.maximum(m, 0.0), lam_min, ES


def erlang_c(c, a):
    if c <= a:
        return 1.0
    tail = stats.poisson.pmf(c, a) * c / (c - a)
    return tail / (stats.poisson.cdf(c - 1, a) + tail)


def sizing(mt, lam, ES, mult, eps_list=(0.01, 0.05), tau=0.25):
    a = mult * mt
    res = {}
    for eps in eps_list:
        res[f"c_MOL_eps{eps}"] = next(c for c in range(1, 400) if stats.poisson.sf(c - 1, a).max() <= eps)
    w = lam / lam.sum()
    for c in range(1, 400):
        p = np.array([erlang_c(c, ai) * (math.exp(-(c - ai) * tau / ES) if c > ai else 1.0) for ai in a])
        if (w * p).sum() <= 0.01:
            res["c_EC"] = c
            res["P15_EC_at_cEC"] = float((w * p).sum())
            break
    res["max_offered_load"] = float(a.max())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    a = ap.parse_args()
    root = Path(a.project)
    out, fig = root / "results" / "phase4", root / "figures" / "phase4"
    out.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    ev = load_engine(root)
    df = ev.load()
    rates, A, B = ev.inputs(df)
    mt, lam, ES = offered_load(ev, df, rates)
    pd.DataFrame({"minute": range(1440), "time": [f"{k // 60:02d}:{k % 60:02d}" for k in range(1440)], "lambda_per_min": lam,
                  "m_t": mt}).to_csv(out / "p4_offered_load_1min.csv", index=False)
    m15 = mt.reshape(96, 15).mean(1)
    lam15 = lam.reshape(96, 15).sum(1)
    pd.DataFrame({"q": range(96), "time": [f"{k // 4:02d}:{15 * (k % 4):02d}" for k in range(96)], "arrivals_per_15min": lam15,
                  "m_t_mean15": m15}).to_csv(out / "p4_offered_load_15min.csv", index=False, float_format="%.12g")
    PR = pd.read_csv(root / "results" / "phase1r" / "validation_v2_profile.csv")
    f, ax = plt.subplots(figsize=(9, 4))
    ax.plot(np.arange(1440) / 60, mt, color="k", lw=1.5, label="Mt/G/inf offered load m(t) (analytic)")
    ax.plot(np.arange(48) / 2, PR.data_mean, "o", ms=3, color="#C55A11", label="data: mean occupancy (all sessions)")
    ax.plot(np.arange(48) / 2, PR.band_long_mean, "s", ms=3, color="#1F4E78", label="DES band_long (m = 1.0, c = 52)")
    ax.set(xlabel="hour of day", ylabel="chargers occupied", title="Offered load m(t) vs data and DES", xticks=range(0, 25, 3))
    ax.legend(fontsize=8)
    f.tight_layout()
    f.savefig(fig / "p4_offered_load.png", dpi=300)
    plt.close(f)
    half = mt.reshape(48, 30)[:, 0]
    fit = dict(rmse_vs_data=float(np.sqrt(np.mean((half - PR.data_mean.values) ** 2))),
               rmse_vs_des=float(np.sqrt(np.mean((half - PR.band_long_mean.values) ** 2))), max_m_t=float(mt.max()),
               t_of_max=f"{int(np.argmax(mt)) // 60:02d}:{int(np.argmax(mt)) % 60:02d}", mean_m_t=float(mt.mean()),
               little_check_lambda_ES=float(lam.sum() * ES * 60 / 1440), ES_hours=ES)
    F = pd.read_csv(root / "results" / "phase3" / "p3_frontier.csv")
    rows = []
    for i in range(11):
        mult = round(1.0 + 0.1 * i, 1)
        s = sizing(mt, lam, ES, mult)
        d = F[(F.arrivals == "pooled") & np.isclose(F.m, mult)].iloc[0]
        rows.append(dict(m=mult, DES_c_star=d.c_star, DES_c_star_lower=d.c_star_lower, **s,
                         err_MOL01=s["c_MOL_eps0.01"] - d.c_star, err_MOL05=s["c_MOL_eps0.05"] - d.c_star, err_EC=s["c_EC"] - d.c_star))
    T = pd.DataFrame(rows)
    T.to_csv(out / "p4_mol_vs_des.csv", index=False)
    print(T.to_string(index=False))
    fit.update(mean_abs_err_MOL01=float(T.err_MOL01.abs().mean()), mean_abs_err_MOL05=float(T.err_MOL05.abs().mean()),
               mean_abs_err_EC=float(T.err_EC.abs().mean()))
    (out / "p4_summary.json").write_text(json.dumps(fit, indent=1))
    print(json.dumps(fit, indent=1))
    f, ax = plt.subplots(figsize=(8, 4.5))
    ax.step(T.m, T.DES_c_star, where="mid", lw=2, color="#1F4E78", label="DES c*(m) (rule)")
    ax.plot(T.m, T["c_MOL_eps0.01"], "o--", color="#C55A11", label="MOL, eps = 1%")
    ax.plot(T.m, T["c_MOL_eps0.05"], "s--", color="#70AD47", label="MOL, eps = 5%")
    ax.plot(T.m, T.c_EC, "^-", color="#7030A0", label="Erlang-C approximation of P15 <= 1%")
    ax.set(xlabel="demand growth factor m", ylabel="chargers", title="Analytic sizing rules vs the DES frontier")
    ax.legend(fontsize=8)
    f.tight_layout()
    f.savefig(fig / "p4_mol_vs_des.png", dpi=300)
    plt.close(f)


if __name__ == "__main__":
    main()
