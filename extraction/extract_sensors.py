"""
VendFlow — Phase 1: Extraction
Source: Kaggle — Vending Machine Sales
Owner: Ahmed

Rule: this script does NOT clean, rename, or filter anything.
It only pulls the raw file and saves it, unchanged, with a timestamp.

Auth setup (one-time, per machine):
Either: run `kaggle auth login` in your terminal (OAuth, recommended)
Or: place a Kaggle API token at ~/.kaggle/kaggle.json
See: https://www.kaggle.com/settings/api
"""

from pathlib import Path
from datetime import datetime
import pandas as pd
import kaggle  # pip install kaggle

# ============================================================
# CONFIGURATION
# ============================================================

KAGGLE_DATASET = "ziya07/smart-manufacturing-iot-cloud-monitoring-dataset"
OUTPUT_DIR = Path("data/raw/sensors")
DATASET_LABEL = "smart_manufacturing_data"


def extract():
    """
    Download the dataset from Kaggle and save it with a timestamped
    filename. Returns the path to the saved file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    files_before = set(OUTPUT_DIR.glob("*.csv"))
    kaggle.api.dataset_download_files(KAGGLE_DATASET, path=OUTPUT_DIR, unzip=True)
    files_after = set(OUTPUT_DIR.glob("*.csv"))

    new_files = files_after - files_before
    if len(new_files) != 1:
        raise RuntimeError(
            f"Expected exactly 1 new CSV, found {len(new_files)}: {new_files}"
        )
    downloaded_file = new_files.pop()
    final_path = OUTPUT_DIR / f"{DATASET_LABEL}_{timestamp}.csv"
    downloaded_file.rename(final_path)
    return final_path


def log_result(filepath):
    """
    Read the row count of the saved file (just to log it — this is NOT
    cleaning, just a receipt of what was pulled) and print a summary.
    """
    count = pd.read_csv(filepath).shape[0]
    print(f"Extracted {count} rows -> {filepath}")


def main():
    print(f"[{datetime.now()}] Starting extraction: {KAGGLE_DATASET}")
    try:
        filepath = extract()
        log_result(filepath)
        print("Done.")
    except Exception as e:
        print(f"Extraction FAILED: {e}")
        raise


if __name__ == "__main__":
    main()