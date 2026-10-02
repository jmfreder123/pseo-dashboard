import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path

import insights

# ============================================================
# Page setup
# ============================================================
st.set_page_config(
    page_title="PSEO Talent Stickiness Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Analytics (GA4) -- injects tracking tag into the app's HTML head once at startup
def _inject_ga(measurement_id):
    snippet = (
        '<script async src="https://www.googletagmanager.com/gtag/js?id=' + measurement_id + '"></script>'
        '<script>window.dataLayer = window.dataLayer || [];function gtag(){dataLayer.push(arguments);}'
        "gtag('js', new Date());gtag('config', '" + measurement_id + "');</script>"
    )
    # Patching Streamlit's own package HTML only works where that directory is
    # writable -- i.e. locally. On Streamlit Cloud it is read-only and the write
    # raises PermissionError at import time, which takes the whole app down. The
    # tag is not worth the site, so failure here is silent and the app starts
    # without analytics.
    try:
        index_path = Path(st.__file__).parent / "static" / "index.html"
        html = index_path.read_text(encoding="utf-8")
        if measurement_id not in html:
            index_path.write_text(html.replace("<head>", "<head>" + snippet, 1), encoding="utf-8")
    except (OSError, PermissionError):
        pass

_inject_ga("G-W4SJXLVGL6")

# Set Plotly default template for cleaner-looking charts
pio.templates.default = "plotly_white"

# Opening animation: a graduate leaves home, walks through the door, comes out
# the other side and shakes hands with an employer. Hand-drawn SVG and CSS in
# assets/intro.html. It stays on the page and replays once a minute (the scene
# itself is about five seconds; the final frame holds the rest of the time).
# Drawn on every run so nothing above the tab bar ever changes between reruns.
try:
    _intro = (Path(__file__).parent / "assets" / "intro.html").read_text(encoding="utf-8")
    st.components.v1.html(_intro, height=104)
except OSError:
    pass

ASSETS_DIR = Path(__file__).parent / "assets"


def scene(name, width=240, height=72):
    """A small looping drawing at the top of a tab (assets/scenes/<name>.html).
    Decorative only; a missing file is skipped rather than shown as an error."""
    try:
        html = (ASSETS_DIR / "scenes" / f"{name}.html").read_text(encoding="utf-8")
    except OSError:
        return
    st.components.v1.html(html, width=width, height=height)


st.title("PSEO Talent Stickiness Dashboard")
st.caption("Bachelor's degree graduate retention across institutions, industries, cohorts, and regions")

# ============================================================
# Data loading
# ============================================================
DATA_DIR = Path(__file__).parent / "data"

def _load_glob(pattern):
    """Concatenate every state file matching pattern.

    States register by dropping their CSVs in data/ -- no code change needed
    to add one. Build them with build_state_data.py.
    """
    paths = sorted(DATA_DIR.glob(pattern))
    if not paths:
        st.error(f"No data files matching {pattern!r} in {DATA_DIR}")
        st.stop()
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    df["grad_cohort"] = df["grad_cohort"].astype(str)
    df["horizon"] = df["horizon"].astype(int)
    return df

# cache_resource, not cache_data: cache_data hands every session its own
# unpickled copy of the frames (about 45 MB each for the flows), which is what
# made memory grow with every visitor. cache_resource shares one object. That
# is safe here because nothing below mutates these frames -- every filter
# builds a new frame with a boolean mask, and the one place that adds a column
# (insights.leaver_destinations) copies first.
@st.cache_resource
def load_tsi():
    return _load_glob("*_tsi.csv")

@st.cache_resource
def load_flows():
    return _load_glob("*_regional_flows.csv")

@st.cache_resource
def load_benchmark():
    """Participating-state reference series, or None if not built.

    Deliberately not named *_tsi.csv: it is a reference line, not a state, and
    must stay out of the state/institution filters.
    """
    path = DATA_DIR / "benchmark.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["grad_cohort"] = df["grad_cohort"].astype(str)
    df["horizon"] = df["horizon"].astype(int)
    return df

tsi = load_tsi()
flows = load_flows()
benchmark = load_benchmark()

# ============================================================
# Sidebar filters
# ============================================================
st.sidebar.header("Filters")
st.sidebar.caption(
    "Four flagships are selected to start. Add more states and schools below, "
    "or filter by industry and graduation year."
)

# The flagship university of each state. Used as the fallback selection for any
# multi-state comparison that the opening set does not cover, so no combination
# of states ever opens empty. Mirrors FLAGSHIP in insights.py.
FLAGSHIPS = [
    "UA",                                  # Arizona
    "UT Austin",                           # Texas
    "CU Boulder",                          # Colorado
    "University of Oregon",                # Oregon
    "University of Utah",                  # Utah
    "University of Montana",               # Montana
    "University of South Carolina (USC)",  # South Carolina
    "University of Hawaii (UH)",           # Hawaii
    "Ohio State",                          # Ohio
    "SUNY Buffalo",                        # New York
]

# What a first-time visitor sees: the flagships of the four states the dashboard
# launched with. Deliberately short so the Institution filter fits its box.
OPENING_INSTITUTIONS = ["UA", "UT Austin", "CU Boulder", "University of Oregon"]

# State
states_available = sorted(tsi["state"].unique())
states_selected = st.sidebar.multiselect(
    "State",
    options=states_available,
    default=states_available
)

# Institution (depends on state)
institutions_available = sorted(
    tsi[tsi["state"].isin(states_selected)]["institution_cat"].unique()
)
# The institution selection is reset only when the state selection changes.
# Three cases:
#   first load              -> the opening four (what a first-time visitor sees)
#   one state               -> every institution in it (the point is that state's detail)
#   two or more states      -> the flagship of each selected state, including when
#                              every state is selected
# The final `or` guards a state with no flagship listed, so nothing ever opens empty.
# Streamlit recreates a multiselect whenever its `default` changes, which is why
# the selection is written to session_state under a fixed key instead: any other
# filter change leaves the institutions alone.
first_load = "prev_states" not in st.session_state
if first_load:
    default_institutions = [i for i in OPENING_INSTITUTIONS if i in institutions_available]
elif len(states_selected) == 1:
    default_institutions = institutions_available
else:
    default_institutions = (
        [i for i in FLAGSHIPS if i in institutions_available]
        or institutions_available
    )
if st.session_state.get("prev_states") != states_selected:
    st.session_state["institutions"] = default_institutions
    st.session_state["prev_states"] = states_selected
    # Remember what the app chose, and whether it was the first-load set, so
    # the Sankey tab can tell an untouched opening selection from a deliberate one.
    st.session_state["institutions_auto"] = default_institutions
    st.session_state["institutions_auto_is_opening"] = first_load
institutions_selected = st.sidebar.multiselect(
    "Institution",
    options=institutions_available,
    key="institutions",
)

# Industry
industries_available = sorted(tsi["industry_cat"].unique())
industries_selected = st.sidebar.multiselect(
    "Industry",
    options=industries_available,
    default=industries_available
)

# Horizon
horizons_available = sorted(tsi["horizon"].unique())
horizon_selected = st.sidebar.selectbox(
    "Horizon (single, for heatmap and Sankey)",
    options=horizons_available,
    index=0,
    format_func=lambda h: f"Y{h}"
)
horizons_for_lineplot = st.sidebar.multiselect(
    "Horizons for line plot",
    options=horizons_available,
    default=horizons_available,
    format_func=lambda h: f"Y{h}"
)

# Cohort
cohorts_available = sorted(tsi["grad_cohort"].unique())
cohorts_selected = st.sidebar.multiselect(
    "Cohort",
    options=cohorts_available,
    default=cohorts_available
)

# Reference line (Retention Over Time tab only)
if benchmark is not None:
    show_benchmark = st.sidebar.checkbox(
        "Show participating-state reference",
        value=True,
        help="Dashed line on Retention Over Time: all PSEO states aggregated. "
             "Not a national figure -- PSEO covers about two thirds of states.",
    )
else:
    show_benchmark = False

# ============================================================
# Apply filters
# ============================================================
def filter_tsi(df):
    return df[
        (df["state"].isin(states_selected)) &
        (df["institution_cat"].isin(institutions_selected)) &
        (df["industry_cat"].isin(industries_selected)) &
        (df["grad_cohort"].isin(cohorts_selected))
    ]

def filter_flows(df):
    return df[
        (df["state"].isin(states_selected)) &
        (df["institution_cat"].isin(institutions_selected)) &
        (df["industry_cat"].isin(industries_selected)) &
        (df["grad_cohort"].isin(cohorts_selected))
    ]

tsi_filtered = filter_tsi(tsi)
flows_filtered = filter_flows(flows)

# ============================================================
# Sample size summary at top
# ============================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("States", len(states_selected))
col2.metric("Institutions", len(institutions_selected))
col3.metric("Industries", len(industries_selected))
col4.metric("Observed cells", f"{tsi_filtered['emp_n_'].notna().sum():,}")

# ============================================================
# Tabs
# ============================================================
tab0, tab_ins, tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Insights",
    "Heatmap",
    "Retention Over Time",
    "Regional Flows (Sankey)",
    "Summary Table"
])

