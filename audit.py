"""
Standard audit for PSEO Talent Stickiness Dashboard.
Compares bundled CSVs against raw LEHD PSEO files for 10 spot-check cells.
"""

import pandas as pd
import sys
from pathlib import Path

# ============================================================
# Configuration — adjust paths if your files are elsewhere
# ============================================================
DROPBOX_BASE = Path("/Users/johnfredericks/ASU Dropbox/John Fredericks/PSEO Explorer")
DASHBOARD_DATA = Path.home() / "Code" / "PSEO_Dashboard" / "data"

RAW_AZ = DROPBOX_BASE / "pseof_az.csv"
RAW_TX = DROPBOX_BASE / "OR, UT, CO, TX" / "pseof_tx.csv"

BUNDLED_AZ_TSI = DASHBOARD_DATA / "az_tsi.csv"
BUNDLED_AZ_FLOWS = DASHBOARD_DATA / "az_regional_flows.csv"
BUNDLED_TX_TSI = DASHBOARD_DATA / "tx_tsi.csv"
BUNDLED_TX_FLOWS = DASHBOARD_DATA / "tx_regional_flows.csv"

# Institution code lookups
AZ_INST_CODES = {"ASU": "00108100", "NAU": "00108200", "UA": "00108300"}
TX_INST_CODES = {
    "UT Austin": "00365800",
    "Texas A&M": "00363200",
    "Sam Houston State": "00360600",
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


def main():
    print("Loading raw PSEO files (this takes a moment)...")
    raw_az = pd.read_csv(RAW_AZ, dtype=str, low_memory=False)
    raw_tx = pd.read_csv(RAW_TX, dtype=str, low_memory=False)

    print("Loading bundled dashboard CSVs...")
    bundled_az_tsi = pd.read_csv(BUNDLED_AZ_TSI)
    bundled_az_flows = pd.read_csv(BUNDLED_AZ_FLOWS)
    bundled_tx_tsi = pd.read_csv(BUNDLED_TX_TSI)
    bundled_tx_flows = pd.read_csv(BUNDLED_TX_FLOWS)

    print("\n" + "=" * 70)
    print("STANDARD AUDIT — 10 spot checks")
    print("=" * 70)

    # AZ TSI checks
    print("\n### AZ TSI checks ###")
    audit_tsi("AZ-1: ASU Education 2004 Y1", raw_az, bundled_az_tsi,
              "ASU", AZ_INST_CODES["ASU"], "Education", "2004", 1)
    audit_tsi("AZ-2: UA Information 2010 Y10", raw_az, bundled_az_tsi,
              "UA", AZ_INST_CODES["UA"], "Information", "2010", 10)
    audit_tsi("AZ-3: NAU Utilities 2007 Y5", raw_az, bundled_az_tsi,
              "NAU", AZ_INST_CODES["NAU"], "Utilities", "2007", 5)

    # AZ flows checks
    print("\n### AZ regional flows checks ###")
    # For "all industries" we'd need ind_level=A; we kept ind_level=S only.
    # Substitute: ASU Education -> Mountain Y1 (largest single flow we can verify)
    audit_flows("AZ-4: ASU Education -> Mountain Y1", raw_az, bundled_az_flows,
                "ASU", AZ_INST_CODES["ASU"], "Education", "2004", "Mountain", 1)
    audit_flows("AZ-5: UA Information -> Pacific Y1", raw_az, bundled_az_flows,
                "UA", AZ_INST_CODES["UA"], "Information", "2004", "Pacific", 1)

    # TX TSI checks
    print("\n### TX TSI checks ###")
    audit_tsi("TX-1: UT-Austin Information 2004 Y1", raw_tx, bundled_tx_tsi,
              "UT Austin", TX_INST_CODES["UT Austin"], "Information", "2004", 1)
    audit_tsi("TX-2: Texas A&M Education 2010 Y5", raw_tx, bundled_tx_tsi,
              "Texas A&M", TX_INST_CODES["Texas A&M"], "Education", "2010", 5)
    audit_tsi("TX-3: Sam Houston Health Care 2016 Y1", raw_tx, bundled_tx_tsi,
              "Sam Houston State", TX_INST_CODES["Sam Houston State"], "Health Care", "2016", 1)

    # TX flows checks
    print("\n### TX regional flows checks ###")
    audit_flows("TX-4: UT-Austin Information -> West South Central Y1", raw_tx, bundled_tx_flows,
                "UT Austin", TX_INST_CODES["UT Austin"], "Information", "2004", "West South Central", 1)
    audit_flows("TX-5: Texas A&M Information -> Pacific Y1", raw_tx, bundled_tx_flows,
                "Texas A&M", TX_INST_CODES["Texas A&M"], "Information", "2004", "Pacific", 1)

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
    raw_az = pd.read_csv(RAW_AZ, dtype=str, low_memory=False)
    raw_tx = pd.read_csv(RAW_TX, dtype=str, low_memory=False)
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
    audit_dashboard_aggregation()