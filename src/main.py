import requests
from .config import API_BASE_URL, API_USERNAME, API_PASSWORD, JOB_DIRECTORY, CACHE_FILE, HISTORY_FILE, CACHE_EXPIRY_HOURS
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
from datetime import datetime, timedelta

class TidalAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        # Set timeout to prevent hanging
        self.session.timeout = 30

    def get_jobs(self, job_directory):
        """Fetch jobs from a specific directory using Tidal API"""
        url = f"{self.base_url}/api/jobs"
        params = {'directory': job_directory} if job_directory else {}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Adapt response to expected format
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'jobs' in data:
                return data['jobs']
            else:
                raise ValueError("Unexpected API response format")
                
        except requests.exceptions.ConnectionError:
            raise Exception("Unable to connect to Tidal server. Check network connectivity and server address.")
        except requests.exceptions.Timeout:
            raise Exception("Connection to Tidal server timed out. Server may be unresponsive.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Authentication failed. Check username and password.")
            elif e.response.status_code == 403:
                raise Exception("Access denied. Check user permissions.")
            elif e.response.status_code == 404:
                raise Exception("API endpoint not found. Check API base URL.")
            else:
                raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_job_triggers(self, job_id):
        """Fetch job triggers for a specific job"""
        url = f"{self.base_url}/api/jobs/{job_id}/dependencies"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get job triggers for {job_id}: {str(e)}")

    def get_job_status(self, job_id):
        """Fetch current status of a specific job"""
        url = f"{self.base_url}/api/jobs/{job_id}/status"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get job status for {job_id}: {str(e)}")

    def get_job_output(self, job_id):
        """Fetch job execution output/logs"""
        url = f"{self.base_url}/api/jobs/{job_id}/output"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('output', '') if isinstance(data, dict) else str(data)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get job output for {job_id}: {str(e)}")

    def get_job_log(self, job_id, log_type="stdout"):
        """Fetch specific job log (stdout, stderr, etc.)"""
        url = f"{self.base_url}/api/jobs/{job_id}/logs/{log_type}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get job log for {job_id}: {str(e)}")

class JobCache:
    def __init__(self, cache_file, expiry_hours):
        self.cache_file = cache_file
        self.expiry_hours = expiry_hours
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        cache_dir = os.path.dirname(self.cache_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def is_cache_valid(self):
        """Check if cache exists and is not expired"""
        if not os.path.exists(self.cache_file):
            return False
        
        cache_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
        expiry_time = cache_time + timedelta(hours=self.expiry_hours)
        return datetime.now() < expiry_time

    def save_cache(self, data):
        """Save data to cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_cache(self):
        """Load data from cache"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return None

class JobHistory:
    def __init__(self, history_file):
        self.history_file = history_file
        self._ensure_history_dir()

    def _ensure_history_dir(self):
        """Ensure history directory exists"""
        history_dir = os.path.dirname(self.history_file)
        if history_dir and not os.path.exists(history_dir):
            os.makedirs(history_dir)

    def add_status_entry(self, job_id, job_name, status, output=None, error_log=None):
        """Add a status entry to job history with optional output"""
        timestamp = datetime.now().isoformat()
        entry = {
            'timestamp': timestamp,
            'job_id': job_id,
            'job_name': job_name,
            'status': status,
            'output': output,
            'error_log': error_log
        }
        
        history = self.load_history()
        history.append(entry)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(history) > 1000:
            history = history[-1000:]
        
        self.save_history(history)

    def load_history(self):
        """Load job history from file"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return []

    def save_history(self, history):
        """Save job history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def get_job_history(self, job_name, limit=10):
        """Get recent history for a specific job"""
        history = self.load_history()
        job_history = [entry for entry in history if entry['job_name'] == job_name]
        return job_history[-limit:] if job_history else []

def build_job_graph(jobs, api):
    """Build a directed graph of job dependencies"""
    G = nx.DiGraph()
    for job in jobs:
        job_id = job['id']
        job_name = job['name']
        G.add_node(job_name)
        triggers = api.get_job_triggers(job_id)
        for trg in triggers:
            trg_name = trg['triggered_job_name']
            G.add_edge(job_name, trg_name)
    return G

def visualize_graph(G):
    plt.figure(figsize=(12,8))
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray', arrows=True)
    plt.title('Tidal Job Trigger Flow')
    plt.show()

def main():
    # Initialize cache and history
    cache = JobCache(CACHE_FILE, CACHE_EXPIRY_HOURS)
    history = JobHistory(HISTORY_FILE)
    
    # Try to load from cache first
    cached_data = None
    if cache.is_cache_valid():
        cached_data = cache.load_cache()
        print("Loading job graph from cache...")
    
    if cached_data:
        # Use cached data
        jobs = cached_data['jobs']
        graph_data = cached_data['graph']
        G = nx.node_link_graph(graph_data)
    else:
        # Fetch fresh data from API
        print("Fetching fresh data from Tidal API...")
        api = TidalAPI(API_BASE_URL, API_USERNAME, API_PASSWORD)
        jobs = api.get_jobs(JOB_DIRECTORY)
        G = build_job_graph(jobs, api)
        
        # Cache the data
        cache_data = {
            'jobs': jobs,
            'graph': nx.node_link_data(G),
            'timestamp': datetime.now().isoformat()
        }
        cache.save_cache(cache_data)
        print("Data cached for future use.")
    
    # Update job status history
    api = TidalAPI(API_BASE_URL, API_USERNAME, API_PASSWORD)
    for job in jobs:
        try:
            status = api.get_job_status(job['id'])
            history.add_status_entry(job['id'], job['name'], status.get('status', 'unknown'))
        except Exception as e:
            print(f"Failed to get status for job {job['name']}: {e}")
    
    # Visualize the graph
    visualize_graph(G)
    
    # Show recent history for first job as example
    if jobs:
        sample_job = jobs[0]['name']
        recent_history = history.get_job_history(sample_job, limit=5)
        print(f"\nRecent history for job '{sample_job}':")
        for entry in recent_history:
            print(f"  {entry['timestamp']}: {entry['status']}")

if __name__ == "__main__":
    main()
