# VendFlow — Data Integration (Track 1)

> **Owner:** Ahmed Alqunber
> **Track:** Data Integration & Pipeline Architecture
> **Status:** Complete

This module builds the **unified machine registry** for VendFlow — the translator
that links four disconnected data sources (sales, sensor telemetry, perishable
inventory, and weather) through a single machine identifier and a common time
window. Everything downstream in the VendFlow pipeline joins against the outputs
of this script.

---

## What this script does

The four source datasets weren't designed to share IDs. Sales calls a machine
`VJ300320611`; sensors call it `machine_1`; perishable inventory calls it
`STORE_001`; weather knows nothing about machines and only about coordinates.

`build_integration.py`:

1. Invents a single official identifier (`VM_001` … `VM_050`) for every physical
   machine in a synthetic 50-machine fleet.
2. Maps every source's identifier to that official ID.
3. Assigns each machine to one of 5 real New Jersey locations (with real
   latitude/longitude).
4. Clones the 5-machine sales pattern across the 50-machine fleet.
5. Shifts all timestamps into a common analytical year (2024) so cross-source
   joins are possible.
6. Writes four normalized CSVs that the rest of the pipeline consumes.

---

## Repository structure
.
├── build_integration.py # main script (this module)
├── data/
│ ├── raw/ # source CSVs (see "Data sources" below)
│ │ ├── vending_machine_sales.csv
│ │ ├── smart_manufacturing_data.csv
│ │ └── perishable_goods_management.csv
│ └── normalized/ # output CSVs (produced by this script)
│ ├── machine_registry.csv
│ ├── sales_normalized.csv
│ ├── sensors_normalized.csv
│ └── perishable_normalized.csv
└── README.md

---

## Prerequisites

- Python 3.10+
- pandas

```bash
pip install pandas
```

---

## How to run

1. Download the three source CSVs (links below) into `data/raw/`.
2. Edit the `CONFIGURATION` block at the top of `build_integration.py` to point
   `INPUT_DIR` and `OUTPUT_DIR` to your local paths.
3. Run:

```bash
python build_integration.py
```

Expected output:
Loading source data...
Building machine registry...
Normalizing sales...
Normalizing sensors...
Normalizing perishable inventory...
Saving outputs...
Done. Outputs written to data/normalized

---

## Data sources

| Source                              | Rows        | Original ID          | Coverage       |
| ----------------------------------- | ----------- | -------------------- | -------------- |
| [Vending Machine Sales][sales]      | 9,617       | `Device ID` (5 unique) | Full year 2022 |
| [Smart Manufacturing IoT][iot]      | 100,000     | `machine_id` (1–50)  | Jan–Mar 2025   |
| [Managing Perishable Inventory][inv] | 100,000    | `store_id` (STORE_001–STORE_050) | 2023–2025      |
| [Open-Meteo Historical Weather API][meteo] | on demand | latitude, longitude | Any year       |

[sales]: https://www.kaggle.com/datasets/awesomeasingh/vending-machine-sales
[iot]: https://www.kaggle.com/datasets/ziya07/smart-manufacturing-iot-cloud-monitoring-dataset
[inv]: https://www.kaggle.com/datasets/minahilfatima12328/managing-perishable-inventory-data
[meteo]: https://open-meteo.com/en/docs/historical-weather-api

Weather is not consumed by this script — it's fetched by Track 5 using the
locations stored in `machine_registry.csv`.

---

## Outputs

### `machine_registry.csv` (50 rows)

The master translator. One row per physical machine.

| Column                | Type   | Description                                    |
| --------------------- | ------ | ---------------------------------------------- |
| `official_id`         | string | Unified fleet ID: `VM_001` … `VM_050`.         |
| `location_name`       | string | One of the 5 NJ locations.                     |
| `latitude`            | float  | For weather API queries.                       |
| `longitude`           | float  | For weather API queries.                       |
| `sales_device_id`     | string | Original ID in `vending_machine_sales.csv`.    |
| `sensor_machine_id`   | int    | Original ID in `smart_manufacturing_data.csv`. |
| `perishable_store_id` | string | Original ID in `perishable_goods_management.csv`. |

### `sales_normalized.csv` (96,170 rows)

Sales transactions cloned across the 50-machine fleet, with dates in 2024.
Original `Device ID` column dropped; new `official_id` column added.

### `sensors_normalized.csv` (100,000 rows)

Sensor readings mapped to `official_id`, timestamps shifted from Jan–Mar 2025
to Jan–Mar 2024. Original `machine_id` column dropped.

