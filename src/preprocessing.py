from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

EXPECTED = [
    "Data", "Time", "latitude", "longitude", "PM1", "PM2.5", "PM10",
    "CO2", "SO2", "NO2", "CO", "O3", "H2S", "TEMP.", "HUMI."
]

def _read_csv_tolerant(path: Path) -> pd.DataFrame:
    # The supplied CSV has malformed quoted lines. First try strict parsing;
    # if it fails, use the Python parser and skip malformed records with a warning.
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except (pd.errors.ParserError, UnicodeDecodeError):
        print(f"WARNING: malformed CSV records detected in {path.name}; retrying with tolerant parsing.")
        return pd.read_csv(path, encoding="utf-8-sig", engine="python", on_bad_lines="warn")

def load_one(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = _read_csv_tolerant(path)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def prepare(df: pd.DataFrame, source: str) -> pd.DataFrame:
    missing_cols = [c for c in EXPECTED if c not in df.columns]
    if missing_cols:
        raise ValueError(f"{source} is missing expected columns: {missing_cols}")

    df = df[EXPECTED].copy()
    df["source_file"] = source

    # Parse date/time in separate steps because the two files use different date formats.
    date_text = df["Data"].astype(str).str.strip()
    df["date"] = pd.to_datetime(date_text, errors="coerce", yearfirst=True)
    time_text = df["Time"].astype(str).str.strip()
    df["time"] = pd.to_timedelta(time_text, errors="coerce")
    df["timestamp"] = df["date"].dt.normalize() + df["time"]

    numeric_cols = ["latitude", "longitude", "PM1", "PM2.5", "PM10", "CO2",
                    "SO2", "NO2", "CO", "O3", "H2S", "TEMP.", "HUMI."]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows without a valid timestamp or PM2.5 value.
    df = df.dropna(subset=["timestamp", "PM2.5"]).copy()

    # Coordinates must be geographically valid. Invalid / absent coordinates
    # remain missing so pollution analysis can still use those rows, but mapping won't.
    invalid_coords = (
        df["latitude"].notna() & ~df["latitude"].between(-90, 90)
    ) | (
        df["longitude"].notna() & ~df["longitude"].between(-180, 180)
    )
    df.loc[invalid_coords, ["latitude", "longitude"]] = np.nan

    # This project currently focuses on PM2.5, temperature, humidity and geography.
    # Keep all available columns; don't silently remove high values as outliers.
    df = df.drop_duplicates(subset=["timestamp", "latitude", "longitude", "PM2.5", "source_file"])
    return df.sort_values("timestamp").reset_index(drop=True)

def run_preprocessing() -> pd.DataFrame:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    paths = sorted([p for p in RAW.iterdir() if p.suffix.lower() in [".csv", ".xlsx", ".xls"]])
    if not paths:
        raise FileNotFoundError(f"No CSV/Excel files found in {RAW}")

    frames = []
    for path in paths:
        print(f"Reading: {path.name}")
        frames.append(prepare(load_one(path), path.name))

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    out = PROCESSED / "cleaned_data.csv"
    combined.to_csv(out, index=False)

    print(f"\nSaved: {out}")
    print(f"Rows after cleaning: {len(combined):,}")
    print(f"Rows with valid coordinates: {combined[['latitude','longitude']].dropna().shape[0]:,}")
    print(f"Date range: {combined['timestamp'].min()} to {combined['timestamp'].max()}")
    print(f"Missing PM2.5: {combined['PM2.5'].isna().sum():,}")
    return combined
