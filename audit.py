"""
Standard audit for PSEO Talent Stickiness Dashboard.
Compares bundled CSVs against raw LEHD PSEO files for 10 spot-check cells.
"""

import os
import pandas as pd
import sys
from pathlib import Path

# ============================================================
# Configuration — override with environment variables if your
# raw PSEO files live somewhere other than the default.
#
#   PSEO_RAW_BASE   directory holding the raw pseof_*.csv files
#   PSEO_DATA_DIR   directory holding the bundled dashboard CSVs
# ============================================================
DROPBOX_BASE = Path(
    os.environ.get("PSEO_RAW_BASE", Path.home() / "Dropbox" / "PSEO Explorer")
)
DASHBOARD_DATA = Path(
    os.environ.get("PSEO_DATA_DIR", Path(__file__).parent / "data")
)

RAW_AZ = DROPBOX_BASE / "pseof_az.csv"
RAW_TX = DROPBOX_BASE / "OR, UT, CO, TX" / "pseof_tx.csv"

# Raw files are cached here when downloaded from the Census release
RAW_CACHE = Path(os.environ.get("PSEO_RAW_CACHE", Path(__file__).parent / ".raw_cache"))
PSEO_BASE_URL = "https://lehd.ces.census.gov/data/pseo/latest_release"

BUNDLED_AZ_TSI = DASHBOARD_DATA / "az_tsi.csv"
BUNDLED_AZ_FLOWS = DASHBOARD_DATA / "az_regional_flows.csv"
BUNDLED_TX_TSI = DASHBOARD_DATA / "tx_tsi.csv"
BUNDLED_TX_FLOWS = DASHBOARD_DATA / "tx_regional_flows.csv"
BUNDLED_CO_TSI = DASHBOARD_DATA / "co_tsi.csv"
BUNDLED_CO_FLOWS = DASHBOARD_DATA / "co_regional_flows.csv"
RAW_CO = DROPBOX_BASE / "OR, UT, CO, TX" / "pseof_co.csv"

# Institution code lookups
AZ_INST_CODES = {"ASU": "00108100", "NAU": "00108200", "UA": "00108300"}
TX_INST_CODES = {
    "UT Austin": "00365800",
    "Texas A&M": "00363200",
    "Sam Houston State": "00360600",
}

CO_INST_CODES = {
    "CU Boulder": "00137000",
    "Colorado School of Mines": "00134800",
    "Metro State Denver": "00136000",
    "Colorado State": "00135000",
}

OR_INST_CODES = {
    "University of Oregon": "00322300",
    "Oregon State": "00321000",
    "Portland State": "00321600",
    "Oregon Tech": "00321100",
}

MT_INST_CODES = {
    "Montana State": "00253200",
    "University of Montana": "00253600",
    "MSU Billings": "00253000",
    "Montana Tech": "00253100",
}

UT_INST_CODES = {
    "University of Utah": "00367500",
    "Utah State": "00367700",
    "Utah Valley": "00402700",
    "Weber State": "00368000",
}

# Industry NAICS code lookups
INDUSTRY_CODES = {
    "Agriculture": "11", "Mining": "21", "Utilities": "22",
    "Construction": "23", "Manufacturing": "31-33", "Wholesale": "42",
    "Retail": "44-45", "Transportation": "48-49", "Information": "51",
    "Finance": "52", "Real Estate": "53", "Professional Services": "54",
    "Management": "55", "Admin/Waste": "56", "Education": "61",
    "Health Care": "62", "Arts/Entertainment": "71", "Food/Hospitality": "72",
    "Other Services": "81", "Public Admin": "92",
}

# Region code lookups (Census divisions)
REGION_CODES = {
    "New England": "1", "Middle Atlantic": "2", "East North Central": "3",
    "West North Central": "4", "South Atlantic": "5", "East South Central": "6",
    "West South Central": "7", "Mountain": "8", "Pacific": "9",
}


