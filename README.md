# my-health-viz

Visualize your Apple Health data with Python. Drop your `export.xml` into the `data/` folder and generate insightful charts about your sleep, heart rate, and activity.

## Features

- **Sleep Duration Trend** — line chart of nightly sleep over time
- **Resting Heart Rate Trend** — line chart of resting heart rate over time
- **Daily Steps Bar Chart** — bar chart of step counts per day
- **Summary Dashboard** — all four charts in a single figure

## Requirements

- Python 3.8+
- Apple Health export (exported from the Health app on iPhone)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

1. On your iPhone, open the **Health** app
2. Tap your profile picture → **Export All Health Data**
3. Unzip the export and copy `export.xml` into the `data/` folder:
   ```
   data/export.xml
   ```
4. Run the visualizer:
   ```bash
   python src/visualize.py
   ```

Charts are saved as PNG files in the project root:
- `sleep_trend.png`
- `heart_rate_trend.png`
- `steps_chart.png`
- `dashboard.png`

## Project Structure

```
my-health-viz/
├── data/               # Place your export.xml here (git-ignored)
├── src/
│   ├── parse_health.py # Parses export.xml into pandas DataFrames
│   └── visualize.py    # Generates charts from parsed data
├── requirements.txt
└── README.md
```
