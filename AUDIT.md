# Audit results

Spot-check validation of the bundled dashboard CSVs in `data/` against the raw
LEHD PSEO release files. Reproduce with:

```bash
python3 audit.py            # all states, plus the Layer 3 aggregation audit
python3 audit.py ut         # a single state
python3 audit.py co tx      # a subset
```

Raw files are read from the configured local paths if present, otherwise
downloaded from `https://lehd.ces.census.gov/data/pseo/latest_release/` and
cached in `.raw_cache/` (gitignored).

## Run of 2026-08-02 — 49/49 pass

Source: PSEO `latest_release`, IPEDS HD2023. 32 per-state spot checks,
12 benchmark checks, and 5 Layer 3 aggregation checks, no failures.

`python3 audit.py` runs everything; `python3 audit.py mt benchmark` runs a
subset.

### Arizona (5/5)

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| AZ-1 ASU Education 2004 Y1 | 3788 / 4140 | 0.9150 | PASS |
| AZ-2 UA Information 2010 Y10 | 183 / 719 | 0.2545 | PASS |
| AZ-3 NAU Utilities 2007 Y5 | 37 / 42 | 0.8810 | PASS |
| AZ-4 ASU Education → Mountain Y1 | 3788 / 3834 | — | PASS |
| AZ-5 UA Information → Pacific Y1 | 0 / 146 | — | PASS |

### Colorado (5/5)

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| CO-1 CU Boulder Information 2004 Y1 | 328 / 545 | 0.6018 | PASS |
| CO-2 Colorado School of Mines Mining 2010 Y10 | 83 / 188 | 0.4415 | PASS |
| CO-3 Metro State Denver Health Care 2016 Y1 | 1267 / 1441 | 0.8793 | PASS |
| CO-4 CU Boulder Information → Pacific Y1 | 0 / 116 | — | PASS |
| CO-5 Colorado State Education → Mountain Y1 | 636 / 672 | — | PASS |

### Texas (5/5)

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| TX-1 UT-Austin Information 2004 Y1 | 731 / 1142 | 0.6401 | PASS |
| TX-2 Texas A&M Education 2010 Y5 | 3011 / 3365 | 0.8948 | PASS |
| TX-3 Sam Houston Health Care 2016 Y1 | 982 / 1018 | 0.9646 | PASS |
| TX-4 UT-Austin Information → West South Central Y1 | 731 / 742 | — | PASS |
| TX-5 Texas A&M Information → Pacific Y1 | 0 / 18 | — | PASS |

### Oregon (5/5)

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| OR-1 U Oregon Information 2004 Y1 | 289 / 423 | 0.6832 | PASS |
| OR-2 Oregon State Manufacturing 2010 Y10 | 572 / 850 | 0.6729 | PASS |
| OR-3 Portland State Health Care 2016 Y1 | 1321 / 1538 | 0.8589 | PASS |
| OR-4 U Oregon Information → Pacific Y1 | 289 / 372 | — | PASS |
| OR-5 Oregon State Education → Mountain Y1 | 0 / 35 | — | PASS |

### Utah (7/7)

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| UT-1 U Utah Information 2010 Y1 | 217 / 241 | 0.9004 | PASS |
| UT-2 U Utah Health Care 2010 Y10 | 1001 / 1588 | 0.6304 | PASS |
| UT-3 Utah State Education 2016 Y5 | 1121 / 1690 | 0.6633 | PASS |
| UT-4 Weber State Manufacturing 2016 Y1 | 343 / 436 | 0.7867 | PASS |
| UT-5 U Utah Information → Pacific Y1 | 0 / 10 | — | PASS |
| UT-6 Utah Valley Health Care → Mountain Y1 | 771 / 805 | — | PASS |
| UT-7 cohorts 2004 and 2007 absent | — | — | PASS |

### Layer 3 — dashboard aggregation logic (5/5)

These replicate the dashboard's own filter-and-aggregate path rather than
comparing files, so they test the ratio-of-sums logic the heatmap, line plot,
and Sankey depend on.

