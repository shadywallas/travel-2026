---
name: update-weather
description: Use when the user asks to update, recalculate or check the weather shown for each destination (day and night temperature, feels like, humidity, rain in data/trips.json), for example after adding a destination or city, changing a route or its day split, or when a weather value looks wrong.
---

# Updating destination weather

## Overview

Per-city December climate averages live in `data/climate.json`. `scripts/weather.py` turns them into each destination's `day_c`, `night_c`, `feels_c`, `humidity_pct`, `rain` and `rain_level` in `data/trips.json`, weighting each city by its days in `data/itinerary.json`. Research only cities that have no row yet; the script does all the arithmetic, so never type the six fields by hand.

## Steps

1. Work in a git worktree on its own branch made from `main`, not in the main checkout. Run everything from that worktree's root.
2. If the change the user describes is not in `data/itinerary.json` yet (for example, the day plan still names the old city), stop and ask the user how to proceed. Changing day plans, hotels or routes is not part of this skill.
3. Run `python3 .claude/skills/update-weather/scripts/weather.py`. It prints each destination's current and new values, then warnings:
   - **route says … but the day plan has …**: `route` in trips.json and the day plan disagree, and the script leaves that destination unchanged. Ask the user which is right.
   - **no climate.json row for X**: research city X (step 4).
   - **climate.json has X, which is not in the day plan**: the city was dropped; delete its row.
4. Add one row per missing city to `data/climate.json`, creating it as a JSON list if needed:

   | Key | Value |
   |---|---|
   | `country` | Exactly as in trips.json |
   | `city` | Exactly as in itinerary.json |
   | `high_c`, `low_c` | December mean daily maximum and minimum, °C, as published (one decimal is fine) |
   | `humidity_pct` | December average relative humidity, %; the daily mean, not converted |
   | `rainy_days` | December average days with at least 1 mm of rain |
   | `source` | URL of the page the numbers came from |

   - **Station:** the one in or nearest the city. When there are several, or the city is generic (such as "Resort island"), use the one nearest that city's hotel in hotels.json.
   - **Source, in order:** the city's Wikipedia "Climate data for …" table when it cites the national weather service; that service's own normals; NOAA NCEI climate normals; Weather Spark. Use the same kind of source for every city in one destination.
   - **Rainy days at another threshold** (such as 0.1 mm): take `rainy_days` from the next source for the same station, and say so in your report.
   - Keep the keys in the order above, and save with `json.dumps(rows, ensure_ascii=False, indent=1)` with no newline at the end, like the other data files.
5. Run the script again and read every change, then run it with `--write`.
6. Preview the page (`python3 -m http.server 8000`) and check the destination's weather in its table row and its phone card, and the "Least humid" and "Coolest feels-like" sorts.
7. Report to the user: old and new values per destination, the climate rows you added with their sources, and any warnings left. Commit on the branch; push or merge only when the user asks.

## How weather.py works out the values

| Field | Worked out from |
|---|---|
| `day_c`, `night_c`, `humidity_pct` | Day-weighted averages of `high_c`, `low_c` and `humidity_pct`, rounded half up |
| `feels_c` | Weighted average of each city's NOAA heat index at `high_c`, using the afternoon humidity: `humidity_pct` × es(mean of high and low) ÷ es(`high_c`), with es from the Magnus formula |
| `rain_level`, `rain` | Weighted rainy days: 5 or fewer is Low (1); over 5 to 9, Low to medium (2); over 9 to 13, Medium (3); over 13 to 17, Medium to high (4); over 17, High (5) |

Destinations without a day plan (the demoted ones) weight their climate.json cities equally.

## Common mistakes

- **Editing the six fields in trips.json by hand:** the next run overwrites them. Fix climate.json instead.
- **Working out feels like from the daily average humidity:** this overstates it by 3 to 4 °C. Let the script do it.
- **Inventing a rain rating:** the rating comes only from `rainy_days` and the table above.
- **Updating the weather for a city the day plan does not have yet:** the weights follow itinerary.json, so the plan must change first (step 2).
