# Tidal Automation API configuration
import os
from dotenv import load_dotenv
from .security import get_decrypted_credentials

# Load environment variables from .env file
load_dotenv()

# Get decrypted credentials
try:
    DECRYPTED_USERNAME, DECRYPTED_PASSWORD = get_decrypted_credentials()
except Exception as e:
    print(f"Warning: Could not load encrypted credentials: {e}")
    print("Using placeholder values. Run setup_credentials.py to configure encrypted credentials.")
    DECRYPTED_USERNAME = "your-username"
    DECRYPTED_PASSWORD = "your-password"

# API Configuration
API_BASE_URL = os.getenv('TIDAL_API_URL', 'https://your-tidal-server/api')
API_USERNAME = DECRYPTED_USERNAME
API_PASSWORD = DECRYPTED_PASSWORD
JOB_DIRECTORY = os.getenv('TIDAL_JOB_DIRECTORY', 'your-job-directory')

# Cache and history settings
CACHE_FILE = "data/job_graph_cache.json"
HISTORY_FILE = "data/job_history.json"
OUTPUT_DIR = "data/job_outputs"
CACHE_EXPIRY_HOURS = int(os.getenv('CACHE_EXPIRY_HOURS', '24'))
