"""
Encryption Module for Secure Credential Storage
FIXED VERSION - Compatible with cryptography 41.0.7+

Author: BLESSING OMOREGIE
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Optional
import json


class CredentialEncryption:
    """
    Military-grade encryption for sensitive credentials.
    Uses Fernet (symmetric encryption) with PBKDF2 key derivation.
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize encryption with master password.
        
        Args:
            master_password: Master password for encryption key derivation.
                           If None, uses environment variable MASTER_KEY.
        """
        if master_password is None:
            master_password = os.getenv('MASTER_KEY')
            if not master_password:
                raise ValueError(
                    "MASTER_KEY environment variable not set. "
                    "Set it with: [System.Environment]::SetEnvironmentVariable('MASTER_KEY', 'your-key', 'User')"
                )
        
        self.salt = self._get_or_create_salt()
        self.cipher = self._derive_cipher(master_password)
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create encryption salt."""
        salt_file = 'config/.salt'
        
        if os.path.exists(salt_file):
            with open(salt_file, 'rb') as f:
                return f.read()
        else:
            salt = os.urandom(16)
            os.makedirs('config', exist_ok=True)
            with open(salt_file, 'wb') as f:
                f.write(salt)
            try:
                os.chmod(salt_file, 0o600)
            except:
                pass
            return salt
    
    def _derive_cipher(self, password: str) -> Fernet:
        """Derive encryption cipher from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data.
        
        Args:
            data: Plain text to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Plain text
        """
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(decoded)
        return decrypted.decode()
    
    def encrypt_credentials(self, credentials: dict) -> str:
        """
        Encrypt MT5 credentials dictionary.
        
        Args:
            credentials: Dict with login, password, server
            
        Returns:
            Encrypted JSON string
        """
        json_str = json.dumps(credentials)
        return self.encrypt(json_str)
    
    def decrypt_credentials(self, encrypted_json: str) -> dict:
        """
        Decrypt MT5 credentials.
        
        Args:
            encrypted_json: Encrypted credentials string
            
        Returns:
            Dictionary with credentials
        """
        json_str = self.decrypt(encrypted_json)
        return json.loads(json_str)


_encryptor: Optional[CredentialEncryption] = None


def get_encryptor() -> CredentialEncryption:
    """Get or create global encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryption()
    return _encryptor


def encrypt_api_key(api_key: str) -> str:
    """Convenience function to encrypt API key."""
    return get_encryptor().encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Convenience function to decrypt API key."""
    return get_encryptor().decrypt(encrypted_key)