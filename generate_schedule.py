#!/usr/bin/env python3
import urllib.request, urllib.parse, json, datetime, sys, os

ALIAS     = os.environ["POCARR_LOGIN"]
PASSWORD  = os.environ["POCARR_PASSWORD"]
TZ_OFFSET = 2  # UTC+2

NETWORKS = {
    "GG":      ("gg ",  "USD", 20,  100),
    "Winamax": ("win",  "EUR", 15,  300),
}

def fetch(net):
    params = urllib.parse.urlencode({
        "alias": ALIAS, "password": PASSWORD,
        "network": net, "time": "86400"
    })
    url = f"https://gs.pocarr.com/api/tour?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)

SKIP_FLAGS = {"SAT", "R", "DN", "BJ", "HIT"}

def flags_to_type(flags_str):
    f = set(flags_str.split(",")) if flags_str else set()
    if f & SKIP_FLAGS:
        return None          # пропустити
    has_b  = bool(f & {"B", "K"})
    has_t  = "T"  in f
    has_st = "ST" in f
    has_mb = "MB" in f
    if has_mb:            return "m"
    if has_b and has_st:  return "hko"
    if has_b and has_t:   return "tko"
    if has_b:             return "ko"
    if has_st:            return "hy"
    return ""               # звичайний фріз

def fmt_gtd(gtd):
    g = int(float(gtd)) if gtd else 0
    if g <= 0: return ""
    return f"{g // 1000}k g" if g >= 1000 else f"{g} g"

def fmt_buyin(buyin, curr):
    sym = "€" if curr == "EUR" else "$"
    v = int(round(buyin))
    return f"{sym}{v}"

def local_dt(ts):
    return datetime.datetime.utcfromtimestamp(int(ts)) + datetime.timedelta(hours=TZ_OFFSET)

def main():
    today     = datetime.datetime.utcnow() + datetime.timedelta(hours=TZ_OFFSET)
    day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = day_start + datetime.timedelta(days=1)

    rows = []
    for net, (label, want_curr, min_bi, max_bi) in NETWORKS.items():
        try:
            data = fetch(net)
        except Exception as e:
            print(f"# WARNING: {net}: {e}", file=sys.stderr)
            continue

        for t in data:
            try:
                stake = float(t.get("@stake") or 0)
                rake  = float(t.get("@rake")  or 0)
                buyin = stake + rake
                curr  = t.get("@currency", "")
                flags = t.get("@flags") or ""
                gtd   = t.get("@guarantee")
                ts    = int(t.get("@scheduledStartDate", 0))
                dt    = local_dt(ts)

                if curr != want_curr:          continue
                if not (min_bi <= buyin <= max_bi): continue
                if not (day_start <= dt < day_end): continue

                typ = flags_to_type(flags)
                if typ is None:                continue   # пропустити SAT/R тощо

                rows.append((dt, label, curr, buyin, typ, float(gtd) if gtd else 0))
            except Exception:
                continue

    rows.sort(key=lambda x: x[0])

    seen, unique = set(), []
    for row in rows:
        key = (row[0].strftime("%H:%M"), row[1], int(round(row[3])), row[4])
        if key not in seen:
            seen.add(key)
            unique.append(row)

    print(f"SCHEDULE {today.strftime('%d.%m.%Y')} (UTC+{TZ_OFFSET})\n")
    print("BEFORE CHECK NOTES + GOALS\n")

    prev_hour = None
    for dt, label, curr, buyin, typ, gtd in unique:
        if prev_hour is not None and dt.hour != prev_hour:
            print()
        prev_hour = dt.hour
        parts = [dt.strftime("%H-%M"), label, fmt_buyin(buyin, curr)]
        if typ:
            parts.append(typ)
        g = fmt_gtd(gtd)
        if g:
            parts.append(g)
        print("  ".join(parts))

if __name__ == "__main__":
    main()