| Check | Value | Result |
|---|---|---|
| L3-1 ASU Education 2004 Y1, single cell | 3788 / 4140 = 0.9150 | PASS |
| L3-2 ASU Education, all cohorts, Y1 | 17132 / 20803 = 0.8235 | PASS |
| L3-3 Cross-state: ASU + UT Austin, Education 2004 Y1 | 6484 / 7204 = 0.9001 | PASS |
| L3-4 AZ aggregate, all inst × ind × cohorts, Y1 | 203146 / 289679 = 0.7013 | PASS |
| L3-5 Sankey flow, ASU Education → Mountain 2004 Y1 | 3834 | PASS |

**L3-4 is the strongest single result here.** Its expected value comes from an
earlier Stata `total` command, so the match confirms the Streamlit aggregation
reproduces the Stata pipeline's output — not merely that the bundled CSVs match
the raw release. L3-2 and L3-3 confirm that cross-cohort and cross-state
aggregation compose correctly when several filters are active at once.

### Montana (5/5)

| Check | in-state / total | Result |
|---|---|---|
| MT-1 Montana State Mining 2004 Y1 | — | PASS |
| MT-2 U Montana Education 2010 Y10 | — | PASS |
| MT-3 Montana Tech Manufacturing 2016 Y5 | — | PASS |
| MT-4 Montana State Education → Mountain Y1 | — | PASS |
| MT-5 U Montana Information → Pacific Y1 | — | PASS |

### Benchmark (12/12)

The participating-state reference series is a sum over 31 states, so there is
no single raw file to diff against. These check arithmetic invariants,
agreement with the state files that feed it, and that the IPEDS sector rule
still selects what it was validated to select.

| Check | Result |
|---|---|
| BM-1 `SI_by_cohort == emp_instate_ / emp_n_` (max dev 3.45e-08) | PASS |
| BM-2 in-state never exceeds total | PASS |
| BM-3 no negative counts | PASS |
| BM-4 20 NAICS sectors present | PASS |
| BM-5 horizons are exactly 1, 5, 10 | PASS |
| BM-6 cohorts are the triennial set | PASS |
| BM-7 single label, marked `BENCH` | PASS |
| BM-8 benchmark ≥ sum of the 6 dashboard states (280 cells) | PASS |
| BM-9 composition recorded — 31 states, 356 institutions | PASS |
| BM-10 PSEO's `us` file (WGU) excluded | PASS |
| BM-11 IPEDS rule keeps all 54 curated institutions | PASS |
| BM-12 IPEDS rule drops community colleges and WGU | PASS |

BM-11 and BM-12 are the regression guards that matter: they pin the sector
rule to the behaviour it was validated on, so a future IPEDS vintage that
reclassified Utah's dual-mission universities or a Colorado community college
would fail the audit rather than silently change the baseline.

## Run of 2026-08-22 — full-column comparison against Stata