# ---------------- Overview ----------------
with tab0:
    scene("overview")
    st.markdown(
        """
        ### A year after graduation, most college graduates are still working in the state where they earned their degree. Ten years out, the picture looks very different.

        This dashboard presents the Talent Stickiness Index (TSI), a measure of the share
        of a university's graduates who remain employed in that same state at one, five,
        and ten years after graduation. Built on the U.S. Census Bureau's Postsecondary
        Employment Outcomes (PSEO) data, it covers bachelor's degree graduates from public
        universities in Arizona, Texas, Colorado, Oregon, Utah, Montana, South
        Carolina, Hawaii, Ohio, and New York, spanning graduation cohorts from 2004 to 2019 and twenty
        industries defined by two-digit NAICS codes. Utah's data begin with the 2010
        cohort.

        The TSI is purely descriptive. It documents where graduates work; it does not explain why
        graduates stay or leave.
        """
    )

    st.markdown("#### How to read this dashboard")
    st.markdown(
        """
        - **State** and **Institution** filters compare retention across schools.
        - **Industry** filters isolate retention within a sector.
        - **Horizon** controls how many years after graduation the data reflects (Y1, Y5, Y10).
        - **Cohort** controls which graduating classes are included.
        """
    )

    st.markdown("The four panels each answer a different question:")
    st.markdown(
        """
        - **Heatmap** — which institution-industry combinations retain the most graduates?
        - **Retention Over Time** — how does retention change as graduates move further from graduation?
        - **Regional Flows** — where do graduates who leave the state actually go?
        - **Summary Table** — the underlying values, filterable and downloadable.
        """
    )

    with st.expander("Data and method"):
        st.markdown(
            """
            Data come from the U.S. Census Bureau's Postsecondary Employment Outcomes
            (PSEO) program, which links graduate records from participating state systems
            to Longitudinal Employer-Household Dynamics (LEHD) employment records.

            The TSI is calculated as the ratio of in-state employed graduates to total
            employed graduates within each cell. Aggregate values are weighted: counts
            are summed across cohorts before the ratio is computed. Suppressed cells are
            dropped before aggregation.

            Y10 data are observed only for the 2004, 2007, and 2010 cohorts. Y5 data
            exclude the 2019 cohort. Coverage varies by institution and industry; cells
            with fewer than the PSEO disclosure threshold are suppressed in the source data.
            """
        )

    with st.expander("About"):
        st.markdown(
            """
            This dashboard was built by John M. Fredericks and Roxanne Murphy, both of whom are doctoral students in Educational
            Policy and Evaluation at Arizona State University, in collaboration with
            advisors Mr. Margarita Pivovarova. It is part of their work
            supported by the PSEO Coalition.

            **Source data:** U.S. Census Bureau, LEHD Postsecondary Employment Outcomes (PSEO).
            **Source code:** [github.com/jmfreder123/pseo-dashboard](https://github.com/jmfreder123/pseo-dashboard)
            **Contact:** [jmfrede5@asu.edu]
            """
        )

