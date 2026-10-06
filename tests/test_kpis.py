import pandas as pd
import pytest

from app.kpis import (aov_bridge, cancelled_bulk_lines, customer_mix, driver_table, retention, revenue_bridge, filter_period, kpi_summary,
                      monthly_kpis, same_period_last_year, yoy_change)


@pytest.fixture
def df():
    return pd.DataFrame({
        "Invoice": ["1", "1", "2", "C3", "4"],
        "InvoiceDate": pd.to_datetime(["2010-01-05", "2010-01-05", "2010-01-20", "2010-01-21", "2010-02-01"]),
        "CustomerID": pd.array([10, 10, None, 10, 11], dtype="Int64"),
        "Revenue": [30.0, 20.0, 50.0, -10.0, 100.0],
        "IsReturn": [False, False, False, True, False],
    })


def test_summary(df):
    k = kpi_summary(df)
    assert k["gross_sales"] == 200
    assert k["returns"] == 10
    assert k["net_revenue"] == 190
    assert k["orders"] == 3
    assert k["aov"] == pytest.approx(200 / 3)
    assert k["active_customers"] == 2  # missing ID not counted
    assert k["return_rate"] == pytest.approx(0.05)


def test_monthly(df):
    m = monthly_kpis(df)
    assert list(m["net_revenue"]) == [90, 100]
    assert list(m["orders"]) == [2, 1]


def test_empty_frame_is_safe(df):
    k = kpi_summary(df.iloc[0:0])
    assert k["orders"] == 0 and k["aov"] == 0 and k["return_rate"] == 0


def test_filter_period_end_inclusive(df):
    assert len(filter_period(df, "2010-01-20", "2010-01-21")) == 2


def test_yoy():
    ch = yoy_change({"a": 120, "b": 5}, {"a": 100, "b": 0})
    assert ch["a"] == pytest.approx(0.2) and ch["b"] is None
    s, e = same_period_last_year("2011-03-01", "2011-03-31")
    assert (s, e) == (pd.Timestamp("2010-03-01"), pd.Timestamp("2010-03-31"))


def test_driver_table():
    base = dict(InvoiceDate=pd.Timestamp("2011-01-01"), CustomerID=pd.NA)
    cur = pd.DataFrame([dict(base, Invoice="1", Country="A", Revenue=100.0, IsReturn=False),
                        dict(base, Invoice="C2", Country="A", Revenue=-10.0, IsReturn=True),
                        dict(base, Invoice="3", Country="B", Revenue=50.0, IsReturn=False)])
    prev = pd.DataFrame([dict(base, Invoice="4", Country="A", Revenue=60.0, IsReturn=False),
                         dict(base, Invoice="5", Country="C", Revenue=40.0, IsReturn=False)])
    t = driver_table(cur, prev, "Country").set_index("Country")
    assert t.loc["A", "net"] == 90 and t.loc["A", "change"] == 30
    assert t.loc["C", "net"] == 0 and t.loc["C", "change"] == -40
    assert t["change"].sum() == 40
    assert t["share_of_change"].sum() == pytest.approx(1.0)
    assert t.loc["A", "return_rate"] == pytest.approx(0.1)
    assert list(t.index) == ["B", "A", "C"]  # sorted by change


def test_aov_bridge(df):
    b = aov_bridge(df, df)
    # 3 orders, 4 sale lines, £200 gross
    assert b["lines_per_order"] == pytest.approx(4 / 3)
    assert b["revenue_per_line"] == pytest.approx(50)


def test_cancelled_bulk_lines():
    d = pd.DataFrame({
        "CustomerID": pd.array([1, 1, 2, 3], dtype="Int64"),
        "StockCode": ["X", "X", "X", "Y"],
        "Quantity": [20_000, -20_000, 20_000, -5],
        "IsReturn": [False, True, False, True],
    })
    assert list(cancelled_bulk_lines(d)) == [True, True, False, False]


def test_customer_mix(df):
    cur = filter_period(df, "2010-01-20", "2010-02-28")
    m = customer_mix(df, cur, "2010-01-20")
    # 11 first buys on 02-01 (new); 10 only has a return here, so it is not counted as a
    # customer but its return still lands in returning revenue; invoice 2 has no ID
    assert m["returning_customers"] == 0 and m["new_customers"] == 1
    assert m["returning_revenue"] == -10 and m["new_revenue"] == 100
    assert m["unidentified_revenue"] == 50
    assert sum(v for k, v in m.items() if k.endswith("revenue")) == kpi_summary(cur)["net_revenue"]


def test_retention():
    d = pd.DataFrame({
        "Invoice": ["a", "b", "c", "d", "e"],
        "InvoiceDate": pd.to_datetime(["2010-03-01", "2010-03-02", "2011-03-01", "2011-03-02", "2011-03-03"]),
        "CustomerID": pd.array([1, 2, 1, 3, 1], dtype="Int64"),
        "Revenue": [100.0, 40.0, 70.0, 25.0, -5.0],
        "IsReturn": [False, False, False, False, True],
    })
    s, t = retention(d[d["InvoiceDate"].dt.year == 2011], d[d["InvoiceDate"].dt.year == 2010])
    assert s["ly_customers"] == 2 and s["retained"] == 1 and s["retention_rate"] == 0.5
    assert s["lost_revenue_ly"] == 40      # customer 2 did not come back
    assert s["retained_change"] == -35     # customer 1: 65 net vs 100
    assert 3 not in set(t["CustomerID"])   # new customers are not in the table


def test_revenue_bridge_adds_up(df):
    cur, prev = filter_period(df, "2010-01-20", "2010-02-28"), filter_period(df, "2010-01-01", "2010-01-19")
    b = revenue_bridge(cur, prev)
    assert b["lost"] == -60          # customer 10: 50 of sales, then only a -10 return
    assert b["gained"] == 100        # customer 11
    assert b["unidentified"] == 50
    assert sum(b.values()) == kpi_summary(cur)["net_revenue"] - kpi_summary(prev)["net_revenue"]
