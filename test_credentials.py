#!/usr/bin/env python3
"""
Test script to verify encrypted credentials are working properly
"""

import sys
import os

# Add src to path for imports
sys.path.append('src')

def test_credentials():
    print("=== Testing Encrypted Credentials ===")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found. Run setup_credentials.py first.")
        return False
    
    # Check if encryption key exists
    if not os.path.exists('data/secret.key'):
        print("❌ Encryption key not found. Run setup_credentials.py first.")
        return False
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test credential decryption
        from security import get_decrypted_credentials
        username, password = get_decrypted_credentials()
        
        print("✅ Environment file loaded successfully")
        print("✅ Encryption key loaded successfully")
        print("✅ Credentials decrypted successfully")
        print(f"✅ Username: {username[:3]}***")
        print(f"✅ Password: ***")
        
        # Test config loading
        from config import API_USERNAME, API_PASSWORD, API_BASE_URL, JOB_DIRECTORY
        print("✅ Configuration loaded successfully")
        print(f"✅ API URL: {API_BASE_URL}")
        print(f"✅ Job Directory: {JOB_DIRECTORY}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing credentials: {e}")
        return False

if __name__ == "__main__":
    success = test_credentials()
    if success:
        print("\n🎉 All credential tests passed! Your setup is ready.")
    else:
        print("\n💥 Credential test failed. Please check your setup.")
    sys.exit(0 if success else 1)
