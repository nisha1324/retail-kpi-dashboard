import pandas as pd
import pytest

from app.kpis import filter_period, kpi_summary, monthly_kpis, same_period_last_year, yoy_change


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
