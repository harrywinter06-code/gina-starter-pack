#!/usr/bin/env python3
"""Pull the REAL settled-outcome + pre-resolution-price dataset for the FLB backtest.

Universe = the strategy's actual universe: resolved Polymarket negRisk multi-outcome
events (elections, sports champions, Fed, etc.). For each constituent we record the
YES price at 24h / 72h / 168h BEFORE resolution (clean, pre-result, from the CLOB
prices-history endpoint) paired with the actual settled outcome. This is the dataset
that confirms or refutes favourite-longshot bias: does the longshot tail resolve YES
LESS often than its pre-resolution price implied?

Run locally (this machine has curl + network; the Gina sandbox does not).
Output: flb_dataset.json
"""
import json, subprocess, time, datetime

GAMMA = "https://gamma-api.polymarket.com/events"
HIST = "https://clob.polymarket.com/prices-history"
MAX_EVENTS = 320            # resolved negRisk events to scan
MAX_HISTORY_CALLS = 6000    # per-token history-fetch budget; sized so >=137 distinct
                            # events yield usable rows (prior 3200 cut at 107 distinct).
WINDOW_DAYS = 9
HORIZONS_H = [24, 72, 168]
TOL_H = 18                  # accept nearest history point within this many hours of target


def curl(url):
    # Capture raw bytes and decode UTF-8 ourselves; subprocess text mode uses the
    # Windows ANSI codepage (cp1252) and chokes on UTF-8 bytes in the API payloads.
    try:
        out = subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0", url],
                             capture_output=True, timeout=40)
        text = out.stdout.decode("utf-8", "replace").strip()
        return json.loads(text) if text else None
    except Exception:
        return None


def parse_end_ts(ev):
    for k in ("endDate", "closedTime", "umaEndDate"):
        v = ev.get(k)
        if not v:
            continue
        try:
            return int(datetime.datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
        except Exception:
            continue
    return None


def first_token(m):
    raw = m.get("clobTokenIds")
    if not raw:
        return None
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
        return str(arr[0]) if arr else None
    except Exception:
        return None


def outcome_yes(m):
    raw = m.get("outcomePrices")
    if not raw:
        return None
    try:
        arr = json.loads(raw) if isinstance(raw, str) else raw
        # YES is index 0; resolved markets are "1"/"0"
        return 1 if str(arr[0]).strip() in ("1", "1.0") else 0
    except Exception:
        return None


def price_at(history, end_ts, hrs):
    if not history:
        return None
    tgt = end_ts - hrs * 3600
    best = min(history, key=lambda x: abs(x["t"] - tgt))
    if abs(best["t"] - tgt) > TOL_H * 3600:
        return None
    return float(best["p"])


def main():
    # Collect resolved negRisk multi-outcome events, paginating by volume.
    events = []
    offset = 0
    while len(events) < MAX_EVENTS:
        batch = curl(f"{GAMMA}?closed=true&limit=100&offset={offset}&order=volume&ascending=false")
        if not batch:
            break
        for ev in batch:
            mk = ev.get("markets") or []
            if ev.get("negRisk") and len(mk) >= 4:
                events.append(ev)
        offset += 100
        if len(batch) < 100 or offset > 4000:
            break
        time.sleep(0.1)
    print(f"resolved negRisk events collected: {len(events)} (cap {MAX_EVENTS})")
    events = events[:MAX_EVENTS]

    rows = []
    calls = 0
    ei = -1  # last processed event index; -1 if the event list came back empty
    for ei, ev in enumerate(events):
        end_ts = parse_end_ts(ev)
        if not end_ts:
            continue
        start_ts = end_ts - WINDOW_DAYS * 86400
        for m in (ev.get("markets") or []):
            if calls >= MAX_HISTORY_CALLS:
                break
            tok = first_token(m)
            oy = outcome_yes(m)
            if tok is None or oy is None:
                continue
            calls += 1
            hist = curl(f"{HIST}?market={tok}&startTs={start_ts}&endTs={end_ts}&fidelity=180")
            h = hist.get("history") if isinstance(hist, dict) else hist
            if not h:
                continue
            row = {
                "event": ev.get("slug", "?"),
                "name": (m.get("groupItemTitle") or m.get("question", "?"))[:60],
                "outcome_yes": oy,
                "end_ts": end_ts,
            }
            ok = False
            for hh in HORIZONS_H:
                p = price_at(h, end_ts, hh)
                row[f"p_{hh}h"] = p
                if p is not None:
                    ok = True
            if ok:
                rows.append(row)
            time.sleep(0.05)
        if calls >= MAX_HISTORY_CALLS:
            print(f"hit history-call budget at event {ei}")
            break
        if ei % 10 == 0:
            print(f"  event {ei}/{len(events)} | rows={len(rows)} | calls={calls}")

    # `events` must report the events the backtest can actually analyse — i.e. those with
    # >=1 usable row — NOT the number scanned/collected. The prior code wrote len(events)
    # (the collected list, capped at MAX_EVENTS) which over-reported by ~2x and seeded the
    # bogus "137"/"220" event counts in the docs. Count distinct event slugs present in rows.
    distinct_events = len({r["event"] for r in rows})
    with open("flb_dataset.json", "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "events": distinct_events,
                   "events_scanned": len(events), "events_processed": ei + 1,
                   "history_calls": calls, "horizons_h": HORIZONS_H}, fh)
    print(f"DONE: {len(rows)} constituent rows from {distinct_events} distinct resolved "
          f"negRisk events ({len(events)} scanned, {ei + 1} processed, {calls} history calls)")


if __name__ == "__main__":
    main()
