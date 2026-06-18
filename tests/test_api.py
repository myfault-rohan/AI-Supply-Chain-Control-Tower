from fastapi.testclient import TestClient
from backend.api_server import app

client = TestClient(app)

def test_health():
    """Verify the health endpoint is active."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_seller_risk_endpoint():
    """Verify the seller risk endpoint returns formatted data."""
    with TestClient(app) as test_client: # Context manager triggers lifespan
        response = test_client.get("/api/v1/seller-risk?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "seller_id" in data[0]
            assert "churn_probability" in data[0]
            assert "risk_tier" in data[0]
            assert "top_drivers" in data[0]
