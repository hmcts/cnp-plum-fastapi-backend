import os
import httpx

TEST_URL = os.environ.get("TEST_URL", "http://localhost:8000")


def test_root_endpoint_is_reachable():
    response = httpx.get(f"{TEST_URL}/")
    assert response.status_code == 200
