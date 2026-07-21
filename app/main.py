from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookRead


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)


    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks", response_model=WebhookRead)
    def create_webhook(payload: WebhookCreate, db: Session = Depends(get_db)) -> Webhook:
        webhook = Webhook(
            name=payload.name,
            target_url=payload.target_url,
            signing_secret=payload.signing_secret,
            is_enabled=payload.is_enabled,
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)
        return webhook

    return app


app = create_app()