"""Export the README image of the dashboard's country-drivers chart (Jan-Nov 2011 vs 2010).

Run after prepare_data.py: python scripts/export_driver_chart.py
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.kpis import cancelled_bulk_lines, driver_table, filter_period  # noqa: E402

df = pd.read_parquet(ROOT / "data" / "processed" / "transactions.parquet")
df = df[~cancelled_bulk_lines(df)]
t = driver_table(filter_period(df, "2011-01-01", "2011-11-30"),
                 filter_period(df, "2010-01-01", "2010-11-30"), "Country")
top = pd.concat([t.head(8), t.tail(8)]).drop_duplicates("Country")
top = top.assign(direction=["Gain" if c >= 0 else "Decline" for c in top["change"]])

chart = alt.Chart(top, title="Change in net revenue by country, Jan–Nov 2011 vs 2010").mark_bar().encode(
    x=alt.X("change:Q", title="Change vs last year (£)", axis=alt.Axis(format="~s")),
    y=alt.Y("Country:N", sort=alt.EncodingSortField("change", order="descending"), title=None),
    color=alt.Color("direction:N", legend=None,
                    scale=alt.Scale(domain=["Gain", "Decline"], range=["#2a78d6", "#eb6834"])),
).properties(width=560, height=360)
out = ROOT / "docs" / "country_drivers_2011_vs_2010.png"
out.write_bytes(vlc.vegalite_to_png(chart.to_json(), scale=2))
print("wrote", out.relative_to(ROOT), f"(total change £{t['change'].sum():+,.0f})")
