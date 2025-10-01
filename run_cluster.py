#!/usr/bin/env python
import argparse
import json
import os
import subprocess
import sys
import time
import signal
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cluster.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cluster_manager")

# Default configuration
DEFAULT_BASE_PORT = 5000
DEFAULT_NODE_COUNT = 2
DEFAULT_PROXY_PORT = 8000
DEFAULT_ALGORITHM = "round_robin"

# Global process tracking
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully shut down all processes"""
    logger.info("Shutting down cluster...")
    for p in processes:
        try:
            if p.poll() is None:  # If process is still running
                p.terminate()
                logger.info(f"Terminated process PID {p.pid}")
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
    
    logger.info("All processes terminated. Exiting.")
    sys.exit(0)

def start_server(port, server_id, cluster_nodes):
    """Start a server instance"""
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["SERVER_ID"] = server_id
    env["CLUSTER_MODE"] = "true"
    env["CLUSTER_NODES"] = json.dumps(cluster_nodes)
    
    logger.info(f"Starting server {server_id} on port {port}")
    
    # Start the server process
    process = subprocess.Popen(
        [sys.executable, "run_server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    processes.append(process)
    return process

def start_proxy(proxy_port, backend_nodes, algorithm, sticky_sessions=False):
    """Start the reverse proxy"""
    backends_str = ",".join(backend_nodes)
    
    cmd = [
        sys.executable, "reverse_proxy.py",
        "--port", str(proxy_port),
        "--backends", backends_str,
        "--algorithm", algorithm
    ]
    
    if sticky_sessions:
        cmd.append("--sticky-sessions")
    
    logger.info(f"Starting reverse proxy on port {proxy_port}")
    logger.info(f"Backend nodes: {backends_str}")
    logger.info(f"Algorithm: {algorithm}")
    
    # Start the proxy process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    processes.append(process)
    return process

def wait_for_server(url, max_retries=10, retry_delay=1):
    """Wait for a server to become available"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                logger.info(f"Server at {url} is ready")
                return True
        except Exception:
            pass
        
        time.sleep(retry_delay)
    
    logger.warning(f"Server at {url} did not become ready in time")
    return False

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Cluster Manager')
    
    parser.add_argument('-n', '--nodes', type=int, default=DEFAULT_NODE_COUNT,
                        help=f'Number of server nodes to start (default: {DEFAULT_NODE_COUNT})')
    
    parser.add_argument('-b', '--base-port', type=int, default=DEFAULT_BASE_PORT,
                        help=f'Base port for server nodes (default: {DEFAULT_BASE_PORT})')
    
    parser.add_argument('-p', '--proxy-port', type=int, default=DEFAULT_PROXY_PORT,
                        help=f'Port for the reverse proxy (default: {DEFAULT_PROXY_PORT})')
    
    parser.add_argument('-a', '--algorithm', type=str, default=DEFAULT_ALGORITHM,
                        choices=['round_robin', 'least_connections', 'ip_hash'],
                        help=f'Load balancing algorithm (default: {DEFAULT_ALGORITHM})')
    
    parser.add_argument('-s', '--sticky-sessions', action='store_true',
                        help='Enable sticky sessions (default: disabled)')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse command line arguments
    args = parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Generate list of nodes
    backend_nodes = []
    for i in range(args.nodes):
        port = args.base_port + i
        backend_nodes.append(f"http://localhost:{port}")
    
    # Start server nodes
    for i in range(args.nodes):
        port = args.base_port + i
        server_id = f"server-{i+1}"
        start_server(port, server_id, backend_nodes)
    
    # Wait for servers to start
    logger.info("Waiting for servers to start...")
    for node in backend_nodes:
        wait_for_server(node)
    
    # Start reverse proxy
    start_proxy(args.proxy_port, backend_nodes, args.algorithm, args.sticky_sessions)
    
    logger.info(f"Cluster is running. Access via http://localhost:{args.proxy_port}")
    logger.info("Press Ctrl+C to shut down the cluster")
    
    # Keep the script running until Ctrl+C
    try:
        while True:
            # Check if any process has terminated unexpectedly
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    exit_code = p.poll()
                    stdout, stderr = p.communicate()
                    logger.error(f"Process {i} terminated with exit code {exit_code}")
                    if stdout:
                        logger.error(f"Stdout: {stdout}")
                    if stderr:
                        logger.error(f"Stderr: {stderr}")
            
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main() 