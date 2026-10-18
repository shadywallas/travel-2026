"""Turn per-city climate averages (data/climate.json) into the weather fields in data/trips.json.

Run from the repository root:
    python3 .claude/skills/update-weather/scripts/weather.py            # show current and new values
    python3 .claude/skills/update-weather/scripts/weather.py --write    # also save them to trips.json

For each destination, every city in data/climate.json is weighted by its number of days in
data/itinerary.json (equal weights when the destination has no day plan yet):
    day_c, night_c, humidity_pct   weighted averages of high_c, low_c, humidity_pct
    feels_c                        weighted average of each city's heat index at high_c, using the afternoon
                                   humidity worked out from humidity_pct (dew point held at the daily mean's)
    rain_level, rain               from the weighted rainy_days, using RAIN_LEVELS below
"""
import json
import math
import re
import sys
from collections import Counter

DATA = "data/"
FIELDS = ["day_c", "night_c", "feels_c", "humidity_pct", "rain", "rain_level"]
CITY_KEYS = ["country", "city", "high_c", "low_c", "humidity_pct", "rainy_days", "source"]
# Highest December rainy-day count (days with at least 1 mm) for each level.
RAIN_LEVELS = [(5, 1, "Low"), (9, 2, "Low to medium"), (13, 3, "Medium"), (17, 4, "Medium to high"), (99, 5, "High")]


def load(name):
    with open(DATA + name, encoding="utf-8") as f:
        return json.load(f)


def save(name, rows):
    # Same layout as the other data files: 1-space indent, no trailing newline.
    with open(DATA + name, "w", encoding="utf-8") as f:
        f.write(json.dumps(rows, ensure_ascii=False, indent=1))


def half_up(x):
    return int(math.floor(x + 0.5))


def saturation_hpa(temp_c):
    """Magnus formula for saturation vapour pressure."""
    return 6.1094 * math.exp(17.625 * temp_c / (temp_c + 243.04))


def afternoon_rh(high_c, low_c, mean_rh):
    """Humidity at the day's high, assuming the air's moisture stays as it is at the daily mean temperature."""
    mean_c = (high_c + low_c) / 2
    return min(100.0, mean_rh * saturation_hpa(mean_c) / saturation_hpa(high_c))


def route_days(route):
    """{"Krabi": 5, "Bangkok": 3} from "Krabi 5 days, Bangkok 3 days" (the format the page reads)."""
    out = {}
    for part in route.split(", "):
        m = re.match(r"^(.*) (\d+) days?$", part)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def heat_index_c(temp_c, rh):
    """NOAA heat index (Rothfusz regression with its standard adjustments), in degrees C."""
    t = temp_c * 9 / 5 + 32
    hi = 0.5 * (t + 61 + (t - 68) * 1.2 + rh * 0.094)
    if (hi + t) / 2 >= 80:
        hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh - 0.00683783 * t * t
              - 0.05481717 * rh * rh + 0.00122874 * t * t * rh + 0.00085282 * t * rh * rh
              - 0.00000199 * t * t * rh * rh)
        if rh < 13 and 80 <= t <= 112:
            hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
        elif rh > 85 and 80 <= t <= 87:
            hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return (hi - 32) * 5 / 9


def with_fields(trip, new):
    """Set the weather fields, keeping the key order; a destination without them gets them after route."""
    if all(k in trip for k in FIELDS):
        return {**trip, **new}
    out = {}
    for k, v in trip.items():
        if k not in FIELDS:
            out[k] = v
        if k == "route":
            out.update(new)
    out.update({k: v for k, v in new.items() if k not in out})
    return out


def rain_for(days):
    for limit, level, label in RAIN_LEVELS:
        if days <= limit:
            return level, label


def main():
    write = "--write" in sys.argv[1:]
    trips, plans = load("trips.json"), load("itinerary.json")
    try:
        climate = load("climate.json")
    except FileNotFoundError:
        print("data/climate.json does not exist yet; create it with one row per city")
        climate = []
    problems = []
    for i, c in enumerate(climate):
        missing = [k for k in CITY_KEYS if k not in c]
        if missing:
            problems.append(f"climate.json row {i} ({c.get('city', '?')}): missing {', '.join(missing)}")
    if problems:
        sys.exit("\n".join(problems))

    days = Counter((p["country"], p["city"]) for p in plans)
    changed = 0
    for i, t in enumerate(trips):
        country = t["country"]
        cities = [c for c in climate if c["country"] == country]
        planned = sorted({city for (k, city) in days if k == country})
        in_route = route_days(t.get("route", ""))
        if planned and in_route and in_route != {city: days[(country, city)] for city in planned}:
            problems.append(f"{country}: route says {t['route']!r} but the day plan has "
                            + ", ".join(f"{city} {days[(country, city)]} days" for city in planned)
                            + "; weather left unchanged until they agree")
            continue
        known = {c["city"] for c in cities}
        missing = [city for city in planned if city not in known]
        if missing or not cities:
            why = f"no climate.json row for {', '.join(missing)}" if missing else "no climate.json rows"
            problems.append(f"{country}: {why}; weather left unchanged")
            continue
        if planned:
            extra = sorted(known - set(planned))
            if extra:
                problems.append(f"{country}: climate.json has {', '.join(extra)}, which is not in the day plan (ignored)")
            cities = [c for c in cities if c["city"] in planned]
            if not cities:
                continue
        weights = [days[(country, c["city"])] if planned else 1 for c in cities]
        total = sum(weights)

        def avg(values):
            return sum(v * w for v, w in zip(values, weights)) / total

        rainy = avg([c["rainy_days"] for c in cities])
        level, label = rain_for(rainy)
        new = {
            "day_c": half_up(avg([c["high_c"] for c in cities])),
            "night_c": half_up(avg([c["low_c"] for c in cities])),
            "feels_c": half_up(avg([heat_index_c(c["high_c"], afternoon_rh(c["high_c"], c["low_c"], c["humidity_pct"]))
                                    for c in cities])),
            "humidity_pct": half_up(avg([c["humidity_pct"] for c in cities])),
            "rain": label,
            "rain_level": level,
        }
        split = ", ".join(f"{c['city']} {w}d" for c, w in zip(cities, weights)) if planned else "equal weights"
        diffs = [f"{k} {t.get(k)} -> {new[k]}" for k in FIELDS if t.get(k) != new[k]]
        print(f"{country} ({split}; {rainy:.1f} rainy days): " + ("; ".join(diffs) if diffs else "no change"))
        if diffs:
            changed += 1
            trips[i] = with_fields(t, new)

    for p in problems:
        print("WARNING: " + p)
    if write and changed:
        save("trips.json", trips)
        print(f"Saved {changed} destination(s) to data/trips.json")
    elif changed:
        print("Dry run: add --write to save these values")


if __name__ == "__main__":
    main()
