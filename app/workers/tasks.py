from app.db.session import SessionLocal
from app.services.webhook_delivery_attempt_service import get_retry_delay_seconds
from app.services.webhook_delivery_service import deliver_webhook
from app.workers.celery_app import celery_app


@celery_app.task
def deliver_webhook_task(webhook_id: int, payload: str) -> dict[str, int | str | bool] | None:
    db = SessionLocal()
    try:
        delivery_result = deliver_webhook(
            db=db,
            webhook_id=webhook_id,
            payload=payload,
        )
        if delivery_result is None:
            return None

        if delivery_result.should_retry:
            countdown = get_retry_delay_seconds(delivery_result.attempt_number)
            deliver_webhook_task.apply_async(
                args=[webhook_id, payload],
                countdown=countdown,
            )
        
        return {
            "delivery_attempt_id": delivery_result.delivery_attempt_id,
            "webhook_id": delivery_result.webhook_id,
            "status": delivery_result.status,
            "should_retry": delivery_result.should_retry,
        }
    finally:
        db.close()