The limitation recorded below ("a stronger check for publication would be a
full-column comparison against a Stata-generated file rather than sampled
cells") has now been carried out for AZ, CO, and TX.

No new Stata run was required. AZ, CO, and TX were originally built in Stata
and those exports are committed in `data/`, so the comparison is against
artifacts that already existed. Each state was rebuilt with
`build_state_data.py` from **the same local raw files the Stata pipeline
consumed**, not a fresh Census download, so the release vintage is held fixed
and any difference is attributable to implementation rather than data. Labels
were supplied through `--rename` to match the Stata value labels, and the
documented thresholds were reapplied (CO 320, TX 340, AZ none).

Every cell of both files was compared, joined on
`institution_cat × industry_cat × grad_cohort × horizon` (plus `region_cat`
for flows).

| State | TSI cells | flow cells | `emp_instate_` | `emp_n_` | `SI_by_cohort` |
|-------|-----------|------------|----------------|----------|----------------|
| AZ | 1,080 | 9,720 | 0 differ | 0 differ | 1 differs |
| CO | 4,320 | 38,880 | 0 differ | 0 differ | 0 differ |
| TX | 7,200 | 64,800 | 0 differ | 0 differ | 1 differs |

116,280 cells compared. Key sets are identical in every file: no row is present
in one build and absent from the other.

### The two differences

```
AZ  ASU, Other Services, 2010, Y10           305/512  .59570312  vs  .59570313
TX  U Houston Downtown, Prof Svcs, 2013, Y1  481/512  .93945312  vs  .93945313
```

Both denominators are 512. A power of two makes the float32 quotient exactly
representable, so the decimal expansion terminates in a 5 at the ninth place
and the eighth-place rounding is a genuine tie: 0.595703125 and 0.939453125.
Python rounds half to even, Stata rounds half away from zero. This is a
tie-breaking convention, not a numerical disagreement, and it can only arise
where `emp_n_` is a power of two.

### Institution selection

`--min-observed 320` selected Colorado's twelve institutions and
`--min-observed 340` selected Texas's twenty — the same sets the `.do` files
enumerate by hand in `inlist()`. The coverage-and-threshold path is therefore
confirmed against Stata, not merely the arithmetic downstream of it.

### Row ordering

Flows files differ in row order in all three states while being
content-identical (sorted diff: 0 lines). `app.py` aggregates and is
indifferent, but `cmp` is the wrong tool for checking these files.

## South Carolina — built without Stata

SC has no Stata counterpart; it was built by `build_state_data.py` alone, which
is defensible only because of the comparison above. Its twelve institutions
come from running the IPEDS sector rule directly rather than from a threshold,
because no threshold separates sector in South Carolina (see README).

Values below were checked against an independent read of the raw release using
separate filtering code, so a shared bug would have to appear in both paths.

| Check | in-state / total | TSI | Result |
|---|---|---|---|
| SC-1 USC Education 2004 Y1 | 546 / 697 | 0.7834 | PASS |
| SC-2 Clemson Manufacturing 2010 Y10 | 486 / 902 | 0.5388 | PASS |
| SC-3 The Citadel Public Admin 2007 Y5 | 94 / 121 | 0.7769 | PASS |
| SC-4 Coastal Carolina Food/Hospitality 2016 Y1 | 364 / 560 | 0.6500 | PASS |
| SC-5 USC Beaufort Health Care 2019 Y1 | 120 / 195 | 0.6154 | PASS |
| SC-6 Clemson Manufacturing 2004 → South Atlantic Y1 | 359 / 534 | — | PASS |
| SC-7 SC aggregate, all inst × ind × cohorts, Y1 | 121556 / 198965 | 0.6109 | PASS |

SC-7 is the Layer 3 analogue. Its `emp_n_` total of 198,965 equals the
`grads_y1` figure recorded for SC in `data/benchmark_composition.csv`, computed
by a different code path at a different time. SC was already a benchmark
contributor before it became a dashboard state, so adding it does not move the
reference line and `benchmark.csv` needs no regeneration.

South Carolina's release is `V4.13.0 / 2025Q4`. The six earlier states were
built from files downloaded in April 2026. Whether those vintages differ has
not been established.

## Scope and limitations

- **These are spot checks, not full verification.** 27 sampled cells against a
  corpus of 16,560 TSI cells and 149,040 flow cells. They confirm the analytic
  filters, institution and industry label mappings, and the reshape are
  correct; they cannot rule out an error confined to cells not sampled. The
  Layer 3 checks are broader — L3-4 aggregates every Arizona cell at Y1 — but
  cover only AZ and TX.
- **AZ, TX, and CO were built in Stata; OR, UT, MT, and SC were built by
  `build_state_data.py`.** Both paths reproduce the raw values exactly at
  every cell checked, which is the evidence that the Python builder is a
  faithful reimplementation of the `.do` pipeline.
- **Layer 3 covers only AZ and TX.** Its expected values are hardcoded for
  those states, so it is skipped unless both are in scope. There is no
  equivalent aggregation check for CO, OR, or UT.
- ~~A stronger check for publication would be a full-column comparison against
  a Stata-generated file rather than sampled cells.~~ Done for AZ, CO, and TX
  on 2026-08-22; see above. Not done for OR, UT, MT, or SC, none of which have
  a Stata counterpart to compare against.
