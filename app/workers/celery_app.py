from celery import Celery

from app.core.settings import get_settings


settings = get_settings()

celery_app = Celery(
    "webhookvault",
    broker=settings.redis_url,
)
