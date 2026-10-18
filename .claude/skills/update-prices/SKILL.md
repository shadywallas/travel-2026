---
name: update-prices
description: Use when the user asks to update, recalculate, research or check the trip costs (data/prices.json), for example after adding a destination or city, changing day plans, activities or hotels, or changing how many days a route spends in each city.
---

# Updating trip prices

## Overview

`data/prices.json` holds every cost line, and the page adds them up per day, per city and per destination. The prices must describe the current plan: one row per paid item in each day's plan, one hotel row per night, and flights and visas on day 0. `scripts/check_prices.py` finds what changed and what is missing; research and judgement are yours.

## Steps

1. Work in a git worktree on its own branch made from `main`, not in the main checkout, and run everything from that worktree's root. If the user names destinations, work only on those. Price demoted destinations only when the user names them.
2. Run `python3 .claude/skills/update-prices/scripts/check_prices.py`, adding `--country "<name>"` to see that destination's current rows under each changed day. It prints:
   - totals per destination and per city;
   - every day whose plan, city, activities or hotel changed since that destination's prices were last committed, and route changes (check flights). A destination stays listed until its new prices are committed;
   - errors (missing nights, food, flights or visas; days not in the plan) and warnings (an accommodation row that does not name that night's hotel).
3. For each changed day, read its `plan` and `romantic` text in itinerary.json, its rows in activities.json, and its city's hotel in hotels.json. Make the day's rows match the table below, and delete rows for anything no longer in the plan.
4. Research each price using the rules below. For more than one destination, give each its own subagent running in parallel, pass it these rules, and have it return rows rather than edit the file.
5. Write the rows (see Format), then run the check again until it shows 0 errors and no warnings you cannot explain.
6. Preview the page (`python3 -m http.server 8000`) and open the destination's plan on desktop and at phone width. A demoted destination is in the Demoted section. Each day, city and hotel card should show the new totals.
7. Report to the user: each destination's old and new total and its new city totals (from the check before and after), and every price that is an estimate (empty `source`). Commit on the branch; push or merge only when the user asks.

## What each day needs

| Category | Day | Rows |
|---|---|---|
| `flights` | 0 | International economy flights for two from Cairo, one stop: out on 24 Dec to the route's first city, back on 2 Jan from its last city |
| `visa` | 0 | Egyptian passports, for two; a row with `usd` 0 and the reason when visa-free |
| `accommodation` | every day | Exactly one row: that night's hotel, as named in hotels.json for the day's city, with room type and the rate for that date |
| `transport` | the day it happens | Every move in the plan: transfers, domestic flights, boats, taxis. Use `usd` 0 and "(included in room rate)" when the hotel includes it. The transfer to the airport on 2 Jan goes on the last day |
| `activity` | the day it happens | Every paid item in the plan or activities.json: tours, tickets, classes, spa, park fees. Free places need no row |
| `food` | every day | Lunch and dinner for two (breakfast is in the room rate), in one row or two. Meals go here even when activities.json lists them, such as a compulsory New Year's Eve dinner, at their real price |

## Research rules

- The trip runs 24 Dec 2026 to 2 Jan 2027, for two adults. 24 Dec is the overnight flight, so day 1 is 25 Dec (Christmas night), and day N's night is the date of day N in itinerary.json. Hotels charge more for Christmas and New Year's Eve nights.
- `usd` is the total for both people, in whole US dollars. Keep a sourced price exact; round only estimates, to the nearest $5.
- When you convert, use the current rate (for example from xe.com) and show the local amount in `item`, for example "2 × 1,413 baht".
- Include service charge and taxes. For prices quoted "++" or "plus tax", add them and say so in `item`.
- Prefer the official site, then booking sites (Trip.com, Booking.com, Kayak), then recent guides. Put the page in `source`; leave it empty for an estimate.

## Format

- Keys in this order: `country`, `day`, `category`, `item`, `usd`, `source`.
- Keep each destination's rows together and sorted by day.
- Save with `json.dumps(rows, ensure_ascii=False, indent=1)`, with no newline at the end. This keeps the ’, – and × characters as they are.

## Common mistakes

- **Moving a city's days without moving its hotel nights:** a night stays at the old hotel. The check flags it.
- **Keeping rows for activities that left the plan:** the page still adds them up.
- **Using a day number that is not in the plan:** the page silently counts it as a trip-wide cost. The check flags it.
- **Pricing per person:** every `usd` is for two.
- **Leaving an old hotel name after a rename:** the check warns.
