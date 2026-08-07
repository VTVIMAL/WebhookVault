from unittest.mock import patch

from app.services.webhook_delivery_service import DeliveryResult
from app.workers.tasks import deliver_webhook_task


def test_deliver_webhook_task_schedules_retry_when_needed() -> None:
    delivery_result = DeliveryResult(
        delivery_attempt_id=1,
        webhook_id=123,
        status="failed",
        attempt_number=1,
        should_retry=True,
    )

    with patch("app.workers.tasks.deliver_webhook", return_value=delivery_result), patch(
        "app.workers.tasks.get_retry_delay_seconds",
        return_value=60,
    ), patch("app.workers.tasks.deliver_webhook_task.apply_async") as mock_apply_async:
        result = deliver_webhook_task.run(123, '{"event":"payment.failed"}')

    assert result == {
        "delivery_attempt_id": 1,
        "webhook_id": 123,
        "status": "failed",
        "should_retry": True,
    }
    mock_apply_async.assert_called_once_with(
        args=[123, '{"event":"payment.failed"}'],
        countdown=60,
    )

def test_deliver_webhook_task_does_not_schedule_retry_when_not_needed() -> None:
    delivery_result = DeliveryResult(
        delivery_attempt_id=2,
        webhook_id=123,
        status="success",
        attempt_number=1,
        should_retry=False,
    )

    with patch("app.workers.tasks.deliver_webhook", return_value=delivery_result),patch(
        "app.workers.tasks.deliver_webhook_task.apply_async"
    ) as mock_apply_async:
        result = deliver_webhook_task.run(123, '{"event":"payment.succeeded"}')

    assert result == {
        "delivery_attempt_id": 2,
        "webhook_id": 123,
        "status": "success",
        "should_retry": False,
    }
    mock_apply_async.assert_not_called()