def load_raw(state):
    """Return the raw pseof_<state>.csv as a DataFrame.

    Looks in the configured local paths first, then falls back to downloading
    from the Census release into RAW_CACHE. The fallback is what lets a state
    be audited on a machine that has no local copy of the raw file.
    """
    st = state.lower()
    candidates = [
        DROPBOX_BASE / f"pseof_{st}.csv",
        DROPBOX_BASE / "OR, UT, CO, TX" / f"pseof_{st}.csv",
        RAW_CACHE / f"pseof_{st}.csv",
    ]
    for p in candidates:
        if p.exists():
            print(f"  raw {st}: {p}")
            return pd.read_csv(p, dtype=str, low_memory=False)

    import gzip
    import urllib.request

    url = f"{PSEO_BASE_URL}/{st}/pseof_{st}.csv.gz"
    print(f"  raw {st}: not found locally, downloading {url}")
    RAW_CACHE.mkdir(parents=True, exist_ok=True)
    dest = RAW_CACHE / f"pseof_{st}.csv"
    with urllib.request.urlopen(url) as r:
        dest.write_bytes(gzip.decompress(r.read()))
    return pd.read_csv(dest, dtype=str, low_memory=False)


def load_bundled(state, kind):
    """Load a bundled dashboard CSV: kind is 'tsi' or 'regional_flows'."""
    return pd.read_csv(DASHBOARD_DATA / f"{state.lower()}_{kind}.csv")


def find_raw_tsi_cell(raw_df, inst_code, industry_code, cohort, horizon):
    """Pull a single TSI cell from raw LEHD PSEO data."""
    h = str(horizon)
    row = raw_df[
        (raw_df["institution"] == inst_code) &
        (raw_df["industry"] == industry_code) &
        (raw_df["grad_cohort"] == str(cohort)) &
        (raw_df["degree_level"] == "05") &
        (raw_df["cipcode"] == "00") &
        (raw_df["geography"] == "00")
    ]
    if row.empty:
        return None
    emp_n = pd.to_numeric(row[f"y{h}_grads_emp"].iloc[0], errors="coerce")
    emp_in = pd.to_numeric(row[f"y{h}_grads_emp_instate"].iloc[0], errors="coerce")
    return emp_in, emp_n


def find_raw_flows_cell(raw_df, inst_code, industry_code, cohort, region_code, horizon):
    """Pull a single flows cell from raw LEHD PSEO data."""
    h = str(horizon)
    row = raw_df[
        (raw_df["institution"] == inst_code) &
        (raw_df["industry"] == industry_code) &
        (raw_df["grad_cohort"] == str(cohort)) &
        (raw_df["degree_level"] == "05") &
        (raw_df["cipcode"] == "00") &
        (raw_df["geography"] == region_code)
    ]
    if row.empty:
        return None
    emp_n = pd.to_numeric(row[f"y{h}_grads_emp"].iloc[0], errors="coerce")
    emp_in = pd.to_numeric(row[f"y{h}_grads_emp_instate"].iloc[0], errors="coerce")
    return emp_in, emp_n


def find_bundled_tsi_cell(bundled_df, inst_label, industry_label, cohort, horizon):
    """Pull from bundled dashboard CSV."""
    row = bundled_df[
        (bundled_df["institution_cat"] == inst_label) &
        (bundled_df["industry_cat"] == industry_label) &
        (bundled_df["grad_cohort"].astype(str) == str(cohort)) &
        (bundled_df["horizon"] == horizon)
    ]
    if row.empty:
        return None
    return row["emp_instate_"].iloc[0], row["emp_n_"].iloc[0], row["SI_by_cohort"].iloc[0]


def find_bundled_flows_cell(bundled_df, inst_label, industry_label, cohort, region_label, horizon):
    """Pull from bundled dashboard regional flows CSV."""
    row = bundled_df[
        (bundled_df["institution_cat"] == inst_label) &
        (bundled_df["industry_cat"] == industry_label) &
        (bundled_df["grad_cohort"].astype(str) == str(cohort)) &
        (bundled_df["region_cat"] == region_label) &
        (bundled_df["horizon"] == horizon)
    ]
    if row.empty:
        return None
    return row["emp_instate_"].iloc[0], row["emp_n_"].iloc[0]


