"""Fetch every ACN-Data charging session for one site and date range.

Token: set the ACN_API_TOKEN env var, or put the token alone in acn_token.txt
next to this script. Get one at https://ev.caltech.edu/register.

Usage:  python fetch_acn_sessions.py [--site caltech] [--start 2019-03-01] [--end 2019-05-31]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

BASE_URL = "https://ev.caltech.edu/api/v1/"
SITE_TZ = ZoneInfo("America/Los_Angeles")  # ACN sites are in California
HERE = Path(__file__).resolve().parent


def load_token() -> str:
    token = os.environ.get("ACN_API_TOKEN", "").strip()
    token_file = HERE / "acn_token.txt"
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit("No API token. Set ACN_API_TOKEN or create acn_token.txt (see docstring).")
    return token


def gmt(dt: datetime) -> str:
    """Format as the RFC-1123 GMT string the Eve API expects in `where`."""
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def get_json(session: requests.Session, url: str, params=None, retries: int = 4) -> dict:
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, timeout=60)
            if r.status_code == 401:
                sys.exit("401 Unauthorized: the API token is invalid or not yet activated.")
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"  request failed ({e}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_sessions(token: str, site: str, start: datetime, end_excl: datetime) -> tuple[list[dict], int | None]:
    """Follow `_links.next` until the API stops returning one. Returns (items, server-reported total)."""
    s = requests.Session()
    s.auth = (token, "")  # ACN uses the token as basic-auth username, empty password
    where = f'connectionTime>="{gmt(start)}" and connectionTime<"{gmt(end_excl)}"'
    params = {"where": where, "sort": "connectionTime"}

    payload = get_json(s, BASE_URL + f"sessions/{site}", params=params)
    total = payload.get("_meta", {}).get("total")
    items: list[dict] = []
    page = 1
    while True:
        batch = payload.get("_items", [])
        items.extend(batch)
        print(f"  page {page}: +{len(batch)} (running {len(items)}" + (f" / {total})" if total else ")"))
        nxt = payload.get("_links", {}).get("next")
        if not nxt or not batch:
            break
        page += 1
        payload = get_json(s, BASE_URL + nxt["href"])
    return items, total


def parse_time(v):
    if not v:
        return None
    try:
        return parsedate_to_datetime(v)
    except (TypeError, ValueError):
        return None


def audit(items: list[dict]) -> list[str]:
    notes: list[str] = []
    n = len(items)

    ids = Counter(it.get("sessionID") or it.get("_id") for it in items)
    dups = {k: c for k, c in ids.items() if c > 1}
    if dups:
        notes.append(f"Duplicate sessionIDs: {len(dups)} (e.g. {list(dups)[:3]})")

    # Null / missing fields, per key
    keys = sorted({k for it in items for k in it})
    for k in keys:
        missing = sum(1 for it in items if it.get(k) in (None, ""))
        if missing:
            notes.append(f"Field '{k}' missing/null in {missing}/{n} sessions ({missing / n:.1%})")

    kwh = [it.get("kWhDelivered") for it in items]
    zero = sum(1 for v in kwh if v == 0)
    neg = sum(1 for v in kwh if isinstance(v, (int, float)) and v < 0)
    tiny = sum(1 for v in kwh if isinstance(v, (int, float)) and 0 < v < 0.1)
    big = [v for v in kwh if isinstance(v, (int, float)) and v > 100]
    if zero:
        notes.append(f"kWhDelivered == 0: {zero} sessions")
    if neg:
        notes.append(f"kWhDelivered < 0: {neg} sessions")
    if tiny:
        notes.append(f"kWhDelivered in (0, 0.1): {tiny} sessions (plugged in, barely charged)")
    if big:
        notes.append(f"kWhDelivered > 100: {len(big)} sessions (max {max(big):.1f})")

    bad_order = long_stay = done_after_disc = done_before_conn = 0
    for it in items:
        c, d, done = (parse_time(it.get(f)) for f in ("connectionTime", "disconnectTime", "doneChargingTime"))
        if c and d:
            if d <= c:
                bad_order += 1
            elif d - c > timedelta(hours=48):
                long_stay += 1
        if done and d and done > d:
            done_after_disc += 1
        if done and c and done < c:
            done_before_conn += 1
    if bad_order:
        notes.append(f"disconnectTime <= connectionTime: {bad_order} sessions")
    if long_stay:
        notes.append(f"Connected longer than 48h: {long_stay} sessions")
    if done_after_disc:
        notes.append(f"doneChargingTime after disconnectTime: {done_after_disc} sessions")
    if done_before_conn:
        notes.append(f"doneChargingTime before connectionTime: {done_before_conn} sessions")
    return notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="caltech")
    ap.add_argument("--start", default="2019-03-01", help="first local date (inclusive)")
    ap.add_argument("--end", default="2019-05-31", help="last local date (inclusive)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    start = datetime.fromisoformat(a.start).replace(tzinfo=SITE_TZ)
    end_excl = datetime.fromisoformat(a.end).replace(tzinfo=SITE_TZ) + timedelta(days=1)
    out = Path(a.out) if a.out else HERE / f"acn_{a.site}_{a.start}_{a.end}.json"

    print(f"Fetching {a.site} sessions, {start.isoformat()} -> {end_excl.isoformat()} (exclusive)")
    items, total = fetch_sessions(load_token(), a.site, start, end_excl)

    if total is not None and total != len(items):
        sys.exit(f"INCOMPLETE: server reports {total} sessions but {len(items)} were fetched. Not saving.")
    if len(items) <= 100:
        sys.exit(f"Only {len(items)} sessions fetched (expected > 100). Not saving.")

    items.sort(key=lambda it: parse_time(it.get("connectionTime")) or datetime.min.replace(tzinfo=timezone.utc))
    doc = {
        "site": a.site,
        "range_local": {"start": a.start, "end_inclusive": a.end, "timezone": str(SITE_TZ)},
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "_items": items,
    }
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    with tmp.open(encoding="utf-8") as f:  # validate before replacing the final file
        assert json.load(f)["count"] == len(items)
    tmp.replace(out)

    conn = [t for t in (parse_time(it.get("connectionTime")) for it in items) if t]
    print("\n===== RESULT =====")
    print(f"Total sessions      : {len(items)}" + (f" (server total {total})" if total is not None else ""))
    print(f"First connectionTime: {min(conn).astimezone(SITE_TZ)}  ({min(conn)} UTC)")
    print(f"Last  connectionTime: {max(conn).astimezone(SITE_TZ)}  ({max(conn)} UTC)")
    print(f"Saved               : {out}  ({out.stat().st_size / 1e6:.2f} MB, json.load OK)")
    print("\nMissing / anomalous values:")
    for n in audit(items) or ["none found"]:
        print(f"  - {n}")


if __name__ == "__main__":
    main()
