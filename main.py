from src.preprocessing import run_preprocessing
from src.pollution_analysis import summarize_pollution
from src.weather_analysis import weather_correlations
from src.hotspot_detection import detect_hotspots
from src.priority_scoring import calculate_priority
from src.visualization import save_pm25_trend
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    df = run_preprocessing()
    df["timestamp"] = __import__("pandas").to_datetime(df["timestamp"], errors="coerce")

    daily = summarize_pollution(df)
    daily.to_csv(OUT / "daily_pollution_summary.csv", index=False)

    corr = weather_correlations(df)
    corr.to_csv(OUT / "weather_correlations.csv")

    hotspots = detect_hotspots(df)
    hotspots.to_csv(OUT / "hotspot_results.csv", index=False)

    priorities = calculate_priority(hotspots)
    priorities.to_csv(OUT / "intervention_priority.csv", index=False)

    save_pm25_trend(df)
    print("\nPipeline completed. Check data/processed/ and reports/figures/.")

if __name__ == "__main__":
    main()
