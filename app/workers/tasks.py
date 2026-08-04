from app.db.session import SessionLocal
from app.services.webhook_delivery_service import deliver_webhook
from app.workers.celery_app import celery_app


@celery_app.task
def deliver_webhook_task(webhook_id: int, payload: str) -> dict[str, int | str] | None:
    db = SessionLocal()
    try:
        delivery_attempt = deliver_webhook(
            db=db,
            webhook_id=webhook_id,
            payload=payload,
        )
        if delivery_attempt is None:
            return None
        
        return {
            "delivery_attempt_id": delivery_attempt.id,
            "webhook_id": delivery_attempt.webhook_id,
            "status": delivery_attempt.status,
        }
    finally:
        db.close()