#!/usr/bin/env python3
import urllib.request, urllib.parse, json, datetime, sys, os

ALIAS    = os.environ["POCARR_LOGIN"]
PASSWORD = os.environ["POCARR_PASSWORD"]
TZ_OFFSET = 2  # UTC+2

def fetch(network):
    params = urllib.parse.urlencode({"alias": ALIAS, "password": PASSWORD, "network": network, "time": "86400"})
    url = f"https://gs.pocarr.com/api/tour?{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)

def is_satellite(name, network):
    n = (name or "").lower()
    if network == "GG":
        return (" seats" in n or "seats " in n or " seat" in n or "seat " in n or
                " qualifier" in n or "qualifier " in n or " step" in n or "step " in n or
                (" sat" in n and " satu" not in n) or "sat  " in n)
    if network == "Winamax":
        return ((" sat" in n and " satu" not in n) or "sat  " in n or
                "satellite" in n or "package" in n or "qualif" in n or
                "last chance" in n or "hit&run" in n)
    return False

def flags_to_type(flags):
    f = set(flags.split(",")) if flags else set()
    has_b  = "B"  in f
    has_t  = "T"  in f
    has_st = "ST" in f
    has_mb = "MB" in f
    if has_mb:            return "m"
    if has_b and has_st:  return "hko"
    if has_b and has_t:   return "tko"
    if has_b:             return "ko"
    if has_st:            return "hy"
    return ""

def fmt_gtd(gtd):
    g = int(gtd)
    if g <= 0: return ""
    if g >= 1000:
        k = g // 1000
        return f"{k}k g"
    return f"{g} g"

def fmt_buyin(buyin, curr):
    sym = "$" if curr == "USD" else "€"
    v = int(round(buyin))
    return f"{sym}{v}"

def ts_to_local(ts):
    dt = datetime.datetime.utcfromtimestamp(int(ts)) + datetime.timedelta(hours=TZ_OFFSET)
    return dt

def net_label(net):
    if "GG" in net:      return "gg "
    if "Winamax" in net: return "win"
    return net[:3].lower()

def main():
    now_utc = datetime.datetime.utcnow()
    today_local = now_utc + datetime.timedelta(hours=TZ_OFFSET)
    day_start = today_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = day_start + datetime.timedelta(days=1, hours=1)  # include 00:xx

    all_tours = []
    for net in ["GG", "Winamax"]:
        try:
            all_tours += fetch(net)
        except Exception as e:
            print(f"# WARNING: failed to fetch {net}: {e}", file=sys.stderr)

    rows = []
    for t in all_tours:
        try:
            name  = t.get("@name", "") or ""
            net   = t.get("@network", "")
            stake = float(t.get("@stake", 0) or 0)
            rake  = float(t.get("@rake",  0) or 0)
            buyin = stake + rake
            curr  = t.get("@currency", "USD")
            flags = t.get("@flags", "") or ""
            gtd   = float(t.get("@guarantee", 0) or 0)
            ts    = t.get("@scheduledStartDate", 0)

            netlbl = net_label(net)

            dt = ts_to_local(ts)
            if not (day_start <= dt < day_end):
                continue

            flag_set = set(flags.split(",")) if flags else set()
            if flag_set & {"SAT", "R", "DN"}:
                continue

            if is_satellite(name, "GG" if "GG" in net else "Winamax"):
                continue

            if curr == "USD" and not (20 <= buyin <= 100):
                continue
            if curr == "EUR" and not (15 <= buyin <= 300):
                continue
            if curr not in ("USD", "EUR"):
                continue

            typ = flags_to_type(flags)
            rows.append((dt, netlbl, curr, buyin, typ, gtd))
        except Exception:
            continue

    rows.sort(key=lambda x: x[0])

    seen = set()
    unique = []
    for row in rows:
        key = (row[0].strftime("%H:%M"), row[1], int(round(row[3])), row[4])
        if key not in seen:
            seen.add(key)
            unique.append(row)

    print(f"SCHEDULE {today_local.strftime('%d.%m.%Y')} (UTC+{TZ_OFFSET})")
    print()
    print("BEFORE CHECK NOTES + GOALS")
    print()

    prev_hour = None
    for dt, netlbl, curr, buyin, typ, gtd in unique:
        h = dt.hour
        if prev_hour is not None and h != prev_hour:
            print()
        prev_hour = h

        time_str  = dt.strftime("%H-%M")
        buyin_str = fmt_buyin(buyin, curr)
        gtd_str   = fmt_gtd(gtd)

        parts = [time_str, netlbl, buyin_str]
        if typ:
            parts.append(typ)
        if gtd_str:
            parts.append(gtd_str)

        print("  ".join(parts))

if __name__ == "__main__":
    main()
