#!/usr/bin/env python3
"""Build a participating-state reference series for the dashboard.

Aggregates the same analytic frame used per state across every state in the
PSEO release, then computes the Talent Stickiness Index as a ratio of sums --
the same aggregation the dashboard applies everywhere else.

    python3 build_benchmark.py --out data

This is NOT a national figure. PSEO covers roughly two thirds of states and
excludes California, Florida, New Jersey, and others; the result describes the
states that participate, weighted by how many graduates they contribute. The
output records its own composition in benchmark_composition.csv so the claim
can be checked rather than assumed.

Memory: states are processed one at a time and reduced immediately, so peak
usage is one state's raw file (Texas, ~360 MB) rather than all of them.
"""

import argparse
import sys

import pandas as pd

from build_state_data import (
    COHORTS,
    FIPS,
    IND_LABEL,
    REGION,
    analytic_frame,
    coverage,
    fmt,
    load_state,
)

GROUP_KEYS = ["grad_cohort", "industry_cat", "horizon"]


def reduce_state(st, min_observed=None):
    """Return (per-cell sums for st, composition row) or (None, row) on failure."""
    df, names = load_state(st)
    full = analytic_frame(df, st, triennial=False)
    cov = coverage(full, names)
    frame = full[full.grad_cohort.isin(COHORTS)]

    keep = (
        cov.index[cov.total_observed >= min_observed].tolist()
        if min_observed is not None
        else cov.index.tolist()
    )
    if not keep:
        return None, {"state": st.upper(), "institutions": 0, "cohorts": "", "note": "no institutions survived"}

    f = frame[frame.institution.isin(keep) & (frame.geography == "00")].copy()
    f["industry_cat"] = f.industry.map(IND_LABEL)
    f = f[f.industry_cat.notna()]

    rows = []
    for h in (1, 5, 10):
        t = f[["grad_cohort", "industry_cat", f"y{h}_grads_emp_instate", f"y{h}_grads_emp"]].copy()
        t.columns = ["grad_cohort", "industry_cat", "emp_instate_", "emp_n_"]
        t["horizon"] = h
        rows.append(t)
    long = pd.concat(rows, ignore_index=True)

    # Suppressed cells contribute nothing to either side of the ratio
    long = long.dropna(subset=["emp_instate_", "emp_n_"])
    agg = long.groupby(GROUP_KEYS, as_index=False)[["emp_instate_", "emp_n_"]].sum()

    comp = {
        "state": st.upper(),
        "institutions": len(keep),
        "cohorts": ",".join(sorted(f.grad_cohort.unique())),
        "grads_y1": int(long.loc[long.horizon == 1, "emp_n_"].sum()),
        "note": "",
    }
    return agg, comp


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=".", help="output directory")
    p.add_argument("--min-observed", type=int,
                   help="apply a coverage threshold in every state (default: keep all)")
    p.add_argument("--states", nargs="+", help="limit to these state codes (default: all)")
    p.add_argument("--exclude", nargs="+", default=[],
                   help="state codes to leave out, e.g. --exclude id")
    a = p.parse_args()

    states = [s.lower() for s in (a.states or sorted(FIPS))]
    states = [s for s in states if s not in {e.lower() for e in a.exclude}]

    parts, comps = [], []
    for i, st in enumerate(states, 1):
        print(f"[{i}/{len(states)}] {st} …", file=sys.stderr, flush=True)
        try:
            agg, comp = reduce_state(st, a.min_observed)
        except Exception as e:                                  # noqa: BLE001
            print(f"  skipped {st}: {type(e).__name__}: {e}", file=sys.stderr)
            comps.append({"state": st.upper(), "institutions": 0, "cohorts": "",
                          "grads_y1": 0, "note": f"failed: {type(e).__name__}"})
            continue
        comps.append(comp)
        if agg is not None:
            parts.append(agg)
            print(f"  {comp['institutions']} institutions, "
                  f"{comp['grads_y1']:,} Y1 grads", file=sys.stderr)

    if not parts:
        sys.exit("no states produced data")

    total = (
        pd.concat(parts, ignore_index=True)
        .groupby(GROUP_KEYS, as_index=False)[["emp_instate_", "emp_n_"]]
        .sum()
    )
    total["SI_by_cohort"] = (total.emp_instate_ / total.emp_n_).where(total.emp_n_ != 0)
    total["state"] = "BENCH"
    total["institution_cat"] = "Participating-state avg"
    total = total[["institution_cat", "industry_cat", "grad_cohort", "horizon",
                   "emp_instate_", "emp_n_", "SI_by_cohort", "state"]]
    total = total.sort_values(["industry_cat", "grad_cohort", "horizon"])

    comp_df = pd.DataFrame(comps).sort_values("state")

    bench_path = f"{a.out}/benchmark.csv"
    comp_path = f"{a.out}/benchmark_composition.csv"
    fmt(total, floats=("SI_by_cohort",)).to_csv(bench_path, index=False)
    comp_df.to_csv(comp_path, index=False)

    ok = comp_df[comp_df.institutions > 0]
    print(f"\nstates included : {len(ok)} of {len(states)}")
    print(f"institutions    : {ok.institutions.sum():,}")
    print(f"Y1 grads        : {ok.grads_y1.sum():,}")
    print("\naggregate TSI by horizon:")
    for h in (1, 5, 10):
        s = total[total.horizon == h]
        print(f"  Y{h:<3} {s.emp_instate_.sum() / s.emp_n_.sum():.4f}")
    print(f"\nwrote {bench_path}\nwrote {comp_path}")


if __name__ == "__main__":
    main()
