#!/usr/bin/env python3
"""Build PSEO dashboard CSVs for a state, straight from the Census release.

Reproduces the Stata pipeline (AZ/TX/CO/OR) without needing Stata, and writes
files byte-compatible with `export delimited`: value labels rather than codes,
empty strings for missing, and float32 precision on the index.

    python3 build_state_data.py or --out ../PSEO_Dashboard/data
    python3 build_state_data.py ut --min-observed 300 --dry-run

With no --institutions/--min-observed, every institution surviving the
analytic frame is kept (correct for AZ and OR). Use --min-observed to apply a
coverage threshold the way TX (340) and CO (320) do; run --coverage first to
see the distribution before choosing one.
"""

import argparse
import gzip
import io
import sys
import urllib.request

import numpy as np
import pandas as pd

BASE = "https://lehd.ces.census.gov/data/pseo/latest_release"
COHORTS = ["2004", "2007", "2010", "2013", "2016", "2019"]

# State FIPS for the aggregate row that must be dropped
FIPS = {
    "al": "01", "az": "04", "co": "08", "ct": "09", "dc": "11", "ga": "13",
    "hi": "15", "ia": "19", "id": "16", "il": "17", "in": "18", "la": "22",
    "ma": "25", "me": "23", "mi": "26", "mn": "27", "mo": "29", "mt": "30",
    "nc": "37", "ny": "36", "oh": "39", "ok": "40", "or": "41", "pa": "42",
    "ri": "44", "sc": "45", "sd": "46", "tx": "48", "ut": "49", "va": "51",
    "wi": "55", "wv": "54", "wy": "56",
}

INDUSTRY = [
    ("11", "Agriculture"), ("21", "Mining"), ("22", "Utilities"),
    ("23", "Construction"), ("31-33", "Manufacturing"), ("42", "Wholesale"),
    ("44-45", "Retail"), ("48-49", "Transportation"), ("51", "Information"),
    ("52", "Finance"), ("53", "Real Estate"), ("54", "Professional Services"),
    ("55", "Management"), ("56", "Admin/Waste"), ("61", "Education"),
    ("62", "Health Care"), ("71", "Arts/Entertainment"), ("72", "Food/Hospitality"),
    ("81", "Other Services"), ("92", "Public Admin"),
]
IND_LABEL = dict(INDUSTRY)

REGION = {
    1: "New England", 2: "Middle Atlantic", 3: "East North Central",
    4: "West North Central", 5: "South Atlantic", 6: "East South Central",
    7: "West South Central", 8: "Mountain", 9: "Pacific",
}

COUNT_COLS = [f"y{h}_grads_emp{s}" for h in (1, 5, 10) for s in ("", "_instate")]

# Dashboard axes need short labels, not the Census legal names. Codes not
# listed here fall back to the crosswalk label; override with --rename.
SHORT_LABELS = {
    # Oregon
    "00319300": "Eastern Oregon",
    "00321100": "Oregon Tech",
    "00321000": "Oregon State",
    "00321600": "Portland State",
    "00321900": "Southern Oregon",
    "00322300": "University of Oregon",
    "00320900": "Western Oregon",
    # Montana
    "00253200": "Montana State",
    "00253600": "University of Montana",
    "00253000": "MSU Billings",
    "00253100": "Montana Tech",
    "00253300": "MSU Northern",
    "00253700": "U Montana Western",
    # Utah
    "00367500": "University of Utah",
    "00367700": "Utah State",
    "00402700": "Utah Valley",
    "00368000": "Weber State",
    "00367800": "Southern Utah",
    "00367100": "Utah Tech",
}


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


def load_state(st):
    flows = gzip.decompress(fetch(f"{BASE}/{st}/pseof_{st}.csv.gz"))
    df = pd.read_csv(io.BytesIO(flows), dtype=str, low_memory=False)
    inst = pd.read_csv(
        io.BytesIO(fetch(f"{BASE}/{st}/pseo_{st}_institutions.csv")),
        dtype=str, encoding="utf-8-sig",
    )
    return df, dict(zip(inst.institution, inst.label))


def analytic_frame(df, st, triennial=True):
    """The filters shared by every state pipeline.

    triennial=False keeps every cohort. The .do files compute total_observed
    on all cohorts and only then restrict to the triennial set, so coverage
    thresholds are quoted on the all-cohort scale -- Colorado's documented
    `>= 320` selects 12 institutions there but 0 if the cohort filter is
    applied first. Coverage must therefore be computed with triennial=False.
    """
    mask = (
        (df.institution != FIPS[st])
        & (df.degree_level == "05")
        & (df.cipcode == "00")
        & (df.grad_cohort != "0000")
        & (df.ind_level != "A")
    )
    if triennial:
        mask &= df.grad_cohort.isin(COHORTS)
    f = df[mask].copy()
    for c in COUNT_COLS:
        f[c] = pd.to_numeric(f[c], errors="coerce")
    return f


def coverage(frame, names):
    """total_observed per institution, on national rows only."""
    nat = frame[frame.geography == "00"]
    obs = pd.DataFrame({
        f"obs_y{h}": (nat[f"y{h}_grads_emp"].notna() & (nat[f"y{h}_grads_emp"] > 0)).astype(int)
        for h in (1, 5, 10)
    }, index=nat.index)
    obs["institution"] = nat.institution
    cov = obs.groupby("institution").sum()
    cov["total_observed"] = cov.sum(axis=1)
    cov["label"] = [names.get(i, "?") for i in cov.index]
    return cov.sort_values("total_observed", ascending=False)


