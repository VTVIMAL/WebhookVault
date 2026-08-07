from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WebhookDeliveryAttemptRead(BaseModel):
    id: int
    webhook_id: int
    payload: str
    attempt_number: int
    status: str
    response_status_code: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)