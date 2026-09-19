# VendFlow — Data Cleaning & Validation (Track 2)
 
**Owner:** Reema & Alaa
**Track:** Data Cleaning & Validation
**Status:** Complete
 
This module inspects and cleans three of the raw VendFlow data sources — sales, perishable inventory, and sensor telemetry — before they are consumed by the rest of the pipeline. (Weather is handled separately, as its own track.) Each source has its own script; every script applies the same discipline: inspect first, document what's wrong, then fix only what's documented.
 
## What these scripts do
 
The three raw sources come from different systems with different quality issues: missing values, inconsistent formats, and physically invalid readings. None of them share IDs or a common time window — that part is handled separately by `build_integration.py` (Track 1). This track's job is narrower: make each source internally correct and trustworthy on its own, before any cross-source joins happen.
 
- `clean_sales.py` — standardizes columns, fixes missing product/category/price fields, removes duplicates.
- `clean_inventory.py` — validates dates, ranges and flag columns, removes duplicates.
- `clean_sensors.py` — fixes an invalid negative-vibration reading, removes duplicates, sorts for trend analysis.
## Repository structure
 
```
.
├── clean_sales.py
├── clean_inventory.py
├── clean_sensors.py
├── data/
│   ├── raw/                        # source CSVs
│   │   ├── vending_machine_sales.csv
│   │   ├── perishable_goods_management.csv
│   │   └── smart_manufacturing_data.csv
│   └── clean/                      # output CSVs (produced by these scripts)
│       ├── sales_clean.csv
│       ├── perishable_goods_clean.csv
│       └── sensors_clean.csv
└── README.md
```
 
## Prerequisites
 
- Python 3.10+
- pandas
```
pip install pandas
```
 ## How to run
 
Each script is independent and can be run on its own:
```
python clean_sales.py
python clean_inventory.py
python clean_sensors.py
```
 
## Data sources
 
| Source | Raw rows | Key issues found |
|---|---|---|
| Vending Machine Sales | 9,617 | 267 missing categories, 6 missing products, 3 missing prices |
| Managing Perishable Inventory | 100,000 | none beyond standard whitespace/duplicate checks |
| Smart Manufacturing IoT | 100,000 | 37 physically invalid negative vibration readings |

 
## Outputs
 
### clean_sales.csv (9,617 rows)
 
| Column | Change |
|---|---|
| all column names | standardized to snake_case |
| `product`, `category` | missing values filled as `"Unknown"` (explicit placeholder, not guessed) |
| `mprice` | missing values filled from `rprice` (same coil, same product) |
| `transdate`, `prcd_date` | converted to proper datetime |
| text columns | whitespace stripped |
 
###  clean_inventory.csv (29,857 rows after dedup)
 
| Column | Change |
|---|---|
| `transaction_date`, `expiration_date` | converted to proper datetime, checked for logical ordering |
| ID/text columns | whitespace stripped |
| percentage & flag columns | verified in valid range (0–100 / 0–1) — no fix needed |
 
### clean_sensors.csv (100,000 rows)
 
| Column | Change |
|---|---|
| `vibration` | 37 negative values corrected with `.abs()` — sign treated as a data-entry error, magnitude kept |
| `timestamp` | converted to proper datetime |
| `failure_type` | whitespace stripped |
| row order | sorted by `machine_id`, then `timestamp` |

 ## Design decisions
  
**Fix vs. drop, decided per case, not by default.** For sensors' negative vibration (37/100,000 ≈ 0.04% of rows), we corrected the sign instead of dropping the rows, since vibration is a magnitude and no other field in those rows looked invalid. For sales' missing category/product (267/9,617), we filled with `"Unknown"` rather than dropping, since the rest of each row was valid and usable.
 
**No cross-source assumptions made here.** These scripts do not touch IDs, do not shift dates, and do not assume any relationship between sources — that logic belongs to Track 1 (`build_integration.py`). This track only validates each source against itself.
 




