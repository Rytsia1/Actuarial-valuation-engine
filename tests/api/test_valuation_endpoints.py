import pytest
from fastapi.testclient import TestClient
from actuary_engine.api.main import app

client = TestClient(app)

def test_post_valuation_valid_input():
    payload = {"age": 30, "product": "WholeLife", "benefit": 100000, "rate": 0.05}
    response = client.post("/valuation", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "bel" in data
    
    # The expected BEL would be pre-calculated or analytically checked
    # Hardcoded deterministic value check (placeholder for actual calculated bel for 100k benefit)
    assert data["bel"] > 0

def test_post_valuation_invalid_input():
    payload_age = {"age": -5, "product": "WholeLife", "benefit": 100000, "rate": 0.05}
    response = client.post("/valuation", json=payload_age)
    assert response.status_code == 422

    payload_rate = {"age": 30, "product": "WholeLife", "benefit": 100000, "rate": 1.5}
    response = client.post("/valuation", json=payload_rate)
    assert response.status_code == 422

def test_post_valuation_missing_input():
    payload = {"age": 30, "product": "WholeLife", "rate": 0.05} # missing benefit
    response = client.post("/valuation", json=payload)
    assert response.status_code == 422

def test_post_valuation_extreme_input():
    payload = {"age": 120, "product": "WholeLife", "benefit": 100000, "rate": 0.05}
    response = client.post("/valuation", json=payload)
    assert response.status_code in [400, 422]

def test_server_error_handling(monkeypatch):
    # Mock the engine to raise an exception
    def mock_valuation(*args, **kwargs):
        raise RuntimeError("Engine failure")
    
    monkeypatch.setattr("actuary_engine.api.main.calculate_valuation", mock_valuation)
    
    payload = {"age": 30, "product": "WholeLife", "benefit": 100000, "rate": 0.05}
    response = client.post("/valuation", json=payload)
    assert response.status_code == 500
