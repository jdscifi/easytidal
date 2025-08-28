import json
from src.main import JobHistory
from datetime import datetime

def view_job_history(job_name=None):
    """Utility script to view job history"""
    history = JobHistory("data/job_history.json")
    
    if job_name:
        print(f"History for job: {job_name}")
        job_history = history.get_job_history(job_name, limit=20)
        for entry in job_history:
            print(f"  {entry['timestamp']}: {entry['status']}")
    else:
        print("All job history:")
        all_history = history.load_history()
        for entry in all_history[-20:]:  # Show last 20 entries
            print(f"  {entry['timestamp']}: {entry['job_name']} - {entry['status']}")

if __name__ == "__main__":
    import sys
    job_name = sys.argv[1] if len(sys.argv) > 1 else None
    view_job_history(job_name)
