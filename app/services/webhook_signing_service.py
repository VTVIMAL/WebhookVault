import hashlib
import hmac


def generate_webhook_signature(payload: str, signing_secret: str) -> str:
    return hmac.new(
        signing_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()