"""
VendFlow — Data Integration Pipeline (Track 1)
Owner: Ahmed

Purpose:
    Build the unified machine registry (VM_001..VM_050) and produce
    normalized versions of the three raw datasets, so that all four
    sources (including weather, added later) can be joined by a single
    machine identifier and a common time window (2024).
"""

import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURATION — edit these before running
# ============================================================

INPUT_DIR = Path("D:\\Documents\\Certifications\\SDA DE\\Project\\data\\raw")
OUTPUT_DIR = Path("D:\\Documents\\Certifications\\SDA DE\\Project\\data\\normalized")

LOCATIONS = {
    "Brunswick Sq Mall":            {"lat": 40.50624027716083, "lon": -74.38483126763923},
    "Earle Asphalt":                {"lat": 40.17946252732867, "lon": -74.10898016488436},
    "GuttenPlans":                  {"lat": 40.464480736534945, "lon": -74.13392450835369},
    "EB Public Library":            {"lat": 40.60088764525522, "lon": -74.44251218728009},
    "New Brunswick Train Station":  {"lat": 40.5508115893351, "lon": -74.44045667148427}
}

SALES_MACHINE_TO_LOCATION = {
    # "<Device ID from raw sales CSV>": "<location name>",
    "VJ300320611": "Brunswick Sq Mall",
    "VJ300320686": "Earle Asphalt",
    "VJ300320609": "GuttenPlans",
    "VJ300320692": "EB Public Library",
    "VJ300205292": "New Brunswick Train Station"
}

TARGET_YEAR = 2024


# ============================================================
# 1. LOAD RAW DATA
# ============================================================

def load_source_data():
    """
    Read the three raw Kaggle CSVs and return them as DataFrames.

    Returns:
        (sales_df, sensors_df, perishable_df)
    """
    sales_df = pd.read_csv(INPUT_DIR / "vending_machine_sales.csv")
    sensors_df = pd.read_csv(INPUT_DIR / "smart_manufacturing_data.csv")
    perishable_df = pd.read_csv(INPUT_DIR / "perishable_goods_management.csv")
    return sales_df, sensors_df, perishable_df


# ============================================================
# 2. BUILD THE MACHINE REGISTRY (the "translator")
# ============================================================

def build_machine_registry():
    """
    Produce the 50-row master table linking every physical machine
    (VM_001..VM_050) to its identifiers in each source.

    Layout:
        VM_001..VM_010 → Brunswick Sq Mall
        VM_011..VM_020 → Earle Asphalt
        VM_021..VM_030 → GuttenPlans
        VM_031..VM_040 → EB Public Library
        VM_041..VM_050 → New Brunswick Train Station

    Sensor and perishable ID mapping is 1-to-1 by number:
        VM_001 → machine_1 (sensors) + store_1 (perishable)
        VM_050 → machine_50 + store_50

    Returns:
        DataFrame with columns:
        [official_id, location_name, latitude, longitude,
         sales_device_id, sensor_machine_id, perishable_store_id]
    """
    machine_registry = []  # list, not dict
    for i, (location_name, coords) in enumerate(LOCATIONS.items(), start=1):    
        for j in range(10):
            vm_num = i * 10 - 9 + j
            official_id = f"VM_{vm_num:03d}"
            sales_device_id = next(
                (k for k, v in SALES_MACHINE_TO_LOCATION.items() if v == location_name),
                None
            )
            machine_registry.append({
                "official_id": official_id,
                "location_name": location_name,
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "sales_device_id": sales_device_id,
                "sensor_machine_id": vm_num,
                "perishable_store_id": f"STORE_{vm_num:03d}"
            })
    return pd.DataFrame(machine_registry)

# ============================================================
# 3. NORMALIZE SALES DATA (clone 5 → 50, shift 2022 → 2024)
# ============================================================

