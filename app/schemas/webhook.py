from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class WebhookCreate(BaseModel):
    name: str
    target_url: HttpUrl
    signing_secret: str
    is_enabled: bool


class WebhookRead(BaseModel):
    id: int
    name: str
    target_url: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookUpdate(BaseModel):
    name: str | None = None
    target_url: HttpUrl | None = None
    signing_secret: str | None = None
    is_enabled: bool | None = None