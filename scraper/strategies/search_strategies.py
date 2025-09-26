"""
Search strategy implementations for different website types.
"""

import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode, urljoin, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from ..utils.http_client import HTTPClient

# Import Playwright strategy if available
try:
    from .playwright_strategy import PlaywrightSearchStrategy
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class SearchStrategy(ABC):
    """Abstract base class for search strategies."""
    
    def __init__(self, timeout: int = 30, use_pycurl: bool = True):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.http_client = HTTPClient(timeout=timeout, use_pycurl=use_pycurl)
        self.name = self.__class__.__name__.replace('SearchStrategy', '').lower()
    
    @abstractmethod
    def search(self, base_url: str, query: str, website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform search using this strategy."""
        pass
    
    @abstractmethod
    def can_handle(self, website_info: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the given website."""
        pass


class FormSearchStrategy(SearchStrategy):
    """Strategy for websites with search forms."""
    
    def can_handle(self, website_info: Dict[str, Any]) -> bool:
        return website_info.get('has_search_form', False)
    
    def search(self, base_url: str, query: str, website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search using form submission."""
        self.logger.info(f"Using form search strategy for query: {query}")
        
        results = []
        search_endpoints = website_info.get('search_endpoints', [])
        search_params = website_info.get('search_params', {})
        
        if not search_endpoints:
            # Try to construct search URL from base URL
            search_endpoints = [base_url]
        
        for endpoint in search_endpoints:
            try:
                # Prepare search parameters
                params = {}
                for param_name, param_value in search_params.items():
                    if param_value == 'SEARCH_TERM':
                        params[param_name] = query
                    else:
                        params[param_name] = param_value
                
                # Make search request
                response = self.http_client.get(endpoint, params=params)
                response.raise_for_status()
                
                # Parse results
                soup = BeautifulSoup(response.content, 'html.parser')
                page_results = self._extract_results_from_page(soup, endpoint, query)
                results.extend(page_results)
                
                self.logger.info(f"Found {len(page_results)} results from {endpoint}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error searching {endpoint}: {e}")
        
        return results
    
    def _extract_results_from_page(self, soup: BeautifulSoup, url: str, query: str) -> List[Dict[str, Any]]:
        """Extract search results from the page."""
        results = []
        
        # Look for common result containers
        result_selectors = [
            '.result', '.search-result', '.item', '.entry',
            '[class*="result"]', '[class*="item"]', '[class*="entry"]'
        ]
        
        for selector in result_selectors:
            result_elements = soup.select(selector)
            if result_elements:
                break
        
        # If no specific result containers, look for links
        if not result_elements:
            result_elements = soup.find_all('a', href=True)
        
        for element in result_elements:
            try:
                result_data = self._extract_result_data(element, url, query)
                if result_data:
                    results.append(result_data)
            except Exception as e:
                self.logger.debug(f"Error extracting result data: {e}")
        
        return results
    
    def _extract_result_data(self, element, base_url: str, query: str) -> Optional[Dict[str, Any]]:
        """Extract data from a result element."""
        result_data = {
            'url': '',
            'title': '',
            'description': '',
            'query': query,
            'source_url': base_url
        }
        
        # Extract URL
        if element.name == 'a':
            href = element.get('href', '')
            result_data['url'] = urljoin(base_url, href)
        else:
            link = element.find('a', href=True)
            if link:
                href = link.get('href', '')
                result_data['url'] = urljoin(base_url, href)
        
        # Extract title
        title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find('a')
        if title_elem:
            result_data['title'] = title_elem.get_text().strip()
        
        # Extract description
        desc_elem = element.find(['p', 'span', 'div'], class_=re.compile(r'desc|summary|excerpt', re.I))
        if desc_elem:
            result_data['description'] = desc_elem.get_text().strip()
        
        return result_data if result_data['url'] else None


class QueryParamSearchStrategy(SearchStrategy):
    """Strategy for websites that use query parameters for search."""
    
    def can_handle(self, website_info: Dict[str, Any]) -> bool:
        # This strategy can handle most websites as a fallback
        return True
    
    def search(self, base_url: str, query: str, website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search using query parameters."""
        self.logger.info(f"Using query parameter search strategy for query: {query}")
        
        results = []
        
        # Common search parameter names
        search_params = ['q', 'query', 'search', 's', 'term', 'keyword']
        
        for param in search_params:
            try:
                params = {param: query}
                response = self.http_client.get(base_url, params=params)
                response.raise_for_status()
                
                # Check if this looks like a search results page
                if self._is_search_results_page(response.content, query):
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_results = self._extract_results_from_page(soup, base_url, query)
                    results.extend(page_results)
                    
                    self.logger.info(f"Found {len(page_results)} results using parameter '{param}'")
                    break
                
            except requests.RequestException as e:
                self.logger.debug(f"Error with parameter '{param}': {e}")
        
        return results
    
    def _is_search_results_page(self, content: bytes, query: str) -> bool:
        """Check if the page contains search results."""
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text().lower()
        
        # Look for indicators of search results
        indicators = [
            'results found',
            'search results',
            'no results',
            'found 0 results',
            'your search for',
            'showing results for'
        ]
        
        return any(indicator in text for indicator in indicators)
    
    def _extract_results_from_page(self, soup: BeautifulSoup, url: str, query: str) -> List[Dict[str, Any]]:
        """Extract search results from the page."""
        results = []
        
        # Look for result containers
        result_elements = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'result|item|entry', re.I))
        
        if not result_elements:
            # Fallback: look for all links
            result_elements = soup.find_all('a', href=True)
        
        for element in result_elements:
            try:
                result_data = self._extract_result_data(element, url, query)
                if result_data:
                    results.append(result_data)
            except Exception as e:
                self.logger.debug(f"Error extracting result data: {e}")
        
        return results
    
    def _extract_result_data(self, element, base_url: str, query: str) -> Optional[Dict[str, Any]]:
        """Extract data from a result element."""
        result_data = {
            'url': '',
            'title': '',
            'description': '',
            'query': query,
            'source_url': base_url
        }
        
        # Extract URL
        if element.name == 'a':
            href = element.get('href', '')
            result_data['url'] = urljoin(base_url, href)
        else:
            link = element.find('a', href=True)
            if link:
                href = link.get('href', '')
                result_data['url'] = urljoin(base_url, href)
        
        # Extract title
        title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find('a')
        if title_elem:
            result_data['title'] = title_elem.get_text().strip()
        
        # Extract description
        desc_elem = element.find(['p', 'span', 'div'], class_=re.compile(r'desc|summary|excerpt', re.I))
        if desc_elem:
            result_data['description'] = desc_elem.get_text().strip()
        
        return result_data if result_data['url'] else None


