"""
HTTP client utilities with support for both requests and pycurl.
"""

import logging
import time
from typing import Dict, Any, Optional, Union
from urllib.parse import urlencode

import requests

# Try to import pycurl
try:
    import pycurl
    from io import BytesIO
    PYCURL_AVAILABLE = True
except ImportError:
    PYCURL_AVAILABLE = False


class HTTPClient:
    """HTTP client with support for both requests and pycurl."""
    
    def __init__(self, timeout: int = 30, use_pycurl: bool = True):
        self.timeout = timeout
        self.use_pycurl = use_pycurl and PYCURL_AVAILABLE
        self.logger = logging.getLogger(__name__)
        
        # Setup requests session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        if self.use_pycurl:
            self.logger.info("Using pycurl for HTTP requests")
        else:
            self.logger.info("Using requests for HTTP requests")
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
            headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Perform GET request using either pycurl or requests.
        
        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Response object
        """
        if self.use_pycurl:
            return self._get_pycurl(url, params, headers)
        else:
            return self._get_requests(url, params, headers)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None,
             headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Perform POST request using either pycurl or requests.
        
        Args:
            url: URL to request
            data: POST data
            headers: Additional headers
            
        Returns:
            Response object
        """
        if self.use_pycurl:
            return self._post_pycurl(url, data, headers)
        else:
            return self._post_requests(url, data, headers)
    
    def _get_requests(self, url: str, params: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """GET request using requests library."""
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        return self.session.get(url, params=params, headers=request_headers, timeout=self.timeout)
    
    def _post_requests(self, url: str, data: Optional[Dict[str, Any]] = None,
                      headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """POST request using requests library."""
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        return self.session.post(url, data=data, headers=request_headers, timeout=self.timeout)
    
    def _get_pycurl(self, url: str, params: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """GET request using pycurl."""
        if params:
            url = f"{url}?{urlencode(params)}"
        
        return self._pycurl_request(url, headers=headers)
    
    def _post_pycurl(self, url: str, data: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """POST request using pycurl."""
        post_data = urlencode(data) if data else None
        return self._pycurl_request(url, data=post_data, headers=headers)
    
    def _pycurl_request(self, url: str, data: Optional[str] = None,
                       headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """Perform HTTP request using pycurl."""
        buffer = BytesIO()
        
        # Setup curl
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url.encode('utf-8'))
        curl.setopt(pycurl.WRITEDATA, buffer)
        curl.setopt(pycurl.TIMEOUT, self.timeout)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        curl.setopt(pycurl.SSL_VERIFYHOST, False)
        
        # Set headers
        header_list = []
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if headers:
            default_headers.update(headers)
        
        for key, value in default_headers.items():
            header_list.append(f"{key}: {value}")
        
        curl.setopt(pycurl.HTTPHEADER, header_list)
        
        # Set POST data if provided
        if data:
            curl.setopt(pycurl.POSTFIELDS, data.encode('utf-8'))
        
        try:
            curl.perform()
            
            # Get response info
            status_code = curl.getinfo(pycurl.HTTP_CODE)
            content_type = curl.getinfo(pycurl.CONTENT_TYPE)
            effective_url = curl.getinfo(pycurl.EFFECTIVE_URL)
            
            # Create response object
            response = requests.Response()
            response.status_code = status_code
            response.url = effective_url
            response.headers = {'Content-Type': content_type} if content_type else {}
            response._content = buffer.getvalue()
            
            return response
            
        except pycurl.error as e:
            self.logger.error(f"Pycurl error: {e}")
            # Fallback to requests
            return self._get_requests(url)
        
        finally:
            curl.close()
    
    def head(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        Perform HEAD request.
        
        Args:
            url: URL to request
            headers: Additional headers
            
        Returns:
            Response object
        """
        if self.use_pycurl:
            return self._head_pycurl(url, headers)
        else:
            return self._head_requests(url, headers)
    
    def _head_requests(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """HEAD request using requests library."""
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        return self.session.head(url, headers=request_headers, timeout=self.timeout)
    
    def _head_pycurl(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """HEAD request using pycurl."""
        buffer = BytesIO()
        
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url.encode('utf-8'))
        curl.setopt(pycurl.WRITEDATA, buffer)
        curl.setopt(pycurl.TIMEOUT, self.timeout)
        curl.setopt(pycurl.NOBODY, True)  # HEAD request
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.SSL_VERIFYPEER, False)
        curl.setopt(pycurl.SSL_VERIFYHOST, False)
        
        # Set headers
        header_list = []
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if headers:
            default_headers.update(headers)
        
        for key, value in default_headers.items():
            header_list.append(f"{key}: {value}")
        
        curl.setopt(pycurl.HTTPHEADER, header_list)
        
        try:
            curl.perform()
            
            status_code = curl.getinfo(pycurl.HTTP_CODE)
            content_type = curl.getinfo(pycurl.CONTENT_TYPE)
            effective_url = curl.getinfo(pycurl.EFFECTIVE_URL)
            
            response = requests.Response()
            response.status_code = status_code
            response.url = effective_url
            response.headers = {'Content-Type': content_type} if content_type else {}
            response._content = b''
            
            return response
            
        except pycurl.error as e:
            self.logger.error(f"Pycurl HEAD error: {e}")
            return self._head_requests(url)
        
        finally:
            curl.close()
