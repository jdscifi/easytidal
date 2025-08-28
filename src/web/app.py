from flask import Flask, render_template, jsonify, request
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import TidalAPI, JobCache, JobHistory, build_job_graph
from config import API_BASE_URL, API_USERNAME, API_PASSWORD, JOB_DIRECTORY, CACHE_FILE, HISTORY_FILE, CACHE_EXPIRY_HOURS
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
            # Return sample data if API fails
            jobs = [
                {'id': '1', 'name': 'Job_A', 'status': 'success'},
                {'id': '2', 'name': 'Job_B', 'status': 'running'},
                {'id': '3', 'name': 'Job_C', 'status': 'pending'}
            ]
            G = nx.DiGraph()
            G.add_edge('Job_A', 'Job_B')
            G.add_edge('Job_B', 'Job_C')
            data_source = "sample"
    
    return jobs, G, data_source

def create_plotly_graph(G):
    """Create a Plotly graph from NetworkX graph"""
    pos = nx.spring_layout(G, seed=42)
    
    # Create edges
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(x=edge_x, y=edge_y,
                           line=dict(width=2, color='#888'),
                           hoverinfo='none',
                           mode='lines')

    # Create nodes
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(x=node_x, y=node_y,
                           mode='markers+text',
                           hoverinfo='text',
                           text=node_text,
                           textposition="middle center",
                           marker=dict(showscale=True,
                                     colorscale='YlGnBu',
                                     reversescale=True,
                                     color=[],
                                     size=30,
                                     colorbar=dict(
                                         thickness=15,
                                         title="Node Connections",
                                         xanchor="left",
                                         titleside="right"
                                     ),
                                     line=dict(width=2, color='black')))

    # Color nodes by number of connections
    node_adjacencies = []
    for node in G.nodes():
        adjacencies = list(G.neighbors(node))
        node_adjacencies.append(len(adjacencies))

    node_trace.marker.color = node_adjacencies

    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                        title='Tidal Job Flow Graph',
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Job dependencies and triggers",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            xanchor='left', yanchor='bottom',
                            font=dict(color='#888', size=12)
                        )],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route('/')
def index():
    """Main dashboard page"""
    jobs, G, data_source = get_job_data()
    graph_json = create_plotly_graph(G)
    
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

@app.route('/api/jobs')
def api_jobs():
    """API endpoint to get jobs data"""
    jobs, G, data_source = get_job_data()
    return jsonify({
        'jobs': jobs,
        'edges': list(G.edges()),
        'data_source': data_source,
        'job_count': len(jobs),
        'edge_count': G.number_of_edges()
    })

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
