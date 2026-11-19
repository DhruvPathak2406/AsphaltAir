# PM2.5-Based Pollution Intervention Prioritization

A Python Project with an HTML/CSS/JavaScript frontend and data preprocessing.


The source datasets are in `data/raw/`. Processed outputs are written to `data/processed/`.

## Live dashboard

Run `python server.py` and open <http://localhost:8000>. The dashboard polls
the analysis server every five seconds. When a supported file in `data/raw/`
is appended or replaced, the pipeline reruns and the map, statistics, and
priority table refresh automatically.

To analyse another city, select a raw CSV (UTF-8) or XLSX file in the
dashboard and click **Clean and analyse**. Files can be up to 20 MB; for
Excel, the first sheet is used. Use the optional column mapping fields when
your headers are not recognised. The upload is analysed separately in memory;
it does not modify the live files or saved pipeline outputs. Download the
cleaned CSV, or return to live data using the button in the dashboard.
The map uses online Leaflet resources and Esri tiles; tile requests disclose
the viewed map area to the tile provider.

Cleaning converts recognised dates and PM2.5/weather/coordinate fields,
removes duplicate rows and clears out-of-range coordinates. Rows with invalid
dates are removed if the dataset contains parseable dates; if there is no
date column, rows are retained but no trend can be generated. Other missing
values are left missing, and unknown columns are retained. Automatic detection
cannot understand every schema or infer units: check the output and map columns
explicitly when needed. Malformed CSV records with extra fields are skipped
rather than shifting values into the wrong columns, and the dashboard reports
how many records were skipped. The PM2.5 hotspot ranking requires coordinates
and at least 10 valid PM2.5 readings per rounded coordinate group; a dataset
without those fields can still be cleaned and downloaded.

Add CSV or Excel datasets to `data/raw/`. Each dataset must include a
parseable date/time column and at least one numeric measurement column.
The trend chart uses PM2.5 when available; otherwise, it plots the numeric
measurement columns it finds, excluding date/time, location, and ID fields.
PM2.5-specific summaries and hotspot analyses are populated when those
measurements and coordinates are present.

This local mode uses polling and the existing CSV/Excel input format; it does
not yet connect directly to a physical sensor or external API.

## Deploy to Vercel

The Flask app in `server.py` serves the dashboard and API on Vercel. Push the
project to GitHub, import the repository in Vercel with the repository root as
the project root, and deploy. Vercel installs the dependencies from
`requirements.txt`.

Vercel bundles the files in `data/raw/` as the live dataset. Its filesystem is
read-only, so the app writes generated analysis files to temporary storage;
changes made to the deployed instance do not persist across deployments.
Uploads are analysed in memory and are not added to the live dataset. Vercel's
function request-body limit means uploads are limited to 4 MB there; local
uploads remain limited to 20 MB.

## Current scope
- PM2.5 pollution analysis
- Temperature and humidity analysis
- Geographic hotspot analysis using valid latitude/longitude
- Initial priority ranking based on pollution severity and persistence

Traffic is intentionally excluded for the current version. Population exposure is not available in the provided datasets, so it is not included in the score.
