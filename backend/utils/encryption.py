import os
from cryptography.fernet import Fernet

def get_cipher() -> Fernet:
    key = os.getenv("DOCUMENT_ENCRYPTION_KEY")
    if not key:
        print("[WARNING] DOCUMENT_ENCRYPTION_KEY is missing! Using a generated active key for current session.")
        key = Fernet.generate_key().decode('utf-8')
        os.environ["DOCUMENT_ENCRYPTION_KEY"] = key
    return Fernet(key.encode('utf-8'))

def encrypt_data(data: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.encrypt(data)

def decrypt_data(data: bytes) -> bytes:
    cipher = get_cipher()
    return cipher.decrypt(data)
