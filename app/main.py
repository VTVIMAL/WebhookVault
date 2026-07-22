from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.session import get_db
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookRead, WebhookUpdate
from app.services.webhook_service import create_webhook, get_webhook_by_id, list_webhooks, update_webhook, delete_webhook


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)


    @app.get("/health")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/webhooks", response_model=WebhookRead)
    def create_webhook_endpoint(payload: WebhookCreate, db: Session = Depends(get_db),) -> Webhook:
        return create_webhook(db, payload)

    @app.get("/webhooks/{webhook_id}", response_model=WebhookRead)
    def get_webhook_endpoint(webhook_id: int, db: Session = Depends(get_db)) -> Webhook:
        webhook = get_webhook_by_id(db, webhook_id)
        if webhook is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return webhook

    @app.get("/webhooks", response_model=list[WebhookRead])
    def list_webhook_endpoints(db: Session = Depends(get_db)) -> list[Webhook]:
        return list_webhooks(db)

    @app.patch("/webhooks/{webhook_id}", response_model=WebhookRead)
    def update_webhook_endpoint(
        webhook_id: int,
        payload: WebhookUpdate,
        db: Session = Depends(get_db),
    ) -> Webhook:
        webhook = update_webhook(db, webhook_id, payload)
        if webhook is None:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return webhook

    @app.delete("/webhooks/{webhook_id}", status_code=204)
    def delete_webhook_endpoint(
        webhook_id: int,
        db: Session = Depends(get_db),
    ) -> Response:
        deleted = delete_webhook(db, webhook_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Webhook not found")
        return Response(status_code=204)

    
    return app


app = create_app()