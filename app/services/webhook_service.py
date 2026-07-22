from sqlalchemy.orm import Session

from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate


def create_webhook(db: Session, payload: WebhookCreate) -> Webhook:
    webhook = Webhook(
        name=payload.name,
        target_url=str(payload.target_url),
        signing_secret=payload.signing_secret,
        is_enabled=payload.is_enabled,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


def get_webhook_by_id(db: Session, webhook_id: int) -> Webhook | None:
    return db.get(Webhook, webhook_id)


def list_webhooks(db: Session) -> list[Webhook]:
    return db.query(Webhook).order_by(Webhook.id.asc()).all()


def update_webhook(db: Session, webhook_id: int, payload: WebhookUpdate) -> Webhook | None:
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        return None

    update_data = payload.model_dump(exclude_unset=True)

    if "target_url" in update_data:
        update_data["target_url"] = str(update_data["target_url"])

    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    db.commit()
    db.refresh(webhook)
    return webhook


def delete_webhook(db: Session, webhook_id: int) -> bool:
    webhook = db.get(Webhook, webhook_id)
    if webhook is None:
        return False

    db.delete(webhook)
    db.commit()
    return True