from pathlib import Path
from typing import Optional, Set, Tuple

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

TIMESTAMP_COLUMNS = {
    "timestamp", "datetime", "dateandtime", "recordedat", "observedat",
    "measuredat", "createdat", "collectedat", "sampledat",
    "datetimeutc",
}
DATE_COLUMNS = {
    "date", "data", "day", "measurementdate", "sampledate", "recordeddate",
    "daterecorded", "observationdate", "dateofobservation", "collectiondate",
    "datecollected", "samplingdate",
}
TIME_COLUMNS = {
    "time", "measurementtime", "timeofmeasurement", "sampletime", "recordedtime",
    "timeofobservation", "timecollected",
}


def _normalized_name(name: str) -> str:
    return "".join(character.lower() for character in name if character.isalnum())


def _find_column(
    df: pd.DataFrame,
    names: Set[str],
    prefixes: Tuple[str, ...] = (),
) -> Optional[str]:
    normalized = {column: _normalized_name(str(column)) for column in df.columns}
    for column, name in normalized.items():
        if name in names:
            return column
    for column, name in normalized.items():
        if any(name.startswith(prefix) for prefix in prefixes):
            return column
    return None


def _infer_date_column(df: pd.DataFrame) -> Optional[str]:
    for column in df.columns:
        values = df[column]
        if pd.api.types.is_datetime64_any_dtype(values):
            return column
        if pd.api.types.is_numeric_dtype(values):
            continue

        text = values.dropna().astype(str).str.strip()
        has_date_pattern = text.str.contains(
            r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}|[A-Za-z]{3,}\s+\d{1,2}",
            regex=True,
        )
        if not has_date_pattern.any():
            continue

        parsed = pd.to_datetime(values, errors="coerce", yearfirst=True)
        if parsed.notna().sum() / len(text) >= 0.5:
            return column
    return None


def _find_timestamp(df: pd.DataFrame, source: str) -> pd.Series:
    timestamp_column = _find_column(df, TIMESTAMP_COLUMNS)
    if timestamp_column is not None:
        timestamp = pd.to_datetime(df[timestamp_column], errors="coerce", yearfirst=True)
    else:
        date_column = _find_column(df, DATE_COLUMNS)
        if date_column is None:
            date_column = _infer_date_column(df)
        if date_column is None:
            raise ValueError(
                f"{source} must contain a date/time column "
                f"(for example: timestamp, datetime, or date)."
            )

        dates = pd.to_datetime(df[date_column], errors="coerce", yearfirst=True)
        time_column = _find_column(df, TIME_COLUMNS)
        if time_column is not None:
            times = pd.to_timedelta(df[time_column].astype(str), errors="coerce")
            timestamp = dates.dt.normalize() + times
        else:
            timestamp = dates

    if not timestamp.notna().any():
        raise ValueError(f"{source} does not contain any parseable date/time values.")
    return timestamp


def _read_csv_tolerant(path, source_name: Optional[str] = None, on_bad_line=None) -> pd.DataFrame:
    source_name = source_name or Path(getattr(path, "name", path)).name
    try:
        if hasattr(path, "seek"):
            path.seek(0)
        return pd.read_csv(path, encoding="utf-8-sig")
    except (pd.errors.ParserError, UnicodeDecodeError):
        print(f"WARNING: malformed CSV records detected in {source_name}; retrying with tolerant parsing.")
        if hasattr(path, "seek"):
            path.seek(0)
        return pd.read_csv(
            path,
            encoding="utf-8-sig",
            engine="python",
            on_bad_lines=on_bad_line or "warn",
        )

