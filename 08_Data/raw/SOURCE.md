# Source of the raw data

**File:** `acn_caltech_2019-03-01_2019-05-31.json` (read-only — never edit; derived data go to `data/derived/`)

| Item | Value |
|---|---|
| Dataset | ACN-Data (Adaptive Charging Network), Caltech EV charging sessions |
| Citation | Lee, Z.J., Li, T., Low, S.H. (2019). ACN-Data: Analysis and Applications of an Open EV Charging Dataset. *Proceedings of the Tenth ACM International Conference on Future Energy Systems (e-Energy '19)*, 139–149. doi:10.1145/3307772.3328313 *(DOI verified 2026-11-14: it is the CrossRef link of ref. [20] in Király et al. 2026, `reference/sustainability-18-08695.pdf`, p. 35)* |
| Dataset page | https://ev.caltech.edu/dataset |
| API endpoint | `https://ev.caltech.edu/api/v1/sessions/caltech` (token as basic-auth user; the token is never stored in this project) |
| Query | site = `caltech`; local dates 2019-03-01 to 2019-05-31 inclusive (America/Los_Angeles); `where = connectionTime>="Fri, 01 Mar 2019 08:00:00 GMT" and connectionTime<"Sat, 01 Jun 2019 07:00:00 GMT"`; `sort = connectionTime`; all pages followed via `_links.next` |
| Script | `scripts/fetch_acn_sessions.py` (defaults reproduce this query; refuses to save if the count ≠ server `_meta.total`) |
| Downloaded | 2026-11-11 04:00:55 UTC (`fetched_at_utc` inside the file) |
| Sessions | **2,953** (`count` in the file = server total) |
| Stations | 52 distinct `stationID`; one site (`siteID` 0002); `timezone` = America/Los_Angeles for every session |
| First / last connection (local) | 2019-03-01 06:24:58 PST / 2019-05-31 21:32:23 PDT |
| File size | 2,650,694 bytes |
| **SHA-256** | `8cb3624fefb4abd14fe243ad843a5982f1b609d5e5f23140d33f16a9a9757567` (re-checked 2026-11-14: match) |

**File structure:** top level `site`, `range_local {start, end_inclusive, timezone}`, `fetched_at_utc`, `count`, `_items`.
Each item has: `_id, clusterID, connectionTime, disconnectTime, doneChargingTime, kWhDelivered, sessionID, siteID, spaceID, stationID, timezone, userID, userInputs`. Times are RFC-1123 GMT strings (e.g. `Fri, 01 Mar 2019 08:00:00 GMT`); convert to America/Los_Angeles before any time-of-day use.

**Check the hash:** `sha256sum data/raw/acn_caltech_2019-03-01_2019-05-31.json` (or `Get-FileHash -Algorithm SHA256` in PowerShell).
