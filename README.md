# PM2.5-Based Pollution Intervention Prioritization

A Python Project with an HTML/CSS/JavaScript frontend and data preprocessing.


The source datasets are in `data/raw/`. Processed outputs are written to `data/processed/`.

## Live local dashboard

Run `python server.py` and open <http://localhost:8000>. The dashboard polls
the analysis server every five seconds. When a supported file in `data/raw/`
is appended or replaced, the pipeline reruns and the map, statistics, and
priority table refresh automatically.

This local mode uses polling and the existing CSV/Excel input format; it does
not yet connect directly to a physical sensor or external API.

## Current scope
- PM2.5 pollution analysis
- Temperature and humidity analysis
- Geographic hotspot analysis using valid latitude/longitude
- Initial priority ranking based on pollution severity and persistence

Traffic is intentionally excluded for the current version. Population exposure is not available in the provided datasets, so it is not included in the score.
