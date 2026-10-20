import pandas as pd

def calculate_priority(hotspots: pd.DataFrame) -> pd.DataFrame:
    if hotspots.empty:
        hotspots = hotspots.copy()
        hotspots["ips"] = pd.Series(dtype=float)
        hotspots["priority"] = pd.Series(dtype=str)
        return hotspots

    result = hotspots.copy()
    low = result["average_pm25"].min()
    high = result["average_pm25"].max()
    if high == low:
        result["severity_score"] = 100.0
    else:
        result["severity_score"] = (result["average_pm25"] - low) / (high - low) * 100

    # Initial prototype score: pollution severity only. Traffic and population
    # exposure are excluded because the supplied data does not establish them.
    # Persistence can be added after selecting a defensible time window.
    result["ips"] = result["severity_score"].round(2)
    result["priority"] = pd.cut(
        result["ips"], bins=[-0.001, 40, 70, 100.001],
        labels=["Low", "Medium", "High"], include_lowest=True
    ).astype(str)
    return result.sort_values("ips", ascending=False).reset_index(drop=True)
