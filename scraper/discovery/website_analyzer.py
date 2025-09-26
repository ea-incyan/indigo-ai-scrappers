"""
Website analyzer that discovers the structure and search capabilities of target websites.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from ..utils.http_client import HTTPClient


class WebsiteAnalyzer:
    """Analyzes websites to discover their structure and search capabilities."""
    
    def __init__(self, timeout: int = 30, use_pycurl: bool = True):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.http_client = HTTPClient(timeout=timeout, use_pycurl=use_pycurl)
    
    def analyze_website(self, url: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of the target website.
        
        Args:
            url: Target website URL
            
        Returns:
            Dictionary containing analysis results
        """
        self.logger.info(f"Starting website analysis for: {url}")
        
        analysis = {
            'has_search_form': False,
            'search_endpoints': [],
            'sitemap_urls': [],
            'search_params': {},
            'requires_js': False,
            'robots_txt': None,
            'meta_info': {},
            'forms': [],
            'links': []
        }
        
        try:
            # Fetch the homepage
            response = self.http_client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analyze various aspects
            analysis.update(self._analyze_search_forms(soup, url))
            analysis.update(self._analyze_sitemaps(url))
            analysis.update(self._analyze_robots_txt(url))
            analysis.update(self._analyze_meta_info(soup))
            analysis.update(self._analyze_javascript_requirements(soup))
            analysis.update(self._analyze_forms(soup, url))
            analysis.update(self._analyze_links(soup, url))
            
            self.logger.info("Website analysis completed successfully")
            
        except requests.RequestException as e:
            self.logger.error(f"Error fetching website: {e}")
            analysis['error'] = str(e)
        except Exception as e:
            self.logger.error(f"Error analyzing website: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _analyze_search_forms(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Analyze search forms on the page."""
        search_info = {
            'has_search_form': False,
            'search_endpoints': [],
            'search_params': {},
            'form_methods': [],
            'search_inputs': []
        }
        
        # Look for search forms with various patterns
        search_form_patterns = [
            {'action': re.compile(r'search|query|find', re.I)},
            {'method': 'get'},
            {'id': re.compile(r'search|query|find', re.I)},
            {'class': re.compile(r'search|query|find', re.I)}
        ]
        
        search_forms = []
        for pattern in search_form_patterns:
            search_forms.extend(soup.find_all('form', pattern))
        
        # Also look for forms with search-related inputs
        search_inputs = soup.find_all('input', {
            'type': ['text', 'search'],
            'name': re.compile(r'search|query|q|find|term|keyword', re.I)
        })
        
        # Look for inputs with search-related placeholders or IDs
        search_inputs.extend(soup.find_all('input', {
            'placeholder': re.compile(r'search|query|find|enter', re.I)
        }))
        
        search_inputs.extend(soup.find_all('input', {
            'id': re.compile(r'search|query|find', re.I)
        }))
        
        for input_elem in search_inputs:
            form = input_elem.find_parent('form')
            if form and form not in search_forms:
                search_forms.append(form)
        
        for form in search_forms:
            search_info['has_search_form'] = True
            
            # Extract form action
            action = form.get('action', '')
            method = form.get('method', 'get').lower()
            
            if action:
                search_url = urljoin(base_url, action)
                search_info['search_endpoints'].append(search_url)
            else:
                # If no action, use the current page
                search_info['search_endpoints'].append(base_url)
            
            search_info['form_methods'].append(method)
            
            # Extract search parameters
            form_search_inputs = form.find_all('input', {
                'type': ['text', 'search'],
                'name': re.compile(r'search|query|q|find|term|keyword', re.I)
            })
            
            # Also check inputs with search-related placeholders/IDs
            form_search_inputs.extend(form.find_all('input', {
                'placeholder': re.compile(r'search|query|find|enter', re.I)
            }))
            
            form_search_inputs.extend(form.find_all('input', {
                'id': re.compile(r'search|query|find', re.I)
            }))
            
            for input_elem in form_search_inputs:
                param_name = input_elem.get('name', 'q')
                input_type = input_elem.get('type', 'text')
                placeholder = input_elem.get('placeholder', '')
                
                search_info['search_params'][param_name] = 'SEARCH_TERM'
                search_info['search_inputs'].append({
                    'name': param_name,
                    'type': input_type,
                    'placeholder': placeholder,
                    'id': input_elem.get('id', '')
                })
        
        return search_info
    
    def _analyze_sitemaps(self, base_url: str) -> Dict[str, Any]:
        """Look for sitemap files."""
        sitemap_info = {'sitemap_urls': []}
        
        # Common sitemap locations
        sitemap_paths = [
            '/sitemap.xml',
            '/sitemap_index.xml',
            '/sitemaps.xml',
            '/robots.txt'  # robots.txt often contains sitemap references
        ]
        
        for path in sitemap_paths:
            try:
                sitemap_url = urljoin(base_url, path)
                response = self.http_client.head(sitemap_url)
                
                if response.status_code == 200:
                    sitemap_info['sitemap_urls'].append(sitemap_url)
                    self.logger.info(f"Found sitemap: {sitemap_url}")
                    
            except requests.RequestException:
                continue
        
        return sitemap_info
    
    def _analyze_robots_txt(self, base_url: str) -> Dict[str, Any]:
        """Analyze robots.txt file."""
        robots_info = {'robots_txt': None}
        
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            response = self.http_client.get(robots_url)
            
            if response.status_code == 200:
                robots_info['robots_txt'] = response.text
                
                # Parse robots.txt for sitemap references
                sitemap_lines = [line for line in response.text.split('\n') 
                               if line.strip().lower().startswith('sitemap:')]
                
                for line in sitemap_lines:
                    sitemap_url = line.split(':', 1)[1].strip()
                    robots_info.setdefault('sitemap_urls', []).append(sitemap_url)
                
                self.logger.info(f"Found robots.txt with {len(sitemap_lines)} sitemap references")
                
        except requests.RequestException:
            pass
        
        return robots_info
    
    def _analyze_meta_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract meta information from the page."""
        meta_info = {}
        
        # Extract title
        title = soup.find('title')
        if title:
            meta_info['title'] = title.get_text().strip()
        
        # Extract meta description
        description = soup.find('meta', {'name': 'description'})
        if description:
            meta_info['description'] = description.get('content', '').strip()
        
        # Extract meta keywords
        keywords = soup.find('meta', {'name': 'keywords'})
        if keywords:
            meta_info['keywords'] = keywords.get('content', '').strip()
        
        return {'meta_info': meta_info}
    
    def _analyze_javascript_requirements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Determine if the site requires JavaScript for search functionality."""
        js_info = {'requires_js': False}
        
        # Look for JavaScript frameworks
        scripts = soup.find_all('script')
        js_frameworks = ['react', 'vue', 'angular', 'jquery', 'bootstrap']
        
        for script in scripts:
            src = script.get('src', '')
            content = script.get_text()
            
            # Check for framework indicators
            for framework in js_frameworks:
                if framework in src.lower() or framework in content.lower():
                    js_info['requires_js'] = True
                    break
            
            if js_info['requires_js']:
                break
        
        # Look for AJAX/XHR indicators
        ajax_indicators = ['xhr', 'ajax', 'fetch', 'xmlhttprequest']
        page_text = soup.get_text().lower()
        
        for indicator in ajax_indicators:
            if indicator in page_text:
                js_info['requires_js'] = True
                break
        
        return js_info
    
    def _analyze_forms(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Analyze all forms on the page."""
        forms_info = {'forms': []}
        
        forms = soup.find_all('form')
        for form in forms:
            form_info = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get').lower(),
                'inputs': []
            }
            
            # Extract form inputs
            inputs = form.find_all('input')
            for input_elem in inputs:
                input_info = {
                    'name': input_elem.get('name', ''),
                    'type': input_elem.get('type', 'text'),
                    'placeholder': input_elem.get('placeholder', ''),
                    'value': input_elem.get('value', '')
                }
                form_info['inputs'].append(input_info)
            
            forms_info['forms'].append(form_info)
        
        return forms_info
    
    def _analyze_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Analyze links on the page for search-related patterns."""
        links_info = {'links': []}
        
        links = soup.find_all('a', href=True)
        search_patterns = [
            r'search',
            r'query',
            r'find',
            r'results',
            r'category',
            r'filter'
        ]
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            
            # Check if link is search-related
            is_search_related = any(
                re.search(pattern, href.lower()) or re.search(pattern, text)
                for pattern in search_patterns
            )
            
            if is_search_related:
                link_info = {
                    'href': urljoin(base_url, href),
                    'text': link.get_text().strip(),
                    'title': link.get('title', '')
                }
                links_info['links'].append(link_info)
        
        return links_info