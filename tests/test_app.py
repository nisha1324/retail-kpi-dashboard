"""Smoke test: the dashboard renders without errors on the real data."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "transactions.parquet"


@pytest.mark.skipif(not DATA.exists(), reason="run scripts/prepare_data.py first")
def test_dashboard_renders():
    at = AppTest.from_file("../app/dashboard.py", default_timeout=120).run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert labels == ["Net revenue", "Orders", "Avg order value", "Active customers", "Return rate"]
    for m in at.metric:
        print(m.label, m.value, m.delta)
