import time
import threading
import logging
import os
import platform
from functools import wraps
from collections import defaultdict, deque
from flask import request, abort, g
import redis
import ipaddress
try:
    import geoip2.database
except ImportError:
    pass  # Will handle this gracefully later
try:
    from user_agents import parse
except ImportError:
    pass  # Will handle this gracefully later

# Determine if running on Windows
IS_WINDOWS = platform.system() == 'Windows'

# Configure logging with Windows-friendly paths
log_file = os.path.join(os.getcwd(), "ddos_protection.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger("ddos_protection")

# Initialize Redis connection for rate limiting and distributed tracking
# Windows-compatible Redis connection
try:
    # Default Redis configuration
    redis_host = 'localhost'
    redis_port = 6379
    
    # Connect to Redis with a timeout suitable for Windows
    redis_client = redis.Redis(
        host=redis_host, 
        port=redis_port, 
        db=0,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()  # Test connection
    REDIS_AVAILABLE = True
    logger.info(f"Successfully connected to Redis at {redis_host}:{redis_port}")
except Exception as e:
    logger.warning(f"Redis not available: {e}. Falling back to in-memory storage (not suitable for multiple workers)")
    REDIS_AVAILABLE = False

# In-memory fallback storage
IP_REQUEST_COUNTS = defaultdict(int)  # For rate limiting
IP_CONNECTIONS = defaultdict(int)     # For connection limiting
LAST_CLEANUP = time.time()
BLACKLISTED_IPS = set()
ANOMALY_TRACKING = defaultdict(list)  # For anomaly detection

# Configuration
class DDoSConfig:
    # Rate limiting
    RATE_LIMIT = 100  # Max requests per minute per IP
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Connection limiting (Slowloris protection)
    MAX_CONNECTIONS_PER_IP = 20
    CONNECTION_TIMEOUT = 30  # seconds
    
    # SYN flood protection parameters (Windows-compatible)
    SYN_BACKLOG = 1024
    SYN_COOKIES = True
    
    # General settings
    CLEANUP_INTERVAL = 60  # seconds
    
    # Blacklisting
    BLACKLIST_THRESHOLD = 5  # violations before blacklisting
    BLACKLIST_DURATION = 3600  # seconds (1 hour)
    
    # Whitelisted IPs (e.g., your own servers, trusted services)
    WHITELISTED_IPS = set([
        '127.0.0.1',  # localhost
        '::1',        # IPv6 localhost
        # Add your trusted IPs here
    ])
    
    # Geo-filtering - list of allowed/blocked country codes
    GEO_BLOCKING_ENABLED = False
    # Use absolute path for Windows compatibility
    GEO_DATABASE_PATH = os.path.join(os.getcwd(), "GeoLite2-Country.mmdb")
    BLOCKED_COUNTRIES = []  # e.g., ['CN', 'RU'] to block specific countries
    ALLOWED_COUNTRIES = []  # If set, only these countries are allowed
    
    # Anomaly detection
    ANOMALY_DETECTION_ENABLED = True
    ANOMALY_WINDOW = 300  # 5 minutes
    ANOMALY_THRESHOLD = 0.8  # 80% deviation from baseline

# Clean up expired data periodically
def cleanup_expired_data():
    global LAST_CLEANUP, IP_REQUEST_COUNTS, IP_CONNECTIONS
    
    current_time = time.time()
    if current_time - LAST_CLEANUP > DDoSConfig.CLEANUP_INTERVAL:
        # Reset counters
        IP_REQUEST_COUNTS = defaultdict(int)
        # Don't reset connections, they should be tracked continuously
        
        # Update cleanup time
        LAST_CLEANUP = current_time
        
        logger.debug("Cleaned up expired rate limiting data")

# SYN Flood Protection - Windows compatible version
def configure_syn_cookies(app):
    """
    Configure SYN cookies to mitigate SYN flood attacks
    This provides guidance for both Linux and Windows environments
    """
    if IS_WINDOWS:
        logger.info("Windows SYN Flood protection recommendations:")
        logger.info("1. Ensure Windows Defender Firewall is enabled")
        logger.info("2. Consider using a hardware firewall or Windows native TCP/IP hardening")
        logger.info("3. For IIS server, configure connection limits in applicationHost.config")
        logger.info("Windows registry settings that may help:")
        logger.info("   - Set TcpMaxDataRetransmissions to a lower value (e.g., 3)")
        logger.info("   - Configure SynAttackProtect in HKLM\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters")
        
        # For Windows web servers
        if app.config.get('SERVER_NAME') and 'iis' in app.config.get('SERVER_NAME').lower():
            logger.info("For IIS, consider setting maxConnections and connectionTimeout in web.config")
    else:
        # Linux advice
        logger.info("SYN Cookies protection should be configured at the OS/server level")
        logger.info("For Linux: sysctl -w net.ipv4.tcp_syncookies=1")
        logger.info("For web servers: configure appropriate backlog and timeout settings")
        
        # Additional instructions for configuring web servers
        if app.config.get('SERVER_NAME') == 'gunicorn':
            logger.info("For Gunicorn, use: --backlog=%s", DDoSConfig.SYN_BACKLOG)
        elif app.config.get('SERVER_NAME') == 'uwsgi':
            logger.info("For uWSGI, use: --listen=%s", DDoSConfig.SYN_BACKLOG)

# HTTP Flood Protection via Rate Limiting
def rate_limit():
    """
    Decorator for Flask routes to apply rate limiting
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Skip for whitelisted IPs
            client_ip = request.remote_addr
            if client_ip in DDoSConfig.WHITELISTED_IPS:
                return f(*args, **kwargs)
            
            # Check if IP is blacklisted
            if client_ip in BLACKLISTED_IPS:
                logger.warning(f"Blocked request from blacklisted IP: {client_ip}")
                abort(403)  # Forbidden
            
            # Rate limiting logic
            key = f"rate_limit:{client_ip}"
            current_time = int(time.time())
            
            if REDIS_AVAILABLE:
                # Use Redis for distributed rate limiting
                try:
                    # Increment counter and set expiry with Redis
                    # Windows Redis may have slightly different connection reliability
                    # so add additional error handling
                    current_count = redis_client.incr(key)
                    redis_client.expire(key, DDoSConfig.RATE_LIMIT_WINDOW)
                    
                    if current_count > DDoSConfig.RATE_LIMIT:
                        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                        # Track violation for potential blacklisting
                        violation_key = f"violations:{client_ip}"
                        violations = redis_client.incr(violation_key)
                        redis_client.expire(violation_key, DDoSConfig.BLACKLIST_DURATION)
                        
                        if violations >= DDoSConfig.BLACKLIST_THRESHOLD:
                            blacklist_key = f"blacklist:{client_ip}"
                            redis_client.set(blacklist_key, 1)
                            redis_client.expire(blacklist_key, DDoSConfig.BLACKLIST_DURATION)
                            logger.warning(f"Blacklisted IP for repeated violations: {client_ip}")
                        
                        abort(429)  # Too Many Requests
                except (redis.RedisError, ConnectionError, TimeoutError) as e:
                    logger.error(f"Redis error in rate limiting: {e}")
                    # Fall back to in-memory storage with Windows-compatible exception handling
                    IP_REQUEST_COUNTS[client_ip] += 1
            else:
                # Use in-memory rate limiting (not suitable for distributed setup)
                cleanup_expired_data()  # Clean up old data
                IP_REQUEST_COUNTS[client_ip] += 1
                
                if IP_REQUEST_COUNTS[client_ip] > DDoSConfig.RATE_LIMIT:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    abort(429)  # Too Many Requests
            
            # Track for anomaly detection
            if DDoSConfig.ANOMALY_DETECTION_ENABLED:
                track_request_for_anomaly(client_ip)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Slowloris Protection via Connection Limiting
def connection_limiter(app):
    """
    Flask before_request and teardown_request handlers to limit connections per IP
    """
    @app.before_request
    def limit_connections():
        client_ip = request.remote_addr
        
        # Skip for whitelisted IPs
        if client_ip in DDoSConfig.WHITELISTED_IPS:
            return
        
        # Check if IP is blacklisted
        if client_ip in BLACKLISTED_IPS:
            logger.warning(f"Blocked connection from blacklisted IP: {client_ip}")
            abort(403)  # Forbidden
        
        # Add a timestamp to the current request to detect slow requests
        g.request_start_time = time.time()
        
        # Connection tracking
        if REDIS_AVAILABLE:
            key = f"connections:{client_ip}"
            try:
                # Force connection key expiration to avoid stuck counters
                pipe = redis_client.pipeline()
                current_connections = pipe.incr(key).expire(key, DDoSConfig.CONNECTION_TIMEOUT).execute()[0]
                
                # More aggressive limiting for slow connections
                if request.headers.get('X-SlowTest') or 'slow' in request.headers.get('User-Agent', '').lower():
                    max_connections = max(1, DDoSConfig.MAX_CONNECTIONS_PER_IP // 4)  # Stricter limit for identified slow clients
                else:
                    max_connections = DDoSConfig.MAX_CONNECTIONS_PER_IP
                
                if current_connections > max_connections:
                    logger.warning(f"Connection limit exceeded for IP: {client_ip}, count: {current_connections}")
                    # Record violation
                    violation_key = f"violations:{client_ip}"
                    violations = redis_client.incr(violation_key)
                    redis_client.expire(violation_key, DDoSConfig.BLACKLIST_DURATION)
                    
                    if violations >= DDoSConfig.BLACKLIST_THRESHOLD:
                        blacklist_key = f"blacklist:{client_ip}"
                        redis_client.set(blacklist_key, 1)
                        redis_client.expire(blacklist_key, DDoSConfig.BLACKLIST_DURATION)
                        BLACKLISTED_IPS.add(client_ip)
                        logger.warning(f"Blacklisted IP for connection violations: {client_ip}")
                    
                    # Immediately close connection
                    redis_client.decr(key)
                    abort(429)  # Too Many Requests
            except (redis.RedisError, ConnectionError, TimeoutError) as e:
                logger.error(f"Redis error in connection limiting: {e}")
                # Fall back to in-memory
                IP_CONNECTIONS[client_ip] = IP_CONNECTIONS.get(client_ip, 0) + 1
        else:
            # Use in-memory connection tracking
            with threading.Lock():  # Thread-safe operation
                IP_CONNECTIONS[client_ip] = IP_CONNECTIONS.get(client_ip, 0) + 1
                
                # More aggressive limiting for slow connections
                if request.headers.get('X-SlowTest') or 'slow' in request.headers.get('User-Agent', '').lower():
                    max_connections = max(1, DDoSConfig.MAX_CONNECTIONS_PER_IP // 4)  # Stricter limit for identified slow clients
                else:
                    max_connections = DDoSConfig.MAX_CONNECTIONS_PER_IP
                
                if IP_CONNECTIONS[client_ip] > max_connections:
                    logger.warning(f"Connection limit exceeded for IP: {client_ip}, count: {IP_CONNECTIONS[client_ip]}")
                    IP_CONNECTIONS[client_ip] -= 1  # Decrement before aborting
                    abort(429)  # Too Many Requests
    
    @app.after_request
    def monitor_response_time(response):
        """Monitor for slow responses that might indicate Slowloris attack attempts"""
        if hasattr(g, 'request_start_time'):
            response_time = time.time() - g.request_start_time
            
            # Check if this is a suspiciously slow request (possibly Slowloris)
            if response_time > DDoSConfig.CONNECTION_TIMEOUT * 0.5:  # If response takes more than half the timeout
                client_ip = request.remote_addr
                if client_ip not in DDoSConfig.WHITELISTED_IPS:
                    logger.warning(f"Slow request detected from IP: {client_ip}, time: {response_time:.2f}s")
                    
                    # Add custom header for tracking
                    response.headers['X-Slow-Request-Detected'] = 'true'
                    
                    # Record violation
                    if REDIS_AVAILABLE:
                        try:
                            slow_key = f"slow:{client_ip}"
                            redis_client.incr(slow_key)
                            redis_client.expire(slow_key, DDoSConfig.BLACKLIST_DURATION)
                            
                            # If too many slow requests, reduce connection limit for this IP
                            slow_count = int(redis_client.get(slow_key) or 0)
                            if slow_count >= 3:
                                logger.warning(f"Multiple slow requests from IP: {client_ip}, reducing connection limit")
                        except (redis.RedisError, ConnectionError, TimeoutError):
                            pass
                    
        return response
    
    @app.teardown_request
    def teardown(exception=None):
        client_ip = request.remote_addr if hasattr(request, 'remote_addr') else None
        
        if client_ip and client_ip not in DDoSConfig.WHITELISTED_IPS:
            if REDIS_AVAILABLE:
                try:
                    key = f"connections:{client_ip}"
                    redis_client.decr(key)
                    # Ensure counter doesn't go below zero
                    count = int(redis_client.get(key) or 0)
                    if count < 0:
                        redis_client.set(key, 0)
                except (redis.RedisError, ConnectionError, TimeoutError) as e:
                    logger.error(f"Redis error in connection cleanup: {e}")
                    if client_ip in IP_CONNECTIONS:
                        with threading.Lock():  # Thread-safe operation
                            IP_CONNECTIONS[client_ip] = max(0, IP_CONNECTIONS[client_ip] - 1)
            else:
                if client_ip in IP_CONNECTIONS:
                    with threading.Lock():  # Thread-safe operation
                        IP_CONNECTIONS[client_ip] = max(0, IP_CONNECTIONS[client_ip] - 1)

# Add a middleware specifically for Slowloris protection
def add_slowloris_middleware(app):
    """
    Add a WSGI middleware to protect against Slowloris attacks at a lower level
    This works in addition to the connection limiter
    """
    class SlowlorisProtectionMiddleware:
        def __init__(self, app):
            self.app = app
            self.connections = defaultdict(int)
            self.lock = threading.Lock()
        
        def __call__(self, environ, start_response):
            # Get client IP from environment
            client_ip = environ.get('REMOTE_ADDR', '')
            
            # Skip whitelisted IPs
            if client_ip in DDoSConfig.WHITELISTED_IPS:
                return self.app(environ, start_response)
            
            # Check if client is already blacklisted
            if is_blacklisted(client_ip):
                # Return 403 Forbidden response for blacklisted IPs
                def blacklisted_response(status, headers, exc_info=None):
                    if exc_info:
                        return start_response("403 Forbidden", [("Content-Type", "text/plain")], exc_info)
                    return start_response("403 Forbidden", [("Content-Type", "text/plain")])
                
                return [b"Forbidden: Too many connection attempts"]
            
            # Track connection
            with self.lock:
                self.connections[client_ip] += 1
                connection_count = self.connections[client_ip]
            
            # Enforce connection limit
            if connection_count > DDoSConfig.MAX_CONNECTIONS_PER_IP:
                with self.lock:
                    self.connections[client_ip] -= 1
                
                # Return 429 Too Many Requests response
                def limit_response(status, headers, exc_info=None):
                    if exc_info:
                        return start_response("429 Too Many Requests", [("Content-Type", "text/plain")], exc_info)
                    return start_response("429 Too Many Requests", [("Content-Type", "text/plain")])
                
                logger.warning(f"WSGI middleware blocked connection from IP: {client_ip}, connections: {connection_count}")
                return [b"Too Many Requests: Connection limit exceeded"]
            
            # Wrap the start_response function to track connection close
            def custom_start_response(status, headers, exc_info=None):
                # Pass through to original start_response
                if exc_info:
                    result = start_response(status, headers, exc_info)
                else:
                    result = start_response(status, headers)
                
                # Decrease connection count when response is complete
                with self.lock:
                    self.connections[client_ip] = max(0, self.connections[client_ip] - 1)
                
                return result
            
            # Set a timeout for the request processing
            environ['REQUEST_TIMEOUT'] = DDoSConfig.CONNECTION_TIMEOUT
            
            # Process the request
            try:
                return self.app(environ, custom_start_response)
            except Exception as e:
                logger.error(f"Error in WSGI middleware: {e}")
                # Decrease connection count on error
                with self.lock:
                    self.connections[client_ip] = max(0, self.connections[client_ip] - 1)
                raise
    
    # Wrap the application with the middleware
    app.wsgi_app = SlowlorisProtectionMiddleware(app.wsgi_app)
    logger.info("Added Slowloris protection WSGI middleware")

# Caching Implementation - Windows compatible
def configure_caching(app, config=None):
    """
    Configure caching for Flask app
    """
    try:
        from flask_caching import Cache
        
        cache_config = {
            "CACHE_TYPE": "redis" if REDIS_AVAILABLE else "simple",
            "CACHE_DEFAULT_TIMEOUT": 300,
        }
        
        if REDIS_AVAILABLE:
            cache_config["CACHE_REDIS_HOST"] = "localhost"
            cache_config["CACHE_REDIS_PORT"] = 6379
            cache_config["CACHE_REDIS_DB"] = 1  # Use a different DB than rate limiting
            # Add Windows-specific timeout settings for better reliability
            cache_config["CACHE_REDIS_SOCKET_TIMEOUT"] = 5
            cache_config["CACHE_REDIS_SOCKET_CONNECT_TIMEOUT"] = 5
        
        # For Windows, the filesystem cache path needs to be absolute and use correct slashes
        if not REDIS_AVAILABLE and IS_WINDOWS:
            cache_dir = os.path.join(os.getcwd(), 'flask_cache')
            os.makedirs(cache_dir, exist_ok=True)
            cache_config["CACHE_DIR"] = cache_dir
        
        if config:
            cache_config.update(config)
        
        cache = Cache(app, config=cache_config)
        logger.info(f"Caching configured with {cache_config['CACHE_TYPE']} backend")
        return cache
    except ImportError:
        logger.warning("Flask-Caching not installed. Install with: pip install Flask-Caching")
        return None

# Geo-filtering Implementation - Windows compatible
def geo_filter():
    """
    Decorator for Flask routes to apply geo-filtering
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not DDoSConfig.GEO_BLOCKING_ENABLED:
                return f(*args, **kwargs)
            
            # Check if geoip2 is installed
            if 'geoip2' not in globals():
                logger.warning("geoip2 module not installed, geo-filtering disabled")
                return f(*args, **kwargs)
            
            client_ip = request.remote_addr
            
            # Skip for whitelisted IPs
            if client_ip in DDoSConfig.WHITELISTED_IPS:
                return f(*args, **kwargs)
            
            # Skip for local/private IPs
            try:
                ip_obj = ipaddress.ip_address(client_ip)
                if ip_obj.is_private or ip_obj.is_loopback:
                    return f(*args, **kwargs)
            except ValueError:
                logger.warning(f"Invalid IP address: {client_ip}")
                pass
            
            # Verify database exists (important for Windows path handling)
            if not os.path.exists(DDoSConfig.GEO_DATABASE_PATH):
                logger.warning(f"GeoIP database not found at {DDoSConfig.GEO_DATABASE_PATH}, geo-filtering disabled")
                return f(*args, **kwargs)
            
            try:
                # Load GeoIP database with Windows-compatible path
                with geoip2.database.Reader(DDoSConfig.GEO_DATABASE_PATH) as reader:
                    response = reader.country(client_ip)
                    country_code = response.country.iso_code
                    
                    # Apply geo-filtering rules
                    if DDoSConfig.ALLOWED_COUNTRIES and country_code not in DDoSConfig.ALLOWED_COUNTRIES:
                        logger.warning(f"Blocked request from non-allowed country: {country_code}, IP: {client_ip}")
                        abort(403)  # Forbidden
                    
                    if country_code in DDoSConfig.BLOCKED_COUNTRIES:
                        logger.warning(f"Blocked request from blocked country: {country_code}, IP: {client_ip}")
                        abort(403)  # Forbidden
            except Exception as e:
                logger.error(f"Error in geo-filtering for IP: {client_ip}: {e}")
                # In case of error, allow the request to proceed
                pass
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Anomaly Detection
def track_request_for_anomaly(client_ip):
    """
    Track requests for anomaly detection
    """
    current_time = time.time()
    
    if REDIS_AVAILABLE:
        try:
            # Use Redis sorted sets for time-based tracking
            key = f"anomaly:{client_ip}"
            score = current_time
            redis_client.zadd(key, {str(score): score})
            # Remove old entries
            redis_client.zremrangebyscore(key, 0, current_time - DDoSConfig.ANOMALY_WINDOW)
            # Count entries in the window
            count = redis_client.zcard(key)
            
            # Check for anomalies
            if count > (DDoSConfig.RATE_LIMIT * DDoSConfig.ANOMALY_WINDOW / DDoSConfig.RATE_LIMIT_WINDOW * DDoSConfig.ANOMALY_THRESHOLD):
                logger.warning(f"Anomaly detected for IP: {client_ip}, request count: {count}")
                # Could trigger additional protection mechanisms here
        except (redis.RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Redis error in anomaly tracking: {e}")
            # Fall back to in-memory
            ANOMALY_TRACKING[client_ip].append(current_time)
    else:
        # In-memory tracking
        ANOMALY_TRACKING[client_ip].append(current_time)
        
        # Remove old entries
        while ANOMALY_TRACKING[client_ip] and ANOMALY_TRACKING[client_ip][0] < current_time - DDoSConfig.ANOMALY_WINDOW:
            ANOMALY_TRACKING[client_ip].pop(0)
        
        # Check for anomalies
        count = len(ANOMALY_TRACKING[client_ip])
        if count > (DDoSConfig.RATE_LIMIT * DDoSConfig.ANOMALY_WINDOW / DDoSConfig.RATE_LIMIT_WINDOW * DDoSConfig.ANOMALY_THRESHOLD):
            logger.warning(f"Anomaly detected for IP: {client_ip}, request count: {count}")
            # Could trigger additional protection mechanisms here

# Request validation for HTTP flood protection
def validate_request():
    """
    Validate request to detect and block suspicious patterns
    """
    # Check if user_agents is installed
    if 'parse' not in globals():
        logger.warning("user_agents module not installed, detailed User-Agent parsing disabled")
        return True
    
    # Check for User-Agent
    user_agent = request.headers.get('User-Agent', '')
    if not user_agent:
        logger.warning(f"Request without User-Agent from IP: {request.remote_addr}")
        return False
    
    # Parse User-Agent to check if it's a bot/crawler
    try:
        ua = parse(user_agent)
        if ua.is_bot and request.remote_addr not in DDoSConfig.WHITELISTED_IPS:
            logger.info(f"Bot request detected: {user_agent} from IP: {request.remote_addr}")
            # You might want to apply stricter rate limits for bots
    except Exception as e:
        logger.error(f"Error parsing User-Agent: {e}")
    
    # Check for Referer for cross-site requests
    referer = request.headers.get('Referer', '')
    
    # Check for abnormal request patterns
    if request.method == 'POST' and not referer:
        logger.warning(f"POST request without Referer from IP: {request.remote_addr}")
        # This might be suspicious but not necessarily malicious
    
    return True

# Helper function to check if an IP is blacklisted
def is_blacklisted(ip):
    """
    Check if an IP is blacklisted
    """
    if ip in BLACKLISTED_IPS:
        return True
        
    if REDIS_AVAILABLE:
        try:
            key = f"blacklist:{ip}"
            return bool(redis_client.exists(key))
        except (redis.RedisError, ConnectionError, TimeoutError):
            # Fall back to in-memory
            return ip in BLACKLISTED_IPS
    else:
        return ip in BLACKLISTED_IPS

# Apply all DDoS protection measures to a Flask app
def protect_flask_app(app, config=None):
    """
    Apply all DDoS protection measures to a Flask app
    """
    if config:
        for key, value in config.items():
            if hasattr(DDoSConfig, key):
                setattr(DDoSConfig, key, value)
    
    # Configure SYN Cookies
    configure_syn_cookies(app)
    
    # Configure connection limiting (Slowloris protection)
    connection_limiter(app)
    
    # Add WSGI middleware for deeper Slowloris protection
    add_slowloris_middleware(app)
    
    # Configure caching
    cache = configure_caching(app)
    
    # Global request validation
    @app.before_request
    def global_protection():
        client_ip = request.remote_addr
        
        # Skip for whitelisted IPs
        if client_ip in DDoSConfig.WHITELISTED_IPS:
            return
        
        # Check blacklist
        if is_blacklisted(client_ip):
            logger.warning(f"Blocked request from blacklisted IP: {client_ip}")
            abort(403)  # Forbidden
        
        # Set a request timeout to mitigate slow clients
        # This is implemented in WSGI servers like Gunicorn and uWSGI
        if hasattr(request, 'environ'):
            request.environ['werkzeug.request.max_content_length'] = 10 * 1024 * 1024  # 10MB
            request.environ['werkzeug.request.max_form_memory_size'] = 1 * 1024 * 1024  # 1MB
        
        # Validate request
        if not validate_request():
            logger.warning(f"Invalid request from IP: {client_ip}")
            abort(400)  # Bad Request
    
    # Set HTTP headers to mitigate certain attacks
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Strict request timeout
        response.call_on_close(lambda: None)  # Force immediate response closing
        
        return response
    
    logger.info(f"DDoS protection measures applied to Flask app on {platform.system()} {platform.release()}")
    return cache

# Usage example:
"""
from flask import Flask
from ddos_protection import protect_flask_app, rate_limit, geo_filter

app = Flask(__name__)

# Apply all protection measures
cache = protect_flask_app(app)

# Apply rate limiting and geo-filtering to specific routes
@app.route('/api/sensitive')
@rate_limit()
@geo_filter()
def sensitive_endpoint():
    return "Protected endpoint"

if __name__ == '__main__':
    app.run()
""" 