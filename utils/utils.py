import random, requests, json
from utils.ntlmdecode import ntlmdecode
from datetime import datetime
import socket

# We can set anything up here for easy parsing and access later, for the moment this only houses the slack webhook, can probably add discord and other platforms at a later date as parsing isn't an issue.

def generate_ip():

    return ".".join(str(random.randint(0,255)) for _ in range(4))


def generate_id():

    return "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(10))


def generate_trace_id():
    str = "Root=1-"
    first = "".join(random.choice("0123456789abcdef") for _ in range(8))
    second = "".join(random.choice("0123456789abcdef") for _ in range(24))
    return str + first + "-" + second


def generate_string(chars):

    return "".join(random.choice("0123456789abcdefghijklmnopqrstuvwxyz") for _ in range(chars))


def add_custom_headers(pluginargs, headers):

    if "custom-headers" in pluginargs.keys():
        for header in pluginargs["custom-headers"]:
            headers[header] = pluginargs["custom-headers"][header]

    if "xforwardedfor" in pluginargs.keys():
        headers["X-My-X-Forwarded-For"] = pluginargs["xforwardedfor"]        

    return headers


def get_owa_domain(url, uri, useragent, proxy_url=None):
    # Stolen from https://github.com/byt3bl33d3r/SprayingToolkit who stole it from https://github.com/dafthack/MailSniper
    auth_header = {
        "Authorization": "NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==",
        'User-Agent': useragent,
        "X-My-X-Forwarded-For" : generate_ip(),
        "x-amzn-apigateway-api-id" : generate_id(),
        "X-My-X-Amzn-Trace-Id" : generate_trace_id(),
    }

    r = make_proxy_request('post', f"{url}{uri}", proxy_url=proxy_url, headers=auth_header)
    if r.status_code == 401:
        # Check for AWS-specific header first (FireProx mode)
        if "x-amzn-Remapped-WWW-Authenticate" in r.headers:
            ntlm_info = ntlmdecode(r.headers["x-amzn-Remapped-WWW-Authenticate"])
            return ntlm_info["NetBIOS_Domain_Name"]
        # Check for standard WWW-Authenticate header (proxy mode)
        elif "WWW-Authenticate" in r.headers:
            ntlm_info = ntlmdecode(r.headers["WWW-Authenticate"])
            return ntlm_info["NetBIOS_Domain_Name"]
        else:
            return "NOTFOUND"
    else:
        return "NOTFOUND"


# Colour Functions - ZephrFish
def prRed(skk):
    return "\033[91m{}\033[00m" .format(skk)

def prGreen(skk):
    return "\033[92m{}\033[00m" .format(skk)

def prYellow(skk):
    return "\033[93m{}\033[00m" .format(skk)


def get_proxy_session(proxy_url=None):
    """
    Get a requests session configured with proxy settings
    
    Args:
        proxy_url (str): Proxy URL in format 'protocol://[user:pass@]host:port'
        
    Returns:
        requests.Session: Configured session
    """
    if proxy_url:
        from utils.proxy import ProxyManager
        proxy_manager = ProxyManager(proxy_url)
        return proxy_manager.get_session()
    else:
        return requests.Session()


def make_proxy_request(method, url, proxy_url=None, max_retries=3, **kwargs):
    """
    Make a request through a proxy if configured with retry logic for 503/502 errors
    
    Args:
        method (str): HTTP method (get, post, etc.)
        url (str): Target URL
        proxy_url (str): Optional proxy URL
        max_retries (int): Maximum number of retries for 503/502 errors
        **kwargs: Additional arguments for requests
        
    Returns:
        requests.Response: Response object
    """
    session = get_proxy_session(proxy_url)
    
    # Remove verify=False from kwargs if present and set it explicitly
    verify = kwargs.pop('verify', False)
    
    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = getattr(session, method.lower())(url, verify=verify, **kwargs)
            
            # If we get 503/502, retry if we haven't exceeded max_retries
            if response.status_code in [502, 503] and retry_count < max_retries:
                retry_count += 1
                # Add a small delay between retries
                import time
                time.sleep(1)
                continue
            else:
                return response
                
        except Exception as e:
            if retry_count < max_retries:
                retry_count += 1
                # Add a small delay between retries
                import time
                time.sleep(1)
                continue
            else:
                raise e
    
    # This should never be reached, but just in case
    return getattr(session, method.lower())(url, verify=verify, **kwargs)


def get_proxy_domain(url, uri, useragent, proxy_url=None):
    """
    Proxy-aware version of get_owa_domain function
    """
    auth_header = {
        "Authorization": "NTLM TlRMTVNTUAABAAAAB4IIogAAAAAAAAAAAAAAAAAAAAAGAbEdAAAADw==",
        'User-Agent': useragent,
        "X-My-X-Forwarded-For" : generate_ip(),
        "x-amzn-apigateway-api-id" : generate_id(),
        "X-My-X-Amzn-Trace-Id" : generate_trace_id(),
    }

    r = make_proxy_request('post', f"{url}{uri}", proxy_url=proxy_url, headers=auth_header)
    if r.status_code == 401:
        ntlm_info = ntlmdecode(r.headers["x-amzn-Remapped-WWW-Authenticate"])
        return ntlm_info["NetBIOS_Domain_Name"]
    else:
        return "NOTFOUND"
