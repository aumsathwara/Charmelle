import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.server import app

client = TestClient(app)

# A very basic "smoke test" to ensure the endpoint runs
# In a real scenario, this would use a dedicated test database
# and fixtures to test relevance, sorting, etc.

def test_recommend_endpoint_runs():
    """
    Tests if the /recommend endpoint returns a successful response
    for a common condition.
    """
    response = client.post("/recommend", json={"conditions": ["dryness"], "limit": 5})
    assert response.status_code == 200
    # The response could be an empty list if the DB is empty, which is valid.
    # So we just check if it's a list (the model validation handles the structure).
    assert isinstance(response.json(), list)

def test_health_check():
    """Tests if the health check endpoint is working."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"} 