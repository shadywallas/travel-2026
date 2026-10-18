# New Year Trip Destination Comparison

A small static website comparing city and activity trips for 24 Dec to 2 Jan (plus Japan in November for comparison), with day-by-day plans, recommended hotels, and links to TikTok, YouTube Shorts and photo searches for each activity.

## Files

- `index.html` - the page
- `data/trips.json` - destinations, average humidity, feels-like temperature, ratings (including monkey exposure, 0 to 5) and routes
- `data/itinerary.json` - day-by-day plans
- `data/activities.json` - activity names and the search words used for video and photo links
- `data/hotels.json` - recommended hotel per stop, with its Booking.com listing (`booking_url`) and photo (`image`)
- `data/prices.json` - estimated costs for two people in US dollars, one row per cost line (see below)
- `data/climate.json` - late-December climate averages per city, used to work out the weather in `trips.json` (see Weather)

To change the trip, edit the JSON files and commit; the page reads them on load.

## Prices

Each row in `data/prices.json` is one cost line:

```json
{ "country": "Thailand", "day": 2, "category": "activity", "item": "Four Islands longtail tour", "usd": 70, "source": "https://..." }
```

- `country` matches `country` in `trips.json`, and `day` matches `day` in `itinerary.json`. The page uses the itinerary to find the city for that day, so city totals follow the plan automatically.
- `day` 0 is for costs of the whole trip: international flights and visas.
- `category` is one of `transport`, `activity`, `accommodation`, `food`, `flights` or `visa`. Hotels have one `accommodation` row per night (the night of that day).
- `usd` is the total for both people, in whole US dollars.
- `source` is the page the price came from, or an empty string for an estimate.

The page adds the rows up into a total per day, per city and per destination, shown in the table, on the phone cards and inside each plan. To change a price, edit its row; to add a cost, add a row.

## Weather

The weather skill (below) works out `day_c`, `night_c`, `feels_c`, `humidity_pct`, `rain` and `rain_level` in `trips.json` from `data/climate.json`, which has one row per city with its December averages and the page they came from. Each city counts for its number of days in the day plan. Feels like is the heat index at the day temperature, using the afternoon humidity. Until the skill has been run for a destination, its weather values are earlier estimates and `data/climate.json` may not exist yet.

## Updating prices and weather with Claude Code

Two project skills in `.claude/skills/` keep these up to date after you add a destination or city, change day plans, activities or hotels, or change a route's days:

- `/update-prices` finds the days whose plan changed since the prices were last updated, re-prices them and checks `prices.json` against the plans.
- `/update-weather` researches climate averages for any new city and recalculates the weather fields.

They run only when you ask, with the slash command or in words, such as "update the prices for the Maldives". Their scripts can also be run on their own from the repository root:

```bash
python3 .claude/skills/update-prices/scripts/check_prices.py --country Maldives
python3 .claude/skills/update-weather/scripts/weather.py          # add --write to save
```

## Publish with GitHub Pages

1. Create a new repository on GitHub and upload all files from this folder (keep the `data` folder).
2. In the repository, open **Settings**, then **Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**, select `main` and `/ (root)`, and save.
4. After a minute or two, the site is available at `https://<your-username>.github.io/<repository-name>/`.

Or from the command line:

```bash
cd site
git init
git add .
git commit -m "Add New Year trip comparison"
git branch -M main
git remote add origin https://github.com/<your-username>/<repository-name>.git
git push -u origin main
```

## Preview locally

The page loads its data with `fetch`, so open it through a local web server rather than double-clicking the file:

```bash
cd site
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.
