#!/usr/bin/env python3
import urllib.request, urllib.parse, json, datetime, sys, os

ALIAS    = os.environ["POCARR_LOGIN"]
PASSWORD = os.environ["POCARR_PASSWORD"]
TZ_OFFSET = 2  # UTC+2

def fetch(network):
    params = urllib.parse.urlencode({"alias": ALIAS, "password": PASSWORD, "network": network, "time": "0"})
    url = f"https://gs.pocarr.com/api/tour?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)

def flags_to_type(flags):
    f = set(flags.split(",")) if flags else set()
    if "MB" in f:                          return "m"
    if "B" in f and "ST" in f:             return "hko"
    if "B" in f and "T" in f:              return "tko"
    if "B" in f:                           return "ko"
    if "ST" in f:                          return "hy"
    return ""

def fmt_gtd(gtd):
    g = int(gtd)
    if g <= 0: return ""
    return f"{g // 1000}k g" if g >= 1000 else f"{g} g"

def fmt_buyin(buyin, curr):
    return f"{'$' if curr == 'USD' else '€'}{int(round(buyin))}"

def net_label(net):
    if "GG" in net:     return "gg "
    if "iPoker" in net: return "win"
    return net[:3].lower()

def main():
    all_tours = []
    for net in ["GG", "IP"]:
        try:
            all_tours += fetch(net)
        except Exception as e:
            print(f"# WARNING: failed {net}: {e}", file=sys.stderr)

    rows = []
    for t in all_tours:
        try:
            stake = float(t.get("@stake") or 0)
            rake  = float(t.get("@rake")  or 0)
            buyin = stake + rake
            curr  = t.get("@currency", "USD")
            flags = t.get("@flags", "") or ""
            gtd   = float(t.get("@guarantee") or 0)
            net   = t.get("@network", "")
            ts    = t.get("@scheduledStartDate", 0)

            skip = {"SAT", "R", "DN"}
            if skip & set(flags.split(",")):
                continue

            if curr == "USD" and not (20 <= buyin <= 100): continue
            if curr == "EUR" and not (15 <= buyin <= 300): continue

            dt = datetime.datetime.utcfromtimestamp(int(ts)) + datetime.timedelta(hours=TZ_OFFSET)
            rows.append((dt, net, curr, buyin, flags_to_type(flags), gtd))
        except Exception:
            continue

    rows.sort(key=lambda x: x[0])

    seen, unique = set(), []
    for row in rows:
        key = (row[0].strftime("%H:%M"), row[2], int(round(row[3])), row[4])
        if key not in seen:
            seen.add(key)
            unique.append(row)

    today = datetime.datetime.utcnow() + datetime.timedelta(hours=TZ_OFFSET)
    print(f"SCHEDULE {today.strftime('%d.%m.%Y')} (UTC+{TZ_OFFSET})\n")
    print("BEFORE CHECK NOTES + GOALS\n")

    prev_hour = None
    for dt, net, curr, buyin, typ, gtd in unique:
        if prev_hour is not None and dt.hour != prev_hour:
            print()
        prev_hour = dt.hour
        parts = [dt.strftime("%H-%M"), net_label(net), fmt_buyin(buyin, curr)]
        if typ: parts.append(typ)
        g = fmt_gtd(gtd)
        if g: parts.append(g)
        print("  ".join(parts))

if __name__ == "__main__":
    main()
