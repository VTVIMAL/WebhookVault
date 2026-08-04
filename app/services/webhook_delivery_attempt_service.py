from sqlalchemy.orm import Session

from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt


def create_delivery_attempt(
    db: Session,
    webhook_id: int,
    payload: str,
    attempt_number: int,
    status: str,
) -> WebhookDeliveryAttempt:
    delivery_attempt = WebhookDeliveryAttempt(
        webhook_id=webhook_id,
        payload=payload,
        attempt_number=attempt_number,
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