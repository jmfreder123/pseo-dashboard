# PSEO Talent Stickiness Dashboard

Interactive dashboard for exploring graduate retention patterns at public
universities in Arizona, Texas, Colorado, and Oregon.

## Setup

```bash
git clone https://github.com/jmfreder123/pseo-dashboard.git
cd pseo-dashboard
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

Two CSVs per state in `data/`, named `{st}_tsi.csv` and `{st}_regional_flows.csv`:

| State | Institutions | Selection rule |
|-------|--------------|----------------|
| AZ | 3 | all four-year publics |
| TX | 20 | `total_observed >= 340` |
| CO | 12 | `total_observed >= 320` |
| OR | 7 | all four-year publics (no threshold — see Notes) |

Source: U.S. Census Bureau Postsecondary Employment Outcomes (PSEO),
2004–2019 graduation cohorts, bachelor's degrees, all CIP codes.

`app.py` discovers states by globbing `data/*_tsi.csv` — dropping a new pair
of CSVs in `data/` is all it takes to add one. Add an entry to
`STATE_INST_COLORS` in `app.py` to give it a Sankey color; otherwise it
renders gray.

## Adding a state

`build_state_data.py` builds the dashboard CSVs directly from the Census
release, reproducing the Stata pipeline without needing Stata:

```bash
# inspect coverage before choosing a threshold
python3 build_state_data.py ut --coverage

# build and write
python3 build_state_data.py ut --out data
```

Omit `--min-observed` to keep every institution surviving the analytic frame —
correct for AZ and OR, where community colleges drop out on their own because
they award no bachelor's degrees. Use `--rename CODE=Label` to shorten an
institution's name for the axes.

## Filters

- **State** — any combination of the loaded states
- **Institution** — populated based on state filter
- **Industry** — 20 NAICS 2-digit sectors
- **Horizon** — Y1, Y5, Y10
- **Cohort** — 2004, 2007, 2010, 2013, 2016, 2019

## Panels

- **Overview** — introduction and method notes
- **Heatmap** — institution × industry, colored by TSI for a single horizon
- **Horizon Decay** — TSI by horizon (Y1/Y5/Y10), one line per institution
- **Regional Flows (Sankey)** — institution → Census region for selected filters
- **Summary Table** — filtered data, sortable and downloadable

## Notes

- TSI is computed as **ratio of sums** within filtered data, not mean of ratios.
- Suppressed cells are dropped before aggregation.
- Y10 data is observed only for the 2004, 2007, and 2010 cohorts; Y5 excludes 2019.
- Coverage thresholds are state-specific and do **not** transfer. Oregon's 7
  publics all fall between 268 and 278 observed cells, so applying CO's 320 or
  TX's 340 would select zero institutions. Always run `--coverage` first.