def to_long(d, extra=()):
    """Stata's `reshape long emp_instate_ emp_n_, j(horizon)`."""
    out = []
    for h in (1, 5, 10):
        keys = ["institution_cat", "industry_cat", "grad_cohort", *extra]
        t = d[keys + [f"y{h}_grads_emp_instate", f"y{h}_grads_emp"]].copy()
        t.columns = keys + ["emp_instate_", "emp_n_"]
        t["horizon"] = h
        out.append(t)
    return pd.concat(out, ignore_index=True)


def fmt(df, floats=()):
    """Match `export delimited`: empty missings, no leading zero on floats."""
    d = df.copy()
    for c in floats:
        v = d[c].astype("float32")
        s = v.map(lambda x: "" if pd.isna(x) else f"{x:.8g}")
        d[c] = s.str.replace(r"^0\.", ".", regex=True).str.replace(r"^-0\.", "-.", regex=True)
    for c in d.columns:
        if c not in floats and d[c].dtype.kind == "f":
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:g}")
    return d


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("state", help="two-letter PSEO state code, e.g. or")
    p.add_argument("--out", default=".", help="output directory for the two CSVs")
    p.add_argument("--min-observed", type=int, help="keep institutions with total_observed >= N")
    p.add_argument("--institutions", nargs="+", help="explicit institution codes to keep")
    p.add_argument("--coverage", action="store_true", help="print coverage table and exit")
    p.add_argument("--dry-run", action="store_true", help="report shape without writing")
    p.add_argument("--rename", nargs="+", default=[], metavar="CODE=LABEL",
                   help="override an institution's dashboard label")
    p.add_argument("--long-names", action="store_true",
                   help="use full Census names instead of short dashboard labels")
    a = p.parse_args()

    st = a.state.lower()
    if st not in FIPS:
        sys.exit(f"'{st}' is not in the PSEO release. Available: {' '.join(sorted(FIPS))}")

    print(f"downloading {st} …", file=sys.stderr)
    df, names = load_state(st)
    # Coverage on all cohorts (the .do-file scale), data on triennial only
    full = analytic_frame(df, st, triennial=False)
    cov = coverage(full, names)
    frame = full[full.grad_cohort.isin(COHORTS)]

    if a.coverage:
        print(cov[["label", "obs_y1", "obs_y5", "obs_y10", "total_observed"]].to_string())
        print("\nthreshold sensitivity:")
        for t in (0, 100, 200, 260, 300, 320, 340, 400):
            print(f"  >= {t:>3}: {(cov.total_observed >= t).sum():>3} institutions")
        return

    if a.institutions:
        keep = [i for i in a.institutions if i in cov.index]
    elif a.min_observed is not None:
        keep = cov.index[cov.total_observed >= a.min_observed].tolist()
    else:
        keep = cov.index.tolist()
    if not keep:
        sys.exit("no institutions survived the filters — check --min-observed against --coverage")

    overrides = dict(r.split("=", 1) for r in a.rename)
    short = {} if a.long_names else SHORT_LABELS

    def label_of(i):
        return overrides.get(i) or short.get(i) or names.get(i, i)

    # institution_cat numbered alphabetically by label, per every existing pipeline
    ordered = sorted(keep, key=label_of)
    inst_label = {i: label_of(i) for i in ordered}
    print(f"{len(ordered)} institutions: {', '.join(inst_label[i] for i in ordered)}", file=sys.stderr)

    f = frame[frame.institution.isin(ordered)].copy()
    f["institution_cat"] = f.institution.map(inst_label)
    f["industry_cat"] = f.industry.map(IND_LABEL)
    f = f[f.industry_cat.notna()]

    up = st.upper()

    tsi = to_long(f[f.geography == "00"])
    tsi["SI_by_cohort"] = (tsi.emp_instate_ / tsi.emp_n_).where(
        tsi.emp_n_.notna() & (tsi.emp_n_ != 0)
    )
    tsi["state"] = up
    tsi = tsi.sort_values(["institution_cat", "industry_cat", "grad_cohort", "horizon"])
    tsi = tsi[["institution_cat", "industry_cat", "grad_cohort", "horizon",
               "emp_instate_", "emp_n_", "SI_by_cohort", "state"]]

    fl = f[f.geography != "00"].copy()
    fl["region_cat"] = fl.geography.astype(int).map(REGION)
    flows = to_long(fl, extra=("region_cat",))
    flows["state"] = up
    flows = flows.sort_values(["institution_cat", "industry_cat", "grad_cohort", "region_cat", "horizon"])
    flows = flows[["institution_cat", "industry_cat", "grad_cohort", "region_cat",
                   "horizon", "emp_instate_", "emp_n_", "state"]]

    print(f"\n{up} TSI    : {len(tsi):,} cells, {tsi.SI_by_cohort.notna().sum():,} observed")
    print(f"{up} flows  : {len(flows):,} cells, {flows.emp_n_.notna().sum():,} observed")

    if a.dry_run:
        print("\n--dry-run: nothing written")
        return

    t_path = f"{a.out}/{st}_tsi.csv"
    f_path = f"{a.out}/{st}_regional_flows.csv"
    fmt(tsi, floats=("SI_by_cohort",)).to_csv(t_path, index=False)
    fmt(flows).to_csv(f_path, index=False)
    print(f"\nwrote {t_path}\nwrote {f_path}")


if __name__ == "__main__":
    main()
