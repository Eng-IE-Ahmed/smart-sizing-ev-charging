# Data

**Source:** Caltech ACN-Data, Caltech parking garage site (`caltech`), https://ev.caltech.edu/dataset
**Citation:** Lee, Z. J., Li, T., & Low, S. H. (2019). ACN-Data: Analysis and applications of an open EV charging
dataset. *Proceedings of the Tenth ACM International Conference on Future Energy Systems (e-Energy '19)*, 139-149.
https://doi.org/10.1145/3307772.3328313

The data belong to Caltech ACN-Data and are redistributed unchanged for reproducibility. They are **not** covered by the
MIT licence of the code.

| Item | Value |
|---|---|
| File | `raw/acn_caltech_2019-03-01_2019-05-31.json` (unchanged API extract) |
| Window | 1 March 2019 - 31 May 2019, Pacific local time (America/Los_Angeles) |
| Sessions | 2,953 in total; 2,577 on weekdays |
| Weekdays | 65 |
| Fields used | `connectionTime`, `disconnectTime`, `doneChargingTime`, `kWhDelivered`, `spaceID`, `stationID` |
| Derived inputs | `derived/` - 48 half-hour arrival rates (pooled weekdays and design day), (arrival, stay) pairs by band |

**Download script:** `06_Code/scripts/fetch_acn_sessions.py` downloads the same window from the ACN API. It needs your
own free ACN API token, read from the environment variable `ACN_API_TOKEN`; no token is stored in this repository.

See also `raw/SOURCE.md` for the request details.
