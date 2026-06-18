"""Тесты шифрования файлов."""

from app.services.crypto_service import decrypt_file, decrypt_key, encrypt_file, encrypt_key


class TestFileCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        data = b"Test secret data for encryption"
        encrypted, key = encrypt_file(data)
        assert encrypted != data
        assert len(key) == 32

        decrypted = decrypt_file(encrypted, key)
        assert decrypted == data

    def test_different_keys_each_call(self):
        data = b"same data"
        _, key1 = encrypt_file(data)
        _, key2 = encrypt_file(data)
        assert key1 != key2

    def test_different_nonces_each_call(self):
        data = b"same data"
        enc1, _ = encrypt_file(data)
        enc2, _ = encrypt_file(data)
        # Разные nonce → разный шифротекст даже для одинаковых данных и потенциально одинаковых ключей
        assert enc1 != enc2

    def test_large_data(self):
        data = b"X" * 1_000_000
        encrypted, key = encrypt_file(data)
        decrypted = decrypt_file(encrypted, key)
        assert decrypted == data

    def test_empty_data(self):
        encrypted, key = encrypt_file(b"")
        assert decrypt_file(encrypted, key) == b""


class TestKeyCrypto:
    def test_encrypt_decrypt_key_roundtrip(self):
        file_key = b"\x01" * 32
        encrypted_b64 = encrypt_key(file_key)
        assert isinstance(encrypted_b64, str)

        decrypted = decrypt_key(encrypted_b64)
        assert decrypted == file_key

    def test_encrypted_key_is_base64(self):
        import base64
        file_key = b"\x42" * 32
        encrypted_b64 = encrypt_key(file_key)
        # Должен декодироваться как base64
        base64.b64decode(encrypted_b64)
