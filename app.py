import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from ingestion import ingest_reports
from analytics import (
    add_quarter_column,
    county_kpis,
    billing_summary,
    collection_efficiency,
    subcounty_performance,
    ward_performance,
    ward_compliance,
    monthly_target_pace,
    historical_comparison,
    current_reporting_period,
    quarter_comparison,
    quarter_target,
    subcounty_quarter_comparison,
    ward_quarter_comparison,
    revenue_leakage,
    leakage_by_subcounty,
    revenue_by_activity,
    sector_concentration,
    unpaid_bills_register,
    aging_analysis,
    voided_cancelled_analysis,
    partpayment_tracking,
    get_financial_years,
    filter_by_fy,
)
from config import SUBCOUNTY_TARGETS, REPORTS_FOLDER
from ai_analyst import configure_gemini, build_data_context, chat_with_analyst, generate_executive_brief


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="County Revenue Intelligence",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Automatically reload the page every 30 seconds so new reports are ingested.
st.markdown(
    """
    <script>
    setTimeout(() => {
        window.location.reload();
    }, 30000);
    </script>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# CHART THEME
# --------------------------------------------------

COLORS = {
    "primary": "#018e11",
    "primary_dark": "#0c8c01",
    "secondary": "#f7bd00",
    "accent": "#FFB236",
    "success": "#0aad01",
    "danger": "#E63946",
    "warning": "#F4A261",
    "muted": "#6C757D",
    "light": "#F8F9FA",
    "white": "#FFFFFF",
    "navy": "#020381",
    "chart": ["#018e11", "#f7bd00", "#0aad01", "#FFB236", "#020381", "#E63946"],
}

PLOTLY_LAYOUT = dict(
    font=dict(family="Source Sans Pro, sans-serif", color="#1a1a1a"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(bgcolor=COLORS["primary_dark"], font_color="white"),
)


# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap');

    /* Global */
    .stApp {
        font-family: 'Source Sans Pro', sans-serif;
    }

    /* Hide default streamlit header/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c8c01 0%, #065a01 100%);
        color: white;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: white !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.15);
    }

    /* Hide sidebar collapse toggle so sidebar stays permanently visible */
    [data-testid="collapsedControl"],
    button[title="Toggle sidebar"],
    button[aria-label="Toggle sidebar"] {
        display: none !important;
    }

    /* Header banner */
    .header-banner {
        background: linear-gradient(135deg, #018e11 0%, #0c8c01 60%, #f7bd00 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-banner h1 {
        color: white;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-banner .subtitle {
        color: rgba(255,255,255,0.75);
        font-size: 0.9rem;
        margin-top: 4px;
    }
    .header-badge {
        background: rgba(255,255,255,0.15);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        backdrop-filter: blur(10px);
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        border-left: 4px solid #018e11;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .kpi-card.success { border-left-color: #0aad01; }
    .kpi-card.danger { border-left-color: #E63946; }
    .kpi-card.warning { border-left-color: #F4A261; }
    .kpi-card.accent { border-left-color: #f7bd00; }
    .kpi-card.primary { border-left-color: #020381; }

    .kpi-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #6C757D;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a1a;
        line-height: 1.2;
    }
    .kpi-delta {
        font-size: 0.8rem;
        margin-top: 4px;
        font-weight: 600;
    }
    .kpi-delta.positive { color: #0aad01; }
    .kpi-delta.negative { color: #E63946; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0c8c01;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #f7bd00;
        display: inline-block;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: #F8F9FA;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        padding: 10px 20px;
        font-weight: 600;
        color: #6C757D;
    }
    .stTabs [aria-selected="true"] {
        background: white;
        color: #018e11;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* Data tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Metric overrides */
    [data-testid="stMetric"] {
        background: white;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    /* Chart containers */
    .chart-container {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }

    /* Status indicators */
    .status-on-track { color: #0aad01; font-weight: 700; }
    .status-at-risk { color: #F4A261; font-weight: 700; }
    .status-behind { color: #E63946; font-weight: 700; }

    /* Dividers */
    .clean-divider {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #dee2e6, transparent);
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HELPER: KPI card
# --------------------------------------------------

def kpi_card(label, value, style="", delta=None, delta_direction=None):
    delta_html = ""
    if delta is not None:
        cls = "positive" if delta_direction == "up" else "negative"
        arrow = "&#9650;" if delta_direction == "up" else "&#9660;"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {delta}</div>'

    st.markdown(f"""
        <div class="kpi-card {style}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


def section_header(text):
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def format_kes(amount):
    return f"KES {amount:,.0f}"


def get_reports_cache_key(folder=REPORTS_FOLDER):
    """Build a simple key based on report filenames and modification times."""
    file_metadata = []
    for filename in sorted(os.listdir(folder)):
        filepath = os.path.join(folder, filename)
        if not os.path.isfile(filepath) or filename.startswith(".") or filename.startswith("~"):
            continue
        stat = os.stat(filepath)
        file_metadata.append((filename, stat.st_mtime, stat.st_size))
    return repr(file_metadata)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

@st.cache_data(ttl=300, show_spinner="Loading revenue data...")
def load_data(report_key):
    try:
        return ingest_reports()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()


df_all = load_data(get_reports_cache_key())

if df_all.empty:
    st.warning("No revenue reports detected. Place report files in data/reports/")
    st.stop()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding: 1rem 0 0.5rem 0;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; color: #f7bd00; margin-bottom: 4px;">
                County Government of
            </div>
            <div style="font-size: 1.5rem; font-weight: 700; color: white; letter-spacing: -0.5px;">
                Uasin Gishu
            </div>
            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.6); margin-top: 4px;">
                Revenue Intelligence Command Center
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    financial_years = get_financial_years(df_all)
    selected_fy = st.selectbox("Financial Year", financial_years, index=0)

    df_fy = filter_by_fy(df_all, selected_fy)

    quarters = ["All Quarters", "Q1 (Jul-Sep)", "Q2 (Oct-Dec)", "Q3 (Jan-Mar)", "Q4 (Apr-Jun)"]
    selected_quarter = st.selectbox("Quarter", quarters, index=0)

    if selected_quarter != "All Quarters":
        q_key = selected_quarter.split(" ")[0]
        df_fy = add_quarter_column(df_fy)
        df_fy = df_fy[df_fy["Quarter"] == q_key]

    subcounties = ["All Subcounties"] + sorted(df_fy["Subcounty"].unique().tolist())
    selected_subcounty = st.selectbox("Subcounty", subcounties, index=0)

    if selected_subcounty != "All Subcounties":
        df_filtered = df_fy[df_fy["Subcounty"] == selected_subcounty]
    else:
        df_filtered = df_fy

    st.divider()

    total_records = len(df_filtered)
    date_range_start = df_filtered["Bill Date"].min()
    date_range_end = df_filtered["Bill Date"].max()

    st.markdown(f"""
        <div style="font-size: 0.75rem; color: rgba(255,255,255,0.5);">
            <div style="margin-bottom: 6px;"><strong style="color: rgba(255,255,255,0.7);">Records:</strong> {total_records:,}</div>
            <div style="margin-bottom: 6px;"><strong style="color: rgba(255,255,255,0.7);">From:</strong> {date_range_start.strftime('%d %b %Y') if pd.notna(date_range_start) else 'N/A'}</div>
            <div><strong style="color: rgba(255,255,255,0.7);">To:</strong> {date_range_end.strftime('%d %b %Y') if pd.notna(date_range_end) else 'N/A'}</div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Refresh data", key="refresh_data"):
        st.cache_data.clear()
        st.experimental_rerun()

    st.divider()

    st.markdown("""
        <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #f7bd00; margin-bottom: 8px;">
            Data Management
        </div>
    """, unsafe_allow_html=True)

    admin_pass = st.text_input("Admin Password", type="password", key="admin_pw", placeholder="Enter password to upload")

    if admin_pass == st.secrets.get("ADMIN_PASSWORD", "ugsangrevenue2026"):
        uploaded_files = st.file_uploader(
            "Upload New Reports",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
            help="Drag and drop CSV or Excel report files here",
        )

        if uploaded_files:
            saved = []
            errors = []
            for f in uploaded_files:
                dest = os.path.join(REPORTS_FOLDER, f.name)
                if os.path.exists(dest):
                    errors.append(f"{f.name} already exists")
                    continue
                try:
                    with open(dest, "wb") as out:
                        out.write(f.getbuffer())
                    saved.append(f.name)
                except Exception as e:
                    errors.append(f"{f.name}: {e}")
            if saved:
                st.success(f"Saved {len(saved)} new file(s): {', '.join(saved)}")
            if errors:
                for err in errors:
                    st.warning(err)
            if saved:
                st.cache_data.clear()
                st.rerun()
    elif admin_pass:
        st.error("Incorrect password")

st.markdown("""
    <div style="position: fixed; bottom: 12px; left: 18px; font-size: 0.6rem; color: rgba(255,255,255,0.18); letter-spacing: 0.5px;" title="Crafted by Ian Sang">
        crafted by Ian Sang
    </div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HEADER BANNER (with persistent Show Sidebar control)
# --------------------------------------------------

period = current_reporting_period(df_all)

hdr_left, hdr_right = st.columns([9,1])
with hdr_left:
    st.markdown(f"""
        <div class="header-banner">
            <div>
                <h1>Uasin Gishu County Revenue Intelligence</h1>
                <div class="subtitle">Single Business Permit Revenue Tracking & Analytics</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
with hdr_right:
    st.markdown(f"<div class=\"header-badge\" style=\"margin-top:8px; text-align:center;\">{period}</div>", unsafe_allow_html=True)


# --------------------------------------------------
# CALCULATIONS
# --------------------------------------------------

kpis = county_kpis(df_filtered)
billing = billing_summary(df_filtered)
efficiency = collection_efficiency(df_filtered)
historical = historical_comparison(df_all)

permit_count = len(df_filtered)
avg_fee = billing["paid"] / permit_count if permit_count > 0 else 0


# --------------------------------------------------
# TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Executive Dashboard",
    "Subcounty Operations",
    "Revenue Intelligence",
    "Collections & Compliance",
    "AI Analyst",
])


# ==================================================
# TAB 1: EXECUTIVE DASHBOARD
# ==================================================

with tab1:

    # -- Row 1: KPIs --
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        progress_status = "success" if kpis["progress_percent"] >= 70 else ("warning" if kpis["progress_percent"] >= 40 else "danger")
        kpi_card("Total Collected", format_kes(kpis["total_collected"]), style=progress_status,
                 delta=f"{kpis['progress_percent']:.0f}% of target",
                 delta_direction="up" if kpis["progress_percent"] >= 50 else "down")

    with c2:
        kpi_card("Remaining Target", format_kes(kpis["remaining_revenue"]), style="primary")

    with c3:
        kpi_card("Collection Efficiency", f"{efficiency:.0f}%", style="success" if efficiency >= 60 else "warning")

    with c4:
        kpi_card("Permits Issued", f"{permit_count:,}", style="accent")

    with c5:
        growth_dir = "up" if historical["growth"] >= 0 else "down"
        kpi_card("YoY Growth", f"{historical['growth']:.0f}%",
                 style="success" if historical["growth"] >= 0 else "danger",
                 delta=f"vs previous FY", delta_direction=growth_dir)

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Row 2: Billing breakdown cards --
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        kpi_card("Paid Revenue", format_kes(billing["paid"]), style="success")
    with b2:
        kpi_card("Unpaid Revenue", format_kes(billing["unpaid"]), style="danger")
    with b3:
        kpi_card("Part-Payments", format_kes(billing["partpaid"]), style="warning")
    with b4:
        kpi_card("Voided / Cancelled", format_kes(billing["voided"] + billing["cancelled"]), style="")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Row 3: Charts --
    col_left, col_right = st.columns(2)

    with col_left:
        section_header("Revenue vs Target Pace")

        pace_df = monthly_target_pace(df_all)
        fig_pace = go.Figure()
        fig_pace.add_trace(go.Bar(
            x=pace_df["Month"], y=pace_df["AmountPaid"],
            name="Monthly Revenue", marker_color=COLORS["secondary"],
            hovertemplate="Revenue: KES %{y:,.0f}<extra></extra>",
        ))
        fig_pace.add_trace(go.Scatter(
            x=pace_df["Month"], y=pace_df["cumulative"],
            name="Cumulative", line=dict(color=COLORS["primary"], width=2.5),
            hovertemplate="Cumulative: KES %{y:,.0f}<extra></extra>",
        ))
        fig_pace.add_trace(go.Scatter(
            x=pace_df["Month"], y=pace_df["target_pace"],
            name="Target Pace", line=dict(color=COLORS["danger"], width=2, dash="dash"),
            hovertemplate="Target: KES %{y:,.0f}<extra></extra>",
        ))
        fig_pace.update_layout(
            **PLOTLY_LAYOUT,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
            xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            height=380,
        )
        st.plotly_chart(fig_pace, key="pace_chart", width="stretch")

    with col_right:
        section_header("Quarter Benchmark")

        comparison_df = quarter_comparison(df_all)
        q_target = quarter_target()

        fig_compare = go.Figure()
        fig_compare.add_trace(go.Bar(
            x=comparison_df["FinancialYear"], y=comparison_df["AmountPaid"],
            text=[f"KES {v:,.0f}" for v in comparison_df["AmountPaid"]],
            textposition="outside", marker_color=COLORS["secondary"],
            hovertemplate="FY %{x}: KES %{y:,.0f}<extra></extra>",
        ))
        fig_compare.add_hline(
            y=q_target, line_dash="dash", line_color=COLORS["danger"],
            annotation_text=f"Target: KES {q_target:,.0f}",
            annotation_font_color=COLORS["danger"],
        )
        fig_compare.update_layout(
            **PLOTLY_LAYOUT,
            yaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
            height=380,
        )
        st.plotly_chart(fig_compare, key="compare_chart", width="stretch")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Row 4: Subcounty performance --
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        section_header("Subcounty Performance vs Target")

        perf_df = subcounty_performance(df_filtered)
        fig_perf = go.Figure()
        fig_perf.add_trace(go.Bar(
            y=perf_df["Subcounty"], x=perf_df["AmountPaid"],
            name="Collected", orientation="h", marker_color=COLORS["secondary"],
            hovertemplate="%{y}: KES %{x:,.0f}<extra></extra>",
        ))
        fig_perf.add_trace(go.Bar(
            y=perf_df["Subcounty"], x=perf_df["RevenueGap"],
            name="Gap to Target", orientation="h", marker_color=COLORS["danger"],
            opacity=0.3,
            hovertemplate="%{y}: KES %{x:,.0f} gap<extra></extra>",
        ))
        fig_perf.update_layout(
            **PLOTLY_LAYOUT,
            barmode="stack",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
            height=350,
        )
        st.plotly_chart(fig_perf, key="perf_chart", width="stretch")

    with col_right2:
        section_header("Subcounty Growth (Quarter-over-Quarter)")

        subcounty_cmp = subcounty_quarter_comparison(df_all)
        numeric_cols = subcounty_cmp.select_dtypes("number").columns

        def color_growth(val):
            if val > 0:
                return "color: #0aad01; font-weight: 600"
            elif val < 0:
                return "color: #E63946; font-weight: 600"
            return ""

        styled_subcounty = (
            subcounty_cmp.style
            .format({col: "{:,.0f}" for col in numeric_cols if col != "Growth%"})
            .format({"Growth%": "{:.0f}%"})
            .map(color_growth, subset=["Growth%"])
        )
        st.dataframe(styled_subcounty, width="stretch", hide_index=True, height=350)


# ==================================================
# TAB 2: SUBCOUNTY OPERATIONS
# ==================================================

with tab2:

    ops_subcounty = st.selectbox(
        "Select Subcounty",
        sorted(df_all["Subcounty"].unique()),
        key="ops_subcounty",
    )

    subcounty_data = df_fy[df_fy["Subcounty"] == ops_subcounty]

    # -- KPIs for selected subcounty --
    sc_target = SUBCOUNTY_TARGETS.get(ops_subcounty, 0)
    sc_collected = subcounty_data["AmountPaid"].sum()
    sc_progress = (sc_collected / sc_target * 100) if sc_target else 0
    sc_efficiency = collection_efficiency(subcounty_data)
    sc_permits = len(subcounty_data)

    s1, s2, s3, s4 = st.columns(4)
    with s1:
        kpi_card("Collected", format_kes(sc_collected),
                 style="success" if sc_progress >= 70 else ("warning" if sc_progress >= 40 else "danger"),
                 delta=f"{sc_progress:.0f}% of KES {sc_target:,.0f} target",
                 delta_direction="up" if sc_progress >= 50 else "down")
    with s2:
        kpi_card("Gap to Target", format_kes(max(sc_target - sc_collected, 0)), style="primary")
    with s3:
        kpi_card("Collection Efficiency", f"{sc_efficiency:.0f}%",
                 style="success" if sc_efficiency >= 60 else "warning")
    with s4:
        kpi_card("Permits", f"{sc_permits:,}", style="accent")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    col_left3, col_right3 = st.columns(2)

    with col_left3:
        section_header("Ward Quarter Comparison")

        ward_cmp = ward_quarter_comparison(subcounty_data)
        num_cols = ward_cmp.select_dtypes("number").columns

        styled_ward = (
            ward_cmp.style
            .format({col: "{:,.0f}" for col in num_cols if col != "Growth%"})
            .format({"Growth%": "{:.0f}%"})
            .map(color_growth, subset=["Growth%"])
        )
        st.dataframe(styled_ward, width="stretch", hide_index=True)

    with col_right3:
        section_header("Ward Revenue Ranking")

        ward_perf = ward_performance(subcounty_data)
        fig_ward = go.Figure()
        fig_ward.add_trace(go.Bar(
            y=ward_perf["Ward"], x=ward_perf["AmountPaid"],
            orientation="h", marker_color=COLORS["secondary"],
            text=[f"KES {v:,.0f}" for v in ward_perf["AmountPaid"]],
            textposition="outside",
            hovertemplate="%{y}: KES %{x:,.0f}<extra></extra>",
        ))
        fig_ward.update_layout(
            **PLOTLY_LAYOUT,
            xaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
            height=max(300, len(ward_perf) * 35 + 60),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_ward, key="ward_chart", width="stretch")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    section_header("Ward Compliance & Collection Rates")

    wc = ward_compliance(subcounty_data)

    fig_compliance = go.Figure()
    fig_compliance.add_trace(go.Bar(
        x=wc["Ward"], y=wc["compliance_rate"],
        name="Compliance Rate %", marker_color=COLORS["success"],
    ))
    fig_compliance.add_trace(go.Bar(
        x=wc["Ward"], y=wc["collection_rate"],
        name="Collection Rate %", marker_color=COLORS["secondary"],
    ))
    fig_compliance.update_layout(
        **PLOTLY_LAYOUT,
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Percentage (%)", tickformat=",.0f", gridcolor="rgba(0,0,0,0.05)"),
        height=400,
    )
    st.plotly_chart(fig_compliance, key="compliance_chart", width="stretch")


# ==================================================
# TAB 3: REVENUE INTELLIGENCE
# ==================================================

with tab3:

    intel_col1, intel_col2 = st.columns(2)

    # -- Revenue Leakage --
    with intel_col1:
        section_header("Revenue Leakage Detection")

        leakage_data = revenue_leakage(df_all)

        if leakage_data:
            leakage_df, leakage_total = leakage_data

            l1, l2 = st.columns(2)
            with l1:
                kpi_card("Potential Leakage", format_kes(leakage_total), style="danger")
            with l2:
                kpi_card("Businesses Lost", f"{len(leakage_df):,}", style="warning")

            st.markdown("", unsafe_allow_html=True)

            leakage_sub = leakage_by_subcounty(df_all)
            fig_leak = go.Figure()
            fig_leak.add_trace(go.Bar(
                x=leakage_sub["Subcounty"], y=leakage_sub["revenue_lost"],
                text=[f"{c}" for c in leakage_sub["businesses_lost"]],
                textposition="outside",
                marker_color=COLORS["danger"],
                hovertemplate="%{x}: KES %{y:,.0f} lost (%{text} businesses)<extra></extra>",
            ))
            fig_leak.update_layout(
                **PLOTLY_LAYOUT,
                yaxis=dict(tickformat=",", title="Revenue Lost", gridcolor="rgba(0,0,0,0.05)"),
                height=350,
            )
            st.plotly_chart(fig_leak, key="leakage_chart", width="stretch")

            with st.expander("View Leaked Businesses Detail"):
                display_cols = ["Business Name", "Subcounty", "Ward", "PreviousRevenue", "LastActiveFY"]
                if "Owner" in leakage_df.columns:
                    display_cols.append("Owner")
                if "Phone Number" in leakage_df.columns:
                    display_cols.append("Phone Number")
                available = [c for c in display_cols if c in leakage_df.columns]
                st.dataframe(
                    leakage_df[available].head(50).style.format({"PreviousRevenue": "KES {:,.0f}"}),
                    width="stretch", hide_index=True,
                )
        else:
            st.info("Not enough data for leakage analysis (requires 2+ financial years).")

    # -- Sector Analysis --
    with intel_col2:
        section_header("Business Sector Analysis")

        sector_df = sector_concentration(df_filtered, top_n=10)

        if not sector_df.empty:
            fig_sector = go.Figure()
            fig_sector.add_trace(go.Pie(
                labels=sector_df["Sector"],
                values=sector_df["Revenue"],
                hole=0.45,
                marker=dict(colors=COLORS["chart"] * 3),
                textinfo="label+percent",
                textposition="outside",
                hovertemplate="%{label}: KES %{value:,.0f} (%{percent})<extra></extra>",
            ))
            fig_sector.update_layout(
                **PLOTLY_LAYOUT,
                showlegend=False,
                height=400,
            )
            st.plotly_chart(fig_sector, key="sector_chart", width="stretch")

        section_header("Top Revenue Activities")

        activity_df = revenue_by_activity(df_filtered, top_n=10)
        if not activity_df.empty:
            styled_activity = (
                activity_df.rename(columns={
                    "activity_description": "Activity",
                    "total_revenue": "Revenue",
                    "business_count": "Businesses",
                    "avg_revenue": "Avg Revenue",
                })
                [["Activity", "Revenue", "Businesses", "Avg Revenue"]]
                .style
                .format({"Revenue": "KES {:,.0f}", "Businesses": "{:,.0f}", "Avg Revenue": "KES {:,.0f}"})
            )
            st.dataframe(styled_activity, width="stretch", hide_index=True)

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Voided / Cancelled Analysis --
    section_header("Voided & Cancelled Bills Analysis")

    vc_status, vc_subcounty = voided_cancelled_analysis(df_filtered)

    vc1, vc2 = st.columns(2)

    with vc1:
        if not vc_status.empty:
            fig_vc = go.Figure()
            fig_vc.add_trace(go.Bar(
                x=vc_status["BillStatus"].str.title(),
                y=vc_status["total_amount"],
                text=[f"{c:,} bills" for c in vc_status["count"]],
                textposition="outside",
                marker_color=[COLORS["warning"], COLORS["danger"]],
                hovertemplate="%{x}: KES %{y:,.0f}<extra></extra>",
            ))
            fig_vc.update_layout(
                **PLOTLY_LAYOUT,
                yaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
                height=300,
            )
            st.plotly_chart(fig_vc, key="vc_chart", width="stretch")
        else:
            st.info("No voided or cancelled bills in this period.")

    with vc2:
        if not vc_subcounty.empty:
            fig_vc_sub = go.Figure()
            for status in vc_subcounty["BillStatus"].unique():
                data = vc_subcounty[vc_subcounty["BillStatus"] == status]
                fig_vc_sub.add_trace(go.Bar(
                    x=data["Subcounty"], y=data["total_amount"],
                    name=status.title(),
                    hovertemplate="%{x}: KES %{y:,.0f}<extra></extra>",
                ))
            fig_vc_sub.update_layout(
                **PLOTLY_LAYOUT,
                barmode="group",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(tickformat=",", gridcolor="rgba(0,0,0,0.05)"),
                height=300,
            )
            st.plotly_chart(fig_vc_sub, key="vc_sub_chart", width="stretch")


# ==================================================
# TAB 4: COLLECTIONS & COMPLIANCE
# ==================================================

with tab4:

    # -- Aging Analysis --
    section_header("Outstanding Bills Aging")

    aging_df = aging_analysis(df_filtered)

    a1, a2 = st.columns([1, 2])

    with a1:
        if not aging_df.empty:
            total_outstanding = aging_df["total_outstanding"].sum()
            total_count = aging_df["count"].sum()

            kpi_card("Total Outstanding", format_kes(total_outstanding), style="danger")
            st.markdown("<br>", unsafe_allow_html=True)
            kpi_card("Unpaid Bills", f"{total_count:,}", style="warning")

    with a2:
        if not aging_df.empty:
            bucket_colors = [COLORS["success"], COLORS["secondary"], COLORS["warning"], COLORS["accent"], COLORS["danger"]]
            fig_aging = go.Figure()
            fig_aging.add_trace(go.Bar(
                x=aging_df["aging_bucket"], y=aging_df["total_outstanding"],
                text=[f"{c:,} bills" for c in aging_df["count"]],
                textposition="outside",
                marker_color=bucket_colors[:len(aging_df)],
                hovertemplate="%{x}: KES %{y:,.0f} (%{text})<extra></extra>",
            ))
            fig_aging.update_layout(
                **PLOTLY_LAYOUT,
                yaxis=dict(tickformat=",", title="Outstanding Amount", gridcolor="rgba(0,0,0,0.05)"),
                height=350,
            )
            st.plotly_chart(fig_aging, key="aging_chart", width="stretch")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Part-payments --
    section_header("Part-Payment Tracking")

    pp_df = partpayment_tracking(df_filtered)

    if not pp_df.empty:
        pp_total_outstanding = pp_df["outstanding"].sum()
        pp_total_paid = pp_df["AmountPaid"].sum()

        pp1, pp2, pp3 = st.columns(3)
        with pp1:
            kpi_card("Part-Payment Cases", f"{len(pp_df):,}", style="warning")
        with pp2:
            kpi_card("Amount Collected", format_kes(pp_total_paid), style="success")
        with pp3:
            kpi_card("Still Outstanding", format_kes(pp_total_outstanding), style="danger")

        st.markdown("<br>", unsafe_allow_html=True)

        display_pp = pp_df.rename(columns={
            "outstanding": "Outstanding",
            "payment_percent": "Paid %",
        })
        st.dataframe(
            display_pp.head(100).style.format({
                "Amount to Pay": "KES {:,.0f}",
                "AmountPaid": "KES {:,.0f}",
                "Outstanding": "KES {:,.0f}",
                "Paid %": "{:.0f}%",
            }),
            width="stretch", hide_index=True, height=400,
        )
    else:
        st.info("No part-payment records found for this period.")

    st.markdown('<hr class="clean-divider">', unsafe_allow_html=True)

    # -- Unpaid Bills Register --
    section_header("Unpaid Bills Register")

    reg_col1, reg_col2 = st.columns([1, 1])
    with reg_col1:
        reg_subcounty = st.selectbox("Filter by Subcounty", ["All"] + sorted(df_filtered["Subcounty"].unique().tolist()), key="reg_sc")
    with reg_col2:
        if reg_subcounty != "All":
            wards_available = sorted(df_filtered[df_filtered["Subcounty"] == reg_subcounty]["Ward"].unique().tolist())
            reg_ward = st.selectbox("Filter by Ward", ["All"] + wards_available, key="reg_ward")
        else:
            reg_ward = "All"

    unpaid_df = unpaid_bills_register(
        df_filtered,
        subcounty=reg_subcounty if reg_subcounty != "All" else None,
        ward=reg_ward if reg_ward != "All" else None,
    )

    if not unpaid_df.empty:
        up1, up2 = st.columns(2)
        with up1:
            kpi_card("Unpaid Records", f"{len(unpaid_df):,}", style="danger")
        with up2:
            kpi_card("Total Outstanding", format_kes(unpaid_df["Outstanding"].sum()), style="danger")

        st.markdown("<br>", unsafe_allow_html=True)

        st.dataframe(
            unpaid_df.head(200).style.format({
                "Amount to Pay": "KES {:,.0f}",
                "AmountPaid": "KES {:,.0f}",
                "Outstanding": "KES {:,.0f}",
            }),
            width="stretch", hide_index=True, height=500,
        )
    else:
        st.info("No unpaid bills found for the selected filters.")


# ==================================================
# TAB 5: AI ANALYST
# ==================================================

with tab5:

    gemini_key = st.secrets.get("GEMINI_API_KEY", "")

    if not gemini_key:
        st.warning("Gemini API key not configured. Add GEMINI_API_KEY to .streamlit/secrets.toml")
        st.markdown("""
            **How to get a free API key:**
            1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
            2. Click "Create API Key"
            3. Add it to your `.streamlit/secrets.toml` file as: `GEMINI_API_KEY = "your-key-here"`
        """)
        st.stop()

    configure_gemini(gemini_key)

    data_context = build_data_context(df_filtered, billing, kpis, efficiency, historical)

    ai_col1, ai_col2 = st.columns([3, 2])

    # -- Chat Analyst --
    with ai_col1:
        section_header("Revenue Analyst Chat")

        st.markdown("""
            <div style="font-size: 0.85rem; color: #6C757D; margin-bottom: 1rem;">
                Ask questions about revenue performance, subcounty comparisons, collection trends, or any data insight.
            </div>
        """, unsafe_allow_html=True)

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_input := st.chat_input("Ask about revenue data...", key="ai_chat"):
            st.session_state.chat_messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    try:
                        history = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.chat_messages[:-1]
                        ]
                        response = chat_with_analyst(data_context, user_input, history if history else None)
                        st.markdown(response)
                        st.session_state.chat_messages.append({"role": "model", "content": response})
                    except Exception as e:
                        st.error(f"AI Error: {e}")

        if st.session_state.chat_messages:
            if st.button("Clear Chat", key="clear_chat"):
                st.session_state.chat_messages = []
                st.rerun()

    # -- Executive Brief --
    with ai_col2:
        section_header("Executive Brief Generator")

        st.markdown("""
            <div style="font-size: 0.85rem; color: #6C757D; margin-bottom: 1rem;">
                Generate a professional executive summary of the current revenue position for county leadership.
            </div>
        """, unsafe_allow_html=True)

        if st.button("Generate Executive Brief", key="gen_brief", type="primary"):
            with st.spinner("Generating executive brief..."):
                try:
                    brief = generate_executive_brief(data_context)
                    st.session_state.executive_brief = brief
                except Exception as e:
                    st.error(f"AI Error: {e}")

        if "executive_brief" in st.session_state:
            st.markdown(st.session_state.executive_brief)

            st.download_button(
                label="Download Brief",
                data=st.session_state.executive_brief,
                file_name="executive_revenue_brief.md",
                mime="text/markdown",
                key="download_brief",
            )

        section_header("Quick Insights")

        quick_questions = [
            "Which subcounty needs the most attention?",
            "What are the top revenue risks?",
            "Summarize collection efficiency by subcounty",
            "What actions would improve revenue collection?",
        ]

        for q in quick_questions:
            if st.button(q, key=f"quick_{q[:20]}", use_container_width=True):
                with st.spinner("Analyzing..."):
                    try:
                        response = chat_with_analyst(data_context, q)
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