# ---------------- Insights ----------------
with tab_ins:
    scene("insights")
    insights.render(tsi, flows)

# ---------------- Heatmap ----------------
with tab1:
    scene("heatmap")
    st.subheader(f"TSI Heatmap — Y{horizon_selected}, ratio of sums across selected cohorts")

    h = tsi_filtered[tsi_filtered["horizon"] == horizon_selected]
    if h.empty:
        st.info("No data for the current filter selection.")
    else:
        agg = (
            h.groupby(["institution_cat", "industry_cat"], as_index=False)
             .agg(emp_instate_=("emp_instate_", "sum"), emp_n_=("emp_n_", "sum"))
        )
        agg["TSI"] = agg["emp_instate_"] / agg["emp_n_"]
        pivot = agg.pivot(index="institution_cat", columns="industry_cat", values="TSI")

        # Sort by mean retention
        pivot = pivot.loc[pivot.mean(axis=1).sort_values(ascending=False).index]
        pivot = pivot[pivot.mean(axis=0).sort_values(ascending=False).index]

        fig = px.imshow(
            pivot,
            color_continuous_scale="RdYlGn",
            zmin=0.3,
            zmax=1.0,
            aspect="auto",
            labels=dict(color="TSI"),
            text_auto=".2f"
        )
        fig.update_layout(
            height=max(400, 35 * len(pivot.index)),
            xaxis_title="Industry",
            yaxis_title="Institution",
            xaxis=dict(tickangle=-45),
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True, config=insights.PLOTLY_CONFIG)