### `perishable_normalized.csv` (~49,986 rows)

Perishable inventory events filtered to 2024 only (originals span 2023–2025),
with `store_id` mapped to `official_id`.

---

## Design decisions

### Fleet expansion: 5 → 50 machines

The sales dataset has only 5 unique machines; the sensor and perishable datasets
have 50 each. To model a realistic fleet-scale operation, we expand the 5
sales machines to 50 by cloning each sales machine's transaction pattern across
10 physical machines at its assigned location.

**Assignment rule:** one sales machine per location, feeding 10 physical
machines. Brunswick Sq Mall originally had 2 Device IDs in the raw sales data;
one was retained and one was reassigned to the newly added New Brunswick Train
Station location.

### 5 physical locations

| Location                     | Machines             | Source                                    |
| ---------------------------- | -------------------- | ----------------------------------------- |
| Brunswick Sq Mall            | `VM_001`–`VM_010`   | Real location from sales dataset          |
| Earle Asphalt                | `VM_011`–`VM_020`   | Real location from sales dataset          |
| GuttenPlans                  | `VM_021`–`VM_030`   | Real location from sales dataset          |
| EB Public Library            | `VM_031`–`VM_040`   | Real location from sales dataset          |
| New Brunswick Train Station  | `VM_041`–`VM_050`   | Added to reach a 50-machine fleet         |

All 5 locations sit within a ~30-mile radius in Middlesex/Monmouth County, NJ.

### Time normalization: everything → 2024

The three raw datasets don't overlap in time (sales: 2022, sensors: Jan–Mar
2025, perishable: 2023–2025). Without normalization, cross-source joins produce
zero rows.

**Approach:**
- Sales: shift 2022 → 2024 (day-of-week alignment is not preserved).
- Sensors: shift Jan–Mar 2025 → Jan–Mar 2024 (time-of-day preserved).
- Perishable: filter to 2024 rows only (no shift needed).
- Weather (Track 5): fetch full 2024 for each location's coordinates.

Sensor coverage is intentionally limited to Q1 2024 — modeled as if telemetry
was retrofitted onto the fleet in a Q1 pilot. Downstream code should handle
"no sensor data outside Jan–Mar" as a normal case.

### Cross-source ID mapping (1-to-1 by number)

Since neither the sensor nor the perishable dataset was designed to share IDs
with the sales dataset, we assign them positionally:

| Registry            | Sensor source  | Perishable source |
| ------------------- | -------------- | ----------------- |
| `VM_001`            | `machine_id=1` | `STORE_001`       |
| `VM_002`            | `machine_id=2` | `STORE_002`       |
| …                   | …              | …                 |
| `VM_050`            | `machine_id=50`| `STORE_050`       |

This is a synthetic pairing, not a real correspondence. It is documented here
and in the script so no analyst mistakes it for a discovered relationship.

---

## Assumptions & limitations

- **Cloned sales patterns are identical across each location's 10 machines.**
  Every VM at Brunswick Sq Mall has the same transaction history as every
  other VM at Brunswick Sq Mall. A real fleet would have machine-level
  variation; this is a modeling simplification.
- **Day-of-week alignment is not preserved when shifting sales from 2022 to
  2024** (e.g., Jan 1 2022 is a Saturday; Jan 1 2024 is a Monday). Analyses
  that depend on real day-of-week seasonality should note this.
- **Weather granularity vs sales granularity:** sales are transaction-level
  (many per hour), weather is hourly. Track 5 handles the join by rounding
  transaction timestamps to the containing hour.

---

## Consuming these outputs (for teammates)

- **Every downstream table joins on `official_id`.** Never join on the raw
  `Device ID`, `machine_id`, or `store_id` columns — those have been dropped
  from the normalized files.
- **All timestamps are in 2024.** Original dates are lost by design.
- **`machine_registry.csv` is the source of truth for `dim_machine`.**
  Alaa's warehouse design (Track 3) should build `DIM_MACHINE` directly from
  this file.

---

## Team

| Track                             | Owner                    |
| --------------------------------- | ------------------------ |
| 1. Data integration               | Ahmed Alqunber           |
| 2. Data cleaning & validation     | Reema Mousa, Alaa Bondagji |
| 3. Data warehouse design          | Atheer Alghamdi          |
| 4. Transformations & metrics      | {{owner}}                |
| 5. Weather enrichment             | {{owner}}                |
| 6. Dashboard & visualization      | {{owner}}                   |
| 7. Documentation & presentation   | Shared                   |