def load_one(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif path.suffix.lower() == ".csv":
        df = _read_csv_tolerant(path)
    else:
        raise ValueError(f"Unsupported file type: {path.name}")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def prepare(
    df: pd.DataFrame,
    source: str,
    column_mapping: Optional[dict] = None,
    allow_missing_timestamp: bool = False,
) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(column).strip() for column in df.columns]
    if not df.columns.is_unique:
        raise ValueError(f"{source} contains duplicate column names after trimming whitespace.")
    original = df.copy()
    mapping = column_mapping or {}
    allowed = {"timestamp", "time", "latitude", "longitude", "PM2.5", "TEMP.", "HUMI."}
    for field, column in mapping.items():
        if field not in allowed or column not in df.columns:
            raise ValueError(f"Invalid column mapping: {field} = {column}.")
    original_columns = set(df.columns)
    if "timestamp" in mapping:
        dates = pd.to_datetime(df[mapping["timestamp"]], errors="coerce", yearfirst=True)
        if "time" in mapping:
            times = pd.to_timedelta(df[mapping["time"]].astype(str), errors="coerce")
            dates = dates.dt.normalize() + times
        if not dates.notna().any():
            raise ValueError(f"{source} does not contain any parseable mapped date/time values.")
        df["timestamp"] = dates
    elif allow_missing_timestamp and not (
        _find_column(df, TIMESTAMP_COLUMNS)
        or _find_column(df, DATE_COLUMNS)
        or _infer_date_column(df)
    ):
        df["timestamp"] = pd.NaT
    else:
        df["timestamp"] = _find_timestamp(df, source)
    df["source_file"] = source

    aliases = {
        "latitude": ({"latitude", "lat"}, ("latitude",)),
        "longitude": ({"longitude", "lon", "long"}, ("longitude",)),
        "PM2.5": ({"pm25"}, ("pm25",)),
        "TEMP.": ({"temp", "temperature"}, ("temperature",)),
        "HUMI.": ({"humi", "humidity", "relativehumidity"}, ("humidity",)),
    }
    for canonical, (names, prefixes) in aliases.items():
        column = mapping.get(canonical) or _find_column(original, names, prefixes)
        if column is None:
            df[canonical] = np.nan
        else:
            df[canonical] = pd.to_numeric(original[column], errors="coerce")

    if df["timestamp"].notna().any():
        df = df.dropna(subset=["timestamp"]).copy()

    # Coordinates must be geographically valid. Invalid / absent coordinates
    # remain missing so pollution analysis can still use those rows, but mapping won't.
    invalid_coords = (
        df["latitude"].notna() & ~df["latitude"].between(-90, 90)
    ) | (
        df["longitude"].notna() & ~df["longitude"].between(-180, 180)
    )
    df.loc[invalid_coords, ["latitude", "longitude"]] = np.nan

    if {"Data", "Time", "latitude", "longitude", "PM2.5"}.issubset(original_columns):
        duplicate_columns = ["timestamp", "latitude", "longitude", "PM2.5", "source_file"]
    else:
        duplicate_columns = list(df.columns)
    df = df.drop_duplicates(subset=duplicate_columns)
    return df.sort_values("timestamp").reset_index(drop=True)

def run_preprocessing(output_dir: Optional[Path] = None) -> pd.DataFrame:
    processed_dir = Path(output_dir) if output_dir is not None else PROCESSED
    processed_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted([p for p in RAW.iterdir() if p.suffix.lower() in [".csv", ".xlsx", ".xls"]])
    if not paths:
        raise FileNotFoundError(f"No CSV/Excel files found in {RAW}")

    frames = []
    for path in paths:
        print(f"Reading: {path.name}")
        frames.append(prepare(load_one(path), path.name))

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    out = processed_dir / "cleaned_data.csv"
    combined.to_csv(out, index=False)

    print(f"\nSaved: {out}")
    print(f"Rows after cleaning: {len(combined):,}")
    print(f"Rows with valid coordinates: {combined[['latitude','longitude']].dropna().shape[0]:,}")
    print(f"Date range: {combined['timestamp'].min()} to {combined['timestamp'].max()}")
    if combined["PM2.5"].notna().any():
        print(f"Missing PM2.5: {combined['PM2.5'].isna().sum():,}")
    else:
        print("No PM2.5 column found; the trend chart will use numeric measurements.")
    return combined
