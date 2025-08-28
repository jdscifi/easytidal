#!/usr/bin/env python3
"""
Credential Setup Script for EasyTidal

This script helps you securely store your Tidal API credentials in an encrypted format.
Your credentials will be encrypted using Fernet symmetric encryption and stored in a .env file.
"""

import getpass
import sys
import os

# Add src to path for imports
sys.path.append('src')
from security import CredentialManager

def main():
    print("=== EasyTidal Credential Setup ===")
    print("This script will encrypt and store your Tidal API credentials securely.")
    print()
    
    # Get credentials from user
    api_url = input("Enter your Tidal API URL (e.g., https://your-tidal-server/api): ").strip()
    if not api_url:
        api_url = "https://your-tidal-server/api"
    
    username = input("Enter your Tidal username: ").strip()
    if not username:
        print("Username cannot be empty!")
        return
    
    password = getpass.getpass("Enter your Tidal password: ").strip()
    if not password:
        print("Password cannot be empty!")
        return
    
    job_directory = input("Enter your job directory name: ").strip()
    if not job_directory:
        job_directory = "your-job-directory"
    
    print("\nEncrypting credentials...")
    
    try:
        # Create credential manager and encrypt credentials
        credential_manager = CredentialManager()
        encrypted_username = credential_manager.encrypt_credential(username)
        encrypted_password = credential_manager.encrypt_credential(password)
        
        # Create .env file
        env_content = f"""# Tidal API Configuration
TIDAL_API_URL={api_url}
TIDAL_USERNAME_ENCRYPTED={encrypted_username}
TIDAL_PASSWORD_ENCRYPTED={encrypted_password}
TIDAL_JOB_DIRECTORY={job_directory}

# Cache Settings
CACHE_EXPIRY_HOURS=24
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Credentials successfully encrypted and saved!")
        print(f"✅ Encryption key saved to: data/secret.key")
        print(f"✅ Configuration saved to: .env")
        print()
        print("⚠️  IMPORTANT SECURITY NOTES:")
        print("   - Keep the 'data/secret.key' file secure and private")
        print("   - Do not commit 'data/secret.key' or '.env' to version control")
        print("   - Back up your encryption key in a secure location")
        print()
        print("Your credentials are now ready to use with EasyTidal!")
        
    except Exception as e:
        print(f"❌ Error setting up credentials: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
