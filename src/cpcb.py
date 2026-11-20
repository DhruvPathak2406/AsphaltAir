import json
import math
import os
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


RESOURCE_URL = "https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
POLLUTANTS = {
    "PM2.5": "average_pm25",
    "PM10": "average_pm10",
    "CO": "average_co",
    "SO2": "average_so2",
    "NO2": "average_no2",
    "OZONE": "average_o3",
    "O3": "average_o3",
}


class CPCBError(Exception):
    pass


def _location(value, field, required=False):
    value = value.strip()
    if (required and not value) or len(value) > 100 or any(ord(c) < 32 for c in value):
        raise ValueError(f"Enter a valid {field} (up to 100 characters).")
    return value


def _fetch_records(city, state, api_key):
    records = []
    offset = 0
    for _ in range(100):
        params = {
            "api-key": api_key, "format": "json", "limit": 1000,
            "offset": offset, "filters[city]": city,
        }
        if state:
            params["filters[state]"] = state
        try:
            request = Request(
                RESOURCE_URL + "?" + urlencode(params),
                headers={"User-Agent": "AsphaltAir/1.0", "Accept": "application/json"},
            )
            with urlopen(request, timeout=20) as response:
                body = response.read(4 * 1024 * 1024 + 1)
            if len(body) > 4 * 1024 * 1024:
                raise CPCBError("CPCB returned an unexpectedly large response.")
            data = json.loads(body)
        except HTTPError as error:
            raise CPCBError(f"CPCB API returned HTTP {error.code}. Check the API key and service status.") from None
        except (URLError, TimeoutError, OSError):
            raise CPCBError("Could not reach the CPCB data service.") from None
        except (ValueError, UnicodeDecodeError):
            raise CPCBError("CPCB returned invalid JSON.") from None
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise CPCBError("CPCB returned an unexpected response.")
        page = data["records"]
        try:
            total = int(data["total"])
        except (KeyError, TypeError, ValueError):
            raise CPCBError("CPCB response is missing its record count.") from None
        if total < 0:
            raise CPCBError("CPCB returned an invalid record count.")
        records.extend(page)
        offset += len(page)
        if offset >= total:
            return records
        if not page:
            raise CPCBError("CPCB returned an incomplete page of station data.")
    raise CPCBError("CPCB returned too many pages; narrow the city and state.")


def get_station_data(city, state=""):
    city = _location(city, "city", required=True)
    state = _location(state, "state")
    api_key = os.environ.get("DATA_GOV_IN_API_KEY", "").strip()
    if not api_key:
        raise CPCBError("Set the DATA_GOV_IN_API_KEY environment variable to use CPCB data.")
    records = _fetch_records(city, state, api_key)
    stations = {}
    skipped = 0
    for record in records:
        if not isinstance(record, dict):
            skipped += 1
            continue
        field = POLLUTANTS.get(str(record.get("pollutant_id", "")).upper())
        if field is None:
            continue
        try:
            lat, lon = float(record["latitude"]), float(record["longitude"])
            timestamp = datetime.strptime(record["last_update"], "%d-%m-%Y %H:%M:%S")
            station = record["station"].strip()
            if not station or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError
        except (KeyError, TypeError, ValueError, AttributeError):
            skipped += 1
            continue
        raw_value = record.get("avg_value", record.get("pollutant_avg"))
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        key = (station, lat, lon)
        entry = stations.setdefault(key, {
            "station_name": station, "latitude_group": lat, "longitude_group": lon,
            "source_times": {}, "_parsed_times": {},
        })
        if field not in entry["_parsed_times"] or timestamp > entry["_parsed_times"][field]:
            entry[field] = value
            entry["source_times"][field] = record["last_update"]
            entry["_parsed_times"][field] = timestamp
    result = []
    for entry in stations.values():
        del entry["_parsed_times"]
        result.append(entry)
    return {"city": city, "state": state, "stations": result, "skipped_records": skipped}
