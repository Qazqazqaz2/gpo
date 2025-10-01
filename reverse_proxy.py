import argparse
import json
import logging
import os
import socket
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import http.client
import requests
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("reverse_proxy")

# Default configuration
DEFAULT_PORT = 8000
DEFAULT_ALGORITHM = "round_robin"
DEFAULT_HEALTH_CHECK_INTERVAL = 10  # seconds
DEFAULT_HEALTH_CHECK_TIMEOUT = 5  # seconds
DEFAULT_STICKY_SESSIONS = False

class ReverseProxyConfig:
    def __init__(self):
        self.port = DEFAULT_PORT
        self.backend_nodes = []
        self.algorithm = DEFAULT_ALGORITHM
        self.health_check_interval = DEFAULT_HEALTH_CHECK_INTERVAL
        self.health_check_timeout = DEFAULT_HEALTH_CHECK_TIMEOUT
        self.sticky_sessions = DEFAULT_STICKY_SESSIONS
        self.proxy_id = str(uuid.uuid4())[:8]

class ClusterState:
    def __init__(self):
        self.active_nodes = []
        self.node_stats = {}
        self.node_index = 0  # For round-robin
        self.lock = threading.Lock()

class ReverseProxyHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.config = args[2].config
        self.cluster_state = args[2].cluster_state
        super().__init__(*args[:2], **kwargs)
    
    def do_GET(self):
        self.handle_request()
    
    def do_POST(self):
        self.handle_request()
    
    def do_PUT(self):
        self.handle_request()
    
    def do_DELETE(self):
        self.handle_request()
    
    def do_HEAD(self):
        self.handle_request()
    
    def do_OPTIONS(self):
        self.handle_request()
    
    def handle_request(self):
        # Special proxy management endpoints
        if self.path == '/proxy/status':
            self.send_proxy_status()
            return
        
        # Get client IP for sticky sessions and IP hash
        client_ip = self.client_address[0]
        
        # Check for sticky session cookie
        sticky_node = None
        if self.config.sticky_sessions:
            cookies = self.headers.get('Cookie', '')
            for cookie in cookies.split(';'):
                cookie = cookie.strip()
                if cookie.startswith('SERVERID='):
                    sticky_node = cookie[9:]
                    break
        
        # Select a backend node
        backend = self.select_node(client_ip, sticky_node)
        if not backend:
            self.send_error(503, "Service Unavailable - No backend servers available")
            return
        
        # Parse the backend URL
        url = urlparse(backend)
        host = url.netloc
        
        # Get request body for POST, PUT etc.
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        # Forward the request to the backend
        try:
            # Track connection in stats
            with self.cluster_state.lock:
                if backend in self.cluster_state.node_stats:
                    self.cluster_state.node_stats[backend]["connections"] += 1
            
            # Create connection to backend
            if url.scheme == 'https':
                conn = http.client.HTTPSConnection(host, timeout=30)
            else:
                conn = http.client.HTTPConnection(host, timeout=30)
            
            # Prepare headers, removing hop-by-hop headers
            headers = dict(self.headers)
            hop_by_hop_headers = [
                'connection', 'keep-alive', 'proxy-authenticate', 
                'proxy-authorization', 'te', 'trailers', 
                'transfer-encoding', 'upgrade'
            ]
            for header in hop_by_hop_headers:
                if header in headers:
                    del headers[header]
            
            # Add proxy headers
            headers['X-Forwarded-For'] = client_ip
            headers['X-Forwarded-Host'] = self.headers.get('Host', '')
            headers['X-Forwarded-Proto'] = url.scheme
            headers['X-Proxy-ID'] = self.config.proxy_id
            
            # Send request to backend
            conn.request(
                method=self.command,
                url=self.path,
                body=body,
                headers=headers
            )
            
            # Get response from backend
            response = conn.getresponse()
            
            # Send response status and headers to client
            self.send_response(response.status, response.reason)
            
            # Add sticky session cookie if enabled
            if self.config.sticky_sessions and response.status < 400:
                backend_id = backend.replace('http://', '').replace('https://', '').replace(':', '_')
                self.send_header('Set-Cookie', f'SERVERID={backend_id}; Path=/; HttpOnly')
            
            # Copy response headers
            for header, value in response.getheaders():
                if header.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(header, value)
            
            # End headers
            self.end_headers()
            
            # Send response body
            self.wfile.write(response.read())
            
            # Close connection to backend
            conn.close()
            
            # Update stats
            with self.cluster_state.lock:
                if backend in self.cluster_state.node_stats:
                    self.cluster_state.node_stats[backend]["connections"] -= 1
                    self.cluster_state.node_stats[backend]["requests"] += 1
            
        except Exception as e:
            logger.error(f"Error forwarding request to {backend}: {e}")
            # If we haven't sent a response yet, send an error
            if not self.wfile.closed:
                self.send_error(502, f"Bad Gateway: {str(e)}")
            
            # Mark node as potentially unhealthy
            with self.cluster_state.lock:
                if backend in self.cluster_state.node_stats:
                    self.cluster_state.node_stats[backend]["errors"] = \
                        self.cluster_state.node_stats[backend].get("errors", 0) + 1
    
    def select_node(self, client_ip, sticky_node=None):
        """Select a backend node based on the configured algorithm"""
        with self.cluster_state.lock:
            if not self.cluster_state.active_nodes:
                return None
            
            # Try to use sticky node if provided
            if sticky_node:
                # Convert from cookie format back to URL
                if '_' in sticky_node:
                    host, port = sticky_node.split('_')
                    sticky_url = f"http://{host}:{port}"
                    if sticky_url in self.cluster_state.active_nodes:
                        return sticky_url
            
            # Apply load balancing algorithm
            if self.config.algorithm == "round_robin":
                # Simple round-robin
                node = self.cluster_state.active_nodes[self.cluster_state.node_index % len(self.cluster_state.active_nodes)]
                self.cluster_state.node_index += 1
                return node
            
            elif self.config.algorithm == "least_connections":
                # Select node with fewest active connections
                return min(
                    self.cluster_state.active_nodes, 
                    key=lambda node: self.cluster_state.node_stats[node]["connections"]
                )
            
            elif self.config.algorithm == "ip_hash":
                # Consistent hashing based on client IP
                hash_value = sum(ord(c) for c in client_ip)
                return self.cluster_state.active_nodes[hash_value % len(self.cluster_state.active_nodes)]
            
            else:
                # Default to round-robin
                node = self.cluster_state.active_nodes[self.cluster_state.node_index % len(self.cluster_state.active_nodes)]
                self.cluster_state.node_index += 1
                return node
    
    def send_proxy_status(self):
        """Send proxy status information"""
        status = {
            "proxy_id": self.config.proxy_id,
            "active_nodes": self.cluster_state.active_nodes,
            "node_stats": self.cluster_state.node_stats,
            "algorithm": self.config.algorithm,
            "sticky_sessions": self.config.sticky_sessions,
            "uptime": time.time() - self.server.start_time
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())

class ReverseProxyServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, config, cluster_state):
        self.config = config
        self.cluster_state = cluster_state
        self.start_time = time.time()
        super().__init__(server_address, RequestHandlerClass)

def health_check(node, timeout):
    """Check if a node is healthy"""
    try:
        response = requests.get(f"{node}/health", timeout=timeout)
        return response.status_code == 200, response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.warning(f"Health check failed for {node}: {e}")
        return False, None

def update_cluster_state(config, cluster_state):
    """Update the list of active nodes in the cluster"""
    healthy_nodes = []
    
    for node in config.backend_nodes:
        is_healthy, node_data = health_check(node, config.health_check_timeout)
        
        if is_healthy:
            healthy_nodes.append(node)
            
            # Initialize or update node stats
            with cluster_state.lock:
                if node not in cluster_state.node_stats:
                    cluster_state.node_stats[node] = {
                        "connections": 0,
                        "requests": 0,
                        "errors": 0
                    }
                
                # Update with data from node if available
                if node_data:
                    cluster_state.node_stats[node]["server_id"] = node_data.get("server_id", "unknown")
                    cluster_state.node_stats[node]["threads"] = node_data.get("threads", 0)
    
    with cluster_state.lock:
        old_count = len(cluster_state.active_nodes)
        cluster_state.active_nodes = healthy_nodes
        new_count = len(cluster_state.active_nodes)
    
    if old_count != new_count:
        logger.info(f"Cluster state updated: {new_count} active nodes (was {old_count})")

def cluster_health_monitor(config, cluster_state):
    """Background thread to monitor cluster health"""
    while True:
        try:
            update_cluster_state(config, cluster_state)
        except Exception as e:
            logger.error(f"Error updating cluster state: {e}")
        
        time.sleep(config.health_check_interval)

def run_proxy_server(config):
    """Run the reverse proxy server"""
    # Initialize cluster state
    cluster_state = ClusterState()
    
    # Initial cluster state update
    update_cluster_state(config, cluster_state)
    
    # Start health monitoring thread
    monitor_thread = threading.Thread(
        target=cluster_health_monitor, 
        args=(config, cluster_state),
        daemon=True
    )
    monitor_thread.start()
    
    # Create and run the server
    server = ReverseProxyServer(
        ('0.0.0.0', config.port),
        ReverseProxyHandler,
        config,
        cluster_state
    )
    
    logger.info(f"Starting reverse proxy on port {config.port}")
    logger.info(f"Load balancing algorithm: {config.algorithm}")
    logger.info(f"Backend nodes: {config.backend_nodes}")
    logger.info(f"Sticky sessions: {'enabled' if config.sticky_sessions else 'disabled'}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server...")
        server.server_close()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Reverse Proxy Load Balancer')
    
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f'Port to run the proxy server on (default: {DEFAULT_PORT})')
    
    parser.add_argument('-b', '--backends', type=str, required=True,
                        help='Comma-separated list of backend servers (e.g., http://localhost:5000,http://localhost:5001)')
    
    parser.add_argument('-a', '--algorithm', type=str, default=DEFAULT_ALGORITHM,
                        choices=['round_robin', 'least_connections', 'ip_hash'],
                        help=f'Load balancing algorithm (default: {DEFAULT_ALGORITHM})')
    
    parser.add_argument('-i', '--health-interval', type=int, default=DEFAULT_HEALTH_CHECK_INTERVAL,
                        help=f'Health check interval in seconds (default: {DEFAULT_HEALTH_CHECK_INTERVAL})')
    
    parser.add_argument('-t', '--health-timeout', type=int, default=DEFAULT_HEALTH_CHECK_TIMEOUT,
                        help=f'Health check timeout in seconds (default: {DEFAULT_HEALTH_CHECK_TIMEOUT})')
    
    parser.add_argument('-s', '--sticky-sessions', action='store_true',
                        help='Enable sticky sessions (default: disabled)')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    # Create configuration
    config = ReverseProxyConfig()
    config.port = args.port
    config.backend_nodes = args.backends.split(',')
    config.algorithm = args.algorithm
    config.health_check_interval = args.health_interval
    config.health_check_timeout = args.health_timeout
    config.sticky_sessions = args.sticky_sessions
    
    # Run the proxy server
    run_proxy_server(config)

if __name__ == "__main__":
    main() 