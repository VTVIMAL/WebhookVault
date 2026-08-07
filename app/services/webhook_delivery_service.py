from collections.abc import Callable
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session


from app.services.webhook_delivery_attempt_service import (
    create_delivery_attempt,
    mark_delivery_attempt_failed,
    mark_delivery_attempt_succeeded,
    should_retry_attempt,
)
from app.services.webhook_service import get_webhook_by_id
from app.services.webhook_signing_service import generate_webhook_signature


@dataclass
class DeliveryResult:
    delivery_attempt_id: int
    webhook_id: int
    status: str
    attempt_number: int
    should_retry: bool



HttpSender = Callable[[str, str, dict[str, str]], httpx.Response]


def default_http_sender(url: str, payload: str, headers: dict[str, str]) -> httpx.Response:
    return httpx.post(
        url,
        content=payload,
        headers=headers,
        timeout=10.0,
    )


def deliver_webhook(
    db: Session,
    webhook_id: int,
    payload: str,
    http_sender: HttpSender = default_http_sender,
) -> DeliveryResult | None:
    webhook = get_webhook_by_id(db, webhook_id)

    if webhook is None:
        return None

    headers = {"Content-Type": "application/json"}
    if webhook.signing_secret:
        headers["X-WebhookVault-Signature"] = generate_webhook_signature(
            payload,
            webhook.signing_secret,
        )

    delivery_attempt = create_delivery_attempt(
        db=db,
        webhook_id=webhook.id,
        payload=payload,
        status="pending",
    )

    headers["X-WebhookVault-Attempt-Number"] = str(delivery_attempt.attempt_number)

    try:
        response = http_sender(webhook.target_url, payload, headers)
    except Exception as exc:
        failed_attempt = mark_delivery_attempt_failed(
            db=db,
            delivery_attempt_id=delivery_attempt.id,
            error_message=str(exc),
        )
        if failed_attempt is None:
            return None

        return DeliveryResult(
            delivery_attempt_id=failed_attempt.id,
            webhook_id=failed_attempt.webhook_id,
            status=failed_attempt.status,
            attempt_number=failed_attempt.attempt_number,
            should_retry=should_retry_attempt(
                failed_attempt.attempt_number,
                failed_attempt.response_status_code,
            ),
        )

    if 200 <= response.status_code < 300:
        succeeded_attempt = mark_delivery_attempt_succeeded(
            db=db,
            delivery_attempt_id=delivery_attempt.id,
            response_status_code=response.status_code,
        )
        if succeeded_attempt is None:
            return None

        return DeliveryResult(
            delivery_attempt_id=succeeded_attempt.id,
            webhook_id=succeeded_attempt.webhook_id,
            status=succeeded_attempt.status,
            attempt_number=succeeded_attempt.attempt_number,
            should_retry=False,
        )
    
    failed_attempt = mark_delivery_attempt_failed(
        db=db,
        delivery_attempt_id=delivery_attempt.id,
        response_status_code=response.status_code,
        error_message=f"Receiver returned status {response.status_code}",
    )
    if failed_attempt is None:
        return None

    return DeliveryResult(
        delivery_attempt_id=failed_attempt.id,
        webhook_id=failed_attempt.webhook_id,
        status=failed_attempt.status,
        attempt_number=failed_attempt.attempt_number,
        should_retry=should_retry_attempt(
            failed_attempt.attempt_number,
            failed_attempt.response_status_code,
        ),
    )


