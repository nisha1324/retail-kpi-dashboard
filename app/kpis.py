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
