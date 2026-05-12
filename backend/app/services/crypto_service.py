import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..config import get_settings

settings = get_settings()


def _master_key() -> bytes:
    return bytes.fromhex(settings.file_encryption_master_key)


def encrypt_file(data: bytes) -> tuple[bytes, bytes]:
    """Шифрует данные случайным ключом. Возвращает (зашифрованные_данные, ключ)."""
    key = os.urandom(32)
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    encrypted = nonce + aesgcm.encrypt(nonce, data, None)
    return encrypted, key


def decrypt_file(encrypted_data: bytes, key: bytes) -> bytes:
    """Расшифровывает данные ключом."""
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_key(file_key: bytes) -> str:
    """Шифрует файловый ключ мастер-ключом. Возвращает base64-строку."""
    master = _master_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(master)
    encrypted = nonce + aesgcm.encrypt(nonce, file_key, None)
    return base64.b64encode(encrypted).decode()


def decrypt_key(encrypted_key_b64: str) -> bytes:
    """Расшифровывает файловый ключ мастер-ключом."""
    master = _master_key()
    data = base64.b64decode(encrypted_key_b64)
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(master)
    return aesgcm.decrypt(nonce, ciphertext, None)
