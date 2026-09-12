from pydantic import SecretStr

from app.core.crypto import decrypt_secret, encrypt_secret


def test_mfa_secret_encryption_round_trip_does_not_store_plaintext() -> None:
    key = SecretStr("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")

    encrypted = encrypt_secret("JBSWY3DPEHPK3PXP", key)

    assert "JBSWY3DPEHPK3PXP" not in encrypted
    assert decrypt_secret(encrypted, key) == "JBSWY3DPEHPK3PXP"
