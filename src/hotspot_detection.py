import pandas as pd

def detect_hotspots(df: pd.DataFrame, min_readings: int = 10) -> pd.DataFrame:
    geo = df.dropna(subset=["latitude", "longitude"]).copy()
    pollutants = {
        "average_pm10": "PM10",
        "average_co2": "CO2",
        "average_so2": "SO2",
        "average_no2": "NO2",
        "average_co": "CO",
        "average_o3": "O3",
        "average_h2s": "H2S",
    }
    for column in pollutants.values():
        if column not in geo:
            geo[column] = float("nan")
        else:
            geo[column] = pd.to_numeric(geo[column], errors="coerce")
    if "estimated_speed_kmh" not in geo:
        geo["estimated_speed_kmh"] = float("nan")
    # Rounded coordinates group repeated measurements at approximately the same point.
    geo["latitude_group"] = geo["latitude"].round(4)
    geo["longitude_group"] = geo["longitude"].round(4)
    groups = ["latitude_group", "longitude_group"]
    pollutant_averages = geo.groupby(groups).agg(
        **{name: (column, "mean") for name, column in pollutants.items()}
    )
    geo = geo.dropna(subset=["PM2.5"])
    result = geo.groupby(groups).agg(
        average_pm25=("PM2.5", "mean"),
        max_pm25=("PM2.5", "max"),
        readings=("PM2.5", "count"),
        average_temp=("TEMP.", "mean"),
        average_humidity=("HUMI.", "mean"),
        average_speed_kmh=("estimated_speed_kmh", "mean"),
        speed_pm25_pairs=("estimated_speed_kmh", "count"),
    ).reset_index()
    result = result[result["readings"] >= min_readings]
    result = result.merge(pollutant_averages, on=groups, how="left")
    paired = geo.dropna(subset=["estimated_speed_kmh"])
    if paired.empty:
        result["speed_pm25_correlation"] = float("nan")
    else:
        correlations = paired.groupby(["latitude_group", "longitude_group"])[
            ["estimated_speed_kmh", "PM2.5"]
        ].apply(
            lambda group: group["estimated_speed_kmh"].corr(group["PM2.5"])
            if len(group) >= 3 and group["estimated_speed_kmh"].nunique() > 1
            and group["PM2.5"].nunique() > 1 else float("nan")
        )
        correlations.name = "speed_pm25_correlation"
        result = result.merge(correlations, on=["latitude_group", "longitude_group"], how="left")
    return result.sort_values("average_pm25", ascending=False).reset_index(drop=True)
