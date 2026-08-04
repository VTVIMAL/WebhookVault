from sqlalchemy.orm import Session

from app.models import webhook
from app.models.webhook import Webhook
from app.services.webhook_delivery_attempt_service import (
    create_delivery_attempt, 
    mark_delivery_attempt_failed,
    mark_delivery_attempt_succeeded
)


def test_create_delivery_attempt_persists_attempt(db_session: Session) -> None:
   
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    delivery_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        attempt_number=1,
        status="pending",
    )

    assert delivery_attempt.id > 0
    assert delivery_attempt.webhook_id == webhook.id
    assert delivery_attempt.payload == '{"event":"payment.succeeded"}'
    assert delivery_attempt.attempt_number == 1
    assert delivery_attempt.status == "pending"
    assert delivery_attempt.response_status_code is None
    assert delivery_attempt.error_message is None


def test_mark_delivery_attempt_succeeded_updates_attempt(db_session: Session) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)


    delivery_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        attempt_number=1,
        status="pending",
    )

    original_updated_at = delivery_attempt.updated_at

    updated_attempt = mark_delivery_attempt_succeeded(
        db=db_session,
        delivery_attempt_id=delivery_attempt.id,
        response_status_code=200,
    )

    assert updated_attempt is not None
    assert updated_attempt.status == "success"
    assert updated_attempt.response_status_code == 200
    assert updated_attempt.error_message is None
    assert updated_attempt.updated_at >= original_updated_at


def test_mark_delivery_attempt_failed_updates_attempt(db_session: Session) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://exmaple.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    delivery_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.failed"}',
        attempt_number=1,
        status="pending",
    )

    original_updated_at = delivery_attempt.updated_at

    updated_attempt = mark_delivery_attempt_failed(
        db=db_session,
        delivery_attempt_id=delivery_attempt.id,
        response_status_code=500,
        error_message="Receiver returned 500",
    )

    assert updated_attempt is not None
    assert updated_attempt.status == "failed"
    assert updated_attempt.response_status_code == 500
    assert updated_attempt.error_message == "Receiver returned 500"
    assert updated_attempt.updated_at >= original_updated_at