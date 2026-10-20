import pandas as pd

def detect_hotspots(df: pd.DataFrame, min_readings: int = 10) -> pd.DataFrame:
    geo = df.dropna(subset=["latitude", "longitude", "PM2.5"]).copy()
    # Rounded coordinates group repeated measurements at approximately the same point.
    geo["latitude_group"] = geo["latitude"].round(4)
    geo["longitude_group"] = geo["longitude"].round(4)
    result = geo.groupby(["latitude_group", "longitude_group"]).agg(
        average_pm25=("PM2.5", "mean"),
        max_pm25=("PM2.5", "max"),
        readings=("PM2.5", "count"),
        average_temp=("TEMP.", "mean"),
        average_humidity=("HUMI.", "mean"),
    ).reset_index()
    result = result[result["readings"] >= min_readings]
    return result.sort_values("average_pm25", ascending=False).reset_index(drop=True)
