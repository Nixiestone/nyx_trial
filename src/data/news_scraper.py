"""
News Scraper Module - COMPLETE
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..utils.logger import get_logger


class NewsScraper:
    """Fetches financial news from multiple sources."""
    
    def __init__(self, config):
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        self.newsapi_url = "https://newsapi.org/v2/everything"
    
    def fetch_news(
        self,
        query: str = "forex trading",
        hours_back: int = 24,
        max_articles: int = 50
    ) -> List[Dict]:
        """Fetch news articles from NewsAPI."""
        
        if not self.config.NEWS_API_KEY:
            self.logger.error("NEWS_API_KEY not configured")
            return []
        
        try:
            from_date = datetime.now() - timedelta(hours=hours_back)
            
            params = {
                'q': query,
                'from': from_date.isoformat(),
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': min(max_articles, 100),
                'apiKey': self.config.NEWS_API_KEY
            }
            
            response = requests.get(
                self.newsapi_url,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.error(f"NewsAPI returned status {response.status_code}")
                return []
            
            data = response.json()
            
            if data.get('status') != 'ok':
                self.logger.error(f"NewsAPI error: {data.get('message', 'Unknown')}")
                return []
            
            articles = data.get('articles', [])
            
            self.logger.info(f"Fetched {len(articles)} articles for '{query}'")
            
            return articles
            
        except requests.exceptions.Timeout:
            self.logger.error("NewsAPI request timed out")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"NewsAPI request failed: {e}")
            return []
        except Exception as e:
            self.logger.exception(f"Error fetching news: {e}")
            return []
    
    def fetch_symbol_news(self, symbol: str, hours_back: int = 24) -> List[Dict]:
        """Fetch news for a specific trading symbol."""
        
        # Symbol-specific queries
        query_map = {
            'EURUSD': 'EUR USD euro dollar forex',
            'GBPUSD': 'GBP USD pound sterling forex',
            'USDJPY': 'USD JPY yen forex',
            'GBPJPY': 'GBP JPY pound yen forex',
            'AUDUSD': 'AUD USD aussie dollar forex',
            'USDCAD': 'USD CAD loonie forex',
            'XAUUSD': 'gold XAU precious metals',
            'XAGUSD': 'silver XAG precious metals',
            'BTCUSD': 'bitcoin BTC cryptocurrency',
            'ETHUSD': 'ethereum ETH cryptocurrency',
            'US30': 'dow jones DJIA stock market',
            'NAS100': 'nasdaq NASDAQ tech stocks',
            'SPX500': 'S&P 500 SPX stock market'
        }
        
        query = query_map.get(symbol, f"{symbol} trading")
        
        return self.fetch_news(query=query, hours_back=hours_back)
    
    def fetch_general_market_news(self, hours_back: int = 24) -> List[Dict]:
        """Fetch general market news."""
        
        queries = [
            'forex trading',
            'stock market',
            'cryptocurrency',
            'financial markets'
        ]
        
        all_articles = []
        
        for query in queries:
            articles = self.fetch_news(
                query=query,
                hours_back=hours_back,
                max_articles=10
            )
            all_articles.extend(articles)
        
        # Remove duplicates based on URL
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        self.logger.info(f"Fetched {len(unique_articles)} unique general market articles")
        
        return unique_articles
    
    def format_article(self, article: Dict) -> Dict:
        """Format article for consistency."""
        
        return {
            'title': article.get('title', ''),
            'description': article.get('description', ''),
            'content': article.get('content', ''),
            'url': article.get('url', ''),
            'source': article.get('source', {}).get('name', 'Unknown'),
            'publishedAt': article.get('publishedAt', ''),
            'author': article.get('author', 'Unknown')
        }


if __name__ == "__main__":
    from config.settings import settings
    
    print("Testing News Scraper...")
    
    scraper = NewsScraper(settings)
    
    # Test general news
    articles = scraper.fetch_news("forex", hours_back=12, max_articles=5)
    print(f"\nFetched {len(articles)} articles")
    
    if articles:
        print("\nFirst article:")
        print(f"  Title: {articles[0].get('title', 'N/A')}")
        print(f"  Source: {articles[0].get('source', {}).get('name', 'N/A')}")
    
    # Test symbol-specific
    symbol_articles = scraper.fetch_symbol_news("EURUSD", hours_back=24)
    print(f"\nFetched {len(symbol_articles)} EURUSD articles")
    
    print("\nNews Scraper test completed!")