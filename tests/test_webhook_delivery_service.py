from faulthandler import is_enabled
import http
from os import name
import httpx
from sqlalchemy.orm import Session


from app.models import webhook
from app.models.webhook import Webhook
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


    def successful_sender(url: str, payload: str) -> httpx.Response:
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

    def failing_sender(url: str, payload: str) -> httpx.Response:
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

    def failing_response_sender(url: str, payload: str) -> httpx.Response:
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