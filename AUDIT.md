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

## Scope and limitations

- **These are spot checks, not full verification.** 27 sampled cells against a
  corpus of 16,560 TSI cells and 149,040 flow cells. They confirm the analytic
  filters, institution and industry label mappings, and the reshape are
  correct; they cannot rule out an error confined to cells not sampled. The
  Layer 3 checks are broader — L3-4 aggregates every Arizona cell at Y1 — but
  cover only AZ and TX.
- **AZ, TX, and CO were built in Stata; OR and UT were built by
  `build_state_data.py`.** Both paths reproduce the raw values exactly at
  every cell checked, which is the evidence that the Python builder is a
  faithful reimplementation of the `.do` pipeline.
- **Layer 3 covers only AZ and TX.** Its expected values are hardcoded for
  those states, so it is skipped unless both are in scope. There is no
  equivalent aggregation check for CO, OR, or UT.
- A stronger check for publication would be a full-column comparison against a
  Stata-generated file rather than sampled cells.
