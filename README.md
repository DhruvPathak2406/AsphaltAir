
# Surat PM2.5 Pollution Intervention Prioritization

An interactive data analytics project to identify PM2.5 pollution hotspots and prioritize potential intervention locations across Surat, Gujarat, India.

The project combines Python-based data analysis, geographic hotspot detection, and an interactive web dashboard to visualize pollution patterns and support data-driven intervention planning.

## Features

- **Data Preprocessing:** Clean and prepare raw pollution datasets.
- **Pollution Analysis:** Analyse PM2.5 concentrations across measured locations.
- **Weather Analysis:** Explore temperature and humidity alongside pollution measurements.
- **Hotspot Detection:** Identify geographic pollution patterns using latitude and longitude.
- **Intervention Priority Score (IPS):** Rank locations as High, Medium, or Low priority.
- **Interactive Heatmap:** Visualize IPS and average PM2.5 on a map of Surat.
- **Dashboard:** Explore summary statistics, coordinate groups, and individual location details.

## Tech Stack

| Category | Technologies |
|---|---|
| Programming | Python, JavaScript |
| Data Analysis | Pandas, NumPy |
| Visualization | Matplotlib, Leaflet.js |
| Frontend | HTML5, CSS3, JavaScript |
| Mapping | Leaflet, external map tiles |
| Data Formats | CSV, XLSX |

## Project Structure

```text
pm25-intervention-prioritization/
├── data/
│   ├── raw/
│   └── processed/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── src/
│   ├── preprocessing.py
│   ├── pollution_analysis.py
│   ├── weather_analysis.py
│   ├── hotspot_detection.py
│   ├── priority_scoring.py
│   └── visualization.py
├── notebooks/
├── reports/
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

## Getting Started

### 1. Install Dependencies

Ensure Python and pip are installed, then run:

```bash
pip install -r requirements.txt
```

### 2. Run the Analysis Pipeline

From the project root directory:

```bash
python main.py
```

This executes the configured preprocessing and analysis pipeline and generates the output files defined by the project.

### 3. Launch the Dashboard

Open `frontend/index.html` in a modern web browser.

Upload the generated cleaned dataset CSV and intervention priority CSV to explore the dashboard and heatmap.

**Note:** An internet connection is required to load the external map tiles and mapping libraries.

## Intervention Priority Score (IPS)

The IPS provides a relative ranking of locations based on the project's prioritization model. Locations are classified into three categories:

- 🔴 **High Priority**
- 🟠 **Medium Priority**
- 🟢 **Low Priority**

The interactive map allows users to switch between the IPS heatmap and average PM2.5 heatmap, helping distinguish intervention priorities from measured pollution concentrations.

## Limitations

- Analysis is limited to the available datasets and measurement locations.
- Traffic volume and population exposure are not currently included.
- The heatmap represents coordinate-based observations rather than official municipal ward boundaries.
- IPS is a project-specific ranking, not an official air-quality index or validated health-risk assessment.

## Future Scope

- Integrate official Surat municipal ward boundaries.
- Add time-based pollution analysis and filtering.
- Incorporate traffic, population exposure, and additional environmental variables.
- Validate and improve the IPS methodology.
- Deploy the dashboard with automated data updates.

## Objective

To develop a geographically informed, data-driven tool that identifies PM2.5 pollution hotspots and helps prioritize potential pollution interventions across Surat.

## Disclaimer

This project is an academic and analytical prototype. Its outputs should not be treated as official regulatory classifications or definitive public-health recommendations.
