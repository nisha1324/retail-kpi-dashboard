"""Smoke test: the dashboard renders without errors on the real data."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "transactions.parquet"


@pytest.mark.skipif(not DATA.exists(), reason="run scripts/prepare_data.py first")
def test_dashboard_renders():
    at = AppTest.from_file("../app/dashboard.py", default_timeout=120).run()
    assert not at.exception
    labels = [m.label for m in at.metric][:5]
    assert labels == ["Net revenue", "Orders", "Avg order value", "Active customers", "Return rate"]
    for m in at.metric[:7]:
        print(m.label, m.value, m.delta)


@pytest.mark.skipif(not DATA.exists(), reason="run scripts/prepare_data.py first")
def test_drivers_tab_both_levels():
    at = AppTest.from_file("../app/dashboard.py", default_timeout=120).run()
    assert [t.label for t in at.tabs] == ["Overview", "Drivers: countries and products"]
    assert "Lines per order" in [m.label for m in at.metric]
    at.radio[0].set_value("Product").run()
    assert not at.exception
