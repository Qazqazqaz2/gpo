from app import app
import os
import waitress
from paste.translogger import TransLogger
import logging
from ddos_protection import DDoSConfig
import socket
import json
import threading
import time
import requests
from flask import request, jsonify, g
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("server")

# Get port from environment or use default
PORT = int(os.environ.get("PORT", 5000))

# Server thread counts - adjust based on your server capacity
THREADS = min(8, os.cpu_count() or 4)  # Conservative default

# More aggressive DDoS protection settings for production
DDoSConfig.RATE_LIMIT = 120  # Max requests per minute per IP
DDoSConfig.MAX_CONNECTIONS_PER_IP = 15  # Max concurrent connections per IP
DDoSConfig.CONNECTION_TIMEOUT = 20  # Shorter timeout in production
DDoSConfig.BLACKLIST_THRESHOLD = 3  # Quicker blacklisting
DDoSConfig.BLACKLIST_DURATION = 3600 * 2  # 2 hours blacklist duration

# Cluster configuration
CLUSTER_MODE = os.environ.get("CLUSTER_MODE", "false").lower() == "true"
SERVER_ID = os.environ.get("SERVER_ID", str(uuid.uuid4())[:8])  # Unique server identifier
CLUSTER_NODES = json.loads(os.environ.get("CLUSTER_NODES", "[]"))  # List of node addresses
HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALTH_CHECK_INTERVAL", 30))  # Seconds
HEALTH_CHECK_TIMEOUT = int(os.environ.get("HEALTH_CHECK_TIMEOUT", 5))  # Seconds
LOAD_BALANCING_ALGORITHM = os.environ.get("LOAD_BALANCING_ALGORITHM", "round_robin")  # round_robin, least_connections, ip_hash

# Runtime cluster state
active_nodes = []
node_stats = {}
node_index = 0  # For round-robin
node_lock = threading.Lock()

def get_local_ip():
    """Get the local IP address of this server"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        logger.warning(f"Could not determine local IP: {e}")
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
LOCAL_NODE = f"http://{LOCAL_IP}:{PORT}"

# Add self to cluster if not already included
if CLUSTER_MODE and LOCAL_NODE not in CLUSTER_NODES:
    CLUSTER_NODES.append(LOCAL_NODE)

def health_check(node):
    """Check if a node is healthy"""
    try:
        response = requests.get(f"{node}/health", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except Exception:
        return False

def update_cluster_state():
    """Update the list of active nodes in the cluster"""
    global active_nodes
    
    if not CLUSTER_MODE:
        active_nodes = [LOCAL_NODE]
        return
    
    healthy_nodes = []
    for node in CLUSTER_NODES:
        if node == LOCAL_NODE or health_check(node):
            healthy_nodes.append(node)
            if node not in node_stats:
                node_stats[node] = {"connections": 0, "requests": 0}
    
    with node_lock:
        active_nodes = healthy_nodes
    
    logger.info(f"Cluster state updated: {len(active_nodes)} active nodes")

def cluster_health_monitor():
    """Background thread to monitor cluster health"""
    while True:
        try:
            update_cluster_state()
        except Exception as e:
            logger.error(f"Error updating cluster state: {e}")
        
        time.sleep(HEALTH_CHECK_INTERVAL)

def select_node(client_ip):
    """Select a node based on the configured load balancing algorithm"""
    global node_index
    
    if not CLUSTER_MODE or not active_nodes:
        return None  # Handle locally
    
    with node_lock:
        if LOAD_BALANCING_ALGORITHM == "round_robin":
            # Simple round-robin
            node = active_nodes[node_index % len(active_nodes)]
            node_index += 1
            return node
        
        elif LOAD_BALANCING_ALGORITHM == "least_connections":
            # Select node with fewest active connections
            return min(active_nodes, key=lambda node: node_stats[node]["connections"])
        
        elif LOAD_BALANCING_ALGORITHM == "ip_hash":
            # Consistent hashing based on client IP
            hash_value = sum(ord(c) for c in client_ip)
            return active_nodes[hash_value % len(active_nodes)]
        
        else:
            # Default to round-robin
            node = active_nodes[node_index % len(active_nodes)]
            node_index += 1
            return node

# Add health check endpoint to the Flask app
@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "server_id": SERVER_ID,
        "connections": sum(1 for _ in waitress.wasyncore.socket_map.values() if hasattr(_, "addr")),
        "threads": THREADS
    })

# Add cluster stats endpoint
@app.route('/cluster/stats')
def cluster_stats():
    return jsonify({
        "server_id": SERVER_ID,
        "active_nodes": active_nodes,
        "stats": node_stats,
        "algorithm": LOAD_BALANCING_ALGORITHM
    })

# Middleware to track request metrics
@app.before_request
def track_request_start():
    g.request_start_time = time.time()
    g.node = LOCAL_NODE
    
    if CLUSTER_MODE:
        with node_lock:
            if g.node in node_stats:
                node_stats[g.node]["connections"] += 1

@app.after_request
def track_request_end(response):
    if hasattr(g, 'request_start_time'):
        request_duration = time.time() - g.request_start_time
        
        if CLUSTER_MODE and hasattr(g, 'node'):
            with node_lock:
                if g.node in node_stats:
                    node_stats[g.node]["connections"] -= 1
                    node_stats[g.node]["requests"] += 1
        
        # Add server ID to response headers for debugging
        response.headers['X-Server-ID'] = SERVER_ID
    
    return response

# Log application startup
logger.info(f"Starting server {SERVER_ID} on port {PORT} with {THREADS} threads")
logger.info(f"Rate limit: {DDoSConfig.RATE_LIMIT} requests/minute/IP")
logger.info(f"Max connections: {DDoSConfig.MAX_CONNECTIONS_PER_IP} per IP")

if CLUSTER_MODE:
    logger.info(f"Cluster mode enabled with {len(CLUSTER_NODES)} configured nodes")
    logger.info(f"Load balancing algorithm: {LOAD_BALANCING_ALGORITHM}")
    # Start cluster health monitoring in background
    monitor_thread = threading.Thread(target=cluster_health_monitor, daemon=True)
    monitor_thread.start()

if __name__ == "__main__":
    # Initialize cluster state
    if CLUSTER_MODE:
        update_cluster_state()
    
    # Wrap app in TransLogger for WSGI request logging
    app_with_logging = TransLogger(app, setup_console_handler=False)
    
    # Start production server
    try:
        # waitress is a production WSGI server that works well on Windows
        waitress.serve(
            app_with_logging,
            host='0.0.0.0',
            port=PORT,
            threads=THREADS,
            connection_limit=500,         # Total connection limit
            channel_timeout=30,           # Timeout for request channels 
            ident=f'Flask-Cluster-{SERVER_ID}', # Server identification
            clear_untrusted_proxy_headers=True,  # Security: don't trust external headers
            max_request_header_size=8192, # Limit header size to prevent memory exhaustion
            max_request_body_size=10*1024*1024, # 10MB max request body
            url_scheme='http'
        )
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise 