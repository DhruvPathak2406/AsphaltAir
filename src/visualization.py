from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "reports" / "figures"

def save_pm25_trend(df):
    FIGURES.mkdir(parents=True, exist_ok=True)
    daily = df.groupby(df["timestamp"].dt.date)["PM2.5"].mean()
    fig, ax = plt.subplots(figsize=(11, 5))
    daily.plot(ax=ax)
    ax.set_title("Daily Average PM2.5")
    ax.set_xlabel("Date")
    ax.set_ylabel("PM2.5 (dataset units; verify instrument units)")
    fig.tight_layout()
    fig.savefig(FIGURES / "daily_pm25_trend.png", dpi=150)
    plt.close(fig)
