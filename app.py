import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path

# ============================================================
# Page setup
# ============================================================
st.set_page_config(
    page_title="PSEO Talent Stickiness Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set Plotly default template for cleaner-looking charts
pio.templates.default = "plotly_white"

st.title("PSEO Talent Stickiness Dashboard")
st.caption("Bachelor's degree graduate retention across institutions, industries, cohorts, and regions")

# ============================================================
# Data loading
# ============================================================
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data
def load_tsi():
    az = pd.read_csv(DATA_DIR / "az_tsi.csv")
    tx = pd.read_csv(DATA_DIR / "tx_tsi.csv")
    co = pd.read_csv(DATA_DIR / "co_tsi.csv")
    df = pd.concat([az, tx, co], ignore_index=True)
    df["grad_cohort"] = df["grad_cohort"].astype(str)
    df["horizon"] = df["horizon"].astype(int)
    return df

@st.cache_data
def load_flows():
    az = pd.read_csv(DATA_DIR / "az_regional_flows.csv")
    tx = pd.read_csv(DATA_DIR / "tx_regional_flows.csv")
    co = pd.read_csv(DATA_DIR / "co_regional_flows.csv")
    df = pd.concat([az, tx, co], ignore_index=True)
    df["grad_cohort"] = df["grad_cohort"].astype(str)
    df["horizon"] = df["horizon"].astype(int)
    return df

tsi = load_tsi()
flows = load_flows()

# ============================================================
# Sidebar filters
# ============================================================
st.sidebar.header("Filters")

# Default institution set: 3 AZ + 3 representative TX
DEFAULT_INSTITUTIONS = [
    "ASU", "NAU", "UA",
    "UT Austin", "Texas A&M", "Sam Houston State",
    "CU Boulder", "Colorado State"
]

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
default_institutions = [i for i in DEFAULT_INSTITUTIONS if i in institutions_available]
institutions_selected = st.sidebar.multiselect(
    "Institution",
    options=institutions_available,
    default=default_institutions
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
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Heatmap",
    "Horizon Decay",
    "Regional Flows (Sankey)",
    "Summary Table"
])

# ---------------- Overview ----------------
with tab0:
    st.markdown(
        """
        ### A year after graduation, most college graduates are still working in their state. Ten years out, the picture looks very different.

        This dashboard presents the Talent Stickiness Index (TSI), a measure of the share
        of a university's graduates who remain employed in their home state at one, five,
        and ten years after graduation. It draws on the U.S. Census Bureau's Postsecondary
        Employment Outcomes (PSEO) data and covers bachelor's degree graduates from public
        universities in Arizona, Texas, and Colorado, across graduation cohorts from 2004
        to 2019 and twenty industries defined by two-digit NAICS codes.

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
        - **Horizon Decay** — how does retention change as graduates move further from graduation?
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

# ---------------- Heatmap ----------------
with tab1:
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
        st.plotly_chart(fig, use_container_width=True)

# ---------------- Horizon decay line plot ----------------
with tab2:
    st.subheader("Horizon Decay — TSI by horizon, one line per institution")

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
        fig.update_yaxes(range=[0.4, 1.0], tickformat=".0%")
        fig.update_xaxes(tickmode="array", tickvals=[1, 5, 10], ticktext=["Y1", "Y5", "Y10"])
        fig.update_layout(
            height=600,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------- Sankey ----------------
with tab3:
    st.subheader(f"Regional Flows — Y{horizon_selected}, total counts across selected filters")

    f = flows_filtered[flows_filtered["horizon"] == horizon_selected]
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
            # Light pastel region colors — same across both Sankeys
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
            # Soft state-themed institution palettes
            AZ_INST_COLOR = "#a4506b"   # muted maroon (ASU)
            TX_INST_COLOR = "#c47b3a"   # muted burnt-orange (Texas)
            CO_INST_COLOR = "#5a8b8e"   # muted teal (Colorado mountains)

            states_with_data = sorted(agg["state"].unique())

            if len(states_with_data) == 1:
                cols = [st.container()]
            else:
                cols = st.columns(len(states_with_data))

            for col, state_code in zip(cols, states_with_data):
                with col:
                    state_agg = agg[agg["state"] == state_code]
                    institutions = state_agg["institution_cat"].unique().tolist()
                    regions = state_agg["region_cat"].unique().tolist()

                    # Single muted color for all institutions in a state
                    if state_code == "AZ":
                        inst_color = AZ_INST_COLOR
                    elif state_code == "TX":
                        inst_color = TX_INST_COLOR
                    elif state_code == "CO":
                        inst_color = CO_INST_COLOR
                    else:
                        inst_color = "#888888"
                    inst_colors = [inst_color] * len(institutions)
                    region_colors = [REGION_COLORS.get(r, "#dddddd") for r in regions]
                    node_colors = inst_colors + region_colors

                    labels = institutions + regions
                    label_to_idx = {label: i for i, label in enumerate(labels)}

                    sources = [label_to_idx[i] for i in state_agg["institution_cat"]]
                    targets = [label_to_idx[r] for r in state_agg["region_cat"]]
                    values = state_agg["grads"].tolist()

                    # Very light ribbons — let the node colors do the work
                    def hex_to_rgba(hex_color, alpha=0.18):
                        h = hex_color.lstrip("#")
                        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                        return f"rgba({r},{g},{b},{alpha})"

                    link_colors = [hex_to_rgba(inst_color) for _ in sources]

                    fig = go.Figure(data=[go.Sankey(
                        arrangement="snap",
                        node=dict(
                            pad=25,
                            thickness=14,
                            line=dict(color="rgba(0,0,0,0.2)", width=0.5),
                            label=labels,
                            color=node_colors,
                        ),
                        link=dict(
                            source=sources,
                            target=targets,
                            value=values,
                            color=link_colors,
                        )
                    )])
                    fig.update_layout(
                        height=600,
                        font=dict(size=12, color="#1a1a1a", family="sans-serif"),
                        title=dict(
                            text=f"{state_code} — Y{horizon_selected}",
                            font=dict(size=14, color="#1a1a1a")
                        ),
                        margin=dict(l=20, r=20, t=50, b=20),
                        paper_bgcolor="white",
                        plot_bgcolor="white",
                    )
                    st.plotly_chart(fig, use_container_width=True)

# ---------------- Summary Table ----------------
with tab4:
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
