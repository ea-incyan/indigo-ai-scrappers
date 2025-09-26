"""
Main scraper engine that orchestrates the entire scraping process.
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

from ..discovery.website_analyzer import WebsiteAnalyzer
from ..strategies.search_strategies import SearchStrategyFactory
from ..extractors.data_extractor import DataExtractor
from ..utils.helpers import clean_text, extract_domain


class ScraperEngine:
    """Main engine that coordinates the scraping process."""
    
    def __init__(self, timeout: int = 30, max_results: int = 50, use_pycurl: bool = True):
        self.timeout = timeout
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.website_analyzer = WebsiteAnalyzer(timeout=timeout, use_pycurl=use_pycurl)
        self.search_factory = SearchStrategyFactory(timeout=timeout, use_pycurl=use_pycurl)
        self.data_extractor = DataExtractor(timeout=timeout, use_pycurl=use_pycurl)
    
    def discover_website_structure(self, url: str) -> Dict[str, Any]:
        """
        Discover the structure and search capabilities of the target website.
        
        Args:
            url: Target website URL
            
        Returns:
            Dictionary containing website structure information
        """
        self.logger.info(f"Analyzing website structure for: {url}")
        
        website_info = {
            'url': url,
            'domain': extract_domain(url),
            'search_strategy': None,
            'search_endpoints': [],
            'sitemap_urls': [],
            'has_search_form': False,
            'search_params': {},
            'requires_js': False,
            'robots_txt': None,
            'meta_info': {}
        }
        
        try:
            # Analyze the homepage
            analysis_result = self.website_analyzer.analyze_website(url)
            website_info.update(analysis_result)
            
            # Determine best search strategy
            strategy = self.search_factory.get_best_strategy(website_info)
            website_info['search_strategy'] = strategy.name if strategy else 'unknown'
            
            self.logger.info(f"Website analysis complete. Strategy: {website_info['search_strategy']}")
            
        except Exception as e:
            self.logger.error(f"Error analyzing website: {e}")
            website_info['error'] = str(e)
        
        return website_info
    
    def scrape_data(self, url: str, search_terms: List[Dict[str, Any]], 
                   website_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform the actual data scraping based on discovered website structure.
        
        Args:
            url: Target website URL
            search_terms: List of search terms with metadata
            website_info: Discovered website structure information
            
        Returns:
            Dictionary containing all extracted results
        """
        self.logger.info(f"Starting data extraction for {len(search_terms)} search terms")
        
        results = {
            'metadata': {
                'target_url': url,
                'domain': website_info.get('domain'),
                'search_strategy': website_info.get('search_strategy'),
                'timestamp': time.time(),
                'total_search_terms': len(search_terms),
                'website_info': website_info
            },
            'results': []
        }
        
        # Get the appropriate search strategy
        strategy = self.search_factory.get_strategy(website_info.get('search_strategy', 'unknown'))
        
        if not strategy:
            self.logger.error("No suitable search strategy found")
            results['error'] = "No suitable search strategy found"
            return results
        
        # Process each search term
        for i, search_term in enumerate(search_terms, 1):
            self.logger.info(f"Processing search term {i}/{len(search_terms)}: {search_term}")
            
            try:
                # Create search query from the search term
                search_query = self._create_search_query(search_term)
                
                # Perform search using the strategy
                search_results = strategy.search(url, search_query, website_info)
                
                # Extract data from search results
                extracted_data = self.data_extractor.extract_data(
                    search_results, 
                    search_term, 
                    website_info
                )
                
                # Add to results
                results['results'].extend(extracted_data)
                
                self.logger.info(f"Extracted {len(extracted_data)} results for search term {i}")
                
                # Add delay between searches to be respectful
                if i < len(search_terms):
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Error processing search term {i}: {e}")
                results['results'].append({
                    'search_term_id': search_term.get('id'),
                    'search_term': search_term,
                    'error': str(e),
                    'results_count': 0
                })
        
        self.logger.info(f"Data extraction complete. Total results: {len(results['results'])}")
        return results
    
    def _create_search_query(self, search_term: Dict[str, Any]) -> str:
        """
        Create a search query string from search term metadata.
        
        Args:
            search_term: Dictionary containing search term information
            
        Returns:
            Formatted search query string
        """
        # Combine artist and title if available
        query_parts = []
        
        if 'Artist' in search_term:
            query_parts.append(search_term['Artist'])
        
        if 'Title' in search_term:
            query_parts.append(search_term['Title'])
        
        # If no specific fields, use all string values
        if not query_parts:
            for key, value in search_term.items():
                if isinstance(value, str) and key != 'id':
                    query_parts.append(value)
        
        return ' '.join(query_parts).strip()