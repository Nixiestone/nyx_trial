"""
Sentiment Analysis Module
Author: BLESSING OMOREGIE
GitHub: Nixiestone
Repository: nyx_trial

Analyzes market sentiment from news and social data.
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np

from ..utils.logger import get_logger


class SentimentAnalyzer:
    """
    Analyzes sentiment from news articles and text data.
    Uses multiple sentiment analysis methods and combines them.
    """
    
    def __init__(self, config):
        """
        Initialize sentiment analyzer.
        
        Args:
            config: Settings object
        """
        self.config = config
        self.logger = get_logger(__name__, config.LOG_LEVEL, config.LOG_FILE_PATH)
        
        # Initialize VADER sentiment analyzer
        self.vader = SentimentIntensityAnalyzer()
        
        # Financial keywords for enhanced analysis
        self.bullish_keywords = [
            'bullish', 'rally', 'surge', 'gain', 'rise', 'increase',
            'growth', 'positive', 'strong', 'buy', 'uptrend', 'breakout',
            'support', 'accumulation', 'momentum', 'strength', 'optimistic'
        ]
        
        self.bearish_keywords = [
            'bearish', 'crash', 'drop', 'fall', 'decline', 'decrease',
            'negative', 'weak', 'sell', 'downtrend', 'breakdown', 'resistance',
            'distribution', 'fear', 'pessimistic', 'loss', 'dump'
        ]
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment scores
        """
        if not text:
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'method': 'none'
            }
        
        try:
            # Method 1: VADER (specialized for social media)
            vader_scores = self.vader.polarity_scores(text)
            vader_compound = vader_scores['compound']
            
            # Method 2: TextBlob (general purpose)
            blob = TextBlob(text)
            textblob_polarity = blob.sentiment.polarity
            
            # Method 3: Keyword-based (financial specific)
            keyword_score = self._analyze_keywords(text)
            
            # Combine scores (weighted average)
            combined_score = (
                vader_compound * 0.4 +
                textblob_polarity * 0.3 +
                keyword_score * 0.3
            )
            
            # Normalize to -1 to 1 range
            combined_score = max(-1.0, min(1.0, combined_score))
            
            # Determine label
            if combined_score >= self.config.SENTIMENT_THRESHOLD_BULLISH:
                label = 'bullish'
            elif combined_score <= self.config.SENTIMENT_THRESHOLD_BEARISH:
                label = 'bearish'
            else:
                label = 'neutral'
            
            # Calculate confidence (absolute value)
            confidence = abs(combined_score)
            
            return {
                'score': round(combined_score, 3),
                'label': label,
                'confidence': round(confidence, 3),
                'vader': round(vader_compound, 3),
                'textblob': round(textblob_polarity, 3),
                'keyword': round(keyword_score, 3)
            }
            
        except Exception as e:
            self.logger.exception(f"Error analyzing text: {e}")
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'method': 'error'
            }
    
    def analyze_news_batch(self, news_articles: List[Dict]) -> Dict:
        """
        Analyze sentiment from multiple news articles.
        
        Args:
            news_articles: List of news article dictionaries
                Each dict should have 'title', 'description', 'content'
            
        Returns:
            Aggregated sentiment analysis
        """
        if not news_articles:
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'article_count': 0
            }
        
        try:
            sentiments = []
            
            for article in news_articles:
                # Combine title and description for analysis
                text = f"{article.get('title', '')} {article.get('description', '')}"
                
                if text.strip():
                    sentiment = self.analyze_text(text)
                    sentiments.append(sentiment)
            
            if not sentiments:
                return {
                    'score': 0.0,
                    'label': 'neutral',
                    'confidence': 0.0,
                    'article_count': 0
                }
            
            # Calculate weighted average
            scores = [s['score'] for s in sentiments]
            confidences = [s['confidence'] for s in sentiments]
            
            # Weight by confidence
            weighted_score = sum(
                score * conf for score, conf in zip(scores, confidences)
            ) / sum(confidences) if sum(confidences) > 0 else 0.0
            
            # Average confidence
            avg_confidence = np.mean(confidences)
            
            # Determine label
            if weighted_score >= self.config.SENTIMENT_THRESHOLD_BULLISH:
                label = 'bullish'
            elif weighted_score <= self.config.SENTIMENT_THRESHOLD_BEARISH:
                label = 'bearish'
            else:
                label = 'neutral'
            
            # Count distribution
            bullish_count = sum(1 for s in sentiments if s['label'] == 'bullish')
            bearish_count = sum(1 for s in sentiments if s['label'] == 'bearish')
            neutral_count = sum(1 for s in sentiments if s['label'] == 'neutral')
            
            result = {
                'score': round(weighted_score, 3),
                'label': label,
                'confidence': round(avg_confidence, 3),
                'article_count': len(sentiments),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'neutral_count': neutral_count,
                'distribution': {
                    'bullish': round(bullish_count / len(sentiments), 2),
                    'bearish': round(bearish_count / len(sentiments), 2),
                    'neutral': round(neutral_count / len(sentiments), 2)
                }
            }
            
            self.logger.sentiment_analysis(
                "BATCH",
                {
                    'score': result['score'],
                    'label': result['label'],
                    'confidence': result['confidence']
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.exception(f"Error analyzing news batch: {e}")
            return {
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'article_count': 0
            }
    
    def analyze_symbol_sentiment(
        self,
        symbol: str,
        news_articles: List[Dict],
        time_decay_hours: int = 24
    ) -> Dict:
        """
        Analyze sentiment for a specific trading symbol.
        Applies time decay to give more weight to recent news.
        
        Args:
            symbol: Trading symbol
            news_articles: List of news articles
            time_decay_hours: Hours for time decay calculation
            
        Returns:
            Symbol-specific sentiment analysis
        """
        if not news_articles:
            return {
                'symbol': symbol,
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'article_count': 0
            }
        
        try:
            # Filter articles relevant to symbol
            relevant_articles = self._filter_relevant_articles(symbol, news_articles)
            
            if not relevant_articles:
                return {
                    'symbol': symbol,
                    'score': 0.0,
                    'label': 'neutral',
                    'confidence': 0.0,
                    'article_count': 0
                }
            
            # Analyze with time decay
            sentiments = []
            current_time = datetime.now()
            
            for article in relevant_articles:
                # Get article timestamp
                published_at = article.get('publishedAt')
                if isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except:
                        published_at = current_time
                elif not isinstance(published_at, datetime):
                    published_at = current_time
                
                # Calculate time decay weight
                hours_old = (current_time - published_at).total_seconds() / 3600
                decay_factor = np.exp(-hours_old / time_decay_hours)
                
                # Analyze sentiment
                text = f"{article.get('title', '')} {article.get('description', '')}"
                sentiment = self.analyze_text(text)
                sentiment['weight'] = decay_factor
                
                sentiments.append(sentiment)
            
            # Calculate weighted score
            total_weight = sum(s['weight'] for s in sentiments)
            weighted_score = sum(
                s['score'] * s['weight'] for s in sentiments
            ) / total_weight if total_weight > 0 else 0.0
            
            # Calculate confidence
            avg_confidence = np.mean([s['confidence'] for s in sentiments])
            
            # Determine label
            if weighted_score >= self.config.SENTIMENT_THRESHOLD_BULLISH:
                label = 'bullish'
            elif weighted_score <= self.config.SENTIMENT_THRESHOLD_BEARISH:
                label = 'bearish'
            else:
                label = 'neutral'
            
            result = {
                'symbol': symbol,
                'score': round(weighted_score, 3),
                'label': label,
                'confidence': round(avg_confidence, 3),
                'article_count': len(sentiments),
                'recent_article_count': sum(1 for s in sentiments if s['weight'] > 0.5)
            }
            
            self.logger.sentiment_analysis(
                symbol,
                result
            )
            
            return result
            
        except Exception as e:
            self.logger.exception(f"Error analyzing symbol sentiment: {e}")
            return {
                'symbol': symbol,
                'score': 0.0,
                'label': 'neutral',
                'confidence': 0.0,
                'article_count': 0
            }
    
    def _analyze_keywords(self, text: str) -> float:
        """
        Analyze text using financial keywords.
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score based on keywords
        """
        text_lower = text.lower()
        
        # Count keyword occurrences
        bullish_count = sum(
            text_lower.count(keyword) for keyword in self.bullish_keywords
        )
        bearish_count = sum(
            text_lower.count(keyword) for keyword in self.bearish_keywords
        )
        
        total_count = bullish_count + bearish_count
        
        if total_count == 0:
            return 0.0
        
        # Calculate score
        score = (bullish_count - bearish_count) / total_count
        
        return score
    
    def _filter_relevant_articles(
        self,
        symbol: str,
        articles: List[Dict]
    ) -> List[Dict]:
        """
        Filter articles relevant to a trading symbol.
        
        Args:
            symbol: Trading symbol
            articles: List of articles
            
        Returns:
            Filtered list of relevant articles
        """
        # Symbol mapping for better matching
        symbol_keywords = {
            'EURUSD': ['euro', 'eur', 'usd', 'dollar', 'europe', 'fed', 'ecb'],
            'GBPUSD': ['pound', 'gbp', 'sterling', 'uk', 'britain', 'boe'],
            'USDJPY': ['yen', 'jpy', 'japan', 'boj'],
            'XAUUSD': ['gold', 'xau', 'precious', 'metal'],
            'BTCUSD': ['bitcoin', 'btc', 'crypto', 'cryptocurrency'],
            'US30': ['dow', 'dow jones', 'us30', 'stock'],
            'NAS100': ['nasdaq', 'tech', 'technology'],
        }
        
        keywords = symbol_keywords.get(symbol, [symbol.lower()])
        
        relevant = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()
            
            # Check if any keyword is in the article
            if any(keyword in text for keyword in keywords):
                relevant.append(article)
        
        return relevant


if __name__ == "__main__":
    # Test sentiment analyzer
    from config.settings import settings
    
    print("Testing Sentiment Analyzer...")
    
    analyzer = SentimentAnalyzer(settings)
    
    # Test single text
    test_texts = [
        "EUR/USD rallies higher as markets remain optimistic about economic growth",
        "Gold prices plunge amid fears of recession and market uncertainty",
        "Bitcoin shows neutral movement with mixed signals from traders"
    ]
    
    for text in test_texts:
        result = analyzer.analyze_text(text)
        print(f"\nText: {text}")
        print(f"Score: {result['score']}, Label: {result['label']}, Confidence: {result['confidence']}")
    
    # Test news batch
    test_articles = [
        {'title': 'EUR/USD breaks resistance', 'description': 'Strong bullish momentum'},
        {'title': 'Market fears grow', 'description': 'Bearish sentiment dominates'},
        {'title': 'Economic data mixed', 'description': 'Neutral outlook prevails'}
    ]
    
    batch_result = analyzer.analyze_news_batch(test_articles)
    print(f"\nBatch Analysis:")
    print(f"Score: {batch_result['score']}, Label: {batch_result['label']}")
    print(f"Distribution: {batch_result['distribution']}")
    
    print("\nSentiment Analyzer test completed!")