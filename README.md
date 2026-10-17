# New Year Trip Destination Comparison

A small static website comparing warm two-stop routes for 24 Dec to 2 Jan, with day-by-day plans, recommended hotels, and links to TikTok, YouTube Shorts and photo searches for each activity.

## Files

- `index.html` - the page
- `data/trips.json` - destinations, ratings (including monkey exposure, 0 to 5) and routes
- `data/itinerary.json` - day-by-day plans
- `data/activities.json` - activity names and the search words used for video and photo links
- `data/hotels.json` - recommended hotel per stop, with its Booking.com listing (`booking_url`) and photo (`image`)

To change the trip, edit the JSON files and commit; the page reads them on load.

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