def normalize_sales(sales_df, registry):
    """
    Take the raw 5-machine sales data and produce 50-machine sales data
    by cloning each source machine's transactions across the 10 physical
    machines assigned to its location. Shift dates from 2022 to 2024.

    Row count: ~9,618 × 10 ≈ 96,180 rows.

    Returns:
        DataFrame with an official_id column (VM_XXX) replacing Device ID,
        and dates shifted to 2024.
    """
    sales_df = sales_df.copy()
    cloned_frames = []
    for device_id in sales_df['Device ID'].unique():
        device_rows = sales_df[sales_df['Device ID'] == device_id]
        matching_vms = registry[registry['sales_device_id'] == device_id]['official_id']
        for vm in matching_vms:
            cloned = device_rows.copy()
            cloned['official_id'] = vm
            cloned_frames.append(cloned)
    result = pd.concat(cloned_frames, ignore_index=True)
    result['TransDate'] = shift_year(result['TransDate'], 2022, 2024)
    result = result.drop(columns=["Device ID"])
    return result


def shift_year(date_series, from_year, to_year):
    """
    Move all dates in a Series from `from_year` to `to_year`.

    Note: day-of-week will not be preserved (Jan 1 2022 = Saturday,
    Jan 1 2024 = Monday).
    Feb 29 is safe here — 2022 has no Feb 29, so nothing gets lost
    when shifting to leap-year 2024.
    """
    date_series = pd.to_datetime(date_series)
    return date_series.apply(lambda d: d.replace(year=to_year))


# ============================================================
# 4. NORMALIZE SENSOR DATA
# ============================================================

def normalize_sensors(sensors_df, registry):
    """
    Map sensor machine_id (1..50) → official_id (VM_001..VM_050) and
    shift timestamps from Jan-Mar 2025 → Jan-Mar 2024.

    Returns:
        DataFrame with an official_id column and shifted timestamps.
    """
    sensors_df = sensors_df.copy()
    lookup = dict(zip(registry['sensor_machine_id'], registry['official_id']))
    sensors_df['official_id'] = sensors_df['machine_id'].map(lookup)
    sensors_df['timestamp'] = shift_year(sensors_df['timestamp'], 2025, 2024)
    return sensors_df.drop(columns=["machine_id"])


# ============================================================
# 5. NORMALIZE PERISHABLE DATA
# ============================================================

def normalize_perishable(perishable_df, registry):
    """
    Filter perishable data to 2024 rows only, then map store_id → VM_XXX.

    Returns:
        DataFrame with an official_id column, restricted to 2024.
    """
    perishable_df = perishable_df.copy()
    perishable_df['transaction_date'] = pd.to_datetime(perishable_df['transaction_date'])
    perishable_df = perishable_df[perishable_df['transaction_date'].dt.year == 2024]
    lookup = dict(zip(registry['perishable_store_id'], registry['official_id']))
    perishable_df['official_id'] = perishable_df['store_id'].map(lookup)
    return perishable_df.drop(columns=["store_id"])


# ============================================================
# 6. SAVE OUTPUTS
# ============================================================

def save_outputs(registry, sales, sensors, perishable):
    """Write all four outputs to OUTPUT_DIR as CSVs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    registry.to_csv(OUTPUT_DIR / "machine_registry.csv", index=False)
    sales.to_csv(OUTPUT_DIR / "sales_normalized.csv", index=False)
    sensors.to_csv(OUTPUT_DIR / "sensors_normalized.csv", index=False)
    perishable.to_csv(OUTPUT_DIR / "perishable_normalized.csv", index=False)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Loading source data...")
    sales_df, sensors_df, perishable_df = load_source_data()

    print("Building machine registry...")
    registry = build_machine_registry()

    print("Normalizing sales...")
    sales_normalized = normalize_sales(sales_df, registry)

    print("Normalizing sensors...")
    sensors_normalized = normalize_sensors(sensors_df, registry)

    print("Normalizing perishable inventory...")
    perishable_normalized = normalize_perishable(perishable_df, registry)

    print("Saving outputs...")
    save_outputs(registry, sales_normalized, sensors_normalized, perishable_normalized)

    print(f"Done. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()