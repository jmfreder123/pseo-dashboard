# PSEO Talent Stickiness Dashboard

Interactive dashboard for exploring graduate retention patterns at public
universities in Arizona, Texas, Colorado, Oregon, Utah, Montana, and South
Carolina.

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

| State | Institutions | Cohorts | Selection rule |
|-------|--------------|---------|----------------|
| AZ | 3 | 2004–2019 | all four-year publics |
| TX | 20 | 2004–2019 | `total_observed >= 340` |
| CO | 12 | 2004–2019 | `total_observed >= 320` |
| OR | 7 | 2004–2019 | all four-year publics (no threshold — see Notes) |
| UT | 6 | 2010–2019 | `total_observed >= 100` (drops Snow College) |
| MT | 6 | 2004–2019 | all four-year publics (no threshold) |
| SC | 12 | 2004–2019 | IPEDS sector rule (no threshold — see Notes) |

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
correct for AZ, OR, and MT. Use `--rename CODE=Label` to shorten an
institution's name for the axes.

**`total_observed` is counted across all cohorts, not just the triennial set**,
matching the `.do` files. This matters: Colorado's documented `>= 320` selects
12 institutions on that scale but 0 if the cohort filter is applied first,
because Colorado has a 2001 cohort the triennial filter drops. Thresholds
quoted in this README are on the all-cohort scale and reproduce exactly.

## Participating-state reference line

`build_benchmark.py` aggregates the same analytic frame across every state in
the PSEO release and emits `data/benchmark.csv`, which the Horizon Decay tab
draws as a dashed reference line. `data/benchmark_composition.csv` records
which states and how many institutions went into it.

```bash
python3 build_benchmark.py --out data
```

**It is not a national figure.** PSEO covers about two thirds of states and
excludes California, Florida, and New Jersey among others, so the line is a
participating-state average weighted by graduate counts. Texas alone is
roughly 14% of the weight.

### Defining "public university"

PSEO carries no public/private or two-year/four-year flag, so institution
sector comes from the IPEDS HD file, joined on OPEID — PSEO's 8-digit
institution code is the same identifier IPEDS pads to 10 characters. The rule
is:

```
CONTROL == 1  AND  (INSTCAT == 2  OR  HLOFFER >= 7)
```

Neither half works alone:

- `INSTCAT == 2` ("primarily baccalaureate or above") drops Utah Valley,
  Weber State, Southern Utah, and Utah Tech — real universities that carry
  `INSTCAT 3` because Utah's dual-mission system awards many associate degrees.
- `HLOFFER >= 7` (master's or higher) recovers those four but loses
  University of Montana Western, which is baccalaureate-only.

The union keeps **all 54 institutions** in the curated state files while
dropping every community college that awards a handful of bachelor's degrees
(`INSTCAT 3` with `HLOFFER 5`) and Western Governors University (`CONTROL 2`,
private). Pass `--no-ipeds` to skip the filter and see the difference.

Note that PSEO's `us` file is **not** a national aggregate — it is Western
Governors University alone, filed under `us` because it has no home state.

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
- **Utah's PSEO data begin with the 2010 cohort** — there are no 2004 or 2007
  rows. Filtering to those cohorts yields nothing for UT, and Utah's Y10
  figures rest on the 2010 cohort alone.
- **South Carolina admits no threshold at all.** Its 33 in-frame institutions
  sit between 264 and 338 `total_observed`, with private colleges interleaved
  among the publics: Limestone (330) outranks the Citadel (326), Newberry (329)
  outranks USC Aiken (326). No cut separates sector from sector. SC's twelve
  were selected by running the IPEDS rule directly, then passed to
  `build_state_data.py` via `--institutions`. SC also carries a 2001 cohort, so
  a threshold quoted on the triennial scale selects zero rather than merely
  fewer.
- Coverage thresholds are state-specific and do **not** transfer. Oregon's 7
  publics all fall between 268 and 278 observed cells, so applying CO's 320 or
  TX's 340 would select zero institutions. Utah's six four-year publics sit at
  155–160 while Snow College sits at 14, so a threshold anywhere in that gap
  works. Always run `--coverage` first.
