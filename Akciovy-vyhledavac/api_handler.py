import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from stock_data import StockData
from news_handler import NewsHandler

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class APIHandler:
    """
    Handler pro interakce s API, slouží jako pro StockData a NewsHandler.
    Poskytuje jednotné rozhraní pro načítání dat akcií a zpráv.
    """
    
    @staticmethod
    def fetch_stock_data(ticker: str, period: str = "1mo") -> pd.DataFrame:
        """
        Načítá data akcií pro daný ticker a období.
        
        Parametry:
            ticker: Symbol akcie (např. AAPL, MSFT)
            period: Časové období pro data (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Vrací:
            Pandas DataFrame s cenovými daty akcie
        """
        logger.debug(f"Načítám data akcií pro {ticker} s obdobím {period}")
        stock = StockData(ticker)
        return stock.get_history(period)
    
    @staticmethod
    def fetch_news(ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Načítá zprávy pro daný ticker.
        
        Parametry:
            ticker: Symbol akcie (např. AAPL, MSFT)
            limit: Maximální počet zpráv k vrácení
            
        Vrací:
            Seznam zpráv
        """
        logger.debug(f"Načítám zprávy pro {ticker}")
        return NewsHandler.get_stock_news(ticker, limit)
    
    @staticmethod
    def fetch_company_info(ticker: str) -> Dict[str, Any]:
        """
        Načítá informace o společnosti pro daný ticker.
        
        Parametry:
            ticker: Symbol akcie (např. AAPL, MSFT)
            
        Vrací:
            Slovník s informacemi o společnosti
        """
        logger.debug(f"Načítám informace o společnosti pro {ticker}")
        stock = StockData(ticker)
        return stock.get_company_info()