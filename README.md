# PM2.5-Based Pollution Intervention Prioritization

A Python Project with an HTML/CSS/JavaScript frontend and data preprocessing.


The source datasets are in `data/raw/`. Processed outputs are written to `data/processed/`.

## Live dashboard

Run `python server.py` and open <http://localhost:8000>. The dashboard polls
the analysis server every five seconds. When a supported file in `data/raw/`
is appended or replaced, the pipeline reruns and the map, statistics, and
priority table refresh automatically.

### CPCB station reports

Register with [data.gov.in](https://www.data.gov.in/) and generate an API key
under My Account. Set `DATA_GOV_IN_API_KEY` in the server environment before
starting the app; do not put the key in source control or enter it in the
website. On Windows PowerShell, set the variable in the same terminal before
starting the server:

```powershell
$env:DATA_GOV_IN_API_KEY = "<your data.gov.in API key>"
python server.py
```

On Vercel, add it as a project environment variable and redeploy.

Enter a city and optionally a state, then click **Go real time**. The app
requests [CPCB station data](https://www.data.gov.in/resource/real-time-air-quality-index-various-locations)
through the official data.gov.in API, and checks for updates every 10 minutes
while this mode is active. The feed is reported hourly and may be delayed;
click a point to see the selected pollutant's source-reported time. If an
update fails, the previous display remains visible with an error message.
Choose **Return to local data** to resume the existing file-based dashboard.

Only stations and pollutants actually returned by the feed are shown. The API
response does not specify the units or clarify how its pollutant averages
relate to concentrations, so the app displays the values as reported without
claiming a unit. CO2 and H2S are unavailable in this feed. These current station
reports are not treated as the historical sensor readings required by the
existing priority and speed analysis; IPS is unavailable in CPCB mode.
Colours compare reported values across stations, not official AQI categories.
Source: CPCB via data.gov.in,
[Government Open Data License - India](https://data.gov.in/government-open-data-license-india).

To analyse another city, select a raw CSV (UTF-8) or XLSX file in the
dashboard and click **Clean and analyse**. Files can be up to 20 MB; for
Excel, the first sheet is used. Use the optional column mapping fields when
your headers are not recognised. The upload is analysed separately in memory;
it does not modify the live files or saved pipeline outputs. Download the
cleaned CSV, or return to live data using the button in the dashboard.
The map uses online Leaflet resources and Esri tiles; tile requests disclose
the viewed map area to the tile provider.

Cleaning converts recognised dates, pollutant, weather and coordinate fields,
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

The map shows a point and matching circular boundary per PM2.5 hotspot, coloured
by IPS or average PM2.5, PM10, CO2, SO2, NO2, CO, O3 or H2S. The boundaries
are illustrative, not estimates of pollution spread: their radii are capped at
100 metres and reduced to 45% of the nearest displayed point's distance to
avoid overlap. Coincident points have no boundary. The radius can change when
the selected metric changes which points are displayed. Zoom in to separate
nearby points and click a point or boundary to see its radius and values.
IPS colours use the priority score thresholds;
pollutant colours divide the displayed range at 40% and 70%, and equal values
are all shown in amber. These relative colours are not health thresholds.
Each additional pollutant average
uses the available numeric readings at that rounded location, including rows
without PM2.5. Missing pollutants are not plotted; units are those in the
dataset and must be checked.

The cleaned data includes `estimated_speed_kmh`: Haversine distance between
consecutive coordinates divided by elapsed hours. Each file is treated as one
device track, ordered by timestamp; the speed is assigned to the later reading.
Missing coordinates or timestamps, duplicate timestamps, and non-positive
intervals cannot produce a speed. Long gaps and GPS jitter can make estimates
unreliable; review the data before drawing conclusions.

For each hotspot, the table and map show the mean estimated device speed and
Pearson correlation between speed and PM2.5 at that location, with the number
of paired readings. Correlation requires at least three pairs and variation in
both variables; otherwise it is unavailable. The result describes association,
not causation or traffic speed, and does not change the PM2.5-based IPS.

Add CSV or Excel datasets to `data/raw/`. Each dataset must include a
parseable date/time column and at least one numeric measurement column.
The trend chart uses PM2.5 when available; otherwise, it plots the numeric
measurement columns it finds, excluding date/time, location, and ID fields.
PM2.5-specific summaries and hotspot analyses are populated when those
measurements and coordinates are present.

The local-data mode uses polling and the existing CSV/Excel input format; it
does not connect directly to a physical sensor.

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
