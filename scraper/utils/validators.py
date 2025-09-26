"""
Input validation utilities.
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse


def validate_url(url: str) -> None:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Raises:
        ValueError: If URL is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("URL must use HTTP or HTTPS protocol")
            
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")


def validate_search_terms(search_terms: List[Dict[str, Any]]) -> None:
    """
    Validate search terms format.
    
    Args:
        search_terms: List of search term dictionaries
        
    Raises:
        ValueError: If search terms are invalid
    """
    if not isinstance(search_terms, list):
        raise ValueError("Search terms must be a list")
    
    if not search_terms:
        raise ValueError("Search terms cannot be empty")
    
    for i, term in enumerate(search_terms):
        if not isinstance(term, dict):
            raise ValueError(f"Search term {i} must be a dictionary")
        
        if 'id' not in term:
            raise ValueError(f"Search term {i} must have an 'id' field")
        
        # Check if there's at least one searchable field
        searchable_fields = ['Artist', 'Title', 'query', 'search', 'term']
        has_searchable_field = any(
            field in term and isinstance(term[field], str) and term[field].strip()
            for field in searchable_fields
        )
        
        if not has_searchable_field:
            raise ValueError(f"Search term {i} must have at least one searchable field")


def clean_text(text: str) -> str:
    """
    Clean text content by removing extra whitespace and special characters.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
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


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ''