from src.preprocessing import run_preprocessing
from src.pollution_analysis import summarize_pollution
from src.weather_analysis import weather_correlations
from src.hotspot_detection import detect_hotspots
from src.priority_scoring import calculate_priority
from src.visualization import save_pm25_trend
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed"


def main(output_dir=None):
    out_dir = Path(output_dir) if output_dir is not None else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    df = run_preprocessing(out_dir) if output_dir is not None else run_preprocessing()
    df["timestamp"] = __import__("pandas").to_datetime(df["timestamp"], errors="coerce")

    if df["PM2.5"].notna().any():
        daily = summarize_pollution(df)
    else:
        daily = __import__("pandas").DataFrame(
            columns=["date", "average_pm25", "max_pm25", "readings"]
        )
    daily.to_csv(out_dir / "daily_pollution_summary.csv", index=False)

    corr = weather_correlations(df)
    corr.to_csv(out_dir / "weather_correlations.csv")

    hotspots = detect_hotspots(df)
    hotspots.to_csv(out_dir / "hotspot_results.csv", index=False)

    priorities = calculate_priority(hotspots)
    priorities.to_csv(out_dir / "intervention_priority.csv", index=False)

    if output_dir is not None:
        save_pm25_trend(df, out_dir / "figures")
    else:
        save_pm25_trend(df)
    print(f"\nPipeline completed. Check {out_dir} and the figures directory.")

if __name__ == "__main__":
    main()
