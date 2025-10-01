import argparse
import time
import concurrent.futures
import requests
from colorama import init, Fore, Style
import matplotlib.pyplot as plt
import numpy as np
import os
from tqdm import tqdm

# Initialize colorama for colored terminal output
init()

def make_request(url, session, headers=None, timeout=10):
    """Make a single request and return response data"""
    start_time = time.time()
    
    try:
        response = session.get(url, headers=headers, timeout=timeout)
        end_time = time.time()
        duration = end_time - start_time
        return {
            'success': True,
            'status_code': response.status_code,
            'duration': duration,
            'response_size': len(response.content),
            'headers': dict(response.headers),
        }
    except requests.exceptions.RequestException as e:
        end_time = time.time()
        duration = end_time - start_time
        return {
            'success': False,
            'error': str(e),
            'duration': duration
        }

def run_load_test(url, requests_per_second, duration, concurrency, user_agent=None):
    """
    Run a load test against the specified URL
    
    Args:
        url: Target URL
        requests_per_second: Target RPS
        duration: Test duration in seconds
        concurrency: Number of concurrent connections
        user_agent: Optional user agent string
    """
    print(f"{Fore.CYAN}Starting load test against {url}{Style.RESET_ALL}")
    print(f"  Target RPS: {requests_per_second}")
    print(f"  Duration: {duration} seconds")
    print(f"  Concurrency: {concurrency}")
    
    # Prepare headers
    headers = {}
    if user_agent:
        headers['User-Agent'] = user_agent
    
    # Calculate total requests
    total_requests = int(requests_per_second * duration)
    
    # Prepare results storage
    results = []
    
    # Create session for connection pooling
    session = requests.Session()
    
    # Create thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        start_time = time.time()
        
        # Submit all requests to the thread pool
        future_to_request = {}
        for i in range(total_requests):
            # Calculate delay to maintain target RPS
            target_time = start_time + (i / requests_per_second)
            now = time.time()
            if now < target_time:
                time.sleep(target_time - now)
            
            # Submit request
            future = executor.submit(make_request, url, session, headers)
            future_to_request[future] = i
        
        # Process results as they complete
        with tqdm(total=total_requests, desc="Requests", unit="req") as progress:
            for future in concurrent.futures.as_completed(future_to_request):
                req_id = future_to_request[future]
                try:
                    result = future.result()
                    progress.update(1)
                    results.append(result)
                except Exception as e:
                    progress.update(1)
                    results.append({
                        'success': False,
                        'error': str(e),
                        'duration': 0
                    })
    
    end_time = time.time()
    actual_duration = end_time - start_time
    actual_rps = len(results) / actual_duration
    
    # Calculate success rates and response times
    successful_requests = [r for r in results if r['success']]
    failed_requests = [r for r in results if not r['success']]
    response_times = [r['duration'] for r in successful_requests]
    
    status_codes = {}
    for result in successful_requests:
        status_code = result.get('status_code')
        if status_code:
            status_codes[status_code] = status_codes.get(status_code, 0) + 1
    
    # Print summary results
    print(f"\n{Fore.GREEN}===== Load Test Results ====={Style.RESET_ALL}")
    print(f"Target URL: {url}")
    print(f"Test duration: {actual_duration:.2f} seconds")
    print(f"Target RPS: {requests_per_second}")
    print(f"Actual RPS: {actual_rps:.2f}")
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {len(successful_requests)} ({100 * len(successful_requests) / len(results) if results else 0:.2f}%)")
    print(f"Failed requests: {len(failed_requests)} ({100 * len(failed_requests) / len(results) if results else 0:.2f}%)")
    
    if response_times:
        print(f"\n{Fore.YELLOW}Response Time Statistics:{Style.RESET_ALL}")
        print(f"  Minimum: {min(response_times)*1000:.2f} ms")
        print(f"  Maximum: {max(response_times)*1000:.2f} ms")
        print(f"  Average: {sum(response_times)/len(response_times)*1000:.2f} ms")
        print(f"  90th percentile: {np.percentile(response_times, 90)*1000:.2f} ms")
        print(f"  95th percentile: {np.percentile(response_times, 95)*1000:.2f} ms")
        print(f"  99th percentile: {np.percentile(response_times, 99)*1000:.2f} ms")
    
    print(f"\n{Fore.YELLOW}Status Code Distribution:{Style.RESET_ALL}")
    for status_code, count in sorted(status_codes.items()):
        status_color = Fore.GREEN if status_code < 400 else (Fore.YELLOW if status_code < 500 else Fore.RED)
        print(f"  {status_color}{status_code}: {count} ({100 * count / len(successful_requests):.2f}%){Style.RESET_ALL}")
    
    if failed_requests:
        error_types = {}
        for req in failed_requests:
            error = req.get('error', 'Unknown error')
            error_types[error] = error_types.get(error, 0) + 1
        
        print(f"\n{Fore.RED}Error Types:{Style.RESET_ALL}")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count}")
    
    # Generate visualizations
    generate_charts(results, url)
    
    return results

