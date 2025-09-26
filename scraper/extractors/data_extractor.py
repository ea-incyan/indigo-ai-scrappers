"""
Data extractor that processes search results and extracts relevant information.
"""

import logging
import re
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ..utils.http_client import HTTPClient


class DataExtractor:
    """Extracts and enriches data from search results."""
    
    def __init__(self, timeout: int = 30, use_pycurl: bool = True):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.http_client = HTTPClient(timeout=timeout, use_pycurl=use_pycurl)
    
    def extract_data(self, search_results: List[Dict[str, Any]], 
                    search_term: Dict[str, Any], 
                    website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and enrich data from search results.
        
        Args:
            search_results: Raw search results from strategy
            search_term: Original search term metadata
            website_info: Website structure information
            
        Returns:
            List of enriched result data
        """
        self.logger.info(f"Extracting data from {len(search_results)} search results")
        
        enriched_results = []
        
        for i, result in enumerate(search_results):
            try:
                # Enrich the result with additional data
                enriched_result = self._enrich_result(result, search_term, website_info)
                enriched_results.append(enriched_result)
                
                # Add delay to be respectful
                if i < len(search_results) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"Error enriching result {i}: {e}")
                # Add the original result with error info
                enriched_result = result.copy()
                enriched_result['error'] = str(e)
                enriched_results.append(enriched_result)
        
        self.logger.info(f"Successfully enriched {len(enriched_results)} results")
        return enriched_results
    
    def _enrich_result(self, result: Dict[str, Any], 
                      search_term: Dict[str, Any], 
                      website_info: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single result with additional metadata."""
        enriched = result.copy()
        
        # Add search term information
        enriched['search_term_id'] = search_term.get('id')
        enriched['search_term_data'] = search_term
        enriched['extraction_timestamp'] = time.time()
        
        # Try to fetch additional metadata from the result URL
        if enriched.get('url'):
            try:
                metadata = self._fetch_page_metadata(enriched['url'])
                enriched.update(metadata)
            except Exception as e:
                self.logger.debug(f"Error fetching metadata for {enriched['url']}: {e}")
                enriched['metadata_error'] = str(e)
        
        # Clean and validate data
        enriched = self._clean_result_data(enriched)
        
        return enriched
    
    def _fetch_page_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch additional metadata from a result page."""
        metadata = {
            'page_title': '',
            'page_description': '',
            'page_keywords': '',
            'page_content_length': 0,
            'page_images': [],
            'page_links': [],
            'page_language': '',
            'page_author': '',
            'page_published_date': '',
            'page_modified_date': ''
        }
        
        try:
            response = self.http_client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            if title:
                metadata['page_title'] = title.get_text().strip()
            
            # Extract meta description
            description = soup.find('meta', {'name': 'description'})
            if description:
                metadata['page_description'] = description.get('content', '').strip()
            
            # Extract meta keywords
            keywords = soup.find('meta', {'name': 'keywords'})
            if keywords:
                metadata['page_keywords'] = keywords.get('content', '').strip()
            
            # Extract language
            html_tag = soup.find('html')
            if html_tag:
                metadata['page_language'] = html_tag.get('lang', '')
            
            # Extract author
            author = soup.find('meta', {'name': 'author'})
            if author:
                metadata['page_author'] = author.get('content', '').strip()
            
            # Extract published date
            published = soup.find('meta', {'property': 'article:published_time'})
            if published:
                metadata['page_published_date'] = published.get('content', '').strip()
            
            # Extract modified date
            modified = soup.find('meta', {'property': 'article:modified_time'})
            if modified:
                metadata['page_modified_date'] = modified.get('content', '').strip()
            
            # Extract images
            images = soup.find_all('img', src=True)
            metadata['page_images'] = [urljoin(url, img.get('src')) for img in images[:10]]  # Limit to 10
            
            # Extract links
            links = soup.find_all('a', href=True)
            metadata['page_links'] = [urljoin(url, link.get('href')) for link in links[:20]]  # Limit to 20
            
            # Calculate content length
            text_content = soup.get_text()
            metadata['page_content_length'] = len(text_content)
            
        except requests.RequestException as e:
            self.logger.debug(f"Error fetching page metadata: {e}")
            metadata['fetch_error'] = str(e)
        
        return metadata
    
    def _clean_result_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate result data."""
        cleaned = result.copy()
        
        # Clean text fields
        text_fields = ['title', 'description', 'page_title', 'page_description']
        for field in text_fields:
            if field in cleaned:
                cleaned[field] = self._clean_text(cleaned[field])
        
        # Validate URL
        if 'url' in cleaned:
            cleaned['url'] = self._validate_url(cleaned['url'])
        
        # Add data quality score
        cleaned['data_quality_score'] = self._calculate_quality_score(cleaned)
        
        return cleaned
    
    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        if not isinstance(text, str):
            return str(text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text.strip()
    
    def _validate_url(self, url: str) -> str:
        """Validate and clean URL."""
        if not url:
            return ''
        
        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                return url
            else:
                return ''
        except Exception:
            return ''
    
    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """Calculate a quality score for the result."""
        score = 0.0
        
        # URL presence (20 points)
        if result.get('url'):
            score += 20
        
        # Title presence (20 points)
        if result.get('title') or result.get('page_title'):
            score += 20
        
        # Description presence (15 points)
        if result.get('description') or result.get('page_description'):
            score += 15
        
        # Content length (15 points)
        content_length = result.get('page_content_length', 0)
        if content_length > 1000:
            score += 15
        elif content_length > 500:
            score += 10
        elif content_length > 100:
            score += 5
        
        # Images presence (10 points)
        if result.get('page_images'):
            score += 10
        
        # Links presence (10 points)
        if result.get('page_links'):
            score += 10
        
        # No errors (10 points)
        if not result.get('error') and not result.get('metadata_error') and not result.get('fetch_error'):
            score += 10
        
        return min(score, 100.0)  # Cap at 100