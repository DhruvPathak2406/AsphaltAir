# Asphalt-Air 
### PM2.5 Pollution Monitoring, Geospatial Analysis & Intervention Prioritisation

**Asphalt-Air** is a data-driven environmental monitoring and analysis platform designed to identify, analyse, and prioritise areas experiencing elevated PM2.5 pollution.

The project combines environmental data processing, temporal analysis, geospatial hotspot identification, and interactive visualisation to transform raw pollution measurements into actionable insights. It aims to support better-informed environmental monitoring and targeted pollution mitigation, particularly in urban areas affected by road construction and transportation-related activity.

 **Live Dashboard:** https://asphalt-air.vercel.app/

---

##  Project Objectives

- Analyse spatial and temporal patterns in PM2.5 pollution.
- Identify geographical hotspots using latitude and longitude coordinates.
- Investigate relationships between air pollution and environmental parameters such as temperature and humidity.
- Evaluate pollution severity and persistence to prioritise locations requiring attention.
- Present environmental insights through an interactive web-based dashboard.

##  Key Features

### 1. Environmental Data Processing
- Import and process structured environmental datasets in CSV and Excel formats.
- Perform data cleaning, date conversion, duplicate removal, and coordinate validation.
- Handle missing values while preserving additional dataset information.
- Support configurable column mapping for datasets with different schemas.

### 2. PM2.5 Pollution Analysis
- Analyse PM2.5 concentration patterns across geographical locations.
- Generate statistical summaries of pollution measurements.
- Examine temporal variations to understand how pollution levels change over time.

### 3. Geospatial Hotspot Identification
- Identify pollution hotspots using geographical coordinates.
- Group measurements by rounded latitude and longitude values.
- Evaluate locations based on their observed PM2.5 concentrations.
- Visualise geographical pollution patterns through an interactive map.

### 4. Environmental Correlation Analysis
- Investigate relationships between PM2.5 concentrations and environmental variables.
- Analyse temperature and humidity patterns alongside pollution measurements.
- Use statistical visualisations to explore potential environmental associations.

### 5. Intelligent Hotspot Prioritisation
- Implement a priority-ranking mechanism based on pollution severity and persistence.
- Calculate normalised pollution indicators to support comparative evaluation.
- Categorise hotspots according to their relative intervention priority.
- Present ranked locations to help identify areas requiring further investigation.

### 6. Interactive Web Dashboard
- Custom-built frontend using HTML, CSS, and JavaScript.
- Interactive geographical visualisations using Leaflet.
- Pollution statistics, heatmaps, and prioritised hotspot tables.
- Upload and analyse additional CSV and Excel datasets.
- Automatically refresh dashboard insights when the underlying local datasets change.

---

##  Technology Stack

| Component | Technologies |
|---|---|
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Data Visualisation | Matplotlib, Seaborn |
| Geospatial Visualisation | Folium, Leaflet |
| Backend | Flask |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Vercel |

---

##  Project Architecture

The application follows a data-processing and visualisation workflow:

```text
       Raw Environmental Datasets
             (CSV / XLSX)
                   |
                   v
        Data Cleaning & Processing
                   |
                   v
       Environmental Data Analysis
                   |
          +--------+--------+
          |        |        |
          v        v        v
        PM2.5   Weather   Geospatial
        Analysis Analysis  Analysis
          |        |        |
          +--------+--------+
                   |
                   v
        Hotspot Identification
                   |
                   v
       Severity & Persistence Scoring
                   |
                   v
         Priority Classification
                   |
                   v
        Interactive Web Dashboard
```

---

##  Repository Structure

```text
AsphaltAir/
│
├── data/
│   ├── raw/                 # Original environmental datasets
│   └── processed/           # Cleaned and processed outputs
│
├── frontend/                # HTML, CSS and JavaScript dashboard
│
├── reports/
│   └── figures/             # Generated analytical visualisations
│
├── src/                     # Data processing and analysis modules
│
├── tests/                   # Project tests
│
├── main.py                  # Analysis pipeline entry point
├── server.py                # Flask application and dashboard server
├── requirements.txt         # Python dependencies
├── vercel.json              # Deployment configuration
└── README.md
```

---

##  Getting Started

### Prerequisites

- Python 3.10+
- Git
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/DhruvPathak2406/AsphaltAir.git

cd AsphaltAir
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python server.py
```

Open the following address in your browser:

```text
http://localhost:8000
```

---

##  Data Requirements

The platform supports CSV and Excel datasets containing environmental measurements.

For meaningful PM2.5 hotspot analysis, datasets should include:

- Date/time information.
- PM2.5 concentration measurements.
- Latitude and longitude coordinates.
- Environmental parameters such as temperature and humidity, where available.

The hotspot-ranking mechanism requires valid geographical coordinates and at least 10 valid PM2.5 readings per rounded coordinate group.

Additional columns are retained during preprocessing.

---

## 🔬 Current Scope & Limitations

The current implementation focuses on environmental pollution analysis and hotspot prioritisation.

- PM2.5 analysis and environmental correlations are supported.
- Hotspot prioritisation currently considers pollution severity and persistence.
- Population exposure is not included in the priority score because the required data is unavailable.
- Traffic analysis is outside the current implementation scope.
- The application currently processes uploaded or locally stored datasets rather than directly connecting to physical pollution sensors or external data APIs.

---

##  Future Improvements

- Integration with real-time air quality monitoring sensors.
- Incorporation of additional environmental and meteorological datasets.
- Population-density and exposure-based risk assessment.
- Predictive modelling for identifying emerging pollution hotspots.
- Advanced spatial and temporal pollution trend analysis.
- Expanded intervention planning and reporting capabilities.

---

##  Author

**Dhruv Pathak**

Computer Science & Engineering

- GitHub: [DhruvPathak2406](https://github.com/DhruvPathak2406)
- Project Repository: [Asphalt-Air](https://github.com/DhruvPathak2406/AsphaltAir)

---

*Asphalt-Air — Turning environmental data into actionable insights for cleaner and safer urban environments.*
