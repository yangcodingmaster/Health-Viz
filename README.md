# my-health-viz

Visualize your Apple Health data with Python. Drop your `export.xml` into the `data/` folder and generate insightful charts about your sleep, heart rate, and activity.

## Features

- **Interactive dashboard** — single `dashboard.html` you open in any browser
- **Sleep Duration** — bar + 7-day rolling average, with 7 h / 9 h guidelines
- **Resting Heart Rate** — scatter + 7-day rolling average
- **Daily Steps** — color-coded bars (green = goal met, red = missed), 10k goal line
- **Key Stats panel** — 30-day summary table (averages, goal-hit counts)
- Zoom, pan, hover tooltips, and range slider built in — no server needed

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
5. Open the generated file in your browser:
   ```
   dashboard.html
   ```

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