def generate_charts(results, url):
    """Generate charts from test results"""
    # Create output directory if it doesn't exist
    os.makedirs('load_test_results', exist_ok=True)
    
    # Extract data for plotting
    successful_requests = [r for r in results if r['success']]
    
    # Skip charts if no successful requests
    if not successful_requests:
        print(f"{Fore.RED}No successful requests to generate charts{Style.RESET_ALL}")
        return
    
    response_times = [r['duration']*1000 for r in successful_requests]  # Convert to ms
    
    # Status code distribution
    status_codes = {}
    for result in successful_requests:
        status_code = result.get('status_code')
        if status_code:
            status_codes[status_code] = status_codes.get(status_code, 0) + 1
    
    # Response time histogram
    plt.figure(figsize=(10, 6))
    plt.hist(response_times, bins=50, alpha=0.75, color='blue')
    plt.title('Response Time Distribution')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join('load_test_results', 'response_time_histogram.png'))
    
    # Status code pie chart
    if status_codes:
        plt.figure(figsize=(8, 8))
        labels = [f"Status {code}" for code in status_codes.keys()]
        sizes = list(status_codes.values())
        colors = ['green' if code < 400 else ('orange' if code < 500 else 'red') for code in status_codes.keys()]
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.title('Status Code Distribution')
        plt.savefig(os.path.join('load_test_results', 'status_code_pie.png'))
    
    # Response time over time (to detect trends)
    if len(response_times) > 1:
        plt.figure(figsize=(12, 6))
        plt.plot(range(len(response_times)), response_times, '-o', markersize=2, alpha=0.5)
        plt.title('Response Time Over Test Duration')
        plt.xlabel('Request Number')
        plt.ylabel('Response Time (ms)')
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join('load_test_results', 'response_time_trend.png'))
    
    print(f"{Fore.GREEN}Charts saved to 'load_test_results' directory{Style.RESET_ALL}")

def test_rate_limit_threshold(url, max_rps=100, duration=10, concurrency=20, user_agent=None):
    """
    Test rate limiting by gradually increasing RPS until failures occur
    This helps identify the rate limiting threshold
    """
    print(f"{Fore.CYAN}Testing Rate Limit Threshold for {url}{Style.RESET_ALL}")
    
    # Store results for different RPS values
    rps_results = []
    
    # Start with 1 RPS and double until we hit failure or reach max_rps
    current_rps = 1
    max_success_rate = 100.0
    
    while current_rps <= max_rps and max_success_rate > 90.0:
        print(f"\n{Fore.YELLOW}Testing at {current_rps} RPS...{Style.RESET_ALL}")
        results = run_load_test(url, current_rps, duration, concurrency, user_agent)
        
        # Calculate success rate
        successful_requests = [r for r in results if r['success'] and r.get('status_code', 0) < 429]
        success_rate = 100 * len(successful_requests) / len(results) if results else 0
        
        rps_results.append({
            'rps': current_rps,
            'success_rate': success_rate,
            'results': results
        })
        
        max_success_rate = success_rate
        
        # Double the RPS for next iteration
        current_rps *= 2
    
    # Plot success rate vs RPS
    plt.figure(figsize=(10, 6))
    rps_values = [r['rps'] for r in rps_results]
    success_rates = [r['success_rate'] for r in rps_results]
    
    plt.plot(rps_values, success_rates, '-o', markersize=8)
    plt.title('Success Rate vs. Requests Per Second')
    plt.xlabel('Requests Per Second')
    plt.ylabel('Success Rate (%)')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join('load_test_results', 'rate_limit_threshold.png'))
    
    # Find the threshold where success rate drops below 90%
    threshold_rps = max_rps
    for i, result in enumerate(rps_results):
        if result['success_rate'] < 90:
            if i > 0:
                threshold_rps = rps_results[i-1]['rps']
            else:
                threshold_rps = result['rps'] / 2  # If the first test fails, estimate threshold as half
            break
    
    print(f"\n{Fore.GREEN}===== Rate Limit Threshold Results ====={Style.RESET_ALL}")
    print(f"Estimated rate limit threshold: ~{threshold_rps} RPS")
    print(f"Chart saved to 'load_test_results/rate_limit_threshold.png'")

def main():
    parser = argparse.ArgumentParser(description='Load Testing Tool for DDoS Protection Evaluation')
    parser.add_argument('--url', required=True, help='Target URL to test')
    parser.add_argument('--rps', type=int, default=10, help='Requests per second (default: 10)')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds (default: 30)')
    parser.add_argument('--concurrency', type=int, default=10, help='Number of concurrent connections (default: 10)')
    parser.add_argument('--user-agent', help='Custom User-Agent string')
    parser.add_argument('--find-threshold', action='store_true', help='Find rate limiting threshold')
    parser.add_argument('--max-rps', type=int, default=100, help='Maximum RPS to test when finding threshold (default: 100)')
    
    args = parser.parse_args()
    
    if args.find_threshold:
        test_rate_limit_threshold(args.url, args.max_rps, args.duration, args.concurrency, args.user_agent)
    else:
        run_load_test(args.url, args.rps, args.duration, args.concurrency, args.user_agent)

if __name__ == '__main__':
    main() 