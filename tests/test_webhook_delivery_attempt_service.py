from os import name
from sqlalchemy.orm import Session

from app.models import webhook
from app.models.webhook import Webhook
from app.services.webhook_delivery_attempt_service import (
    create_delivery_attempt, 
    is_retryable_failure,
    should_retry_attempt,
    get_retry_delay_seconds,
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


def test_create_delivery_attempt_increments_attempt_number(db_session: Session) -> None:
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)


    first_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event": "payment.succeeded"}',
        status="pending",
    )

    second_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        status="pending",
    )

    assert first_attempt.attempt_number == 1
    assert second_attempt.attempt_number == 2


def test_is_retryable_failure_returns_true_for_transport_failure() -> None:
    assert is_retryable_failure(None) is True


def test_is_retryable_failure_returns_true_for_5xx() -> None:
    assert is_retryable_failure(500) is True
    assert is_retryable_failure(503) is True


def test_is_retryable_failure_returns_false_for_2xx_and_4xx() -> None:
    assert is_retryable_failure(200) is False
    assert is_retryable_failure(400) is False
    assert is_retryable_failure(404) is False


def test_get_retry_delay_seconds_for_first_attempt() -> None:
    assert get_retry_delay_seconds(1) == 60


def test_get_retry_delay_seconds_for_second_attempt() -> None:
    assert get_retry_delay_seconds(2) == 300


def test_get_retry_delay_seconds_for_third_attempt_and_beyond() -> None:
    assert get_retry_delay_seconds(3) == 900
    assert get_retry_delay_seconds(10) == 900


def test_should_retry_attempt_returns_true_for_retryable_first_attempt() -> None:
    assert should_retry_attempt(1, 500) is True
    assert should_retry_attempt(1, None) is True


def test_should_retry_attempt_returns_true_for_retryable_second_attempt() -> None:
    assert should_retry_attempt(2, 503) is True


def test_should_retry_attempt_returns_false_for_third_attempt() -> None:
    assert should_retry_attempt(3, 500) is False
    assert should_retry_attempt(3, None) is False


def test_should_retry_attempt_returns_false_for_non_retryable_failure() -> None:
    assert should_retry_attempt(1, 400) is False
    assert should_retry_attempt(2, 404) is False