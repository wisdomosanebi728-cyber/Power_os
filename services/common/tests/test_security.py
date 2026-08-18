from datetime import timedelta
import pytest
from poweros_common.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_device_token,
    hash_device_token,
    verify_device_token,
    Roles,
)


def test_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_roundtrip():
    secret = "test-secret-key-for-unit-tests-32bytes-long"
    token = create_access_token(
        subject="user-123",
        role=Roles.OPERATOR,
        community_id="comm-abc",
        secret_key=secret,
        expires_delta=timedelta(minutes=15),
    )
    assert isinstance(token, str)

    payload = decode_access_token(token, secret_key=secret)
    assert payload["sub"] == "user-123"
    assert payload["role"] == Roles.OPERATOR
    assert payload["community_id"] == "comm-abc"
    assert payload["iss"] == "POWER OS"


def test_jwt_expired_token():
    secret = "test-secret-key-for-unit-tests-32bytes-long"
    expired_token = create_access_token(
        subject="user-123",
        role=Roles.CONSUMER,
        secret_key=secret,
        expires_delta=timedelta(seconds=-1),  # already expired
    )
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token(expired_token, secret_key=secret)


def test_device_token_verification():
    raw_token = generate_device_token()
    assert raw_token.startswith("pow_dev_")
    token_hash = hash_device_token(raw_token)

    assert verify_device_token(raw_token, token_hash) is True
    assert verify_device_token("pow_dev_tampered", token_hash) is False
