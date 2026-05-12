import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://docscan:pass@localhost:5432/docscan")
os.environ.setdefault("REDIS_URL", "redis://:pass@localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "pass")
os.environ.setdefault("POSTGRES_PASSWORD", "pass")
os.environ.setdefault("FILE_ENCRYPTION_MASTER_KEY", "aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899")
os.environ.setdefault("ADMIN_PASSWORD", "AdminPass123")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", "certs/private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", "certs/public.pem")

from app.schemas.scan import ScanResponse, ScanBriefResponse, ClientScanResultRequest
print("schemas/scan         OK")

from app.services.scan_service import compute_sha256, ALLOWED_MIME_TYPES
print(f"scan_service         OK - {len(ALLOWED_MIME_TYPES)} mime types")

from app.services.crypto_service import encrypt_file, decrypt_file, encrypt_key, decrypt_key
data = b"hello world"
encrypted, key = encrypt_file(data)
assert decrypt_file(encrypted, decrypt_key(encrypt_key(key))) == data
print("crypto_service       OK - AES-256-GCM работает")

from app.detection.validators import validate_snils, validate_luhn, validate_inn_person
assert validate_luhn("4111111111111111") is True
assert validate_luhn("1234567890123456") is False
print("validators           OK")

from app.detection.masker import mask_value
assert mask_value("4111111111111111", "bank_card") == "4111 **** **** 1111"
assert mask_value("test@example.com", "email") == "te***@example.com"
print("masker               OK")

from app.detection.engine import DetectionEngine
engine = DetectionEngine()
findings = engine.scan("email: test@gmail.com, tel: +7 (999) 123-45-67")
types = [f["finding_type"] for f in findings]
print(f"detection engine     OK - {len(findings)} findings: {types}")

from app.main import app
routes = [r.path for r in app.routes if hasattr(r, "path")]
print(f"main                 OK - {len(routes)} routes")

print()
print("=== ALL MODULES OK ===")
