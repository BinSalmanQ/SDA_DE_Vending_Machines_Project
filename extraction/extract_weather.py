"""
VendFlow — Phase 1: Extraction
Source: Open-Meteo Historical Weather API
Owner: Alaa

Rule: this script does NOT clean, rename, or filter anything.
It only pulls raw hourly weather for each registry location and saves it,
unchanged, with a timestamp.
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import requests

REGISTRY_PATH = Path("data/normalized/machine_registry.csv")  # or wherever it lives
OUTPUT_DIR = Path("data/raw/weather")
START_DATE = "2024-01-01"
END_DATE = "2024-12-31"


def fetch_weather_raw(lat, lon, start_date, end_date):
    """Pull raw weather for one location, no cleaning or transformation."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,weathercode",
        "timezone": "auto",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def extract():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    registry = pd.read_csv(REGISTRY_PATH)
    locations = registry[["location_name", "latitude", "longitude"]].drop_duplicates()

    all_raw = []
    for _, row in locations.iterrows():
        raw_data = fetch_weather_raw(row["latitude"], row["longitude"], START_DATE, END_DATE)
        raw_df = pd.DataFrame(raw_data["hourly"])
        raw_df["latitude"] = raw_data.get("latitude")
        raw_df["longitude"] = raw_data.get("longitude")
        raw_df["location_name"] = row["location_name"]
        all_raw.append(raw_df)
        print(f"{row['location_name']}: {len(raw_df)} records")

    weather_raw_all = pd.concat(all_raw, ignore_index=True)
    final_path = OUTPUT_DIR / f"weather_raw_{timestamp}.csv"
    weather_raw_all.to_csv(final_path, index=False)
    return final_path


def main():
    print(f"[{datetime.now()}] Starting extraction: Open-Meteo weather")
    try:
        filepath = extract()
        print(f"Total records: {sum(1 for _ in open(filepath)) - 1} -> {filepath}")
        print("Done.")
    except Exception as e:
        print(f"Extraction FAILED: {e}")
        raise


if __name__ == "__main__":
    main()