from collections.abc import Callable

import httpx
from sqlalchemy.orm import Session


from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.services.webhook_delivery_attempt_service import (
    create_delivery_attempt,
    mark_delivery_attempt_failed,
    mark_delivery_attempt_succeeded
)
from app.services.webhook_service import get_webhook_by_id


HttpSender = Callable[[str, str], httpx.Response]


def default_http_sender(url: str, payload: str) -> httpx.Response:
    return httpx.post(
        url,
        content=payload,
        headers={"Content-Type": "application/json"},
        timeout=10.0,
    )


def deliver_webhook(
    db: Session,
    webhook_id: int,
    payload: str,
    http_sender: HttpSender = default_http_sender,
) -> WebhookDeliveryAttempt | None:
    webhook = get_webhook_by_id(db, webhook_id)
    if webhook is None:
        return None

    delivery_attempt = create_delivery_attempt(
        db=db,
        webhook_id=webhook.id,
        payload=payload,
        attempt_number=1,
        status="pending",
    )

    try:
        response = http_sender(webhook.target_url, payload)
    except Exception as exc:
        return mark_delivery_attempt_failed(
            db=db,
            delivery_attempt_id=delivery_attempt.id,
            error_message=str(exc)
        )

    if 200 <= response.status_code < 300:
        return mark_delivery_attempt_succeeded(
            db=db,
            delivery_attempt_id=delivery_attempt.id,
            response_status_code=response.status_code,
        )
    
    return mark_delivery_attempt_failed(
        db=db,
        delivery_attempt_id=delivery_attempt.id,
        response_status_code=response.status_code,
        error_message=f"Receiver returned status {response.status_code}",
    )