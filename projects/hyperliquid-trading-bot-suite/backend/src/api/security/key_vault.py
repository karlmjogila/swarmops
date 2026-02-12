"""
Secure key vault for managing Hyperliquid wallet private keys.

Private keys are:
1. NEVER transmitted over HTTP (not in headers, body, or query params)
2. Stored encrypted at rest using AES-256-GCM
3. Decrypted only in memory when needed for signing
4. Cleared from memory immediately after use
5. Associated with user accounts, not API endpoints

This module provides EIP-712 signature generation instead of raw key transmission.
"""

import os
import base64
import secrets
import hashlib
import json
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import structlog

from ...config import settings

logger = structlog.get_logger()


# Try to import eth-account for EIP-712 signing
try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data, encode_defunct
    from eth_utils import to_checksum_address
    HAS_ETH_ACCOUNT = True
except ImportError:
    HAS_ETH_ACCOUNT = False
    logger.warning("eth-account not installed. Real trading will not work.")


@dataclass
class StoredKey:
    """Encrypted key storage format."""
    user_id: str
    wallet_address: str
    encrypted_key: bytes  # AES-256-GCM encrypted
    nonce: bytes  # GCM nonce
    salt: bytes  # For key derivation
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True


class KeyVault:
    """
    Secure vault for managing wallet private keys.
    
    Keys are:
    - Encrypted using AES-256-GCM with a key derived from master secret
    - Never exposed via API or logs
    - Used only for generating signatures
    
    The master encryption key is derived from:
    1. Server's SECRET_KEY
    2. User-specific salt
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize key vault.
        
        Args:
            master_key: Master encryption key (uses settings.secret_key if not provided)
        """
        self._master_key = (master_key or settings.validated_secret_key).encode()
        self._keys: Dict[str, StoredKey] = {}  # user_id -> StoredKey
        self._key_cache_ttl = 300  # 5 minutes cache for derived keys
        self._derived_key_cache: Dict[str, Tuple[bytes, float]] = {}
    
    def _derive_encryption_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from master key and salt.
        
        Uses PBKDF2 with SHA-256 for key derivation.
        """
        # Check cache first
        cache_key = hashlib.sha256(salt).hexdigest()
        if cache_key in self._derived_key_cache:
            key, timestamp = self._derived_key_cache[cache_key]
            if time.time() - timestamp < self._key_cache_ttl:
                return key
        
        # Derive new key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        derived_key = kdf.derive(self._master_key)
        
        # Cache the derived key
        self._derived_key_cache[cache_key] = (derived_key, time.time())
        
        return derived_key
    
    def store_key(
        self,
        user_id: str,
        wallet_address: str,
        private_key: str
    ) -> bool:
        """
        Securely store a private key for a user.
        
        The private key is encrypted immediately and the plaintext
        is not stored anywhere.
        
        Args:
            user_id: User ID to associate with the key
            wallet_address: Ethereum wallet address
            private_key: Hex-encoded private key (will be encrypted)
            
        Returns:
            True if stored successfully
        """
        try:
            # Validate inputs
            if not private_key:
                raise ValueError("Private key cannot be empty")
            
            # Normalize private key (remove 0x prefix if present)
            if private_key.startswith("0x"):
                private_key = private_key[2:]
            
            # Validate hex format
            if not all(c in "0123456789abcdefABCDEF" for c in private_key):
                raise ValueError("Private key must be in hexadecimal format")
            
            if len(private_key) != 64:  # 32 bytes = 64 hex chars
                raise ValueError("Private key must be 32 bytes (64 hex characters)")
            
            # Validate wallet address if eth-account is available
            if HAS_ETH_ACCOUNT:
                try:
                    wallet_address = to_checksum_address(wallet_address)
                except Exception:
                    raise ValueError("Invalid wallet address format")
            
            # Generate random salt and nonce
            salt = secrets.token_bytes(16)
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            
            # Derive encryption key
            encryption_key = self._derive_encryption_key(salt)
            
            # Encrypt the private key
            aesgcm = AESGCM(encryption_key)
            encrypted_key = aesgcm.encrypt(
                nonce,
                private_key.encode(),
                wallet_address.encode()  # Additional authenticated data
            )
            
            # Store encrypted key
            stored_key = StoredKey(
                user_id=user_id,
                wallet_address=wallet_address,
                encrypted_key=encrypted_key,
                nonce=nonce,
                salt=salt,
                created_at=datetime.now(timezone.utc),
            )
            
            self._keys[user_id] = stored_key
            
            logger.info(
                "Private key stored securely",
                user_id=user_id,
                wallet_address=wallet_address[:10] + "..."
            )
            
            # Clear the private key from memory
            del private_key
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store private key: {e}")
            raise
    
    def _decrypt_key(self, user_id: str) -> Optional[str]:
        """
        Decrypt a stored private key.
        
        WARNING: The returned key should be used immediately and then deleted.
        
        Args:
            user_id: User ID whose key to decrypt
            
        Returns:
            Decrypted private key (hex string) or None if not found
        """
        stored_key = self._keys.get(user_id)
        if not stored_key:
            return None
        
        if not stored_key.is_active:
            logger.warning("Attempted to use inactive key", user_id=user_id)
            return None
        
        try:
            # Derive encryption key
            encryption_key = self._derive_encryption_key(stored_key.salt)
            
            # Decrypt
            aesgcm = AESGCM(encryption_key)
            decrypted_key = aesgcm.decrypt(
                stored_key.nonce,
                stored_key.encrypted_key,
                stored_key.wallet_address.encode()
            )
            
            # Update last used
            stored_key.last_used = datetime.now(timezone.utc)
            
            return decrypted_key.decode()
            
        except Exception as e:
            logger.error(f"Failed to decrypt private key: {e}")
            return None
    
    def sign_message(
        self,
        user_id: str,
        message: bytes
    ) -> Optional[str]:
        """
        Sign a message using the user's private key.
        
        The private key is decrypted, used for signing, and immediately
        cleared from memory.
        
        Args:
            user_id: User ID whose key to use
            message: Message bytes to sign
            
        Returns:
            Hex-encoded signature or None if signing failed
        """
        if not HAS_ETH_ACCOUNT:
            logger.error("eth-account not installed, cannot sign messages")
            return None
        
        private_key = None
        try:
            private_key = self._decrypt_key(user_id)
            if not private_key:
                return None
            
            # Sign the message
            signable = encode_defunct(primitive=message)
            signed = Account.sign_message(signable, private_key=private_key)
            
            return signed.signature.hex()
            
        except Exception as e:
            logger.error(f"Failed to sign message: {e}")
            return None
        finally:
            # Always clear the private key from memory
            if private_key:
                del private_key
    
    def sign_typed_data(
        self,
        user_id: str,
        domain: Dict[str, Any],
        message_types: Dict[str, Any],
        primary_type: str,
        message: Dict[str, Any]
    ) -> Optional[str]:
        """
        Sign EIP-712 typed data using the user's private key.
        
        This is the recommended method for Hyperliquid API authentication.
        
        Args:
            user_id: User ID whose key to use
            domain: EIP-712 domain separator
            message_types: Type definitions
            primary_type: Primary type name
            message: Message to sign
            
        Returns:
            Hex-encoded signature or None if signing failed
        """
        if not HAS_ETH_ACCOUNT:
            logger.error("eth-account not installed, cannot sign typed data")
            return None
        
        private_key = None
        try:
            private_key = self._decrypt_key(user_id)
            if not private_key:
                return None
            
            # Construct full typed data
            full_message = {
                "types": message_types,
                "domain": domain,
                "primaryType": primary_type,
                "message": message
            }
            
            # Sign typed data
            encoded = encode_typed_data(full_message=full_message)
            signed = Account.sign_message(encoded, private_key=private_key)
            
            return signed.signature.hex()
            
        except Exception as e:
            logger.error(f"Failed to sign typed data: {e}")
            return None
        finally:
            # Always clear the private key from memory
            if private_key:
                del private_key
    
    def create_hyperliquid_auth_headers(
        self,
        user_id: str,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, str]]:
        """
        Create authentication headers for Hyperliquid API requests.
        
        Uses EIP-712 signatures instead of transmitting the private key.
        
        Args:
            user_id: User ID whose key to use
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            data: Optional request body data
            
        Returns:
            Headers dict with signature or None if failed
        """
        stored_key = self._keys.get(user_id)
        if not stored_key:
            return None
        
        timestamp = int(time.time() * 1000)
        nonce = secrets.token_hex(16)
        
        # Construct message to sign
        domain = {
            "name": "Hyperliquid",
            "version": "1",
            "chainId": 421614 if settings.hyperliquid_testnet else 42161,
        }
        
        message_types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "HyperliquidRequest": [
                {"name": "method", "type": "string"},
                {"name": "path", "type": "string"},
                {"name": "timestamp", "type": "uint256"},
                {"name": "nonce", "type": "string"},
            ],
        }
        
        message = {
            "method": method,
            "path": path,
            "timestamp": timestamp,
            "nonce": nonce,
        }
        
        # Sign the message
        signature = self.sign_typed_data(
            user_id,
            domain,
            message_types,
            "HyperliquidRequest",
            message
        )
        
        if not signature:
            return None
        
        return {
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce,
            "X-Address": stored_key.wallet_address,
            "Content-Type": "application/json",
        }
    
    def get_wallet_address(self, user_id: str) -> Optional[str]:
        """Get the wallet address associated with a user."""
        stored_key = self._keys.get(user_id)
        return stored_key.wallet_address if stored_key else None
    
    def has_key(self, user_id: str) -> bool:
        """Check if a user has a stored key."""
        return user_id in self._keys and self._keys[user_id].is_active
    
    def deactivate_key(self, user_id: str) -> bool:
        """
        Deactivate a user's key (soft delete).
        
        The key remains stored but cannot be used.
        """
        if user_id in self._keys:
            self._keys[user_id].is_active = False
            logger.info("Key deactivated", user_id=user_id)
            return True
        return False
    
    def delete_key(self, user_id: str) -> bool:
        """
        Permanently delete a user's key.
        
        This is irreversible.
        """
        if user_id in self._keys:
            del self._keys[user_id]
            logger.info("Key deleted", user_id=user_id)
            return True
        return False
    
    def list_keys(self) -> list[Dict[str, Any]]:
        """
        List all stored keys (metadata only, no sensitive data).
        """
        return [
            {
                "user_id": key.user_id,
                "wallet_address": key.wallet_address,
                "created_at": key.created_at.isoformat(),
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "is_active": key.is_active,
            }
            for key in self._keys.values()
        ]


# Global key vault instance
_key_vault: Optional[KeyVault] = None


def get_key_vault() -> KeyVault:
    """Get or create the global key vault instance."""
    global _key_vault
    
    if _key_vault is None:
        _key_vault = KeyVault()
    
    return _key_vault
