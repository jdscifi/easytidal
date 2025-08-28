from flask import Flask, render_template, jsonify, request
import sys
import os

# Add the parent directory to the path to import main modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Now import from the src directory
from src.main import TidalAPI, JobCache, JobHistory, build_job_graph
from src.config import API_BASE_URL, API_USERNAME, API_PASSWORD, JOB_DIRECTORY, CACHE_FILE, HISTORY_FILE, CACHE_EXPIRY_HOURS
import networkx as nx
import plotly.graph_objects as go
import plotly.utils
import json
from datetime import datetime

app = Flask(__name__)

def get_job_data():
    """Get job data from cache or API"""
    cache = JobCache(CACHE_FILE, CACHE_EXPIRY_HOURS)
    
    cached_data = None
    if cache.is_cache_valid():
        cached_data = cache.load_cache()
    
    if cached_data:
        jobs = cached_data['jobs']
        graph_data = cached_data['graph']
        G = nx.node_link_graph(graph_data)
        data_source = "cache"
    else:
        try:
            api = TidalAPI(API_BASE_URL, API_USERNAME, API_PASSWORD)
            jobs = api.get_jobs(JOB_DIRECTORY)
            G = build_job_graph(jobs, api)
            
            cache_data = {
                'jobs': jobs,
                'graph': nx.node_link_data(G),
                'timestamp': datetime.now().isoformat()
            }
            cache.save_cache(cache_data)
            data_source = "api"
        except Exception as e:
            # Re-raise the exception to be handled by the calling function
            raise Exception(f"Unable to connect to Tidal API: {str(e)}")
    
    return jobs, G, data_source

def create_plotly_graph(G, jobs):
    """Create a Plotly graph from NetworkX graph with hierarchical layout"""
    if G.number_of_nodes() == 0:
        # Return empty graph
        fig = go.Figure()
        fig.update_layout(title="No job data available")
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Create a job status lookup dictionary
    job_status_lookup = {job['name']: job for job in jobs}
    
    # Use custom hierarchical layout (always use fallback for now)
    pos = create_hierarchical_layout(G)
    
    # Create edges
    edge_x = []
    edge_y = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=3, color='#666'),
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )

    # Create nodes with status-based coloring
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_info = []
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node.replace('_', '<br>'))  # Break long names
        
        # Get job details
        job_details = job_status_lookup.get(node, {})
        status = job_details.get('status', 'unknown')
        start_time = job_details.get('start_time')
        end_time = job_details.get('end_time')
        
        # Color based on status
        if status == 'success':
            color = '#28a745'  # Green
        elif status == 'failed':
            color = '#dc3545'  # Red
        elif status == 'running':
            color = '#007bff'  # Blue
        elif status == 'pending':
            color = '#ffc107'  # Yellow
        else:
            color = '#6c757d'  # Gray
        
        node_colors.append(color)
        
        # Format datetime info
        if start_time:
            try:
                start_str = start_time.split('T')[0] + ' ' + start_time.split('T')[1][:8]
            except:
                start_str = "Invalid time"
        else:
            start_str = "Not started"
            
        if end_time:
            try:
                end_str = end_time.split('T')[0] + ' ' + end_time.split('T')[1][:8]
            except:
                end_str = "Invalid time"
        else:
            end_str = "In progress" if status == 'running' else "Not finished"
        
        # Count connections
        predecessors = list(G.predecessors(node))
        successors = list(G.neighbors(node))
        
        hover_text = f"<b>{node}</b><br>Status: {status.title()}<br>Start: {start_str}<br>End: {end_str}<br>Dependencies: {len(predecessors)}<br>Triggers: {len(successors)}"
        
        node_info.append(hover_text)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        hovertext=node_info,
        text=node_text,
        textposition="middle center",
        textfont=dict(size=9, color='white'),
        marker=dict(
            size=80,
            color=node_colors,
            line=dict(width=2, color='white'),
            opacity=0.9
        ),
        showlegend=False
    )

    # Create layout
    fig = go.Figure(data=[edge_trace, node_trace])
    
    fig.update_layout(
        title=dict(
            text='Tidal Job Dependencies Flow (Left → Right)',
            font=dict(size=18),
            x=0.5
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=40, l=40, r=40, t=60),
        annotations=[
            dict(
                text="🟢 Success  🔴 Failed  🟡 Pending  🔵 Running",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.5, y=-0.05,
                xanchor='center', yanchor='bottom',
                font=dict(color='#666', size=12)
            )
        ],
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        height=500
    )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def create_hierarchical_layout(G):
    """Create a hierarchical layout for dependency visualization"""
    # Calculate levels based on dependencies
    levels = {}
    processed = set()
    
    def assign_level(node, level=0):
        if node in processed:
            return levels.get(node, level)
        
        processed.add(node)
        predecessors = list(G.predecessors(node))
        
        if not predecessors:
            levels[node] = 0
        else:
            max_pred_level = max(assign_level(pred, level) for pred in predecessors)
            levels[node] = max_pred_level + 1
        
        return levels[node]
    
    # Assign levels to all nodes
    for node in G.nodes():
        assign_level(node)
    
    # Group nodes by level
    level_groups = {}
    for node, level in levels.items():
        if level not in level_groups:
            level_groups[level] = []
        level_groups[level].append(node)
    
    # Create positions
    pos = {}
    x_spacing = 200
    y_spacing = 100
    
    for level, nodes in level_groups.items():
        x = level * x_spacing
        num_nodes = len(nodes)
        
        for i, node in enumerate(nodes):
            y = (i - num_nodes/2 + 0.5) * y_spacing
            pos[node] = (x, y)
    
    return pos

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        jobs, G, data_source = get_job_data()
        graph_json = create_plotly_graph(G, jobs)
        
        # Get cache info
        cache = JobCache(CACHE_FILE, CACHE_EXPIRY_HOURS)
        cache_valid = cache.is_cache_valid()
        
        return render_template('index.html', 
                             jobs=jobs, 
                             graph_json=graph_json,
                             data_source=data_source,
                             cache_valid=cache_valid,
                             job_count=len(jobs),
                             edge_count=G.number_of_edges())
    except Exception as e:
        # Show error page when API connection fails
        return render_template('error.html',
                             error_message=str(e),
                             api_url=API_BASE_URL,
                             job_directory=JOB_DIRECTORY,
                             credentials_encrypted=bool(API_USERNAME and API_PASSWORD)), 503

