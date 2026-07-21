from fastapi.testclient import TestClient


def test_create_webhook_returns_created_webhook(client: TestClient) -> None:
    payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "super-secret",
        "is_enabled": True,
    }

    response = client.post("/webhooks", json=payload)

    assert response.status_code == 200


    data = response.json()


    assert data["id"] > 0
    assert data["name"] == payload["name"]
    assert data["target_url"] == payload["target_url"]
    assert data["is_enabled"] is True
    assert "created_at" in data
    assert "updated_at" in data
    assert "signing_secret" not in data