def fmt(x):
    """Format value for display, handling NaN."""
    if x is None:
        return "MISSING"
    if pd.isna(x):
        return "(suppressed)"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def audit_tsi(name, raw_df, bundled_df, inst_label, inst_code, industry_label, cohort, horizon):
    print(f"\n--- {name} ---")
    industry_code = INDUSTRY_CODES[industry_label]

    raw = find_raw_tsi_cell(raw_df, inst_code, industry_code, cohort, horizon)
    bun = find_bundled_tsi_cell(bundled_df, inst_label, industry_label, cohort, horizon)

    if raw is None:
        print(f"  RAW: row not found")
    else:
        raw_in, raw_n = raw
        raw_si = raw_in / raw_n if pd.notna(raw_n) and raw_n > 0 else None
        print(f"  RAW    emp_instate={fmt(raw_in)}  emp_n={fmt(raw_n)}  TSI={fmt(raw_si)}")

    if bun is None:
        print(f"  BUNDLED: row not found")
    else:
        bun_in, bun_n, bun_si = bun
        print(f"  BUNDLE emp_instate={fmt(bun_in)}  emp_n={fmt(bun_n)}  TSI={fmt(bun_si)}")

    # Comparison
    if raw is not None and bun is not None:
        raw_in, raw_n = raw
        bun_in, bun_n, bun_si = bun
        match_in = (pd.isna(raw_in) and pd.isna(bun_in)) or raw_in == bun_in
        match_n = (pd.isna(raw_n) and pd.isna(bun_n)) or raw_n == bun_n
        if match_in and match_n:
            print(f"  PASS  values match")
        else:
            print(f"  FAIL  raw {raw_in}/{raw_n} vs bundled {bun_in}/{bun_n}")


def audit_flows(name, raw_df, bundled_df, inst_label, inst_code, industry_label, cohort, region_label, horizon):
    print(f"\n--- {name} ---")
    industry_code = INDUSTRY_CODES[industry_label]
    region_code = REGION_CODES[region_label]

    raw = find_raw_flows_cell(raw_df, inst_code, industry_code, cohort, region_code, horizon)
    bun = find_bundled_flows_cell(bundled_df, inst_label, industry_label, cohort, region_label, horizon)

    if raw is None:
        print(f"  RAW: row not found")
    else:
        raw_in, raw_n = raw
        print(f"  RAW    emp_instate={fmt(raw_in)}  emp_n={fmt(raw_n)}")

    if bun is None:
        print(f"  BUNDLED: row not found")
    else:
        bun_in, bun_n = bun
        print(f"  BUNDLE emp_instate={fmt(bun_in)}  emp_n={fmt(bun_n)}")

    if raw is not None and bun is not None:
        raw_in, raw_n = raw
        bun_in, bun_n = bun
        match = ((pd.isna(raw_in) and pd.isna(bun_in)) or raw_in == bun_in) and \
                ((pd.isna(raw_n) and pd.isna(bun_n)) or raw_n == bun_n)
        print(f"  {'PASS' if match else 'FAIL'}  values {'match' if match else 'differ'}")


def check_az(raw, tsi, flows):
    print("\n### AZ TSI checks ###")
    audit_tsi("AZ-1: ASU Education 2004 Y1", raw, tsi,
              "ASU", AZ_INST_CODES["ASU"], "Education", "2004", 1)
    audit_tsi("AZ-2: UA Information 2010 Y10", raw, tsi,
              "UA", AZ_INST_CODES["UA"], "Information", "2010", 10)
    audit_tsi("AZ-3: NAU Utilities 2007 Y5", raw, tsi,
              "NAU", AZ_INST_CODES["NAU"], "Utilities", "2007", 5)

    print("\n### AZ regional flows checks ###")
    # For "all industries" we'd need ind_level=A; we kept ind_level=S only.
    # Substitute: ASU Education -> Mountain Y1 (largest single flow we can verify)
    audit_flows("AZ-4: ASU Education -> Mountain Y1", raw, flows,
                "ASU", AZ_INST_CODES["ASU"], "Education", "2004", "Mountain", 1)
    audit_flows("AZ-5: UA Information -> Pacific Y1", raw, flows,
                "UA", AZ_INST_CODES["UA"], "Information", "2004", "Pacific", 1)


