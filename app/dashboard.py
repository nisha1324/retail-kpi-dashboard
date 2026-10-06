"""Retail KPI dashboard. Run: streamlit run app/dashboard.py"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.kpis import (aov_bridge, cancelled_bulk_lines, customer_mix, driver_table, filter_period,  # noqa: E402
                      kpi_summary, monthly_kpis, retention, revenue_bridge, same_period_last_year, yoy_change)

DATA = ROOT / "data" / "processed" / "transactions.parquet"
THIS_YEAR, LAST_YEAR = "#2a78d6", "#eb6834"

st.set_page_config(page_title="Retail KPI dashboard", layout="wide")


@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    # One readable name per stock code (descriptions vary slightly between invoices)
    names = df.groupby("StockCode")["Description"].agg(lambda s: s.mode().iat[0] if s.notna().any() else "")
    df["Product"] = df["StockCode"] + " " + df["StockCode"].map(names).fillna("").str.strip()
    return df


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
drop_bulk = st.checkbox("Exclude cancelled bulk orders (≥10,000 units, ordered and cancelled the same day)", value=True,
                        help="Two keying-error orders (Jan and Dec 2011) were cancelled within minutes. "
                             "They don't change net revenue but inflate AOV, gross sales and the return rate.")
if drop_bulk:
    df = df[~cancelled_bulk_lines(df)]
history = df  # all countries, so "new customer" means new to the business
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


overview, drivers, customers = st.tabs(["Overview", "Drivers: countries and products", "Customers"])

with overview:
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

with drivers:
    if not has_ly:
        st.info("Pick a period that has data for the same period last year to see what changed.")
    else:
        st.subheader("What moved order value?")
        st.caption("AOV = lines per order × revenue per line. More lines means wider baskets; "
                   "more revenue per line means bigger quantities or pricier items.")
        b = aov_bridge(cur, prev)
        a1, a2 = st.columns(2)
        a1.metric("Lines per order", f"{b['lines_per_order']:.1f}",
                  f"{b['lines_per_order'] / b['lines_per_order_ly'] - 1:+.1%} vs LY")
        a2.metric("Revenue per line", f"£{b['revenue_per_line']:.2f}",
                  f"{b['revenue_per_line'] / b['revenue_per_line_ly'] - 1:+.1%} vs LY")

        st.subheader("Where did net revenue change?")
        level = st.radio("Break down by", ["Country", "Product"], horizontal=True)
        t = driver_table(cur, prev, level)
        n = 8
        top = pd.concat([t.head(n), t.tail(n)]).drop_duplicates(level)
        top = top.assign(direction=["Gain" if c >= 0 else "Decline" for c in top["change"]])
        bars = alt.Chart(top).mark_bar().encode(
            x=alt.X("change:Q", title="Change in net revenue vs last year (£)", axis=alt.Axis(format="~s")),
            y=alt.Y(f"{level}:N", sort=alt.EncodingSortField("change", order="descending"), title=None),
            color=alt.Color("direction:N", title=None, legend=None,
                            scale=alt.Scale(domain=["Gain", "Decline"], range=[THIS_YEAR, LAST_YEAR])),
            tooltip=[f"{level}:N",
                     alt.Tooltip("net:Q", title="Net £ (period)", format=",.0f"),
                     alt.Tooltip("net_ly:Q", title="Net £ (last year)", format=",.0f"),
                     alt.Tooltip("change:Q", title="Change £", format="+,.0f")],
        )
        st.altair_chart(bars, width="stretch")
        st.caption(f"Top {n} gains and declines. Total change: £{t['change'].sum():+,.0f}.")

        with st.expander(f"Full table by {level.lower()}"):
            st.dataframe(t.style.format({"net": "£{:,.0f}", "net_ly": "£{:,.0f}", "change": "£{:+,.0f}",
                                         "share_of_change": "{:+.0%}", "returns": "£{:,.0f}",
                                         "returns_ly": "£{:,.0f}", "return_rate": "{:.1%}",
                                         "return_rate_ly": "{:.1%}"}, na_rep="–"), hide_index=True)

with customers:
    mix = customer_mix(history, cur, start)
    st.subheader("Who bought in this period?")
    st.caption("New = first purchase in the data falls inside the period. Data starts in Dec 2009, "
               "so for 2010 periods many existing accounts look new.")
    c = st.columns(4)
    c[0].metric("New customers", f"{mix['new_customers']:,}")
    c[1].metric("Returning customers", f"{mix['returning_customers']:,}")
    c[2].metric("Net revenue from new", f"£{mix['new_revenue']:,.0f}")
    c[3].metric("Net revenue from returning", f"£{mix['returning_revenue']:,.0f}")
    st.caption(f"£{mix['unidentified_revenue']:,.0f} of net revenue has no customer ID (guest checkouts).")

    if not has_ly:
        st.info("Pick a period that has data for the same period last year to see retention.")
    else:
        r, rt = retention(cur, prev)
        st.subheader("Did last year's customers come back?")
        c = st.columns(3)
        c[0].metric("Retention rate", f"{r['retention_rate']:.1%}",
                    help="Share of last year's buyers (same period) who bought again in this period.")
        c[1].metric("Last year's spend of lost customers", f"£{r['lost_revenue_ly']:,.0f}")
        c[2].metric("Spend change of retained customers", f"£{r['retained_change']:+,.0f}")

        b = revenue_bridge(cur, prev)
        labels = {"lost": "Lost customers", "retained": "Retained customers (spend change)",
                  "gained": "New or won-back customers", "unidentified": "No customer ID"}
        bridge = pd.DataFrame({"part": [labels[x] for x in b], "change": list(b.values())})
        bridge["direction"] = ["Gain" if v >= 0 else "Decline" for v in bridge["change"]]
        st.subheader("Change in net revenue by customer group")
        bars = alt.Chart(bridge).mark_bar().encode(
            x=alt.X("change:Q", title="Change in net revenue vs last year (£)", axis=alt.Axis(format="~s")),
            y=alt.Y("part:N", sort=list(labels.values()), title=None),
            color=alt.Color("direction:N", legend=None,
                            scale=alt.Scale(domain=["Gain", "Decline"], range=[THIS_YEAR, LAST_YEAR])),
            tooltip=["part:N", alt.Tooltip("change:Q", title="Change £", format="+,.0f")],
        )
        st.altair_chart(bars, width="stretch")
        st.caption(f"The parts add up to the total change: £{sum(b.values()):+,.0f}.")

        with st.expander("Biggest customer declines (lost or spending less)"):
            country_of = history.groupby("CustomerID")["Country"].agg(lambda s: s.mode().iat[0])
            worst = rt.head(15).assign(Country=lambda d: d["CustomerID"].map(country_of))
            st.dataframe(worst[["CustomerID", "Country", "status", "net_ly", "net", "change"]]
                         .style.format({"net": "£{:,.0f}", "net_ly": "£{:,.0f}", "change": "£{:+,.0f}"}),
                         hide_index=True)
