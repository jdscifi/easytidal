# EasyTidal

A Python project to monitor jobs in a Tidal Automation job directory using the REST API and visualize job dependencies and triggers.

## Features
- Connects to Tidal Automation REST API
- Fetches job data from a specified job directory
- Tracks which job triggers which
- Visualizes job flow using a graph
- **Caches job graph data to avoid repeated API calls**
- **Maintains history of job status changes**
- **Web UI for interactive visualization and monitoring**
- **Stores and displays job execution output and logs**
- **Encrypted credential management for security**

## Setup
1. Install Python 3.8+
2. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
 4. **Configure encrypted credentials**:
   ```powershell
   python setup_credentials.py
   ```
   This will securely encrypt and store your Tidal API credentials.

5. Test your credential setup:
   ```powershell
   python test_credentials.py
   ```

## Usage

### Web UI (Recommended)
- Configure API credentials and job directory in `config.py`
- Start the web server:
   ```powershell
   python app.py
   ```
- Open your browser to: `http://localhost:5000`

### Command Line
- Run the main script:
   ```powershell
   python src/main.py
   ```
- View job history:
   ```powershell
   python view_history.py [job_name]
   ```

## Web Interface Features
- **Dashboard**: Interactive job flow graph with Plotly
- **Real-time Metrics**: Job count, dependencies, cache status
- **Job List**: Status indicators for all jobs
- **History Page**: Filterable job status history
- **Auto-refresh**: Updates every 5 minutes
- **Manual Refresh**: Force data refresh from API

## Caching
- Job graph data is cached in `data/job_graph_cache.json`
- Cache expires after 24 hours (configurable in `config.py`)
- Delete cache file to force fresh data fetch

## Job History
- Job status history is stored in `data/job_history.json`
- Tracks timestamp, job name, and status for each check
- Keeps last 1000 entries to manage file size

## Job Output Storage
- **Automatic Collection**: Job outputs are automatically captured for completed and failed jobs
- **File Storage**: Output files stored in `data/job_outputs/` directory
- **Content**: Each file contains job status, execution times, output logs, and error messages
- **API Access**: Retrieve output via `/api/job/{id}/output` endpoint
- **Web UI**: Click "View Output" buttons in job lists to see execution logs in a modal dialog

## API Endpoints
- `GET /` - Main dashboard
- `GET /history` - Job history page
- `GET /api/jobs` - JSON API for job data
- `GET /api/history?job_name=&limit=` - JSON API for history
- `GET /api/refresh` - Force refresh from Tidal API
- `GET /api/job/{id}/output` - Get job execution output and logs
- `GET /api/jobs/{id}/history` - Get execution history for specific job

## Visualization
- Interactive web-based graph using Plotly
- Hover over nodes to see job details
- Visual indicators for job status and dependencies

## Security Features
- **Encrypted Credentials**: Username and password are encrypted using Fernet symmetric encryption
- **Environment Variables**: Credentials loaded from `.env` file (not committed to version control)
- **Secure Key Management**: Encryption key stored separately from credentials
- **No Hardcoded Secrets**: All sensitive data encrypted at rest

## Credential Management
- **Setup**: Run `python setup_credentials.py` to encrypt and store credentials
- **Test**: Run `python test_credentials.py` to verify credential setup
- **Key Storage**: Encryption key stored in `data/secret.key` (keep secure!)
- **Config File**: Encrypted credentials stored in `.env` file
