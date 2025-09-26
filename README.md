# Intelligent Web Scraper

A comprehensive Python application that intelligently discovers website search capabilities and extracts data efficiently. The scraper automatically determines the best way to search a target website and extracts relevant information based on provided search terms.

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd scrapper
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Run your first scrape
python main.py -u https://bt4gprx.com/ -s search_terms.json
```

## Features

- **Intelligent Website Analysis**: Automatically discovers website structure and search capabilities
- **Multiple Search Strategies**: Supports form-based search, query parameters, sitemap crawling, and JavaScript-heavy sites
- **Dynamic Content Support**: Uses Playwright for websites requiring JavaScript execution
- **Comprehensive Data Extraction**: Extracts URLs, titles, descriptions, metadata, and more
- **Respectful Crawling**: Implements delays and follows robots.txt guidelines
- **Quality Scoring**: Provides data quality scores for each result
- **Flexible Input**: Accepts JSON search terms with custom fields
- **Detailed Logging**: Comprehensive logging for debugging and monitoring

## Installation

### Option 1: Using Virtual Environment (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd scrapper
```

2. Create a virtual environment:
```bash
# Using venv (Python 3.3+)
python3 -m venv venv

# Or using virtualenv
virtualenv venv
```

3. Activate the virtual environment:
```bash
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

4. Upgrade pip and install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. (Optional) Install Playwright browsers for JavaScript support:
```bash
playwright install
```

6. (Optional) Install system dependencies for Playwright (Linux):
```bash
sudo playwright install-deps
```

### Option 2: Global Installation (Not Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd scrapper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Install Playwright browsers for JavaScript support:
```bash
playwright install
```

### Virtual Environment Management

**Activating the virtual environment:**
```bash
# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Deactivating the virtual environment:**
```bash
deactivate
```

**Removing the virtual environment:**
```bash
# Simply delete the venv directory
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows
```

**Creating a new virtual environment:**
```bash
# Remove old environment
rm -rf venv

# Create new environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

### Basic Usage

**Make sure to activate your virtual environment first:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Run the scraper
python main.py -u https://example.com -s search_terms.json
```

### Command Line Options

- `-u, --url`: Target domain URL (homepage) to scrape (required)
- `-s, --search-terms`: JSON file path or JSON string containing search terms (required)
- `-o, --output`: Output file path for results (default: scraped_results.json)
- `-v, --verbose`: Enable verbose logging
- `--max-results`: Maximum number of results per search term (default: 50)
- `--timeout`: Request timeout in seconds (default: 30)

### Search Terms Format

Create a JSON file with your search terms:

```json
[
  {
    "id": 1,
    "Artist": "Beyonce",
    "Title": "Single Ladies (Put a ring on it)"
  },
  {
    "id": 2,
    "Artist": "Beyonce", 
    "Title": "Halo"
  },
  {
    "id": 3,
    "Artist": "Taylor Swift",
    "Title": "Shake It Off"
  }
]
```

### Example Commands

**Remember to activate your virtual environment first:**
```bash
source venv/bin/activate  # Linux/macOS
```

```bash
# Basic scraping
python main.py -u https://bt4gprx.com/ -s search_terms.json

# With custom output and verbose logging
python main.py -u https://example.com -s search_terms.json -o results.json -v

# Using JSON string directly
python main.py -u https://example.com -s '[{"id": 1, "Artist": "Beyonce", "Title": "Single Ladies"}]'

# With custom timeout and max results
python main.py -u https://example.com -s search_terms.json --timeout 60 --max-results 100

# JSONL output format
python main.py -u https://example.com -s search_terms.json --format jsonl -o results.jsonl

# Disable pycurl (use requests instead)
python main.py -u https://example.com -s search_terms.json --no-pycurl
```

## Output Format

The scraper generates a JSON file with the following structure:

```json
{
  "metadata": {
    "target_url": "https://example.com",
    "domain": "example.com",
    "search_strategy": "form",
    "timestamp": 1672531200.0,
    "total_search_terms": 2,
    "website_info": {
      "has_search_form": true,
      "search_endpoints": ["https://example.com/search"],
      "search_params": {"q": "SEARCH_TERM"},
      "requires_js": false
    }
  },
  "results": [
    {
      "search_term_id": 1,
      "search_term_data": {
        "id": 1,
        "Artist": "Beyonce",
        "Title": "Single Ladies"
      },
      "url": "https://example.com/beyonce-single-ladies",
      "title": "Beyonce - Single Ladies (Put a ring on it)",
      "description": "Official music video for Single Ladies",
      "query": "Beyonce Single Ladies",
      "source_url": "https://example.com/search",
      "extraction_timestamp": 1672531200.0,
      "page_title": "Beyonce - Single Ladies",
      "page_description": "Official music video...",
      "page_keywords": "beyonce, single ladies, music video",
      "page_content_length": 2500,
      "page_images": ["https://example.com/image1.jpg"],
      "page_links": ["https://example.com/link1"],
      "page_language": "en",
      "data_quality_score": 85.0
    }
  ]
}
```

## Search Strategies

The scraper automatically determines the best search strategy:

1. **Form Search**: Detects and uses search forms on the website
2. **Query Parameter Search**: Uses URL parameters (e.g., `?q=search_term`)
3. **Sitemap Search**: Searches through website sitemaps
4. **Playwright Search**: Uses browser automation for JavaScript-heavy sites

## Architecture

```
scraper/
├── core/
│   └── scraper_engine.py      # Main orchestration engine
├── discovery/
│   └── website_analyzer.py    # Website structure analysis
├── strategies/
│   ├── search_strategies.py   # Core search strategies
│   └── playwright_strategy.py # JavaScript-heavy sites
├── extractors/
│   └── data_extractor.py      # Data extraction and enrichment
└── utils/
    ├── logger.py              # Logging configuration
    ├── validators.py          # Input validation
    └── helpers.py             # Utility functions
```

## Configuration

The scraper respects robots.txt files and implements respectful crawling practices:

- Delays between requests
- User-Agent rotation
- Rate limiting
- Error handling and retries

## Error Handling

The scraper includes comprehensive error handling:

- Network timeouts and connection errors
- Invalid URLs and malformed responses
- Missing or invalid search terms
- Website structure analysis failures

## Logging

Logs are written to both console and `logs/scraper.log`:

- INFO: General progress and results
- DEBUG: Detailed debugging information (use `-v` flag)
- ERROR: Error conditions and failures

## Performance

- Concurrent processing where possible
- Configurable timeouts and delays
- Memory-efficient data processing
- Quality scoring for result prioritization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting

### Common Issues

1. **Virtual environment not activated**: Make sure to run `source venv/bin/activate` before using the scraper
2. **Python not found**: Ensure Python 3.7+ is installed and accessible
3. **Permission errors**: On Linux/macOS, you might need `sudo` for system-wide installations
4. **Playwright not working**: Install browsers with `playwright install`
5. **Timeout errors**: Increase timeout with `--timeout` parameter
6. **No results found**: Check if the website requires JavaScript or has anti-bot measures
7. **Invalid JSON**: Ensure search terms file is valid JSON format
8. **pycurl installation issues**: Use `--no-pycurl` flag to fallback to requests library

### Debug Mode

Use verbose logging to debug issues:

```bash
python main.py -u https://example.com -s search_terms.json -v
```

### Support

For issues and questions, please open an issue on the GitHub repository.