"""
Playwright-based search strategy for dynamic content.
"""

import logging
import time
from typing import Dict, List, Any, Optional

try:
    from playwright.sync_api import sync_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightSearchStrategy:
    """Search strategy using Playwright for JavaScript-heavy websites."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browser = None
    
    def can_handle(self, website_info: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the given website."""
        if not PLAYWRIGHT_AVAILABLE:
            return False
        
        return website_info.get('requires_js', False)
    
    def search(self, base_url: str, query: str, website_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform search using Playwright."""
        if not PLAYWRIGHT_AVAILABLE:
            self.logger.error("Playwright not available. Install with: pip install playwright")
            return []
        
        self.logger.info(f"Using Playwright search strategy for query: {query}")
        
        results = []
        
        try:
            with sync_playwright() as playwright:
                self.playwright = playwright
                
                # Launch browser
                browser = playwright.chromium.launch(headless=True)
                self.browser = browser
                
                try:
                    page = browser.new_page()
                    
                    # Set timeout
                    page.set_default_timeout(self.timeout * 1000)
                    
                    # Navigate to the website
                    page.goto(base_url)
                    
                    # Wait for page to load
                    page.wait_for_load_state('networkidle')
                    
                    # Try different search methods
                    results = self._try_search_methods(page, query, base_url)
                    
                finally:
                    browser.close()
        
        except Exception as e:
            self.logger.error(f"Error with Playwright search: {e}")
        
        return results
    
    def _try_search_methods(self, page: Page, query: str, base_url: str) -> List[Dict[str, Any]]:
        """Try different search methods on the page."""
        results = []
        
        # Method 1: Look for search input and submit form
        try:
            search_results = self._search_via_form(page, query, base_url)
            if search_results:
                results.extend(search_results)
                self.logger.info(f"Found {len(search_results)} results via form search")
        except Exception as e:
            self.logger.debug(f"Form search failed: {e}")
        
        # Method 2: Try URL-based search
        if not results:
            try:
                search_results = self._search_via_url(page, query, base_url)
                if search_results:
                    results.extend(search_results)
                    self.logger.info(f"Found {len(search_results)} results via URL search")
            except Exception as e:
                self.logger.debug(f"URL search failed: {e}")
        
        # Method 3: Look for search buttons/links
        if not results:
            try:
                search_results = self._search_via_buttons(page, query, base_url)
                if search_results:
                    results.extend(search_results)
                    self.logger.info(f"Found {len(search_results)} results via button search")
            except Exception as e:
                self.logger.debug(f"Button search failed: {e}")
        
        return results
    
    def _search_via_form(self, page: Page, query: str, base_url: str) -> List[Dict[str, Any]]:
        """Search using form submission."""
        results = []
        
        # Look for search input fields
        search_selectors = [
            'input[type="search"]',
            'input[name*="search"]',
            'input[name*="query"]',
            'input[name*="q"]',
            'input[placeholder*="search"]',
            'input[placeholder*="Search"]'
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                search_input = page.query_selector(selector)
                if search_input:
                    break
            except Exception:
                continue
        
        if not search_input:
            return results
        
        try:
            # Clear and fill search input
            search_input.clear()
            search_input.fill(query)
            
            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Search")',
                'button:has-text("Go")',
                'button:has-text("Find")'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = page.query_selector(selector)
                    if submit_button:
                        break
                except Exception:
                    continue
            
            if submit_button:
                # Click submit button
                submit_button.click()
            else:
                # Try pressing Enter
                search_input.press('Enter')
            
            # Wait for results to load
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # Extract results
            results = self._extract_results_from_page(page, base_url, query)
            
        except Exception as e:
            self.logger.debug(f"Error in form search: {e}")
        
        return results
    
    def _search_via_url(self, page: Page, query: str, base_url: str) -> List[Dict[str, Any]]:
        """Search by modifying URL parameters."""
        results = []
        
        # Common search parameter patterns
        search_params = ['q', 'query', 'search', 's', 'term', 'keyword']
        
        for param in search_params:
            try:
                # Construct search URL
                search_url = f"{base_url}?{param}={query}"
                
                # Navigate to search URL
                page.goto(search_url)
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Check if this looks like a results page
                if self._is_search_results_page(page, query):
                    page_results = self._extract_results_from_page(page, base_url, query)
                    if page_results:
                        results.extend(page_results)
                        break
                
            except Exception as e:
                self.logger.debug(f"Error with parameter '{param}': {e}")
        
        return results
    
    def _search_via_buttons(self, page: Page, query: str, base_url: str) -> List[Dict[str, Any]]:
        """Search by clicking search-related buttons."""
        results = []
        
        # Look for search-related buttons/links
        search_buttons = page.query_selector_all('a:has-text("Search"), button:has-text("Search")')
        
        for button in search_buttons:
            try:
                # Click the button
                button.click()
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                
                # Check if we're on a search page
                if self._is_search_page(page):
                    # Try to perform search
                    page_results = self._search_via_form(page, query, base_url)
                    if page_results:
                        results.extend(page_results)
                        break
                
            except Exception as e:
                self.logger.debug(f"Error clicking search button: {e}")
        
        return results
    
    def _is_search_results_page(self, page: Page, query: str) -> bool:
        """Check if current page contains search results."""
        try:
            content = page.content()
            content_lower = content.lower()
            
            # Look for indicators of search results
            indicators = [
                'results found',
                'search results',
                'no results',
                'found 0 results',
                'your search for',
                'showing results for'
            ]
            
            return any(indicator in content_lower for indicator in indicators)
        
        except Exception:
            return False
    
    def _is_search_page(self, page: Page) -> bool:
        """Check if current page is a search page."""
        try:
            # Look for search input fields
            search_inputs = page.query_selector_all('input[type="search"], input[name*="search"]')
            return len(search_inputs) > 0
        
        except Exception:
            return False
    
    def _extract_results_from_page(self, page: Page, base_url: str, query: str) -> List[Dict[str, Any]]:
        """Extract search results from the current page."""
        results = []
        
        try:
            # Look for result containers
            result_selectors = [
                '.result', '.search-result', '.item', '.entry',
                '[class*="result"]', '[class*="item"]', '[class*="entry"]'
            ]
            
            result_elements = []
            for selector in result_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    result_elements = elements
                    break
            
            # If no specific result containers, look for links
            if not result_elements:
                result_elements = page.query_selector_all('a[href]')
            
            for element in result_elements:
                try:
                    result_data = self._extract_element_data(element, base_url, query)
                    if result_data:
                        results.append(result_data)
                except Exception as e:
                    self.logger.debug(f"Error extracting element data: {e}")
        
        except Exception as e:
            self.logger.debug(f"Error extracting results: {e}")
        
        return results
    
    def _extract_element_data(self, element, base_url: str, query: str) -> Optional[Dict[str, Any]]:
        """Extract data from a result element."""
        try:
            result_data = {
                'url': '',
                'title': '',
                'description': '',
                'query': query,
                'source_url': base_url
            }
            
            # Extract URL
            href = element.get_attribute('href')
            if href:
                result_data['url'] = self._normalize_url(href, base_url)
            
            # Extract title
            title_elem = element.query_selector('h1, h2, h3, h4, h5, h6, a')
            if title_elem:
                result_data['title'] = title_elem.inner_text().strip()
            
            # Extract description
            desc_elem = element.query_selector('p, span, div')
            if desc_elem:
                result_data['description'] = desc_elem.inner_text().strip()
            
            return result_data if result_data['url'] else None
        
        except Exception as e:
            self.logger.debug(f"Error extracting element data: {e}")
            return None
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize URL by making it absolute."""
        if not url:
            return ''
        
        # If already absolute, return as is
        if url.startswith(('http://', 'https://')):
            return url
        
        # If relative, make it absolute
        from urllib.parse import urljoin
        return urljoin(base_url, url)