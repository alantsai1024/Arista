"""
Password encryption utilities for MVP.
TODO: Replace with proper encryption (e.g., Vault, Fernet) in production.
"""
import base64
import os
from typing import Optional


# Simple base64 encoding for MVP
# TODO: Replace with proper encryption (Fernet, Vault, etc.) in production
def encrypt_password(password: str) -> str:
    """
    Encrypt password using base64 encoding (MVP only).
    
    TODO: Replace with proper encryption:
    - Use cryptography.fernet.Fernet for symmetric encryption
    - Or integrate with HashiCorp Vault for secrets management
    - Or use AWS Secrets Manager / Azure Key Vault
    """
    encoded = base64.b64encode(password.encode('utf-8')).decode('utf-8')
    return encoded


def decrypt_password(encrypted: str) -> str:
    """
    Decrypt password from base64 encoding (MVP only).
    
    TODO: Replace with proper decryption matching encrypt_password implementation.
    """
    try:
        decoded = base64.b64decode(encrypted.encode('utf-8')).decode('utf-8')
        return decoded
    except Exception as e:
        raise ValueError(f"Failed to decrypt password: {str(e)}")
