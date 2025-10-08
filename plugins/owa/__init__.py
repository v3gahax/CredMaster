import requests
import utils.utils as utils
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


def validate(pluginargs, args):
    #
    # Plugin Args
    #
    # --url https://mail.domain.com   ->  OWA mail target
    #
    if 'url' in pluginargs.keys():
        return True, None, pluginargs
    else:
        error = "Missing url argument, specify as --url https://mail.domain.com"
        return False, error, None


def testconnect(pluginargs, args, api_dict, useragent):

    url = api_dict['proxy_url']
    proxy_url = pluginargs.get('proxy_url')  # Get proxy URL if in proxy mode

    success = True
    headers = {
        'User-Agent' : useragent,
        "X-My-X-Forwarded-For" : utils.generate_ip(),
        "x-amzn-apigateway-api-id" : utils.generate_id(),
        "X-My-X-Amzn-Trace-Id" : utils.generate_trace_id(),
    }

    headers = utils.add_custom_headers(pluginargs, headers)

    # Use proxy-aware request if proxy is configured
    if proxy_url:
        resp = utils.make_proxy_request('get', url, proxy_url=proxy_url, headers=headers)
    else:
        resp = requests.get(url, headers=headers, verify=False)

    if resp.status_code == 504:
        output = "Testconnect: Connection failed, endpoint timed out, exiting"
        success = False
    else:
        output = "Testconnect: Fingerprinting host... Internal Domain name: {domain}, continuing"

    if success:
        domainname = utils.get_owa_domain(url, "/autodiscover/autodiscover.xml", useragent, proxy_url)
        output = output.format(domain=domainname)
        pluginargs['domain'] = domainname

    return success, output, pluginargs
