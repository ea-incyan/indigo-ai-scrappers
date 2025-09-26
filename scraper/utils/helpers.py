"""
Helper utility functions.
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse


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


def is_valid_url(url: str) -> bool:
    """
    Check if URL is valid.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str, base_url: str = '') -> str:
    """
    Normalize URL by making it absolute.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative URLs
        
    Returns:
        Normalized absolute URL
    """
    if not url:
        return ''
    
    # If already absolute, return as is
    if url.startswith(('http://', 'https://')):
        return url
    
    # If relative and we have a base URL, make it absolute
    if base_url:
        from urllib.parse import urljoin
        return urljoin(base_url, url)
    
    return url


def extract_searchable_text(search_term: Dict[str, Any]) -> str:
    """
    Extract searchable text from search term dictionary.
    
    Args:
        search_term: Search term dictionary
        
    Returns:
        Searchable text string
    """
    searchable_fields = ['Artist', 'Title', 'query', 'search', 'term', 'name']
    text_parts = []
    
    for field in searchable_fields:
        if field in search_term and isinstance(search_term[field], str):
            text_parts.append(search_term[field].strip())
    
    return ' '.join(text_parts).strip()


def calculate_relevance_score(result: Dict[str, Any], query: str) -> float:
    """
    Calculate relevance score for a result based on query.
    
    Args:
        result: Result dictionary
        query: Search query
        
    Returns:
        Relevance score (0-100)
    """
    score = 0.0
    query_lower = query.lower()
    query_words = query_lower.split()
    
    # Check title relevance
    title = result.get('title', '') or result.get('page_title', '')
    if title:
        title_lower = title.lower()
        for word in query_words:
            if word in title_lower:
                score += 20
    
    # Check description relevance
    description = result.get('description', '') or result.get('page_description', '')
    if description:
        desc_lower = description.lower()
        for word in query_words:
            if word in desc_lower:
                score += 10
    
    # Check URL relevance
    url = result.get('url', '')
    if url:
        url_lower = url.lower()
        for word in query_words:
            if word in url_lower:
                score += 15
    
    return min(score, 100.0)


def format_results_summary(results: List[Dict[str, Any]]) -> str:
    """
    Format a summary of scraping results.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Formatted summary string
    """
    if not results:
        return "No results found"
    
    total_results = len(results)
    successful_results = len([r for r in results if not r.get('error')])
    failed_results = total_results - successful_results
    
    # Calculate average quality score
    quality_scores = [r.get('data_quality_score', 0) for r in results if not r.get('error')]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    summary = f"""
Results Summary:
- Total results: {total_results}
- Successful: {successful_results}
- Failed: {failed_results}
- Average quality score: {avg_quality:.1f}/100
"""
    
    return summary.strip()