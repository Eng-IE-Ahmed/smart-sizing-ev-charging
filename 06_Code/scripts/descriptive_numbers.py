""" descriptive numbers from the session data for the full-length article (paper_full/).

Reads the raw ACN-Data file read-only through the project set-up (scripts/experiments.setup: Pacific local time,
weekday flag, stays, charge-completion times). Computes the descriptive statistics quoted in the article and in its
Table 2 / Figures 3, 5, 7. No randomness.
Outputs (paper_full/data/): descriptive_numbers.json, d9_band_stats.csv, d9_idle_hist.csv, d9_hour_stats.csv.
Usage: python scripts/descriptive_numbers.py --project .
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    root = Path(ap.parse_args().project).resolve()
    out = root / "paper_full" / "data"
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("p3", root / "scripts" / "experiments.py")
    p3 = importlib.util.module_from_spec(spec)
    sys.modules["p3"] = p3
    spec.loader.exec_module(p3)
    p3.setup(str(root))
    ev, df = p3.G["ev"], p3.G["df"]
    items = json.loads((root / "data" / "raw" / "acn_caltech_2019-03-01_2019-05-31.json").read_text())["_items"]
    raw = pd.DataFrame({"conn": [i["connectionTime"] for i in items], "kwh": [i.get("kWhDelivered") for i in items]})
    raw["conn"] = pd.to_datetime(raw.conn, format="%a, %d %b %Y %H:%M:%S GMT", utc=True).dt.tz_convert(
        "America/Los_Angeles").dt.tz_localize(None)
    raw = raw.sort_values("conn", kind="stable").reset_index(drop=True)
    assert (raw.conn.values == df.conn.values).all()
    df = df.assign(kwh=raw.kwh.astype(float).values)

    # occupancy over all sessions (censoring check)
    t = np.concatenate([df.conn.values.astype("datetime64[s]").astype(float), df.disc.values.astype("datetime64[s]").astype(float)])
    e = np.concatenate([np.ones(len(df)), -np.ones(len(df))])
    o = np.lexsort((e, t))
    max_occ = int(np.cumsum(e[o]).max())

    W = df[df.weekday].copy()
    days = W.date.nunique()
    daily = W.groupby("date").size()
    W["band"] = ev.band_of(W.hr.values)
    ok = W.done.notna() & (W.charge_h > 0) & (W.done <= W.disc)
    W["idle_share"] = np.where(ok, 1 - W.charge_h / W.dur, np.nan)
    Wp = W[ok]

    rows = []
    for b, lab in enumerate(ev.BAND_LABELS):
        x = W[W.band == b]
        xp = Wp[Wp.band == b]
        rows.append(dict(band=lab, sessions=len(x), share_of_arrivals=len(x) / len(W), stay_mean_h=x.dur.mean(),
                         stay_median_h=x.dur.median(), stay_sd_h=x.dur.std(), stay_p90_h=x.dur.quantile(0.9),
                         stays_gt24h=int((x.dur > 24).sum()), valid_pairs=len(xp), charge_mean_h=xp.charge_h.mean(),
                         idle_mean_h=(xp.dur - xp.charge_h).mean(), idle_share_agg=1 - xp.charge_h.sum() / xp.dur.sum(),
                         kwh_mean=x.kwh.mean()))
    B = pd.DataFrame(rows)
    B.to_csv(out / "d9_band_stats.csv", index=False)

    H = W.groupby("hr").agg(sessions=("dur", "size"), stay_mean_h=("dur", "mean"), stay_median_h=("dur", "median")).reset_index()
    H["arrivals_per_weekday"] = H.sessions / days
    H.to_csv(out / "d9_hour_stats.csv", index=False)

    edges = np.linspace(0, 1, 21)
    cnt, _ = np.histogram(Wp.idle_share.clip(0, 1), bins=edges)
    pd.DataFrame(dict(lo=edges[:-1], hi=edges[1:], sessions=cnt)).to_csv(out / "d9_idle_hist.csv", index=False)

    N = dict(sessions_total=int(len(df)), weekday_sessions=int(len(W)), weekend_or_holiday_sessions=int(len(df) - len(W)),
             weekdays=int(days), arrivals_per_weekday_mean=float(daily.mean()), arrivals_per_weekday_sd=float(daily.std()),
             arrivals_per_weekday_min=int(daily.min()), arrivals_per_weekday_max=int(daily.max()),
             stay_mean_h=float(W.dur.mean()), stay_median_h=float(W.dur.median()), stay_sd_h=float(W.dur.std()),
             stays_gt24h=int((W.dur > 24).sum()), stay_max_h=float(W.dur.max()),
             kwh_mean=float(W.kwh.mean()), kwh_median=float(W.kwh.median()),
             valid_pairs=int(len(Wp)), charge_mean_h=float(Wp.charge_h.mean()), idle_mean_h=float((Wp.dur - Wp.charge_h).mean()),
             aggregate_idle_share=float(1 - Wp.charge_h.sum() / Wp.dur.sum()), median_session_idle_share=float(Wp.idle_share.median()),
             share_sessions_idle_over_half=float((Wp.idle_share > 0.5).mean()),
             max_occupancy_all_sessions=max_occ, peak_arrival_hour=int(H.loc[H.sessions.idxmax(), "hr"]),
             share_arrivals_05_11=float(W.band.isin([0, 1, 2]).mean()))
    (out / "descriptive_numbers.json").write_text(json.dumps(N, indent=1))
    print(json.dumps(N, indent=1))
    print(B.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
