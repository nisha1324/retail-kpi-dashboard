"""KPI definitions used by the dashboard. Pure pandas, so they can be tested.

Definitions
- Gross sales: revenue of sale lines (non-return invoices).
- Returns: value of cancellation lines (shown as a positive number).
- Net revenue: gross sales - returns.
- Orders: distinct sale invoices.
- AOV (average order value): gross sales / orders.
- Active customers: distinct identified customers with at least one sale.
- Return rate: returns / gross sales.
"""
import pandas as pd


def kpi_summary(df: pd.DataFrame) -> dict[str, float]:
    sales = df[~df["IsReturn"]]
    gross = float(sales["Revenue"].sum())
    returns = float(-df.loc[df["IsReturn"], "Revenue"].sum())
    orders = int(sales["Invoice"].nunique())
    return {
        "gross_sales": gross,
        "returns": returns,
        "net_revenue": gross - returns,
        "orders": orders,
        "aov": gross / orders if orders else 0.0,
        "active_customers": int(sales["CustomerID"].dropna().nunique()),
        "return_rate": returns / gross if gross else 0.0,
    }


def monthly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar month with the same KPIs as kpi_summary."""
    month = df["InvoiceDate"].dt.to_period("M")
    rows = [{"month": m.to_timestamp(), **kpi_summary(g)} for m, g in df.groupby(month)]
    return pd.DataFrame(rows)


def yoy_change(current: dict[str, float], previous: dict[str, float]) -> dict[str, float | None]:
    """Relative change per KPI; None when the previous value is zero."""
    return {k: (current[k] / previous[k] - 1) if previous.get(k) else None for k in current}


def filter_period(df: pd.DataFrame, start, end) -> pd.DataFrame:
    """Rows with start <= InvoiceDate < end + 1 day (end is inclusive)."""
    start, end = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    return df[(df["InvoiceDate"] >= start) & (df["InvoiceDate"] < end)]


def same_period_last_year(start, end) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(start) - pd.DateOffset(years=1), pd.Timestamp(end) - pd.DateOffset(years=1)


def driver_table(cur: pd.DataFrame, prev: pd.DataFrame, by: str) -> pd.DataFrame:
    """Net revenue and returns per group, this period vs last year.

    `change` is the £ change in net revenue; `share_of_change` is that change as a
    share of the total change, so the rows explain where growth (or decline) came from.
    """
    def per_group(d: pd.DataFrame) -> pd.DataFrame:
        g = d.assign(sales=d["Revenue"].where(~d["IsReturn"], 0.0),
                     ret=-d["Revenue"].where(d["IsReturn"], 0.0))
        return g.groupby(by).agg(gross=("sales", "sum"), returns=("ret", "sum"))

    out = per_group(cur).join(per_group(prev), how="outer", lsuffix="", rsuffix="_ly").fillna(0.0)
    out["net"] = out["gross"] - out["returns"]
    out["net_ly"] = out["gross_ly"] - out["returns_ly"]
    out["change"] = out["net"] - out["net_ly"]
    total = out["change"].sum()
    out["share_of_change"] = out["change"] / total if total else 0.0
    out["return_rate"] = (out["returns"] / out["gross"]).where(out["gross"] > 0)
    out["return_rate_ly"] = (out["returns_ly"] / out["gross_ly"]).where(out["gross_ly"] > 0)
    cols = ["net", "net_ly", "change", "share_of_change", "returns", "returns_ly", "return_rate", "return_rate_ly"]
    return out[cols].sort_values("change", ascending=False).reset_index()


def aov_bridge(cur: pd.DataFrame, prev: pd.DataFrame) -> dict[str, float]:
    """Split the AOV change into lines per order x revenue per line."""
    def parts(d: pd.DataFrame) -> tuple[float, float]:
        s = d[~d["IsReturn"]]
        orders = s["Invoice"].nunique()
        return (len(s) / orders if orders else 0.0, s["Revenue"].sum() / len(s) if len(s) else 0.0)

    (lpo, rpl), (lpo_ly, rpl_ly) = parts(cur), parts(prev)
    return {"lines_per_order": lpo, "lines_per_order_ly": lpo_ly,
            "revenue_per_line": rpl, "revenue_per_line_ly": rpl_ly}


def cancelled_bulk_lines(df: pd.DataFrame, min_qty: int = 10_000) -> pd.Series:
    """Mask of very large sale lines that were fully cancelled, plus their cancellations.

    A pair is a sale and a return with the same customer, stock code and absolute
    quantity (>= min_qty). These look like keying errors: they add the same amount to
    gross sales and to returns, so net revenue is unchanged but AOV and the return
    rate are distorted.
    """
    big = df[df["Quantity"].abs() >= min_qty]
    key = ["CustomerID", "StockCode"]
    sales = big[~big["IsReturn"]].assign(q=big["Quantity"])
    rets = big[big["IsReturn"]].assign(q=-big["Quantity"])
    pairs = sales.reset_index().merge(rets.reset_index(), on=key + ["q"], suffixes=("_s", "_r"))
    idx = set(pairs["index_s"]) | set(pairs["index_r"])
    return df.index.isin(idx)
