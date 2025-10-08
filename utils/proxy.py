#!/usr/bin/env python3
"""
Proxy utility module for CredMaster
Supports SOCKS4, SOCKS4A, SOCKS5, and HTTP proxies
"""

import requests
import socks
import socket
from urllib.parse import urlparse
import logging

class ProxyManager:
    """
    Manages proxy connections for different proxy types
    """
    
    def __init__(self, proxy_url=None):
        """
        Initialize ProxyManager with optional proxy URL
        
        Args:
            proxy_url (str): Proxy URL in format 'protocol://[user:pass@]host:port'
                            Supported protocols: socks4, socks4a, socks5, http
        """
        self.proxy_url = proxy_url
        self.proxy_config = None
        self.session = None
        
        if proxy_url:
            self._parse_proxy_url()
            self._create_session()
    
    def _parse_proxy_url(self):
        """
        Parse proxy URL and extract components
        """
        try:
            parsed = urlparse(self.proxy_url)
            
            if not parsed.scheme:
                raise ValueError("Proxy URL must include protocol (socks4, socks4a, socks5, http)")
            
            if not parsed.hostname:
                raise ValueError("Proxy URL must include hostname")
            
            if not parsed.port:
                raise ValueError("Proxy URL must include port")
            
            self.proxy_config = {
                'protocol': parsed.scheme.lower(),
                'host': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password
            }
            
            # Validate protocol
            if self.proxy_config['protocol'] not in ['socks4', 'socks4a', 'socks5', 'http']:
                raise ValueError(f"Unsupported proxy protocol: {self.proxy_config['protocol']}. "
                               f"Supported protocols: socks4, socks4a, socks5, http")
            
        except Exception as e:
            raise ValueError(f"Invalid proxy URL format: {e}")
    
    def _create_session(self):
        """
        Create requests session with proxy configuration
        """
        self.session = requests.Session()
        
        if self.proxy_config['protocol'] in ['socks4', 'socks4a', 'socks5']:
            self._setup_socks_proxy()
        elif self.proxy_config['protocol'] == 'http':
            self._setup_http_proxy()
    
    def _setup_socks_proxy(self):
        """
        Setup SOCKS proxy configuration
        """
        protocol_map = {
            'socks4': socks.SOCKS4,
            'socks4a': socks.SOCKS4,
            'socks5': socks.SOCKS5
        }
        
        socks_protocol = protocol_map[self.proxy_config['protocol']]
        
        # Store original socket for cleanup
        self._original_socket = socket.socket
        
        # Configure SOCKS proxy
        socks.set_default_proxy(
            socks_protocol,
            self.proxy_config['host'],
            self.proxy_config['port'],
            username=self.proxy_config['username'],
            password=self.proxy_config['password']
        )
        
        # Patch socket to use SOCKS proxy
        socket.socket = socks.socksocket
        
        # For SOCKS4A, we need to handle DNS resolution differently
        if self.proxy_config['protocol'] == 'socks4a':
            # SOCKS4A handles DNS resolution on the proxy server
            pass
    
    def _setup_http_proxy(self):
        """
        Setup HTTP proxy configuration
        """
        proxy_url = f"http://{self.proxy_config['host']}:{self.proxy_config['port']}"
        
        # Add authentication if provided
        if self.proxy_config['username'] and self.proxy_config['password']:
            proxy_url = f"http://{self.proxy_config['username']}:{self.proxy_config['password']}@{self.proxy_config['host']}:{self.proxy_config['port']}"
        
        self.session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
    
    def get_session(self):
        """
        Get configured requests session
        
        Returns:
            requests.Session: Configured session with proxy settings
        """
        return self.session
    
    def test_proxy_connection(self, test_url="http://httpbin.org/ip", timeout=10, max_retries=3):
        """
        Test proxy connection with retry logic for 503/502 errors
        
        Args:
            test_url (str): URL to test connection against
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries for 503/502 errors
            
        Returns:
            tuple: (success: bool, response: str)
        """
        if not self.session:
            return False, "No proxy session configured"
        
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                response = self.session.get(test_url, timeout=timeout)
                
                if response.status_code == 200:
                    return True, f"Proxy connection successful. Response: {response.text[:200]}"
                elif response.status_code in [502, 503]:
                    retry_count += 1
                    if retry_count <= max_retries:
                        last_error = f"Proxy returned {response.status_code}, retrying ({retry_count}/{max_retries})..."
                        continue
                    else:
                        return False, f"Proxy connection failed after {max_retries} retries. Last status: {response.status_code}"
                else:
                    return False, f"Proxy connection failed with status code: {response.status_code}"
                    
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    last_error = f"Connection error, retrying ({retry_count}/{max_retries}): {str(e)}"
                    continue
                else:
                    return False, f"Proxy connection failed after {max_retries} retries: {str(e)}"
        
        return False, f"Proxy connection failed: {last_error}"
    
    def cleanup(self):
        """
        Cleanup proxy configuration and restore original socket
        """
        if self.proxy_config and self.proxy_config['protocol'] in ['socks4', 'socks4a', 'socks5']:
            # Restore original socket if we stored it
            if hasattr(self, '_original_socket'):
                socket.socket = self._original_socket
        
        if self.session:
            self.session.close()
            self.session = None


def create_proxy_session(proxy_url):
    """
    Convenience function to create a proxy session
    
    Args:
        proxy_url (str): Proxy URL in format 'protocol://[user:pass@]host:port'
        
    Returns:
        ProxyManager: Configured proxy manager instance
    """
    return ProxyManager(proxy_url)


def validate_proxy_url(proxy_url):
    """
    Validate proxy URL format
    
    Args:
        proxy_url (str): Proxy URL to validate
        
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    try:
        ProxyManager(proxy_url)
        return True, None
    except Exception as e:
        return False, str(e)


# Example usage and testing
if __name__ == "__main__":
    # Test different proxy types
    test_proxies = [
        "socks5://127.0.0.1:1080",
        "socks4://127.0.0.1:1080", 
        "socks4a://127.0.0.1:1080",
        "http://127.0.0.1:8080",
        "http://user:pass@127.0.0.1:8080"
    ]
    
    for proxy_url in test_proxies:
        print(f"\nTesting proxy: {proxy_url}")
        try:
            proxy_manager = ProxyManager(proxy_url)
            success, message = proxy_manager.test_proxy_connection()
            print(f"Result: {success} - {message}")
            proxy_manager.cleanup()
        except Exception as e:
            print(f"Error: {e}")
