import pandas as pd

def weather_correlations(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["PM2.5", "TEMP.", "HUMI."]
    usable = df[cols].apply(pd.to_numeric, errors="coerce")
    return usable.corr(method="pearson")
