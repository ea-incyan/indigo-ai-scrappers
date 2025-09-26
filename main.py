#!/usr/bin/env python3
"""
Intelligent Web Scraper Application

This application takes a target domain URL and a list of search terms in JSON format,
then intelligently discovers the best way to search the site and extract relevant data.

Author: Senior Python Developer
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from scraper.core.scraper_engine import ScraperEngine
from scraper.utils.logger import setup_logging
from scraper.utils.validators import validate_url, validate_search_terms


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Intelligent Web Scraper for data extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py -u https://bt4gprx.com/ -s search_terms.json
  python main.py -u https://example.com -s '[{"id": 1, "Artist": "Beyonce", "Title": "Single Ladies"}]'
  python main.py -u https://example.com -s search_terms.json -o results.json -v
        """
    )
    
    parser.add_argument(
        '-u', '--url',
        required=True,
        help='Target domain URL (homepage) to scrape'
    )
    
    parser.add_argument(
        '-s', '--search-terms',
        required=True,
        help='JSON file path or JSON string containing search terms'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='scraped_results.json',
        help='Output file path for results (default: scraped_results.json)'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'jsonl'],
        default='json',
        help='Output format: json or jsonl (default: json)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--max-results',
        type=int,
        default=50,
        help='Maximum number of results per search term (default: 50)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--no-pycurl',
        action='store_true',
        help='Disable pycurl and use requests library instead'
    )
    
    return parser.parse_args()


def load_search_terms(search_terms_input: str) -> List[Dict[str, Any]]:
    """Load search terms from file or JSON string."""
    try:
        # Try to parse as JSON string first
        if search_terms_input.strip().startswith('['):
            return json.loads(search_terms_input)
        
        # Otherwise, treat as file path
        search_terms_path = Path(search_terms_input)
        if not search_terms_path.exists():
            raise FileNotFoundError(f"Search terms file not found: {search_terms_input}")
        
        with open(search_terms_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    except Exception as e:
        raise ValueError(f"Error loading search terms: {e}")


def main():
    """Main application entry point."""
    args = parse_arguments()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate inputs
        logger.info("Validating inputs...")
        validate_url(args.url)
        
        search_terms = load_search_terms(args.search_terms)
        validate_search_terms(search_terms)
        
        logger.info(f"Target URL: {args.url}")
        logger.info(f"Number of search terms: {len(search_terms)}")
        logger.info(f"Output file: {args.output}")
        
        # Initialize scraper engine
        logger.info("Initializing scraper engine...")
        scraper = ScraperEngine(
            timeout=args.timeout,
            max_results=args.max_results,
            use_pycurl=not args.no_pycurl
        )
        
        # Discover website structure and search capabilities
        logger.info("Discovering website structure...")
        website_info = scraper.discover_website_structure(args.url)
        
        # Perform searches and extract data
        logger.info("Starting data extraction...")
        results = scraper.scrape_data(args.url, search_terms, website_info)
        
        # Save results
        output_path = Path(args.output)
        if args.format == 'jsonl':
            # Save as JSONL format
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write metadata as first line
                f.write(json.dumps(results['metadata'], ensure_ascii=False) + '\n')
                # Write each result as a separate line
                for result in results.get('results', []):
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
        else:
            # Save as JSON format
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Scraping completed! Results saved to: {output_path}")
        logger.info(f"Total results extracted: {len(results.get('results', []))}")
        
        # Print summary
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Target Domain: {args.url}")
        print(f"Search Strategy: {website_info.get('search_strategy', 'Unknown')}")
        print(f"Total Search Terms: {len(search_terms)}")
        print(f"Total Results: {len(results.get('results', []))}")
        print(f"Output File: {output_path}")
        print("="*60)
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()