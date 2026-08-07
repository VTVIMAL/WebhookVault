from app.services.webhook_signing_service import generate_webhook_signature


def test_generate_webhook_signature_returns_expected_sha256_hmac() -> None:
    payload = '{"event":"payment.succeeded"}'
    signing_secret = "super-secret"

    signature = generate_webhook_signature(payload, signing_secret)
    
    assert signature == "16d91fbf760b24a234f2ef182c90276cdda43be8c046fc7fcb42fdfe113df28e"