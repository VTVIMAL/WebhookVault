from datetime import datetime

from pydantic import BaseModel, ConfigDict



class WebhookCreate(BaseModel):
    name: str
    target_url: str
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