class SitemapSearchStrategy(SearchStrategy):
    """Strategy for searching through sitemaps."""
    
    def can_handle(self, website_info: Dict[str, Any]) -> bool:
        return bool(website_info.get('sitemap_urls'))
    
    def search(self, base_url: str, query: str, website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search through sitemap URLs."""
        self.logger.info(f"Using sitemap search strategy for query: {query}")
        
        results = []
        sitemap_urls = website_info.get('sitemap_urls', [])
        
        for sitemap_url in sitemap_urls:
            try:
                sitemap_results = self._search_sitemap(sitemap_url, query, base_url)
                results.extend(sitemap_results)
                
                self.logger.info(f"Found {len(sitemap_results)} results in sitemap: {sitemap_url}")
                
            except Exception as e:
                self.logger.error(f"Error searching sitemap {sitemap_url}: {e}")
        
        return results
    
    def _search_sitemap(self, sitemap_url: str, query: str, base_url: str) -> List[Dict[str, Any]]:
        """Search through a sitemap for relevant URLs."""
        results = []
        
        try:
            response = self.http_client.get(sitemap_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            
            # Look for URL entries
            urls = soup.find_all('url')
            
            for url_elem in urls:
                try:
                    loc = url_elem.find('loc')
                    if not loc:
                        continue
                    
                    url = loc.get_text().strip()
                    
                    # Check if URL is relevant to query
                    if self._is_url_relevant(url, query):
                        result_data = {
                            'url': url,
                            'title': '',
                            'description': '',
                            'query': query,
                            'source_url': sitemap_url
                        }
                        
                        # Try to extract title from sitemap
                        title_elem = url_elem.find('title')
                        if title_elem:
                            result_data['title'] = title_elem.get_text().strip()
                        
                        results.append(result_data)
                
                except Exception as e:
                    self.logger.debug(f"Error processing sitemap URL: {e}")
        
        except requests.RequestException as e:
            self.logger.error(f"Error fetching sitemap: {e}")
        
        return results
    
    def _is_url_relevant(self, url: str, query: str) -> bool:
        """Check if a URL is relevant to the search query."""
        query_words = query.lower().split()
        url_lower = url.lower()
        
        # Check if any query word appears in the URL
        return any(word in url_lower for word in query_words)


class SearchStrategyFactory:
    """Factory for creating appropriate search strategies."""
    
    def __init__(self, timeout: int = 30, use_pycurl: bool = True):
        self.timeout = timeout
        self.strategies = [
            FormSearchStrategy(timeout, use_pycurl),
            SitemapSearchStrategy(timeout, use_pycurl),
            QueryParamSearchStrategy(timeout, use_pycurl)
        ]
        
        # Add Playwright strategy if available
        if PLAYWRIGHT_AVAILABLE:
            self.strategies.append(PlaywrightSearchStrategy(timeout))
    
    def get_best_strategy(self, website_info: Dict[str, Any]) -> Optional[SearchStrategy]:
        """Get the best strategy for the given website."""
        for strategy in self.strategies:
            if strategy.can_handle(website_info):
                return strategy
        
        return None
    
    def get_strategy(self, strategy_name: str) -> Optional[SearchStrategy]:
        """Get a specific strategy by name."""
        strategy_map = {
            'form': FormSearchStrategy(self.timeout, True),
            'sitemap': SitemapSearchStrategy(self.timeout, True),
            'query_param': QueryParamSearchStrategy(self.timeout, True)
        }
        
        # Add Playwright strategy if available
        if PLAYWRIGHT_AVAILABLE:
            strategy_map['playwright'] = PlaywrightSearchStrategy(self.timeout)
        
        return strategy_map.get(strategy_name)