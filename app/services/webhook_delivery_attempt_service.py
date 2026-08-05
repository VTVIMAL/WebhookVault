from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt


def create_delivery_attempt(
    db: Session,
    webhook_id: int,
    payload: str,
    status: str,
) -> WebhookDeliveryAttempt:
    delivery_attempt = WebhookDeliveryAttempt(
        webhook_id=webhook_id,
        payload=payload,
        attempt_number=get_next_attempt_number(db, webhook_id),
        status=status,
    )
    db.add(delivery_attempt)
    db.commit()
    db.refresh(delivery_attempt)
    return delivery_attempt


def mark_delivery_attempt_succeeded(
    db: Session,
    delivery_attempt_id: int,
    response_status_code: int | None = None,
) -> WebhookDeliveryAttempt | None:
    delivery_attempt = db.get(WebhookDeliveryAttempt, delivery_attempt_id)
    if delivery_attempt is None:
        return None
    
    delivery_attempt.status = "success"
    delivery_attempt.response_status_code = response_status_code

    db.commit()
    db.refresh(delivery_attempt)
    return delivery_attempt


def mark_delivery_attempt_failed(
    db: Session,
    delivery_attempt_id: int,
    response_status_code: int | None = None,
    error_message: str | None = None,
) -> WebhookDeliveryAttempt | None:
    delivery_attempt = db.get(WebhookDeliveryAttempt, delivery_attempt_id)
    if delivery_attempt is None:
        return None

    delivery_attempt.status = "failed"
    delivery_attempt.response_status_code = response_status_code
    delivery_attempt.error_message = error_message

    db.commit()
    db.refresh(delivery_attempt)
    return delivery_attempt


def get_next_attempt_number(db: Session, webhook_id: int) -> int:
    max_attempt_number = (
        db.query(func.max(WebhookDeliveryAttempt.attempt_number))
        .filter(WebhookDeliveryAttempt.webhook_id == webhook_id)
        .scalar()
    )

    if max_attempt_number is None:
        return 1

    return max_attempt_number + 1


def is_retryable_failure(response_status_code: int | None) -> bool:
    if response_status_code is None:
        return True

    return 500 <= response_status_code < 600


def get_retry_delay_seconds(attempt_number: int) -> int:
    if attempt_number <= 1:
        return 60
    if attempt_number == 2:
        return 300
    return 900



MAX_DELIVERY_ATTEMPTS = 3


def should_retry_attempt(attempt_number: int, response_status_code: int | None) -> bool:
    if attempt_number >= MAX_DELIVERY_ATTEMPTS:
        return False

    return is_retryable_failure(response_status_code)