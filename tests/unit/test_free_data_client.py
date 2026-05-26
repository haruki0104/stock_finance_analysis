import json
import pandas as pd
import pytest

from src.data.free_data_client import FreeDataClient


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_twse_month_parsing(monkeypatch):
    client = FreeDataClient()

    sample = {
        "stat": "OK",
        "data": [
            ["110/01/04", "1,000", "10", "11", "9", "10", "10,000", "0"]
        ]
    }

    def fake_get(url, timeout=0):
        return DummyResponse(sample)

    monkeypatch.setattr(client, "_session", type("S", (), {"get": staticmethod(fake_get)})())

    df = client._twse_stock_day("2330", "2023-01-01", "2023-12-31")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert list(df.columns) >= ["date", "stock_id", "Open", "High", "Low", "Close", "Volume"]


def test_twse_json_error(monkeypatch, caplog):
    client = FreeDataClient()

    class BadResp:
        def json(self):
            raise ValueError("invalid json")

    def fake_get(url, timeout=0):
        return BadResp()

    monkeypatch.setattr(client, "_session", type("S", (), {"get": staticmethod(fake_get)})())

    df = client._twse_stock_day("2330", "2023-01-01", "2023-12-31")
    assert isinstance(df, pd.DataFrame)
    assert df.empty