def check_tx(raw, tsi, flows):
    print("\n### TX TSI checks ###")
    audit_tsi("TX-1: UT-Austin Information 2004 Y1", raw, tsi,
              "UT Austin", TX_INST_CODES["UT Austin"], "Information", "2004", 1)
    audit_tsi("TX-2: Texas A&M Education 2010 Y5", raw, tsi,
              "Texas A&M", TX_INST_CODES["Texas A&M"], "Education", "2010", 5)
    audit_tsi("TX-3: Sam Houston Health Care 2016 Y1", raw, tsi,
              "Sam Houston State", TX_INST_CODES["Sam Houston State"], "Health Care", "2016", 1)

    print("\n### TX regional flows checks ###")
    audit_flows("TX-4: UT-Austin Information -> West South Central Y1", raw, flows,
                "UT Austin", TX_INST_CODES["UT Austin"], "Information", "2004", "West South Central", 1)
    audit_flows("TX-5: Texas A&M Information -> Pacific Y1", raw, flows,
                "Texas A&M", TX_INST_CODES["Texas A&M"], "Information", "2004", "Pacific", 1)


def check_co(raw, tsi, flows):
    print("\n### CO TSI checks ###")
    audit_tsi("CO-1: CU Boulder Information 2004 Y1", raw, tsi,
              "CU Boulder", CO_INST_CODES["CU Boulder"], "Information", "2004", 1)
    audit_tsi("CO-2: Colorado School of Mines Mining 2010 Y10", raw, tsi,
              "Colorado School of Mines", CO_INST_CODES["Colorado School of Mines"], "Mining", "2010", 10)
    audit_tsi("CO-3: Metro State Denver Health Care 2016 Y1", raw, tsi,
              "Metro State Denver", CO_INST_CODES["Metro State Denver"], "Health Care", "2016", 1)

    print("\n### CO regional flows checks ###")
    audit_flows("CO-4: CU Boulder Information -> Pacific Y1", raw, flows,
                "CU Boulder", CO_INST_CODES["CU Boulder"], "Information", "2004", "Pacific", 1)
    audit_flows("CO-5: Colorado State Education -> Mountain Y1", raw, flows,
                "Colorado State", CO_INST_CODES["Colorado State"], "Education", "2004", "Mountain", 1)


def check_or(raw, tsi, flows):
    print("\n### OR TSI checks ###")
    audit_tsi("OR-1: U Oregon Information 2004 Y1", raw, tsi,
              "University of Oregon", OR_INST_CODES["University of Oregon"], "Information", "2004", 1)
    audit_tsi("OR-2: Oregon State Manufacturing 2010 Y10", raw, tsi,
              "Oregon State", OR_INST_CODES["Oregon State"], "Manufacturing", "2010", 10)
    audit_tsi("OR-3: Portland State Health Care 2016 Y1", raw, tsi,
              "Portland State", OR_INST_CODES["Portland State"], "Health Care", "2016", 1)

    print("\n### OR regional flows checks ###")
    audit_flows("OR-4: U Oregon Information -> Pacific Y1", raw, flows,
                "University of Oregon", OR_INST_CODES["University of Oregon"], "Information", "2004", "Pacific", 1)
    audit_flows("OR-5: Oregon State Education -> Mountain Y1", raw, flows,
                "Oregon State", OR_INST_CODES["Oregon State"], "Education", "2004", "Mountain", 1)


def check_ut(raw, tsi, flows):
    # UT cohorts start at 2010 -- 2004 and 2007 do not exist in the source.
    print("\n### UT TSI checks ###")
    audit_tsi("UT-1: U Utah Information 2010 Y1", raw, tsi,
              "University of Utah", UT_INST_CODES["University of Utah"], "Information", "2010", 1)
    audit_tsi("UT-2: U Utah Health Care 2010 Y10", raw, tsi,
              "University of Utah", UT_INST_CODES["University of Utah"], "Health Care", "2010", 10)
    audit_tsi("UT-3: Utah State Education 2016 Y5", raw, tsi,
              "Utah State", UT_INST_CODES["Utah State"], "Education", "2016", 5)
    audit_tsi("UT-4: Weber State Manufacturing 2016 Y1", raw, tsi,
              "Weber State", UT_INST_CODES["Weber State"], "Manufacturing", "2016", 1)

    print("\n### UT regional flows checks ###")
    audit_flows("UT-5: U Utah Information -> Pacific Y1", raw, flows,
                "University of Utah", UT_INST_CODES["University of Utah"], "Information", "2010", "Pacific", 1)
    audit_flows("UT-6: Utah Valley Health Care -> Mountain Y1", raw, flows,
                "Utah Valley", UT_INST_CODES["Utah Valley"], "Health Care", "2016", "Mountain", 1)

    print("\n### UT cohort-coverage check ###")
    missing = [c for c in ("2004", "2007") if (tsi["grad_cohort"].astype(str) == c).any()]
    if missing:
        print(f"  FAIL  unexpected cohorts present in bundled UT data: {missing}")
    else:
        print("  PASS  2004 and 2007 absent, as expected for UT")


