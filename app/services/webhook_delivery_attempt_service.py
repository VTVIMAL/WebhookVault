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