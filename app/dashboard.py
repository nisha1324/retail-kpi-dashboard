"""Retail KPI dashboard. Run: streamlit run app/dashboard.py"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.kpis import filter_period, kpi_summary, monthly_kpis, same_period_last_year, yoy_change  # noqa: E402

DATA = ROOT / "data" / "processed" / "transactions.parquet"
THIS_YEAR, LAST_YEAR = "#2a78d6", "#eb6834"

st.set_page_config(page_title="Retail KPI dashboard", layout="wide")


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_parquet(DATA)


if not DATA.exists():
    st.error("No data yet. Run `python scripts/download_data.py` then `python scripts/prepare_data.py`.")
    st.stop()

df = load()
st.title("Retail KPI dashboard")
st.caption("UK online gift wholesaler, Dec 2009 – Dec 2011 (UCI Online Retail II). "
           "Revenue in GBP; returns netted off.")

# Filters in one row above the charts
c1, c2 = st.columns([2, 3])
min_d, max_d = df["InvoiceDate"].min().date(), df["InvoiceDate"].max().date()
start, end = c1.date_input("Period", value=(pd.Timestamp("2011-01-01").date(), pd.Timestamp("2011-11-30").date()),
                           min_value=min_d, max_value=max_d)
countries = ["All"] + sorted(df["Country"].unique())
country = c2.selectbox("Country", countries)
if country != "All":
    df = df[df["Country"] == country]

cur = filter_period(df, start, end)
ly_start, ly_end = same_period_last_year(start, end)
prev = filter_period(df, ly_start, ly_end)
k, kp = kpi_summary(cur), kpi_summary(prev)
has_ly = ly_start.date() >= min_d and len(prev) > 0
ch = yoy_change(k, kp) if has_ly else {key: None for key in k}


def delta(key: str):
    if ch[key] is None:
        return None
    return f"{ch[key]:+.1%} vs LY"


tiles = st.columns(5)
tiles[0].metric("Net revenue", f"£{k['net_revenue']:,.0f}", delta("net_revenue"))
tiles[1].metric("Orders", f"{k['orders']:,}", delta("orders"))
tiles[2].metric("Avg order value", f"£{k['aov']:,.0f}", delta("aov"))
tiles[3].metric("Active customers", f"{k['active_customers']:,}", delta("active_customers"))
tiles[4].metric("Return rate", f"{k['return_rate']:.1%}", delta("return_rate"), delta_color="inverse")
if not has_ly:
    st.caption("No full same-period-last-year data for this range, so YoY deltas are hidden.")

# Monthly net revenue: selected period vs same months last year
m_cur = monthly_kpis(cur).assign(series="Selected period")
m_prev = monthly_kpis(prev).assign(series="Same period last year")
if len(m_prev):
    m_prev["month"] = m_prev["month"] + pd.DateOffset(years=1)
monthly = pd.concat([m_cur, m_prev], ignore_index=True)

st.subheader("Monthly net revenue vs last year")
line = alt.Chart(monthly).mark_line(point=alt.OverlayMarkDef(size=60), strokeWidth=2).encode(
    x=alt.X("yearmonth(month):T", title=None),
    y=alt.Y("net_revenue:Q", title="Net revenue (£)", axis=alt.Axis(format="~s")),
    color=alt.Color("series:N", title=None,
                    scale=alt.Scale(domain=["Selected period", "Same period last year"],
                                    range=[THIS_YEAR, LAST_YEAR]),
                    legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("yearmonth(month):T", title="Month"), "series:N",
             alt.Tooltip("net_revenue:Q", title="Net revenue £", format=",.0f"),
             alt.Tooltip("orders:Q", title="Orders", format=",")],
)
st.altair_chart(line, width="stretch")

with st.expander("Monthly KPI table"):
    show = m_cur[["month", "net_revenue", "orders", "aov", "active_customers", "return_rate"]].copy()
    show["month"] = show["month"].dt.strftime("%Y-%m")
    st.dataframe(show.style.format({"net_revenue": "£{:,.0f}", "aov": "£{:,.0f}",
                                    "return_rate": "{:.1%}"}), hide_index=True)
