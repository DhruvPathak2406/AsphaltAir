import pandas as pd

def summarize_pollution(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(df["timestamp"].dt.date)["PM2.5"].agg(
        average_pm25="mean", max_pm25="max", readings="count"
    ).reset_index(names="date")
