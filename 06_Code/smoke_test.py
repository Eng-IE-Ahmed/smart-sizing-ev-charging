"""Smoke test: re-run 5 replications of the engine at c = 45, m = 1.3 (pooled weekdays, band_long stays)
and compare with the stored replications in 07_Results/tables/phase3/p3_grid_reps.csv (common random numbers, so the
values should match exactly)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code" / "engine"))
import ev_des_engine as ev  # noqa: E402

df = ev.load(); rates, A, B = ev.inputs(df)
mod = ev.ServiceModel("band_long", df)
S = pd.read_csv(ROOT / "07_Results/tables/phase3/p3_grid_reps.csv")
S = S[(S.arrivals == "pooled") & np.isclose(S.m, 1.3) & (S.c == 45)].set_index("rep")
rows = []
for r in range(1, 6):
    o = ev.replicate(rates, A, B, 45, r, 1.3, model=mod)[0]
    rows.append(dict(rep=r, P15_new=o["P15"], P15_stored=S.loc[r, "P15"], Wq_new=o["Wq"], Wq_stored=S.loc[r, "Wq"]))
T = pd.DataFrame(rows)
print(T.to_string(index=False))
d = max((T.P15_new - T.P15_stored).abs().max(), (T.Wq_new - T.Wq_stored).abs().max())
print("max abs difference:", d)
sys.exit(0 if d < 1e-9 else 1)
