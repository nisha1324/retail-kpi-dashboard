"""Export the README image of the dashboard's customer revenue bridge (Jan-Nov 2011 vs 2010).

Run after prepare_data.py: python scripts/export_customer_chart.py
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import vl_convert as vlc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.kpis import cancelled_bulk_lines, filter_period, revenue_bridge  # noqa: E402

df = pd.read_parquet(ROOT / "data" / "processed" / "transactions.parquet")
df = df[~cancelled_bulk_lines(df)]
b = revenue_bridge(filter_period(df, "2011-01-01", "2011-11-30"), filter_period(df, "2010-01-01", "2010-11-30"))
labels = {"lost": "Lost customers", "retained": "Retained customers spending less",
          "gained": "New or won-back customers", "unidentified": "No customer ID"}
fmt = lambda v: f"{'+' if v >= 0 else '−'}£{abs(v) / 1e3:,.0f}k"  # noqa: E731
parts = [f"{labels[k]}  {fmt(v)}" for k, v in b.items()]
data = pd.DataFrame({"part": parts, "change": list(b.values())})
data["direction"] = ["Gain" if v >= 0 else "Decline" for v in data["change"]]

chart = alt.Chart(data, title="Change in net revenue by customer group, Jan–Nov 2011 vs 2010").mark_bar().encode(
    x=alt.X("change:Q", title=f"Change vs last year (£), total {fmt(sum(b.values()))}", axis=alt.Axis(format="~s")),
    y=alt.Y("part:N", sort=parts, title=None, axis=alt.Axis(labelLimit=400)),
    color=alt.Color("direction:N", legend=None,
                    scale=alt.Scale(domain=["Gain", "Decline"], range=["#2a78d6", "#eb6834"])),
).properties(width=560, height=200)
out = ROOT / "docs" / "customer_bridge_2011_vs_2010.png"
out.write_bytes(vlc.vegalite_to_png(chart.to_json(), scale=2))
print("wrote", out.relative_to(ROOT), {k: round(v) for k, v in b.items()}, f"total £{sum(b.values()):+,.0f}")
