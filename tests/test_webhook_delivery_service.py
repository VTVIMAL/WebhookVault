from faulthandler import is_enabled
import http
from os import name
import httpx
from sqlalchemy.orm import Session


from app.models import webhook
from app.models.webhook import Webhook
from app.services.webhook_delivery_attempt_service import create_delivery_attempt
from app.services.webhook_delivery_service import deliver_webhook


def test_deliver_webhook_marks_attempt_success(db_session: Session) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)


    def successful_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        return httpx.Response(status_code=200)

    
    delivery_attempt = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event": "payment.succeeded"}',
        http_sender=successful_sender,
    )

    assert delivery_attempt is not None
    assert delivery_attempt.webhook_id == webhook.id
    assert delivery_attempt.attempt_number == 1
    assert delivery_attempt.status == "success"
    assert delivery_attempt.should_retry is False
    assert delivery_attempt.delivery_attempt_id > 0


def test_deliver_webhook_marks_attempt_failed_on_sender_exception(
    db_session: Session,
) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    def failing_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        raise RuntimeError("connection timeout")

    
    delivery_attempt = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.failed"}',
        http_sender=failing_sender,
    )

    assert delivery_attempt is not None
    assert delivery_attempt.webhook_id == webhook.id
    assert delivery_attempt.attempt_number == 1
    assert delivery_attempt.status == "failed"
    assert delivery_attempt.should_retry is True
    assert delivery_attempt.delivery_attempt_id > 0


def test_deliver_webhook_marks_attempt_failed_on_non_2xx_response(
    db_session: Session,
) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    def failing_response_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        return httpx.Response(status_code=500)

    delivery_attempt = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.failded"}',
        http_sender=failing_response_sender,
    )

    assert delivery_attempt is not None
    assert delivery_attempt.webhook_id == webhook.id
    assert delivery_attempt.attempt_number == 1
    assert delivery_attempt.status == "failed"
    assert delivery_attempt.should_retry is True
    assert delivery_attempt.delivery_attempt_id > 0


def test_deliver_webhook_includes_signature_header_when_secret_exists(
    db_session: Session,
) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="super-secret",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    captured_headers: dict[str, str] = {}

    def successful_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        captured_headers.update(headers)
        return httpx.Response(status_code=200)

    delivery_result = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        http_sender=successful_sender,
    )

    assert delivery_result is not None
    assert "X-WebhookVault-Signature" in captured_headers
    assert captured_headers["Content-Type"] == "application/json"
    assert captured_headers["X-WebhookVault-Signature"] == (
        "16d91fbf760b24a234f2ef182c90276cdda43be8c046fc7fcb42fdfe113df28e"
    )
    assert captured_headers["X-WebhookVault-Attempt-Number"] == "1"



def test_deliver_webhook_omits_signature_header_when_secret_missing(
    db_session: Session,
) -> None:
    webhook = Webhook(
        name="Unsigned Webhook",
        target_url="https://example.com/webhooks/unsigned",
        signing_secret=None,
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    captured_headers: dict[str, str] = {}

    def successful_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        captured_headers.update(headers)
        return httpx.Response(status_code=200)

    delivery_result = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        http_sender=successful_sender,
    )

    assert delivery_result is not None
    assert "X-WebhookVault-Signature" not in captured_headers
    assert captured_headers["Content-Type"] == "application/json"
    assert captured_headers["X-WebhookVault-Attempt-Number"] == "1"


def test_deliver_webhook_retry_attempt_includes_attempt_number_two(
    db_session: Session,
) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="super-secret",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payments.succeeded"}',
        status="failed",
    )

    captured_headers: dict[str, str] = {}

    def successful_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
        captured_headers.update(headers)
        return httpx.Response(status_code=200)

    delivery_result = deliver_webhook(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payments.succeeded"}',
        http_sender=successful_sender,
    )

    assert delivery_result is not None
    assert delivery_result.attempt_number == 2
    assert captured_headers["X-WebhookVault-Attempt-Number"] == "2"