# ---------------- Retention over time line plot ----------------
with tab2:
    scene("retention")
    st.subheader("Retention Over Time — TSI at years 1, 5 and 10, one line per institution")

    h = tsi_filtered[tsi_filtered["horizon"].isin(horizons_for_lineplot)]
    if h.empty:
        st.info("No data for the current filter selection.")
    else:
        agg = (
            h.groupby(["state", "institution_cat", "horizon"], as_index=False)
             .agg(emp_instate_=("emp_instate_", "sum"), emp_n_=("emp_n_", "sum"))
        )
        agg["TSI"] = agg["emp_instate_"] / agg["emp_n_"]

        fig = px.line(
            agg,
            x="horizon",
            y="TSI",
            color="institution_cat",
            line_dash="state",
            markers=True,
            labels=dict(
                horizon="Years post-graduation",
                TSI="Talent Stickiness Index",
                institution_cat="Institution"
            ),
        )
        # Reference line: the same industries and cohorts, aggregated across
        # every PSEO state. Institution and state filters deliberately do not
        # apply -- the point is a fixed baseline to read the lines against.
        if show_benchmark and benchmark is not None:
            b = benchmark[
                benchmark["industry_cat"].isin(industries_selected)
                & benchmark["grad_cohort"].isin(cohorts_selected)
                & benchmark["horizon"].isin(horizons_for_lineplot)
            ]
            if not b.empty:
                bagg = (
                    b.groupby("horizon", as_index=False)
                     .agg(emp_instate_=("emp_instate_", "sum"), emp_n_=("emp_n_", "sum"))
                     .sort_values("horizon")
                )
                bagg["TSI"] = bagg["emp_instate_"] / bagg["emp_n_"]
                fig.add_scatter(
                    x=bagg["horizon"], y=bagg["TSI"],
                    mode="lines+markers",
                    name="Participating-state avg",
                    line=dict(color="#444444", width=3, dash="dash"),
                    marker=dict(size=8, symbol="diamond"),
                )

        fig.update_yaxes(range=[0.4, 1.0], tickformat=".0%")
        fig.update_xaxes(tickmode="array", tickvals=[1, 5, 10], ticktext=["Y1", "Y5", "Y10"])
        fig.update_layout(
            height=600,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True, config=insights.PLOTLY_CONFIG)

        if show_benchmark and benchmark is not None:
            st.caption(
                "The dashed line aggregates every state in the PSEO release, not the "
                "United States. PSEO excludes California, Florida, New Jersey and "
                "others, so read it as a participating-state average. Composition is "
                "recorded in `data/benchmark_composition.csv`."
            )

