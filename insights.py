"""Insights tab: headline stories computed from the full dataset.

Everything here is a ratio of sums over all states, institutions, industries and
cohorts, deliberately ignoring the sidebar filters -- the stories describe the
whole dashboard, and the default filter is four flagships.

Colour: one accent (#9B2247, a validated step of the dashboard's maroon), a
de-emphasis grey, a two-step maroon ordinal ramp, and a single-hue sequential
ramp. Nothing categorical beyond two series.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ACCENT = "#9B2247"
ACCENT_LIGHT = "#C9657F"
GREY = "#B0B0B0"

# One colour per state, everywhere on the dashboard. Slots are assigned in the
# order states joined and never reshuffled, so a state keeps its colour when
# another is added; a ninth state takes the next slot. The eight hues are the
# dataviz skill's validated categorical set (adjacent-pair CVD and normal-vision
# checks pass; three hues sit below 3:1 on white, which is why every chart that
# uses them labels rows by name and carries a table).
STATE_COLORS = {
    "AZ": "#2a78d6",  # blue
    "TX": "#eb6834",  # orange
    "CO": "#1baf7a",  # aqua
    "OR": "#eda100",  # yellow
    "UT": "#e87ba4",  # magenta
    "MT": "#008300",  # green
    "SC": "#4a3aa7",  # violet
    "HI": "#e34948",  # red
    "OH": "#ad1457",  # deep pink
    "NY": "#8bc34a",  # lime
}
STATE_COLOR_DEFAULT = "#888888"

# Plotly's toolbar, trimmed to the single camera (download as PNG). Zoom, pan,
# autoscale and the rest are noise on charts this size. Used by every chart in
# the app so the toolbar looks the same everywhere.
PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d",
        "autoScale2d", "resetScale2d", "toggleSpikelines",
        "hoverClosestCartesian", "hoverCompareCartesian",
        "resetSankeyGroup",
    ],
}

# Fully non-interactive: no zoom, pan, hover or toolbar, and touches fall through
# to the page. Not currently used: it fixes thumb-zoom on phones but costs the
# hover tooltips, and the dashboard is read mostly on desktop. Kept so the
# trade-off can be flipped back with a one-word change per chart.
PLOTLY_STATIC = {"staticPlot": True, "displayModeBar": False}


def state_color(code, alpha=None):
    hex_ = STATE_COLORS.get(code, STATE_COLOR_DEFAULT)
    if alpha is None:
        return hex_
    r, g, b = int(hex_[1:3], 16), int(hex_[3:5], 16), int(hex_[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"
INK = "#1A1A1A"
INK_MUTED = "#6B6B6B"
GRID = "#E8E8E8"
SEQ = ["#FBEFF2", "#9B2247"]   # single hue, light -> dark

STATE_NAMES = {
    "AZ": "Arizona", "CO": "Colorado", "HI": "Hawaii", "MT": "Montana",
    "NY": "New York", "OH": "Ohio", "OR": "Oregon", "SC": "South Carolina",
    "TX": "Texas", "UT": "Utah",
}

# Flagship per state: mirrors DEFAULT_INSTITUTIONS in app.py. Kept here rather
# than imported so this module has no dependency on app.py's load order.
FLAGSHIP = {
    "AZ": "UA", "TX": "UT Austin", "CO": "CU Boulder",
    "OR": "University of Oregon", "UT": "University of Utah",
    "MT": "University of Montana", "SC": "University of South Carolina (USC)",
    "HI": "University of Hawaii (UH)",
    "OH": "Ohio State", "NY": "SUNY Buffalo",
}


def _tsi(df):
    n = df["emp_n_"].sum()
    return df["emp_instate_"].sum() / n if n else float("nan")


def _name(code):
    return STATE_NAMES.get(code, code)


def _base_layout(fig, height, **kw):
    kw.setdefault("margin", dict(l=10, r=20, t=10, b=10))
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, size=13),
        hoverlabel=dict(bgcolor="white", font_size=13),
        **kw,
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
                     linecolor=GRID, tickfont=dict(color=INK_MUTED))
    fig.update_yaxes(showgrid=False, zeroline=False, linecolor=GRID,
                     tickfont=dict(color=INK))
    return fig


# ------------------------------------------------------------------
# Computations
# ------------------------------------------------------------------
def state_horizons(tsi):
    rows = []
    for s, g in tsi.groupby("state"):
        r = {"state": s}
        for h in (1, 5, 10):
            r[f"Y{h}"] = _tsi(g[g["horizon"] == h])
        rows.append(r)
    d = pd.DataFrame(rows)
    d["loss_1_5"] = d["Y1"] - d["Y5"]
    d["loss_5_10"] = d["Y5"] - d["Y10"]
    d["loss_total"] = d["Y1"] - d["Y10"]
    return d


def flagship_gap(tsi):
    y1 = tsi[tsi["horizon"] == 1]
    rows = []
    for s, g in y1.groupby("state"):
        if g["institution_cat"].nunique() < 2 or s not in FLAGSHIP:
            continue
        f = g[g["institution_cat"] == FLAGSHIP[s]]
        o = g[g["institution_cat"] != FLAGSHIP[s]]
        if f.empty or o.empty:
            continue
        rows.append({"state": s, "flagship": FLAGSHIP[s], "flag_tsi": _tsi(f),
                     "others_tsi": _tsi(o), "n_others": o["institution_cat"].nunique()})
    d = pd.DataFrame(rows)
    d["gap"] = d["flag_tsi"] - d["others_tsi"]
    return d


def leaver_destinations(flows):
    """Share of each state's out-of-state employed graduates by Census division, Y1.

    Out-of-state within a division = emp_n_ - emp_instate_, so a graduate from
    Arizona working in Colorado counts as a leaver even though both are Mountain.
    """
    f = flows[flows["horizon"] == 1].copy()
    f["out"] = f["emp_n_"] - f["emp_instate_"]
    f = f.dropna(subset=["out"])
    g = f.groupby(["state", "region_cat"], as_index=False)["out"].sum()
    tot = g.groupby("state")["out"].transform("sum")
    g["share"] = g["out"] / tot
    return g


def industry_tsi(tsi):
    y1 = tsi[tsi["horizon"] == 1]
    rows = [{"industry": i, "tsi": _tsi(g), "grads": g["emp_n_"].sum()}
            for i, g in y1.groupby("industry_cat")]
    return pd.DataFrame(rows).sort_values("tsi", ascending=True)


# ------------------------------------------------------------------
# Charts
# ------------------------------------------------------------------
def chart_leak(d):
    d = d.sort_values("loss_total", ascending=True)
    labels = [_name(s) for s in d["state"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=d["loss_1_5"], orientation="h", name="Lost between year 1 and year 5",
        marker=dict(color=[state_color(s, 0.45) for s in d["state"]],
                    line=dict(color="white", width=2)),
        customdata=d[["Y1", "Y5"]].values,
        hovertemplate="%{y}<br>Year 1 %{customdata[0]:.1%} → year 5 %{customdata[1]:.1%}<br>"
                      "Lost: %{x:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=labels, x=d["loss_5_10"], orientation="h", name="Lost between year 5 and year 10",
        marker=dict(color=[state_color(s) for s in d["state"]],
                    line=dict(color="white", width=2)),
        customdata=d[["Y5", "Y10"]].values,
        hovertemplate="%{y}<br>Year 5 %{customdata[0]:.1%} → year 10 %{customdata[1]:.1%}<br>"
                      "Lost: %{x:.1%}<extra></extra>",
    ))
    for _, r in d.iterrows():
        fig.add_annotation(x=r["loss_total"], y=_name(r["state"]), xanchor="left", xshift=8,
                           text=f"{r['Y1']:.0%} → {r['Y10']:.0%}", showarrow=False,
                           font=dict(color=INK_MUTED, size=12))
    _base_layout(fig, 70 + 36 * len(d), barmode="stack", bargap=0.45,
                 margin=dict(l=10, r=20, t=40, b=10))
    fig.update_traces(showlegend=False)
    fig.add_annotation(xref="paper", yref="paper", x=0, y=1, yanchor="bottom", yshift=10, xanchor="left", showarrow=False,
                       text="Lighter segment: lost between year 1 and year 5 · "
                            "Solid segment: lost between year 5 and year 10",
                       font=dict(size=12, color=INK_MUTED))
    fig.update_xaxes(tickformat=".0%", range=[0, d["loss_total"].max() * 1.45],
                     title="Share of graduates no longer working in-state")
    fig.update_yaxes(categoryorder="array", categoryarray=labels)
    return fig


def chart_destinations(g):
    piv = g.pivot(index="state", columns="region_cat", values="share").fillna(0)
    col_order = piv.sum().sort_values(ascending=False).index.tolist()
    piv = piv[col_order]
    # rows ranked by their share in the leading column; plotly draws the first
    # category at the bottom, so ascending here reads as descending on screen
    row_order = piv[col_order[0]].sort_values(ascending=True).index.tolist()
    piv = piv.loc[row_order]
    text = [[f"{v:.0%}" if v >= 0.05 else "" for v in row] for row in piv.values]
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=col_order, y=[_name(s) for s in row_order],
        colorscale=SEQ, zmin=0, zmax=max(0.5, float(piv.values.max())),
        text=text, texttemplate="%{text}", textfont=dict(size=12),
        xgap=2, ygap=2,
        colorbar=dict(title="Share of those who leave", tickformat=".0%", thickness=12, len=0.8),
        hovertemplate="%{y} → %{x}<br>%{z:.1%} of those who leave<extra></extra>",
    ))
    _base_layout(fig, 80 + 34 * len(row_order))
    fig.update_xaxes(showgrid=False, tickangle=-30, side="bottom")
    return fig


def chart_industries(d):
    # A dot plot, not bars: the values span 70-90%, and a bar axis that starts at
    # 60% would make a 20-point spread look like a 4x difference in length.
    fig = go.Figure(go.Scatter(
        y=d["industry"], x=d["tsi"], mode="markers",
        marker=dict(color=ACCENT, size=11, line=dict(color="white", width=2)),
        customdata=d["grads"],
        hovertemplate="%{y}<br>%{x:.1%} still in-state at year 1<br>%{customdata:,.0f} employed graduates<extra></extra>",
    ))
    # direct-label only the extremes
    n = len(d)
    for i, (_, r) in enumerate(d.iterrows()):
        if i < 3 or i >= n - 3:
            fig.add_annotation(x=r["tsi"], y=r["industry"], xanchor="left", xshift=6,
                               text=f"{r['tsi']:.0%}", showarrow=False,
                               font=dict(color=INK_MUTED, size=12))
    _base_layout(fig, 60 + 26 * n)
    fig.update_xaxes(tickformat=".0%", range=[0.65, 0.95],
                     title="Share still working in-state at year 1")
    fig.update_yaxes(showgrid=True, gridcolor=GRID)
    return fig


# ------------------------------------------------------------------
# Render
# ------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _aggregates(_tsi, _flows):
    """The four summaries behind the tab. The data never change within a
    deployment, so this runs once per server, not once per visitor per click.
    Leading underscores tell Streamlit not to hash the frames on every call."""
    return (state_horizons(_tsi), flagship_gap(_tsi),
            leaver_destinations(_flows), industry_tsi(_tsi))


def render(tsi, flows):
    st.info(
        "These figures cover all ten states and every school on the dashboard. "
        "The filters at left do not apply here.",
        icon="ℹ️",
    )
    st.caption(
        "Each figure is a ratio of sums: graduates employed in-state divided by "
        "graduates employed anywhere."
    )

    hz, fg, dest, ind = _aggregates(tsi, flows)

    # --- KPI row ---
    n_under = int((fg["gap"] < 0).sum())
    top10 = hz.sort_values("Y10", ascending=False).iloc[0]
    top_dest = dest.sort_values("share", ascending=False).iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Flagships that keep fewer graduates", f"{n_under} of {len(fg)}")
    c1.caption("than their state's other public universities, one year out")
    c2.metric("Still in-state ten years out", f"{top10['Y10']:.0%}")
    c2.caption(f"{_name(top10['state'])}, the highest of the {len(hz)} states")
    c3.metric("Biggest destination for graduates who leave", f"{top_dest['share']:.0%}")
    c3.caption(f"of {_name(top_dest['state'])}'s out-of-state graduates work in the "
               f"{top_dest['region_cat']} division")

    st.divider()

    # --- 1. Who keeps their graduates over time ---
    st.subheader("Who keeps their graduates over time")
    lo = hz.sort_values("loss_total").iloc[0]; hi = hz.sort_values("loss_total").iloc[-1]
    st.markdown(
        f"Every state loses graduates as the years pass, but not at the same rate. "
        f"**{_name(hi['state'])}** gives up {hi['loss_total']*100:.0f} points of retention "
        f"between year one and year ten; **{_name(lo['state'])}** gives up "
        f"{lo['loss_total']*100:.0f}. The lighter segment is the early loss, the darker "
        "the later one."
    )
    st.plotly_chart(chart_leak(hz), use_container_width=True, config=PLOTLY_CONFIG)
    with st.expander("Table"):
        t = hz.sort_values("loss_total", ascending=False).copy()
        t["State"] = t["state"].map(_name)
        t = t[["State", "Y1", "Y5", "Y10", "loss_1_5", "loss_5_10", "loss_total"]]
        t.columns = ["State", "Year 1", "Year 5", "Year 10", "Lost Y1→Y5", "Lost Y5→Y10", "Lost total"]
        st.dataframe(t.style.format({c: "{:.1%}" for c in t.columns[1:]}),
                     hide_index=True, use_container_width=True)

    st.divider()

    # --- 2. Where graduates go when they leave ---
    st.subheader("Where graduates go when they leave")
    st.markdown(
        "Of the graduates who work outside their degree state a year after "
        "graduation, where are they? Each row sums to 100% across Census divisions. "
        "A graduate working in a neighbouring state counts as having left even when "
        "both states share a division."
    )
    st.plotly_chart(chart_destinations(dest), use_container_width=True, config=PLOTLY_CONFIG)
    with st.expander("Table"):
        piv = dest.pivot(index="state", columns="region_cat", values="share").fillna(0)
        piv.index = [_name(s) for s in piv.index]
        st.dataframe(piv.style.format("{:.1%}"), use_container_width=True)

    st.divider()

    # --- 3. Which industries hold on ---
    st.subheader("Which industries hold on")
    top = ind.iloc[-1]; bot = ind.iloc[0]
    big = ind.sort_values("grads", ascending=False).iloc[0]
    st.markdown(
        f"Pooled across all eight states, **{top['industry']}** keeps "
        f"{top['tsi']:.0%} of its graduates in-state at year one and "
        f"**{bot['industry']}** keeps {bot['tsi']:.0%}. "
        f"**{big['industry']}**, the largest sector at {big['grads']:,.0f} employed "
        f"graduates, keeps {big['tsi']:.0%}. Sectors that hire locally hold on; "
        "the ones with national labour markets don't."
    )
    st.plotly_chart(chart_industries(ind), use_container_width=True, config=PLOTLY_CONFIG)
    with st.expander("Table"):
        t = ind.sort_values("tsi", ascending=False).copy()
        t.columns = ["Industry", "Year-1 TSI", "Employed graduates"]
        st.dataframe(t.style.format({"Year-1 TSI": "{:.1%}", "Employed graduates": "{:,.0f}"}),
                     hide_index=True, use_container_width=True)
