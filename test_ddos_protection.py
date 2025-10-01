import os
import time
import unittest
import tempfile
from unittest.mock import patch, Mock, MagicMock
import json
import threading
from flask import Flask, request, jsonify

# Import the DDoS protection module
import ddos_protection
from ddos_protection import (
    rate_limit, 
    geo_filter, 
    configure_syn_cookies,
    connection_limiter,
    configure_caching,
    track_request_for_anomaly,
    validate_request,
    is_blacklisted,
    protect_flask_app,
    DDoSConfig
)

class TestDDoSProtection(unittest.TestCase):
    def setUp(self):
        # Create a Flask test app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Reset global variables for each test
        ddos_protection.IP_REQUEST_COUNTS = {}
        ddos_protection.IP_CONNECTIONS = {}
        ddos_protection.BLACKLISTED_IPS = set()
        ddos_protection.ANOMALY_TRACKING = {}
        ddos_protection.LAST_CLEANUP = time.time()
        
        # Configure test routes
        @self.app.route('/test_rate_limit')
        @rate_limit()
        def test_rate_limit():
            return 'OK'
        
        @self.app.route('/test_geo')
        @geo_filter()
        def test_geo():
            return 'OK'
        
        @self.app.route('/test_all')
        @rate_limit()
        @geo_filter()
        def test_all():
            return 'OK'
        
        @self.app.route('/test_validation')
        def test_validation():
            result = validate_request()
            return jsonify({'valid': result})

    def tearDown(self):
        # Clean up after each test
        pass

    @patch('ddos_protection.REDIS_AVAILABLE', False)
    def test_rate_limit_in_memory(self):
        """Test rate limiting using in-memory storage"""
        # Temporarily modify rate limit for testing
        original_rate_limit = DDoSConfig.RATE_LIMIT
        DDoSConfig.RATE_LIMIT = 3  # Set a low limit for testing
        
        test_ip = '192.168.1.100'
        
        # Make requests up to the limit
        for i in range(DDoSConfig.RATE_LIMIT):
            with patch('flask.request.remote_addr', test_ip):
                response = self.client.get('/test_rate_limit')
                self.assertEqual(response.status_code, 200)
        
        # The next request should be rate limited
        with patch('flask.request.remote_addr', test_ip):
            response = self.client.get('/test_rate_limit')
            self.assertEqual(response.status_code, 429)  # Too Many Requests
        
        # Reset the rate limit
        DDoSConfig.RATE_LIMIT = original_rate_limit

    @patch('ddos_protection.REDIS_AVAILABLE', True)
    @patch('ddos_protection.redis_client')
    def test_rate_limit_with_redis(self, mock_redis):
        """Test rate limiting using Redis"""
        # Setup Redis mock
        mock_redis.incr.side_effect = [1, 2, 3, 4]  # Simulate increasing count
        mock_redis.expire.return_value = True
        
        test_ip = '192.168.1.100'
        original_rate_limit = DDoSConfig.RATE_LIMIT
        DDoSConfig.RATE_LIMIT = 3  # Set a low limit for testing
        
        # Make requests up to the limit
        for i in range(DDoSConfig.RATE_LIMIT):
            with patch('flask.request.remote_addr', test_ip):
                response = self.client.get('/test_rate_limit')
                self.assertEqual(response.status_code, 200)
        
        # The next request should be rate limited
        with patch('flask.request.remote_addr', test_ip):
            response = self.client.get('/test_rate_limit')
            self.assertEqual(response.status_code, 429)  # Too Many Requests
        
        # Verify Redis calls
        self.assertEqual(mock_redis.incr.call_count, 4)
        self.assertEqual(mock_redis.expire.call_count, 4)
        
        # Reset the rate limit
        DDoSConfig.RATE_LIMIT = original_rate_limit

    @patch('ddos_protection.REDIS_AVAILABLE', True)
    @patch('ddos_protection.redis_client')
    def test_redis_error_fallback(self, mock_redis):
        """Test fallback to in-memory when Redis fails"""
        # Setup Redis mock to raise an exception
        mock_redis.incr.side_effect = ddos_protection.redis.RedisError("Test Redis failure")
        
        test_ip = '192.168.1.100'
        
        # Make a request that will cause Redis to fail
        with patch('flask.request.remote_addr', test_ip):
            response = self.client.get('/test_rate_limit')
            self.assertEqual(response.status_code, 200)
        
        # Verify it fell back to in-memory tracking
        self.assertEqual(ddos_protection.IP_REQUEST_COUNTS[test_ip], 1)

    def test_connection_limiter(self):
        """Test connection limiting (Slowloris protection)"""
        # Apply connection limiter to app
        connection_limiter(self.app)
        
        # Set a low connection limit for testing
        original_limit = DDoSConfig.MAX_CONNECTIONS_PER_IP
        DDoSConfig.MAX_CONNECTIONS_PER_IP = 3
        
        test_ip = '192.168.1.100'
        
        # Manually increase connection count to simulate concurrent connections
        with self.app.test_request_context():
            with patch('flask.request.remote_addr', test_ip):
                ddos_protection.IP_CONNECTIONS[test_ip] = DDoSConfig.MAX_CONNECTIONS_PER_IP
                
                # The next connection should be rejected
                response = self.client.get('/test_validation')
                self.assertEqual(response.status_code, 429)  # Too Many Requests
        
        # Reset the connection limit
        DDoSConfig.MAX_CONNECTIONS_PER_IP = original_limit

    @patch('geoip2.database.Reader')
    def test_geo_filtering(self, mock_reader):
        """Test geo-filtering functionality"""
        # Enable geo blocking
        DDoSConfig.GEO_BLOCKING_ENABLED = True
        DDoSConfig.BLOCKED_COUNTRIES = ['CN']
        
        # Mock the GeoIP response
        mock_country = Mock()
        mock_country.iso_code = 'CN'
        
        mock_response = Mock()
        mock_response.country = mock_country
        
        mock_reader_instance = MagicMock()
        mock_reader_instance.country.return_value = mock_response
        mock_reader.return_value.__enter__.return_value = mock_reader_instance
        
        # Create a patch for os.path.exists to avoid file not found
        with patch('os.path.exists', return_value=True):
            # Test with blocked country
            test_ip = '1.2.3.4'  # Example Chinese IP
            with patch('flask.request.remote_addr', test_ip):
                response = self.client.get('/test_geo')
                self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test with allowed country
        mock_country.iso_code = 'US'
        test_ip = '8.8.8.8'  # Example US IP
        with patch('os.path.exists', return_value=True):
            with patch('flask.request.remote_addr', test_ip):
                response = self.client.get('/test_geo')
                self.assertEqual(response.status_code, 200)
        
        # Reset geo blocking
        DDoSConfig.GEO_BLOCKING_ENABLED = False
        DDoSConfig.BLOCKED_COUNTRIES = []

    def test_blacklisting(self):
        """Test IP blacklisting functionality"""
        # Blacklist an IP
        test_ip = '192.168.1.200'
        ddos_protection.BLACKLISTED_IPS.add(test_ip)
        
        # Apply protection to create the before_request handler
        protect_flask_app(self.app)
        
        # Request from blacklisted IP should be rejected
        with patch('flask.request.remote_addr', test_ip):
            response = self.client.get('/test_validation')
            self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Request from non-blacklisted IP should be allowed
        with patch('flask.request.remote_addr', '192.168.1.201'):
            response = self.client.get('/test_validation')
            self.assertEqual(response.status_code, 200)

    @patch('ddos_protection.REDIS_AVAILABLE', False)
    def test_anomaly_detection(self):
        """Test anomaly detection functionality"""
        # Enable anomaly detection
        DDoSConfig.ANOMALY_DETECTION_ENABLED = True
        DDoSConfig.ANOMALY_THRESHOLD = 0.5
        DDoSConfig.RATE_LIMIT = 10
        
        test_ip = '192.168.1.100'
        
        # Create a large number of requests in a short time to trigger anomaly detection
        current_time = time.time()
        
        # Manually add request timestamps to simulate high traffic
        ddos_protection.ANOMALY_TRACKING[test_ip] = [
            current_time - i for i in range(
                int(DDoSConfig.RATE_LIMIT * DDoSConfig.ANOMALY_WINDOW / DDoSConfig.RATE_LIMIT_WINDOW * DDoSConfig.ANOMALY_THRESHOLD) + 2
            )
        ]
        
        # Create a mock for the logger to check for warnings
        with patch('ddos_protection.logger.warning') as mock_warning:
            track_request_for_anomaly(test_ip)
            
            # Check if warning was logged for anomaly
            mock_warning.assert_called_with(f"Anomaly detected for IP: {test_ip}, request count: {len(ddos_protection.ANOMALY_TRACKING[test_ip])}")

    @patch('ddos_protection.parse')
    def test_request_validation(self, mock_parse):
        """Test request validation"""
        # Setup mock user agent parser
        mock_ua = Mock()
        mock_ua.is_bot = False
        mock_parse.return_value = mock_ua
        
        # Test with valid request
        with self.app.test_request_context(headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://example.com'
        }):
            self.assertTrue(validate_request())
        
        # Test with missing User-Agent
        with self.app.test_request_context(headers={}):
            with patch('ddos_protection.logger.warning') as mock_warning:
                self.assertFalse(validate_request())
                mock_warning.assert_called()  # Check warning was logged
        
        # Test with bot User-Agent
        mock_ua.is_bot = True
        with self.app.test_request_context(headers={
            'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'
        }):
            with patch('ddos_protection.logger.info') as mock_info:
                self.assertTrue(validate_request())
                mock_info.assert_called()  # Check info was logged about bot detection

    @patch('ddos_protection.flask_caching')
    def test_caching_configuration(self, mock_flask_caching):
        """Test caching configuration"""
        # Setup mock Cache
        mock_cache = Mock()
        mock_flask_caching.Cache.return_value = mock_cache
        
        # Test with Redis available
        with patch('ddos_protection.REDIS_AVAILABLE', True):
            cache = configure_caching(self.app)
            self.assertEqual(cache, mock_cache)
            
            # Get the first call arguments
            args, kwargs = mock_flask_caching.Cache.call_args
            config = kwargs.get('config', args[1] if len(args) > 1 else None)
            
            # Check cache configuration
            self.assertEqual(config['CACHE_TYPE'], 'redis')
        
        # Test with Redis unavailable
        mock_flask_caching.Cache.reset_mock()
        with patch('ddos_protection.REDIS_AVAILABLE', False):
            cache = configure_caching(self.app)
            
            # Get the first call arguments
            args, kwargs = mock_flask_caching.Cache.call_args
            config = kwargs.get('config', args[1] if len(args) > 1 else None)
            
            # Check cache configuration
            self.assertEqual(config['CACHE_TYPE'], 'simple')

    def test_syn_cookies_configuration(self):
        """Test SYN cookies configuration logging"""
        with patch('ddos_protection.logger.info') as mock_info:
            configure_syn_cookies(self.app)
            
            # Verify logging was called
            self.assertTrue(mock_info.called)
            
            # Check if OS-specific advice was provided
            if ddos_protection.IS_WINDOWS:
                mock_info.assert_any_call("Windows SYN Flood protection recommendations:")
            else:
                mock_info.assert_any_call("SYN Cookies protection should be configured at the OS/server level")

    def test_whitelisting(self):
        """Test IP whitelisting functionality"""
        # Add IP to whitelist
        test_ip = '192.168.1.250'
        DDoSConfig.WHITELISTED_IPS.add(test_ip)
        
        # Set a very low rate limit
        original_rate_limit = DDoSConfig.RATE_LIMIT
        DDoSConfig.RATE_LIMIT = 1
        
        # Whitelisted IP should bypass rate limiting
        with patch('flask.request.remote_addr', test_ip):
            # Make more requests than the limit
            for _ in range(DDoSConfig.RATE_LIMIT + 2):
                response = self.client.get('/test_rate_limit')
                self.assertEqual(response.status_code, 200)
        
        # Non-whitelisted IP should be rate limited
        non_whitelisted_ip = '192.168.1.251'
        with patch('flask.request.remote_addr', non_whitelisted_ip):
            # First request should succeed
            response = self.client.get('/test_rate_limit')
            self.assertEqual(response.status_code, 200)
            
            # Second request (exceeding limit) should be blocked
            response = self.client.get('/test_rate_limit')
            self.assertEqual(response.status_code, 429)
        
        # Reset the rate limit
        DDoSConfig.RATE_LIMIT = original_rate_limit

    def test_integration(self):
        """Test full integration of protection measures"""
        # Apply all protection measures
        cache = protect_flask_app(self.app)
        
        # Test with normal request (should pass)
        test_ip = '192.168.1.100'
        with patch('flask.request.remote_addr', test_ip):
            with patch('ddos_protection.validate_request', return_value=True):
                response = self.client.get('/test_validation')
                self.assertEqual(response.status_code, 200)
        
        # Test with invalid request (should be blocked)
        with patch('flask.request.remote_addr', test_ip):
            with patch('ddos_protection.validate_request', return_value=False):
                response = self.client.get('/test_validation')
                self.assertEqual(response.status_code, 400)  # Bad Request

    @patch('ddos_protection.REDIS_AVAILABLE', False)
    def test_cleanup_expired_data(self):
        """Test cleanup of expired rate limiting data"""
        # Add some data
        ddos_protection.IP_REQUEST_COUNTS = {
            '192.168.1.1': 5,
            '192.168.1.2': 10
        }
        
        # Set cleanup time to be in the past
        ddos_protection.LAST_CLEANUP = time.time() - (DDoSConfig.CLEANUP_INTERVAL + 10)
        
        # Trigger cleanup by accessing the rate limiting decorator
        with self.app.test_request_context():
            with patch('flask.request.remote_addr', '192.168.1.3'):
                response = self.client.get('/test_rate_limit')
                self.assertEqual(response.status_code, 200)
        
        # Data should be reset
        self.assertEqual(len(ddos_protection.IP_REQUEST_COUNTS), 1)  # Only contains the new request
        self.assertEqual(ddos_protection.IP_REQUEST_COUNTS['192.168.1.3'], 1)

if __name__ == '__main__':
    unittest.main() 