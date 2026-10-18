"""Check data/prices.json against the trip data and list what changed since the prices were last updated.

Run from the repository root:
    python3 .claude/skills/update-prices/scripts/check_prices.py                      # all destinations
    python3 .claude/skills/update-prices/scripts/check_prices.py --country Maldives   # one destination, with its price rows
    python3 .claude/skills/update-prices/scripts/check_prices.py --since <git-rev>    # compare plans with another commit

"Changed" compares itinerary.json, activities.json, hotels.json and the routes in trips.json in the
working tree with the last commit that changed each destination's rows in data/prices.json (or with
--since for all of them), so re-pricing one destination does not hide the others' changes. Rows edited
but not committed yet do not count. Exits with status 1 when there are errors.
"""
import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict

DATA = "data/"
KEYS = {"country": str, "day": int, "category": str, "item": str, "usd": int, "source": str}
DAY_CATS = {"transport", "activity", "accommodation", "food"}
TRIP_CATS = {"flights", "visa"}


def load(name, rev=None):
    if rev is None:
        with open(DATA + name, encoding="utf-8") as f:
            return json.load(f)
    out = subprocess.run(["git", "show", f"{rev}:{DATA}{name}"], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else []


def words(text):
    return "".join(ch if ch.isalnum() or ch == "-" else " " for ch in text.lower()).split()


def names_hotel(item, hotel):
    """True when the item has the first two meaningful words of the hotel's name (\"Two Seasons\", \"Niva Velassaru\")."""
    key = [w for w in words(hotel) if w not in {"the", "hotel", "resort", "and"}][:2]
    have = set(words(item))
    return all(w in have for w in key)


def price_baselines(countries):
    """country -> the last commit that changed that country's rows in prices.json."""
    out = subprocess.run(["git", "log", "--format=%h", "--", DATA + "prices.json"], capture_output=True, text=True)

    def rows_by_country(rev):
        by = defaultdict(list)
        for r in load("prices.json", rev):
            by[r.get("country")].append(r)
        return by

    found = {}
    for rev in out.stdout.split():
        now, before = rows_by_country(rev), rows_by_country(rev + "^")
        for c in countries:
            if c not in found and c in now and now[c] != before.get(c):
                found[c] = rev
        if len(found) == len(countries):
            break
    return found


def plan_changes(rev, countries):
    """(country, day) -> reasons, for days whose plan, city, activities or hotel changed since rev."""
    changes = defaultdict(list)
    old_it = {(p["country"], p["day"]): p for p in load("itinerary.json", rev)}
    new_it = {(p["country"], p["day"]): p for p in load("itinerary.json")}
    for key in sorted(set(old_it) | set(new_it), key=lambda k: (k[0], k[1])):
        a, b = old_it.get(key), new_it.get(key)
        if not b:
            changes[key].append("day removed from the plan")
        elif not a:
            changes[key].append("new day in the plan")
        else:
            if a["city"] != b["city"]:
                changes[key].append(f"city {a['city']} -> {b['city']}")
            if a["plan"] != b["plan"] or a["romantic"] != b["romantic"]:
                changes[key].append("plan text changed")

    def acts(rows):
        out = defaultdict(set)
        for r in rows:
            out[(r["country"], r["day"])].add((r["kind"], r["name"]))
        return out

    old_a, new_a = acts(load("activities.json", rev)), acts(load("activities.json"))
    for key in set(old_a) | set(new_a):
        added, gone = new_a[key] - old_a[key], old_a[key] - new_a[key]
        if added:
            changes[key].append("new activities: " + ", ".join(sorted(n for _, n in added)))
        if gone:
            changes[key].append("removed activities: " + ", ".join(sorted(n for _, n in gone)))

    old_h = {(h["country"], h["city"]): h["hotel"] for h in load("hotels.json", rev)}
    new_h = {(h["country"], h["city"]): h["hotel"] for h in load("hotels.json")}
    for (country, city) in set(old_h) | set(new_h):
        if old_h.get((country, city)) != new_h.get((country, city)):
            for key, p in new_it.items():
                if key[0] == country and p["city"] == city:
                    changes[key].append(f"hotel {old_h.get((country, city))} -> {new_h.get((country, city))}")

    old_t = {t["country"]: t for t in load("trips.json", rev)}
    for t in load("trips.json"):
        o = old_t.get(t["country"])
        if not o:
            changes[(t["country"], 0)].append("new destination")
        elif o.get("route") != t.get("route"):
            changes[(t["country"], 0)].append(f"route {o.get('route')} -> {t.get('route')} (check flights)")
    return {k: v for k, v in changes.items() if k[0] in countries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country")
    ap.add_argument("--since")
    args = ap.parse_args()

    trips, plans, hotels, prices = load("trips.json"), load("itinerary.json"), load("hotels.json"), load("prices.json")
    names = [t["country"] for t in trips]
    countries = [args.country] if args.country else names
    if args.country and args.country not in names:
        sys.exit(f"Unknown country {args.country!r}; use one of: {', '.join(names)}")
    days_of = defaultdict(dict)
    for p in plans:
        days_of[p["country"]][p["day"]] = p["city"]
    hotel_of = {(h["country"], h["city"]): h["hotel"] for h in hotels}
    errors, warnings = [], []

    for i, r in enumerate(prices):
        where = f"row {i} ({r.get('country')}, day {r.get('day')}, {r.get('category')})"
        bad = [k for k, typ in KEYS.items() if not isinstance(r.get(k), typ) or isinstance(r.get(k), bool)]
        if bad:
            errors.append(f"{where}: missing or wrong type: {', '.join(bad)}")
            continue
        if r["country"] not in names:
            errors.append(f"{where}: country is not in trips.json")
        if r["category"] not in DAY_CATS | TRIP_CATS:
            errors.append(f"{where}: unknown category (the page shows it as Other)")
        elif r["category"] in TRIP_CATS and r["day"] != 0:
            errors.append(f"{where}: {r['category']} belongs on day 0")
        elif r["category"] in DAY_CATS and r["day"] not in days_of[r["country"]]:
            errors.append(f"{where}: day {r['day']} is not in the day plan (the page would count it as a trip-wide cost)")
        if r["usd"] < 0:
            errors.append(f"{where}: negative usd")
        if r["source"] and not r["source"].startswith("http"):
            errors.append(f"{where}: source must be a URL or empty")

    by = defaultdict(list)
    for r in prices:
        by[(r.get("country"), r.get("day"))].append(r)
    status = {t["country"]: t.get("status") for t in trips}
    for country in countries:
        rows = [r for r in prices if r.get("country") == country]
        days = days_of[country]
        if not rows:
            if status.get(country) == "shortlist" and days:
                errors.append(f"{country}: shortlisted with a day plan but has no prices")
            continue
        cats0 = Counter(r["category"] for r in by[(country, 0)])
        for cat in ("flights", "visa"):
            if not cats0[cat]:
                errors.append(f"{country}: no {cat} row on day 0 (use usd 0 for visa-free)")
        for day, city in sorted(days.items()):
            cats = Counter(r["category"] for r in by[(country, day)])
            if cats["accommodation"] != 1:
                errors.append(f"{country} day {day}: {cats['accommodation']} accommodation rows (need exactly 1, the night of that day)")
            hotel = hotel_of.get((country, city))
            for r in by[(country, day)]:
                if r["category"] == "accommodation" and hotel and not names_hotel(r["item"], hotel):
                    warnings.append(f"{country} day {day}: accommodation item does not name the {city} hotel {hotel!r}: {r['item'][:70]}")
            if not cats["food"]:
                errors.append(f"{country} day {day}: no food row")

    print("Totals for two (USD):")
    for country in countries:
        rows = [r for r in prices if r.get("country") == country]
        if rows:
            cats = Counter()
            for r in rows:
                cats[r["category"]] += r["usd"]
            print(f"  {country}: ${sum(cats.values()):,}  (" + ", ".join(f"{k} ${v:,}" for k, v in cats.most_common()) + ")")

    print("\nTotals per city, as the page groups them (day 0 is trip-wide):")
    for country in countries:
        cities = Counter()
        for r in prices:
            if r.get("country") == country and isinstance(r.get("usd"), int):
                cities[days_of[country].get(r.get("day"), "trip-wide")] += r["usd"]
        if cities:
            print(f"  {country}: " + ", ".join(f"{k} ${v:,}" for k, v in cities.items()))

    priced = [c for c in countries if any(r.get("country") == c for r in prices)]
    base = {c: args.since for c in priced} if args.since else price_baselines(priced)
    if base:
        changes = {}
        for rev in sorted(set(base.values())):
            changes.update(plan_changes(rev, [c for c in priced if base[c] == rev]))
        print("\nPlan changes since each destination's last price commit (prices for these need checking):")
        print("  baselines: " + ", ".join(f"{c} {rev}" for c, rev in base.items()))
        if not changes:
            print("  none")
        for key in sorted(changes, key=lambda k: (k[0], k[1])):
            print(f"  {key[0]} day {key[1]}: " + "; ".join(changes[key]))
            if args.country:
                for r in by[key]:
                    print(f"      [{r['category']}] {r['item']} = ${r['usd']}")

    for w in warnings:
        print("WARNING: " + w)
    for e in errors:
        print("ERROR: " + e)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
