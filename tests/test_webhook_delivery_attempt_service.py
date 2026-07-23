from faulthandler import is_enabled
from sqlalchemy.orm import Session

from app.models.webhook import Webhook
from app.services.webhook_delivery_attempt_service import create_delivery_attempt


def test_create_delivery_attempt_persists_attempt(db_session: Session) -> None:
   
    webhook = Webhook(
        name="Payments Webhook",
        target_url="https://example.com/webhooks/payments",
        signing_secret="secret-one",
        is_enabled=True,
    )
    db_session.add(webhook)
    db_session.commit()
    db_session.refresh(webhook)

    delivery_attempt = create_delivery_attempt(
        db=db_session,
        webhook_id=webhook.id,
        payload='{"event":"payment.succeeded"}',
        attempt_number=1,
        status="pending",
    )

    assert delivery_attempt.id > 0
    assert delivery_attempt.webhook_id == webhook.id
    assert delivery_attempt.payload == '{"event":"payment.succeeded"}'
    assert delivery_attempt.attempt_number == 1
    assert delivery_attempt.status == "pending"
    assert delivery_attempt.response_status_code is None
    assert delivery_attempt.error_message is None
