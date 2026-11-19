from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports" / "figures"


def _measurement_columns(df):
    pm25 = pd.to_numeric(df["PM2.5"], errors="coerce") if "PM2.5" in df else None
    if pm25 is not None and pm25.notna().any():
        return {"PM2.5": pm25}

    excluded = {
        "timestamp", "datetime", "dateandtime", "recordedat", "observedat",
        "measuredat", "createdat", "collectedat", "sampledat", "datetimeutc",
        "date", "data", "day", "measurementdate", "sampledate", "recordeddate",
        "daterecorded", "observationdate", "dateofobservation", "collectiondate",
        "datecollected", "samplingdate", "time", "measurementtime",
        "timeofmeasurement", "sampletime", "recordedtime", "timeofobservation",
        "timecollected", "latitude", "lat", "longitude", "lon", "long",
        "sourcefile", "id", "index", "recordid", "serialnumber", "stationid",
    }
    measurements = {}
    for column in df.columns:
        name = "".join(character.lower() for character in str(column) if character.isalnum())
        values = pd.to_numeric(df[column], errors="coerce")
        if (
            name in excluded
            or name.endswith("id")
            or pd.api.types.is_datetime64_any_dtype(df[column])
            or not values.notna().any()
        ):
            continue
        measurements[str(column)] = values
    return measurements


def save_pm25_trend(df, output_dir=None):
    if "timestamp" not in df.columns:
        raise ValueError("The dataset must contain a parsed 'timestamp' column.")

    timestamps = pd.to_datetime(df["timestamp"], errors="coerce")
    measurements = _measurement_columns(df)
    if not measurements:
        raise ValueError("The dataset must contain at least one numeric measurement column.")

    values = pd.DataFrame(measurements, index=df.index)
    valid_timestamps = timestamps.notna()
    daily = values.loc[valid_timestamps].groupby(timestamps.loc[valid_timestamps].dt.date).mean()
    daily = daily.dropna(axis=1, how="all")
    if daily.empty:
        raise ValueError("No numeric measurements have valid date/time values to plot.")

    figures_dir = Path(output_dir) if output_dir is not None else FIGURES
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5))
    if len(daily.columns) == 1:
        column = daily.columns[0]
        daily[column].plot(ax=ax)
        if column == "PM2.5":
            ax.set_title("Daily Average PM2.5")
            ax.set_ylabel("PM2.5 (dataset units; verify instrument units)")
        else:
            ax.set_title(f"Daily Average {column}")
            ax.set_ylabel(f"{column} (dataset units)")
    else:
        daily.plot(ax=ax)
        ax.set_title("Daily Average Measurements")
        ax.set_ylabel("Daily average (dataset units)")
        ax.legend(title="Measurement")
    ax.set_xlabel("Date")
    fig.tight_layout()
    fig.savefig(figures_dir / "daily_pm25_trend.png", dpi=150)
    plt.close(fig)
