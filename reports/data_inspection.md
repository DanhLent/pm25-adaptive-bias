# Data Inspection

Original CSV files were not modified. Root CSV files were copied into `data/raw/` when missing.
This report inspects only CSV files under `data/raw/` to avoid duplicate root/raw reporting.

## open-meteo-10.90N106.80E21m.csv

- Path: `C:\Users\danhlee\Documents\pm_25_pj\data\raw\open-meteo-10.90N106.80E21m.csv`
- Detected header row: 4
- Shape: (11976, 2)
- Inferred role: `cams`

### Detected Source Metadata

- Latitude: `10.900002`
- Longitude: `106.80002`
- Elevation: `21.0`
- Timezone: `Asia/Ho_Chi_Minh`
- UTC offset seconds: `25200.0`

### Columns

`time`, `pm2_5 (μg/m³)`

### Dtypes

| column | dtype |
| --- | --- |
| time | str |
| pm2_5 (μg/m³) | float64 |

### First 5 Rows

| time | pm2_5 (μg/m³) |
| --- | --- |
| 2025-01-01T00:00 | 31.4 |
| 2025-01-01T01:00 | 34.1 |
| 2025-01-01T02:00 | 34.3 |
| 2025-01-01T03:00 | 33.5 |
| 2025-01-01T04:00 | 31.1 |

### Missing Values

| column | missing |
| --- | --- |
| time | 0 |
| pm2_5 (μg/m³) | 0 |

### Inferred Columns

- Likely datetime columns: `time`
- Selected datetime column: `time`
- Likely CAMS PM2.5 column: `pm2_5 (μg/m³)`
- Likely PurpleAir PM2.5 mapping: `{'best': 'pm2_5 (μg/m³)'}`

### Timestamp Ranges

- `time`: 2025-01-01 00:00:00 to 2026-05-14 23:00:00, sampling median=0 days 01:00:00, most_common=0 days 01:00:00

## raw-pm25-gm.csv

- Path: `C:\Users\danhlee\Documents\pm_25_pj\data\raw\raw-pm25-gm.csv`
- Detected header row: 1
- Shape: (1435, 3)
- Inferred role: `purpleair`

### Columns

`DateTime`, `VNU-HCM A`, `VNU-HCM B`

### Dtypes

| column | dtype |
| --- | --- |
| DateTime | str |
| VNU-HCM A | float64 |
| VNU-HCM B | float64 |

### First 5 Rows

| DateTime | VNU-HCM A | VNU-HCM B |
| --- | --- | --- |
| 2026-05-12 10:20:32 | 13.2 | 10.0 |
| 2026-05-12 10:22:32 | 14.5 | 10.8 |
| 2026-05-12 10:24:32 | 13.5 | 10.2 |
| 2026-05-12 10:26:32 | 12.8 | 9.7 |
| 2026-05-12 10:28:32 | 12.4 | 8.8 |

### Missing Values

| column | missing |
| --- | --- |
| DateTime | 0 |
| VNU-HCM A | 0 |
| VNU-HCM B | 0 |

### Inferred Columns

- Likely datetime columns: `DateTime`
- Selected datetime column: `DateTime`
- Likely primary PM2.5/value column for this file: `VNU-HCM B`
- Likely PurpleAir PM2.5 mapping: `{'a': 'VNU-HCM A', 'b': 'VNU-HCM B', 'best': 'VNU-HCM B'}`

### Timestamp Ranges

- `DateTime`: 2026-05-12 10:20:32 to 2026-05-14 10:17:19, sampling median=0 days 00:02:00, most_common=0 days 00:02:00