def _report(name, ok, detail=""):
    print(f"\n--- {name} ---")
    print(f"  {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def check_benchmark():
    """Audit the participating-state reference series.

    There is no single raw file to diff against -- the benchmark is a sum over
    33 states -- so this checks arithmetic invariants, agreement with the
    per-state files that feed it, and that the IPEDS sector rule still selects
    what it was validated to select.
    """
    bench_path = DASHBOARD_DATA / "benchmark.csv"
    comp_path = DASHBOARD_DATA / "benchmark_composition.csv"
    if not bench_path.exists():
        print("\n### BENCHMARK checks ###")
        print("  SKIP  data/benchmark.csv not present -- run build_benchmark.py")
        return

    b = pd.read_csv(bench_path)
    comp = pd.read_csv(comp_path) if comp_path.exists() else None

    print("\n### BENCHMARK arithmetic ###")

    si = b["emp_instate_"] / b["emp_n_"]
    both = b["SI_by_cohort"].notna() & si.notna()
    worst = (b.loc[both, "SI_by_cohort"] - si[both]).abs().max()
    _report("BM-1: SI_by_cohort == emp_instate_ / emp_n_",
            worst < 1e-6, f"max abs deviation {worst:.2e} over {both.sum():,} cells")

    bad = b[(b["emp_instate_"] > b["emp_n_"]) & b["emp_n_"].notna()]
    _report("BM-2: in-state never exceeds total", len(bad) == 0,
            f"{len(bad)} violating cells")

    neg = b[(b[["emp_instate_", "emp_n_"]] < 0).any(axis=1)]
    _report("BM-3: no negative counts", len(neg) == 0, f"{len(neg)} negative cells")

    print("\n### BENCHMARK structure ###")

    _report("BM-4: 20 NAICS sectors present",
            b["industry_cat"].nunique() == 20,
            f"{b['industry_cat'].nunique()} industries")

    _report("BM-5: horizons are exactly 1, 5, 10",
            sorted(b["horizon"].unique()) == [1, 5, 10],
            f"{sorted(b['horizon'].unique())}")

    cohorts = sorted(b["grad_cohort"].astype(str).unique())
    _report("BM-6: cohorts are the triennial set",
            cohorts == ["2004", "2007", "2010", "2013", "2016", "2019"],
            f"{cohorts}")

    _report("BM-7: single label, marked BENCH",
            set(b["state"]) == {"BENCH"} and b["institution_cat"].nunique() == 1,
            f"state={set(b['state'])}, label={b['institution_cat'].unique()[0]!r}")

    print("\n### BENCHMARK vs the states it contains ###")

    # Every dashboard state feeds the benchmark, so for any cell the benchmark
    # total must be at least what those states contribute. This catches a
    # benchmark built from the wrong frame or missing states.
    states = sorted(p.name[:2] for p in DASHBOARD_DATA.glob("*_tsi.csv"))
    parts = [pd.read_csv(DASHBOARD_DATA / f"{s}_tsi.csv") for s in states]
    dash = pd.concat(parts, ignore_index=True)
    dash["grad_cohort"] = dash["grad_cohort"].astype(str)
    b2 = b.copy()
    b2["grad_cohort"] = b2["grad_cohort"].astype(str)

    keys = ["grad_cohort", "industry_cat", "horizon"]
    # Rename rather than lean on merge suffixes: these column names already end
    # in an underscore, so suffixing yields emp_n__dash and reads as a typo.
    d_sum = (dash.groupby(keys, as_index=False)[["emp_instate_", "emp_n_"]].sum()
                 .rename(columns={"emp_instate_": "instate_dash", "emp_n_": "n_dash"}))
    b_sum = b2[keys + ["emp_instate_", "emp_n_"]].rename(
        columns={"emp_instate_": "instate_bench", "emp_n_": "n_bench"})
    m = d_sum.merge(b_sum, on=keys, how="inner")
    short = m[m["n_dash"] > m["n_bench"] + 0.5]
    _report(f"BM-8: benchmark >= sum of {len(states)} dashboard states",
            len(short) == 0,
            f"{len(short)} cells where the states exceed the benchmark "
            f"(of {len(m):,} compared)")

    if comp is not None:
        print("\n### BENCHMARK composition ###")
        included = comp[comp["institutions"] > 0]
        _report("BM-9: composition recorded for every included state",
                len(included) > 0 and included["institutions"].sum() > 0,
                f"{len(included)} states, {included['institutions'].sum():,} institutions")

        _report("BM-10: PSEO's `us` file (WGU) excluded",
                "US" not in set(comp["state"]),
                "WGU is a single private online university, not a national aggregate")

    print("\n### IPEDS sector rule ###")
    try:
        from build_benchmark import public_university_opeids
        ok_ids = public_university_opeids()
    except Exception as e:                                       # noqa: BLE001
        print(f"  SKIP  could not load IPEDS: {type(e).__name__}: {e}")
        return

    curated = {
        "AZ": ["00108100", "00108200", "00108300"],
        "CO": ["00134500", "00134800", "00134900", "00135000", "00135300", "00135800",
               "00136000", "00136500", "00137000", "00137200", "00450800", "00450900"],
        "TX": ["00354100", "00358100", "00359200", "00363000", "00360600", "00362400",
               "00363100", "00363200", "00363900", "00361500", "00364400", "00365200",
               "00361200", "00359400", "00365600", "00365800", "00366100", "00359900",
               "01011500", "00366500"],
        "OR": ["00319300", "00321100", "00321000", "00321600", "00321900", "00322300",
               "00320900"],
        "UT": ["00367500", "00367700", "00402700", "00368000", "00367800", "00367100"],
        "MT": ["00253200", "00253600", "00253000", "00253100", "00253300", "00253700"],
    }
    flat = [c for v in curated.values() for c in v]
    missing = [c for c in flat if c not in ok_ids]
    _report("BM-11: rule keeps every curated dashboard institution",
            not missing, f"{len(flat) - len(missing)}/{len(flat)} retained"
                         + (f", missing {missing}" if missing else ""))

    # Community colleges that award a few bachelor's degrees, and WGU
    should_drop = {
        "00954200": "Community College of Denver",
        "02116300": "Pueblo Community College",
        "00450600": "Colorado Mountain College",
        "00134600": "Arapahoe Community College",
        "03339400": "Western Governors University (private)",
    }
    kept = {c: n for c, n in should_drop.items() if c in ok_ids}
    _report("BM-12: rule drops community colleges and WGU",
            not kept, f"{len(should_drop) - len(kept)}/{len(should_drop)} dropped"
                      + (f", wrongly kept {list(kept.values())}" if kept else ""))


def check_mt(raw, tsi, flows):
    print("\n### MT TSI checks ###")
    audit_tsi("MT-1: Montana State Mining 2004 Y1", raw, tsi,
              "Montana State", MT_INST_CODES["Montana State"], "Mining", "2004", 1)
    audit_tsi("MT-2: U Montana Education 2010 Y10", raw, tsi,
              "University of Montana", MT_INST_CODES["University of Montana"], "Education", "2010", 10)
    audit_tsi("MT-3: Montana Tech Manufacturing 2016 Y5", raw, tsi,
              "Montana Tech", MT_INST_CODES["Montana Tech"], "Manufacturing", "2016", 5)

    print("\n### MT regional flows checks ###")
    audit_flows("MT-4: Montana State Education -> Mountain Y1", raw, flows,
                "Montana State", MT_INST_CODES["Montana State"], "Education", "2004", "Mountain", 1)
    audit_flows("MT-5: U Montana Information -> Pacific Y1", raw, flows,
                "University of Montana", MT_INST_CODES["University of Montana"], "Information", "2004", "Pacific", 1)


CHECKS = {"az": check_az, "tx": check_tx, "co": check_co, "or": check_or,
          "ut": check_ut, "mt": check_mt}


def main():
    args = [s.lower() for s in sys.argv[1:]]
    want_bench = (not args) or ("benchmark" in args)
    states = [s for s in args if s != "benchmark"] or (list(CHECKS) if not args else [])
    unknown = [s for s in states if s not in CHECKS]
    if unknown:
        sys.exit(f"no checks defined for: {', '.join(unknown)}. "
                 f"Known: {', '.join(CHECKS)}, benchmark")

    label = ", ".join([s.upper() for s in states] + (["BENCHMARK"] if want_bench else []))
    print("=" * 70)
    print(f"STANDARD AUDIT — {label}")
    print("=" * 70)

    for st in states:
        print(f"\nLoading {st.upper()} …")
        raw = load_raw(st)
        tsi = load_bundled(st, "tsi")
        flows = load_bundled(st, "regional_flows")
        CHECKS[st](raw, tsi, flows)

    if want_bench:
        check_benchmark()

    print("\n" + "=" * 70)
    print("Audit complete.")
    print("=" * 70)

def audit_dashboard_aggregation():
    """
    Layer 3: Replicate the dashboard's filter + aggregate logic and verify
    it produces the expected TSI for known slices.
    """
    print("\n" + "=" * 70)
    print("LAYER 3 AUDIT — dashboard aggregation logic")
    print("=" * 70)

    # Load combined TSI as the dashboard does
    az = pd.read_csv(BUNDLED_AZ_TSI)
    tx = pd.read_csv(BUNDLED_TX_TSI)
    tsi = pd.concat([az, tx], ignore_index=True)
    tsi["grad_cohort"] = tsi["grad_cohort"].astype(str)
    tsi["horizon"] = tsi["horizon"].astype(int)

    flows_az = pd.read_csv(BUNDLED_AZ_FLOWS)
    flows_tx = pd.read_csv(BUNDLED_TX_FLOWS)
    flows = pd.concat([flows_az, flows_tx], ignore_index=True)
    flows["grad_cohort"] = flows["grad_cohort"].astype(str)
    flows["horizon"] = flows["horizon"].astype(int)

    def dashboard_tsi(state, institutions, industries, cohorts, horizon):
        """Replicates the heatmap/line-plot ratio-of-sums aggregation."""
        f = tsi[
            (tsi["state"].isin(state if isinstance(state, list) else [state])) &
            (tsi["institution_cat"].isin(institutions)) &
            (tsi["industry_cat"].isin(industries)) &
            (tsi["grad_cohort"].isin([str(c) for c in cohorts])) &
            (tsi["horizon"] == horizon)
        ]
        emp_in = f["emp_instate_"].sum()
        emp_n = f["emp_n_"].sum()
        return emp_in, emp_n, (emp_in / emp_n if emp_n > 0 else None)

    def dashboard_flow(state, institutions, industries, cohorts, region, horizon):
        """Replicates the Sankey aggregation for one institution-region pair."""
        f = flows[
            (flows["state"].isin(state if isinstance(state, list) else [state])) &
            (flows["institution_cat"].isin(institutions)) &
            (flows["industry_cat"].isin(industries)) &
            (flows["grad_cohort"].isin([str(c) for c in cohorts])) &
            (flows["region_cat"] == region) &
            (flows["horizon"] == horizon)
        ]
        return f["emp_n_"].sum()

    # === L3-1: Single cell isolation ===
    # Filter AZ → ASU only → Education only → 2004 only → Y1
    # Should match raw cell value (3788 / 4140 = 0.9150)
    print("\n--- L3-1: AZ ASU Education 2004 Y1 (single cell) ---")
    in_, n, si = dashboard_tsi("AZ", ["ASU"], ["Education"], [2004], 1)
    expected_si = 3788 / 4140
    print(f"  Dashboard would display: emp_instate={in_}  emp_n={n}  TSI={si:.4f}")
    print(f"  Expected (from raw):     emp_instate=3788  emp_n=4140  TSI={expected_si:.4f}")
    print(f"  {'PASS' if abs(si - expected_si) < 1e-6 else 'FAIL'}")

    # === L3-2: Cross-cohort aggregation ===
    # AZ → ASU only → Education only → ALL cohorts → Y1
    # Should produce ratio of summed values across 6 cohorts
    print("\n--- L3-2: AZ ASU Education ALL cohorts Y1 (cross-cohort aggregation) ---")
    in_, n, si = dashboard_tsi("AZ", ["ASU"], ["Education"],
                               [2004, 2007, 2010, 2013, 2016, 2019], 1)
    # Manually compute expected from bundled CSV
    az_tsi = pd.read_csv(BUNDLED_AZ_TSI)
    expected = az_tsi[
        (az_tsi["institution_cat"] == "ASU") &
        (az_tsi["industry_cat"] == "Education") &
        (az_tsi["horizon"] == 1)
    ]
    exp_in = expected["emp_instate_"].sum()
    exp_n = expected["emp_n_"].sum()
    exp_si = exp_in / exp_n
    print(f"  Dashboard would display: emp_instate={in_}  emp_n={n}  TSI={si:.4f}")
    print(f"  Expected (manual sum):   emp_instate={exp_in}  emp_n={exp_n}  TSI={exp_si:.4f}")
    print(f"  {'PASS' if abs(si - exp_si) < 1e-6 else 'FAIL'}")

    # === L3-3: Cross-state aggregation ===
    # Both states → ASU and UT Austin → Education → 2004 → Y1
    # Should equal sum of (ASU 2004 Education Y1) + (UT-Austin 2004 Education Y1)
    print("\n--- L3-3: AZ+TX, ASU + UT Austin, Education, 2004, Y1 ---")
    in_, n, si = dashboard_tsi(["AZ", "TX"], ["ASU", "UT Austin"], ["Education"], [2004], 1)
    print(f"  Dashboard would display: emp_instate={in_}  emp_n={n}  TSI={si:.4f}")
    # Verify: pull each component cell from raw and sum
    raw_az = load_raw("az")
    raw_tx = load_raw("tx")
    asu = find_raw_tsi_cell(raw_az, AZ_INST_CODES["ASU"], "61", "2004", 1)
    uta = find_raw_tsi_cell(raw_tx, TX_INST_CODES["UT Austin"], "61", "2004", 1)
    exp_in = asu[0] + uta[0]
    exp_n = asu[1] + uta[1]
    exp_si = exp_in / exp_n
    print(f"  Expected (raw sum):      emp_instate={exp_in}  emp_n={exp_n}  TSI={exp_si:.4f}")
    print(f"  {'PASS' if abs(si - exp_si) < 1e-6 else 'FAIL'}")

    # === L3-4: Aggregate AZ TSI by horizon ===
    # All AZ institutions × all industries × all cohorts × Y1
    # Should equal 70.1% (per your report and earlier audit)
    print("\n--- L3-4: AZ aggregate TSI, all institutions × all industries × all cohorts × Y1 ---")
    in_, n, si = dashboard_tsi(
        "AZ", ["ASU", "NAU", "UA"],
        list(INDUSTRY_CODES.keys()),
        [2004, 2007, 2010, 2013, 2016, 2019], 1
    )
    print(f"  Dashboard would display: emp_instate={in_}  emp_n={n}  TSI={si:.4f}")
    print(f"  Expected (from earlier Stata 'total' command): emp_instate=203146  emp_n=289679  TSI=0.7013")
    expected_si = 203146 / 289679
    print(f"  {'PASS' if abs(si - expected_si) < 1e-3 else 'FAIL'}  (within 0.001 tolerance)")

    # === L3-5: Sankey flow aggregation ===
    # AZ → ASU only → Education only → 2004 only → Mountain → Y1
    # Should match raw cell (3834)
    print("\n--- L3-5: Sankey AZ ASU Education 2004 Mountain Y1 ---")
    val = dashboard_flow("AZ", ["ASU"], ["Education"], [2004], "Mountain", 1)
    print(f"  Dashboard would display flow value: {val}")
    print(f"  Expected (from raw):                3834")
    print(f"  {'PASS' if val == 3834 else 'FAIL'}")

if __name__ == "__main__":
    main()
    # Layer 3 replicates the dashboard's aggregation against hardcoded AZ/TX
    # expectations, so it only makes sense when both are in scope.
    selected = [s.lower() for s in sys.argv[1:]] or list(CHECKS)
    if {"az", "tx"} <= set(selected):
        audit_dashboard_aggregation()
    else:
        print("\n(skipping Layer 3 aggregation audit — it is AZ/TX-specific;"
              " run with no arguments to include it)")