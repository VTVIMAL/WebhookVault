from fastapi.testclient import TestClient

from unittest.mock import Mock, patch

from pytest import Session

from app.models import webhook
from app.services.webhook_delivery_attempt_service import create_delivery_attempt


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


def test_create_webhook_rejects_invalid_target_url(client: TestClient) -> None:
    payload = {
        "name": "Broken Webhook",
        "target_url": "not-a-valid-url",
        "signing_secret": "super-secret",
        "is_enabled": True,
    }

    response = client.post("/webhooks", json=payload)

    assert response.status_code == 422


def test_get_webhook_by_id_returns_webhook(client: TestClient) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "super-secret",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]

    response = client.get(f"/webhooks/{webhook_id}")

    data = response.json()

    assert data["id"] == webhook_id
    assert data["name"] == create_payload["name"]
    assert data["target_url"] == create_payload["target_url"]
    assert data["is_enabled"] is True
    assert "signing_secret" not in data


def test_get_webhook_by_id_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/webhooks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_list_webhooks_returns_webhooks_in_id_order(client: TestClient) -> None:
    first_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }
    second_payload = {
        "name": "Orders Webhook",
        "target_url": "https://example.com/webhooks/orders",
        "signing_secret": "secret-two",
        "is_enabled": False,
    }

    client.post("/webhooks",json=first_payload)
    client.post("/webhooks", json=second_payload)

    response = client.get("/webhooks")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["name"] == first_payload["name"]
    assert data[1]["name"] == second_payload["name"]
    assert "signing_secret" not in data[0]
    assert "signing_secret" not in data[1]


def test_update_webhook_updates_only_provided_fields(client: TestClient) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]

    update_payload = {
        "name": "Updated Payments Webhook",
        "is_enabled": False,
    }

    response = client.patch(f"/webhooks/{webhook_id}", json=update_payload)

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == webhook_id
    assert data["name"] == "Updated Payments Webhook"
    assert data["target_url"] == create_payload["target_url"]
    assert data["is_enabled"] is False
    assert "signing_secret" not in data


def test_update_webhook_returns_404_when_missing(client: TestClient) -> None:
    response = client.patch(
        "/webhooks/99999",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_delete_webhook_returns_204_and_removes_webhook(client: TestClient) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]

    delete_response = client.delete(f"/webhooks/{webhook_id}")

    assert delete_response.status_code == 204
    assert delete_response.text == ""

    get_response = client.get(f"/webhooks/{webhook_id}")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Webhook not found"}


def test_delete_webhook_returns_404_when_missing(client: TestClient) -> None:
    response = client.delete("/webhooks/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_deliver_webhook_endpoint_queues_task(client: TestClient) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]


    mocked_task = Mock()
    mocked_task.id = "task-123"

    with patch("app.main.deliver_webhook_task.delay", return_value=mocked_task) as mock_delay:
        response = client.post(
            f"/webhooks/{webhook_id}/deliver",
            json={
                "payload": {
                    "event": "payment.succeeded",
                    "amount": 1000,
                }
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-123",
        "webhook_id": webhook_id,
        "status": "queued",
    }
    mock_delay.assert_called_once()


def test_deliver_webhook_endpoint_returns_404_when_webhook_missing(
    client: TestClient,
) -> None:
    response = client.post(
        "/webhooks/99999/deliver",
        json={
            "payload": {
                "event": "payment.succeeded",
                "amount": 1000,
            }
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_list_webhook_attempts_returns_attempts_in_attempt_number_order(
    client: TestClient,
    db_session: Session,
) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]

    create_delivery_attempt(
        db=db_session,
        webhook_id=webhook_id,
        payload='{"event":"payments.succeeded"}',
        status="failed",
    )
    create_delivery_attempt(
        db=db_session,
        webhook_id=webhook_id,
        payload='{"event":"payments.succeeded"}',
        status="success",
    )

    response = client.get(f"/webhooks/{webhook_id}/attempts")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["attempt_number"] == 1
    assert data[1]["attempt_number"] == 2
    assert data[0]["webhook_id"] == webhook_id
    assert data[1]["webhook_id"] == webhook_id


def test_list_webhook_attempts_returns_404_when_webhook_missing(
    client: TestClient,
) -> None:
    response = client.get("/webhooks/99999/attempts")

    assert response.status_code == 404
    assert response.json() == {"detail": "Webhook not found"}


def test_get_webhook_attempt_returns_attempt_detail(
    client: TestClient,
    db_session: Session,
) -> None:
    create_payload = {
        "name": "Payments Webhook",
        "target_url": "https://example.com/webhooks/payments",
        "signing_secret": "secret-one",
        "is_enabled": True,
    }

    create_response = client.post("/webhooks", json=create_payload)
    webhook_id = create_response.json()["id"]

    attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook_id,
        payload='{"event":"payment.succeeded"}',
        status="failed",
    )

    response = client.get(f"/webhooks/{webhook_id}/attempts/{attempt.id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == attempt.id
    assert data["webhook_id"] == webhook_id
    assert data["attempt_number"] == 1
    assert data["status"] == "failed"
    assert data["payload"] == '{"event":"payment.succeeded"}'


def test_get_webhook_attempt_returns_404_for_attempt_owned_by_another_webhook(
    client: TestClient,
    db_session: Session,
) -> None:
    first_webhook_response = client.post(
        "/webhooks",
        json={
            "name": "Payments Webhook",
            "target_url": "https://example.com/webhooks/payments",
            "signing_secret": "secret-one",
            "is_enabled": True,
        },
    )
    first_webhook_id = first_webhook_response.json()["id"]

    second_webhook_response = client.post(
        "/webhooks",
        json={
            "name": "Orders Webhook",
            "target_url": "https://example.com/webhooks/orders",
            "signing_secret": "secret-two",
            "is_enabled": True,
        },
    )
    second_webhook_id= second_webhook_response.json()["id"]

    attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=second_webhook_id,
        payload='{"event":"order.created"}',
        status="failed",
    )

    response = client.get(f"/webhooks/{first_webhook_id}/attempts/{attempt.id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Delivery attempt not found"}