# ---------------- Sankey ----------------
# Light pastel region colors
REGION_COLORS = {
    "New England":         "#cfe2f3",
    "Middle Atlantic":     "#d9d2e9",
    "East North Central":  "#d9ead3",
    "West North Central":  "#fff2cc",
    "South Atlantic":      "#f4cccc",
    "East South Central":  "#ead1dc",
    "West South Central":  "#fce5cd",
    "Mountain":            "#d0e0e3",
    "Pacific":             "#f9cb9c",
}


def _hex_to_rgba(hex_color, alpha=0.18):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def sankey_figure(state_code, state_agg, horizon, height=600):
    """One state's institution -> region Sankey. Institutions take the state's
    dashboard colour (insights.STATE_COLORS), regions the pastel set above.
    The figure grows with the institution count so a 28-school state (New
    York) is not squeezed into the same height as a 3-school one."""
    institutions = state_agg["institution_cat"].unique().tolist()
    height = max(height, 32 * len(institutions) + 150)
    regions = state_agg["region_cat"].unique().tolist()
    inst_color = insights.STATE_COLORS.get(state_code, insights.STATE_COLOR_DEFAULT)
    labels = institutions + regions
    idx = {label: i for i, label in enumerate(labels)}
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25,
            thickness=14,
            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
            label=labels,
            color=[inst_color] * len(institutions)
                  + [REGION_COLORS.get(r, "#dddddd") for r in regions],
        ),
        link=dict(
            source=[idx[i] for i in state_agg["institution_cat"]],
            target=[idx[r] for r in state_agg["region_cat"]],
            value=state_agg["grads"].tolist(),
            color=[_hex_to_rgba(inst_color)] * len(state_agg),
        ),
    )])
    fig.update_layout(
        height=height,
        font=dict(size=12, color="#1a1a1a", family="sans-serif"),
        title=dict(
            text=f"{insights.STATE_NAMES.get(state_code, state_code)} — Y{horizon}",
            font=dict(size=14, color="#1a1a1a"),
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def _sankey_step(states, delta):
    cur = st.session_state.get("sankey_state")
    i = states.index(cur) if cur in states else 0
    st.session_state["sankey_state"] = states[(i + delta) % len(states)]


def sankey_nav(states, key):
    """Previous / Next buttons around a 'State — n of N' label. Returns the
    state code currently shown. One state: no buttons, just the label."""
    cur = st.session_state.get("sankey_state")
    if cur not in states:
        cur = states[0]
        st.session_state["sankey_state"] = cur
    if len(states) == 1:
        return cur
    prev_col, mid, next_col = st.columns([1, 3, 1])
    prev_col.button("← Previous", key=f"{key}_prev", use_container_width=True,
                    on_click=_sankey_step, args=(states, -1))
    next_col.button("Next →", key=f"{key}_next", use_container_width=True,
                    on_click=_sankey_step, args=(states, 1))
    mid.markdown(
        f"<div style='text-align:center;padding-top:0.45rem'>"
        f"<b>{insights.STATE_NAMES.get(cur, cur)}</b> &nbsp;·&nbsp; "
        f"{states.index(cur) + 1} of {len(states)}</div>",
        unsafe_allow_html=True,
    )
    return cur


@st.dialog("Regional Flows", width="large")
def sankey_popup(agg, states, horizon):
    cur = sankey_nav(states, "popup")
    fig = sankey_figure(cur, agg[agg["state"] == cur], horizon, height=650)
    st.plotly_chart(fig, use_container_width=True, config=insights.PLOTLY_CONFIG)


with tab3:
    scene("flows")
    st.subheader(f"Regional Flows — Y{horizon_selected}, total counts across selected filters")

    # On first load the sidebar holds the opening four, but the Sankey is the
    # one view where a state-by-state tour is the point, so until the visitor
    # touches the Institution filter it shows the flagship of every state.
    sankey_untouched = (
        st.session_state.get("institutions_auto_is_opening", False)
        and institutions_selected == st.session_state.get("institutions_auto")
    )
    if sankey_untouched:
        sankey_flows = flows[
            (flows["state"].isin(states_selected)) &
            (flows["institution_cat"].isin(FLAGSHIPS)) &
            (flows["industry_cat"].isin(industries_selected)) &
            (flows["grad_cohort"].isin(cohorts_selected))
        ]
        st.caption("Showing the flagship of every state. Change the Institution "
                   "filter at left to pick other schools.")
    else:
        sankey_flows = flows_filtered

    f = sankey_flows[sankey_flows["horizon"] == horizon_selected]
    if f.empty:
        st.info("No regional flow data for the current filter selection.")
    else:
        agg = (
            f.groupby(["state", "institution_cat", "region_cat"], as_index=False)
             .agg(grads=("emp_n_", "sum"))
        )
        agg = agg[agg["grads"] > 0]

        if agg.empty:
            st.info("All counts are zero or suppressed for this filter.")
        else:
            states_with_data = sorted(agg["state"].unique())
            if len(states_with_data) > 1:
                st.caption("One state at a time. Use the buttons to move between states, "
                           "or open the pop-up for a larger view.")
            cur = sankey_nav(states_with_data, "tab")
            fig = sankey_figure(cur, agg[agg["state"] == cur], horizon_selected)
            st.plotly_chart(fig, use_container_width=True, config=insights.PLOTLY_CONFIG)
            if st.button("Open in pop-up", key="sankey_open"):
                sankey_popup(agg, states_with_data, horizon_selected)

# ---------------- Summary Table ----------------
with tab4:
    scene("table")
    st.subheader("Filtered TSI Data")

    if tsi_filtered.empty:
        st.info("No data for the current filter selection.")
    else:
        display_df = tsi_filtered.copy()
        display_df = display_df.sort_values(
            ["state", "institution_cat", "industry_cat", "grad_cohort", "horizon"]
        )
        display_df["SI_by_cohort"] = display_df["SI_by_cohort"].round(3)
        st.dataframe(display_df, use_container_width=True, height=600)

        st.download_button(
            "Download as CSV",
            data=display_df.to_csv(index=False),
            file_name="tsi_filtered.csv",
            mime="text/csv"
        )

# ============================================================
# Footer
# ============================================================
st.markdown("<div style='height: 2.5rem'></div>", unsafe_allow_html=True)
st.divider()
f_left, f_mid, f_right = st.columns([1.1, 3, 2.4], vertical_alignment="center")
with f_left:
    st.image(str(ASSETS_DIR / "pseo_coalition.png"), width=120)
with f_mid:
    st.caption(
        "Built at Arizona State University's Mary Lou Fulton College for Teaching and "
        "Learning Innovation with support from the PSEO Coalition. "
        "Data: U.S. Census Bureau, Post-Secondary Employment Outcomes."
    )
with f_right:
    st.image(str(ASSETS_DIR / "asu_mlf_horizontal.png"), width=320)
