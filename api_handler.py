import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from stock_data import StockData
from news_handler import NewsHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class APIHandler:
    """
    Handler for API interactions, serves as facade for StockData and NewsHandler.
    Provides unified interface for fetching stock data and news.
    """
    
    @staticmethod
    def fetch_stock_data(ticker: str, period: str = "1mo") -> pd.DataFrame:
        """
        Fetches stock data for a given ticker and period.
        
        Args:
            ticker: The stock ticker symbol (e.g. AAPL, MSFT)
            period: Time period for data (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            A pandas DataFrame with stock price data
        """
        logger.debug(f"Fetching stock data for {ticker} with period {period}")
        stock = StockData(ticker)
        return stock.get_history(period)
    
    @staticmethod
    def fetch_news(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches news for a given ticker.
        
        Args:
            ticker: The stock ticker symbol (e.g. AAPL, MSFT)
            limit: Maximum number of news items to return
            
        Returns:
            A list of news items
        """
        logger.debug(f"Fetching news for {ticker}")
        return NewsHandler.get_stock_news(ticker, limit)
    
    @staticmethod
    def fetch_company_info(ticker: str) -> Dict[str, Any]:
        """
        Fetches company information for a given ticker.
        
        Args:
            ticker: The stock ticker symbol (e.g. AAPL, MSFT)
            
        Returns:
            A dictionary with company information
        """
        logger.debug(f"Fetching company info for {ticker}")
        stock = StockData(ticker)
        return stock.get_company_info()