@app.route('/api/jobs')
def api_jobs():
    """API endpoint to get jobs data"""
    try:
        jobs, G, data_source = get_job_data()
        return jsonify({
            'jobs': jobs,
            'dependencies': list(G.edges()),
            'data_source': data_source,
            'job_count': len(jobs),
            'edge_count': G.number_of_edges(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': 'API connection failed',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

@app.route('/api/history')
def api_history():
    """API endpoint to get job history"""
    job_name = request.args.get('job_name')
    limit = int(request.args.get('limit', 20))
    
    history = JobHistory(HISTORY_FILE)
    
    if job_name:
        job_history = history.get_job_history(job_name, limit)
        return jsonify({
            'job_name': job_name,
            'history': job_history
        })
    else:
        all_history = history.load_history()
        return jsonify({
            'history': all_history[-limit:]
        })

@app.route('/history')
def history_page():
    """Job history page"""
    history = JobHistory(HISTORY_FILE)
    all_history = history.load_history()
    
    # Get unique job names
    job_names = list(set([entry['job_name'] for entry in all_history]))
    
    return render_template('history.html', 
                         history=all_history[-50:],  # Show last 50 entries
                         job_names=sorted(job_names))

@app.route('/setup')
def setup_page():
    """Configuration setup page"""
    return render_template('setup.html',
                         api_url=API_BASE_URL,
                         job_directory=JOB_DIRECTORY,
                         credentials_configured=bool(API_USERNAME and API_PASSWORD))

@app.route('/api/refresh')
def api_refresh():
    """Force refresh data from API"""
    cache = JobCache(CACHE_FILE, CACHE_EXPIRY_HOURS)
    
    # Delete cache to force refresh
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    
    try:
        api = TidalAPI(API_BASE_URL, API_USERNAME, API_PASSWORD)
        jobs = api.get_jobs(JOB_DIRECTORY)
        G = build_job_graph(jobs, api)
        
        # Update job status history
        history = JobHistory(HISTORY_FILE)
        for job in jobs:
            try:
                status = api.get_job_status(job['id'])
                history.add_status_entry(job['id'], job['name'], status.get('status', 'unknown'))
            except Exception as e:
                print(f"Failed to get status for job {job['name']}: {e}")
        
        # Cache new data
        cache_data = {
            'jobs': jobs,
            'graph': nx.node_link_data(G),
            'timestamp': datetime.now().isoformat()
        }
        cache.save_cache(cache_data)
        
        return jsonify({
            'success': True,
            'message': 'Data refreshed successfully',
            'job_count': len(jobs),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to refresh data: {str(e)}'
        }), 500

@app.route('/api/job/<job_id>/output')
def get_job_output(job_id):
    """Get job output/logs for a specific job"""
    try:
        output_file = f"data/job_outputs/{job_id}_output.txt"
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'job_id': job_id,
                'output': content,
                'file_path': output_file
            })
        else:
            return jsonify({
                'job_id': job_id,
                'output': 'No output available',
                'file_path': None
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/history')
def get_job_history_api(job_id):
    """Get execution history for a specific job"""
    try:
        history = JobHistory(HISTORY_FILE)
        job_history = []
        all_history = history.load_history()
        
        for entry in all_history:
            if entry.get('job_id') == job_id:
                job_history.append(entry)
        
        return jsonify({
            'job_id': job_id,
            'history': job_history[-10:]  # Last 10 entries
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting EasyTidal Web UI...")
    print("Access the dashboard at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
