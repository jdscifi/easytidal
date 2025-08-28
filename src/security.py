import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class CredentialManager:
    def __init__(self, key_file="data/secret.key"):
        self.key_file = key_file
        self._ensure_key_file()
        self.cipher = self._load_cipher()
    
    def _ensure_key_file(self):
        """Ensure the secret key file exists"""
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        if not os.path.exists(self.key_file):
            # Generate a new key if it doesn't exist
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            print(f"New encryption key generated and saved to {self.key_file}")
    
    def _load_cipher(self):
        """Load the encryption cipher from the key file"""
        with open(self.key_file, 'rb') as f:
            key = f.read()
        return Fernet(key)
    
    def encrypt_credential(self, credential):
        """Encrypt a credential string"""
        if isinstance(credential, str):
            credential = credential.encode()
        encrypted = self.cipher.encrypt(credential)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_credential(self, encrypted_credential):
        """Decrypt a credential string"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_credential.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt credential: {e}")
    
    def setup_credentials(self, username, password):
        """Setup and encrypt credentials for first-time use"""
        encrypted_username = self.encrypt_credential(username)
        encrypted_password = self.encrypt_credential(password)
        
        # Create .env file with encrypted credentials
        env_content = f"""# Tidal API Configuration
TIDAL_API_URL=https://your-tidal-server/api
TIDAL_USERNAME_ENCRYPTED={encrypted_username}
TIDAL_PASSWORD_ENCRYPTED={encrypted_password}
TIDAL_JOB_DIRECTORY=your-job-directory

# Cache Settings
CACHE_EXPIRY_HOURS=24
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("Credentials encrypted and saved to .env file")
        return encrypted_username, encrypted_password

def get_decrypted_credentials():
    """Get decrypted credentials from environment variables"""
    credential_manager = CredentialManager()
    
    encrypted_username = os.getenv('TIDAL_USERNAME_ENCRYPTED')
    encrypted_password = os.getenv('TIDAL_PASSWORD_ENCRYPTED')
    
    if not encrypted_username or not encrypted_password:
        raise ValueError("Encrypted credentials not found in environment variables")
    
    try:
        username = credential_manager.decrypt_credential(encrypted_username)
        password = credential_manager.decrypt_credential(encrypted_password)
        return username, password
    except Exception as e:
        raise ValueError(f"Failed to decrypt credentials: {e}")
