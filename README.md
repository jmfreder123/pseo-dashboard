# PSEO Talent Stickiness Dashboard

Interactive dashboard for exploring graduate retention patterns at Arizona and Texas public universities.

## Setup

```bash
cd "/Users/johnfredericks/ASU Dropbox/John Fredericks/PSEO_Dashboard"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

The dashboard will open in your default browser at `http://localhost:8501`.

## Data

Four CSVs in `data/`:
- `az_tsi.csv` — Arizona TSI by institution × industry × cohort × horizon
- `az_regional_flows.csv` — Arizona regional flows by Census division
- `tx_tsi.csv` — Texas TSI (20 institutions)
- `tx_regional_flows.csv` — Texas regional flows

Source: U.S. Census Bureau Postsecondary Employment Outcomes (PSEO), 2004–2019 graduation cohorts.

## Filters

- **State** — AZ, TX, or both
- **Institution** — populated based on state filter
- **Industry** — 20 NAICS 2-digit sectors
- **Horizon** — Y1, Y5, Y10
- **Cohort** — 2004, 2007, 2010, 2013, 2016, 2019

## Panels

- **Heatmap** — institution × industry, colored by TSI for a single horizon
- **Horizon Decay** — TSI by horizon (Y1/Y5/Y10), one line per institution
- **Regional Flows (Sankey)** — institution → Census region for selected filters
- **Summary Table** — filtered data, sortable and downloadable

## Notes

- TSI is computed as **ratio of sums** within filtered data, not mean of ratios.
- Suppressed cells are dropped before aggregation.
- Y10 data is observed only for the 2004, 2007, and 2010 cohorts; Y5 excludes 2019.