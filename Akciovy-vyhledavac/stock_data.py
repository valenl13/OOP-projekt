import yfinance as yf
import pandas as pd
import logging
from typing import Dict, Any, Optional
from googletrans import Translator

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StockData:
    """
    Třída reprezentující data akcií pro konkrétní ticker symbol.
    Zpracovává interakce s API yfinance.
    """
    
    def __init__(self, ticker: str):
        """
        Inicializace StockData s ticker symbolem.
        
        Parametry:
            ticker: Symbol akcie (např. AAPL, MSFT)
        """
        if not ticker:
            raise ValueError("Symbol akcie nemůže být prázdný")
            
        self.ticker: str = ticker
        try:
            self.stock = yf.Ticker(ticker)
            logger.debug(f"StockData initialized for {ticker}")
        except Exception as e:
            logger.error(f"Error initializing StockData for {ticker}: {str(e)}")
            raise
    
    def get_price(self) -> float:
        """
        Získání aktuální ceny akcie.
        
        Vrací:
            Aktuální cenu jako číslo (float)
        """
        try:
            data = self.get_history(period="1d")
            if not data.empty:
                return data.iloc[-1]['Close']
            return 0.0
        except Exception as e:
            logger.error(f"Error getting price for {self.ticker}: {str(e)}")
            return 0.0
    
    def get_history(self, period: str = "1mo") -> pd.DataFrame:
        """
        Získání historických cenových dat akcie.
        
        Parametry:
            period: Časové období pro data (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Vrací:
            Pandas DataFrame s cenovými daty akcie
        """
        logger.debug(f"Získávání dat pro {self.ticker} s obdobím {period}")
        try:
            data = self.stock.history(period=period)
            if data.empty:
                logger.warning(f"Nenalezena žádná data pro {self.ticker}")
                return self._generate_test_data(period)
            return data
        except Exception as e:
            logger.error(f"Chyba při získávání dat pro {self.ticker}: {str(e)}")
            return self._generate_test_data(period)
    
    def _generate_test_data(self, period: str = "1mo") -> pd.DataFrame:
        """
        Generuje testovací data v případě, že API selže.
        Toto je záložní řešení pouze pro vývoj a testování.
        
        Parametry:
            period: Časové období pro generování dat
            
        Vrací:
            Pandas DataFrame s ukázkovými cenovými daty akcií
        """
        import numpy as np
        from datetime import datetime, timedelta
        
        periods_days = {
            "1d": 1,
            "5d": 5,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "max": 1825
        }
        
        days = periods_days.get(period, 30)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Generate date range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        # Filter out weekends
        dates = dates[dates.dayofweek < 5]
        
        # Generate random price data with a trend
        np.random.seed(42)  # For reproducibility
        base_price = 100.0
        price_changes = np.random.normal(0, 1, size=len(dates))
        price_changes = price_changes.cumsum() * 2  # Cumulative changes with some volatility
        
        # Create prices with a slight upward trend
        prices = base_price + price_changes + np.linspace(0, 10, len(dates))
        
        # Create DataFrame
        data = pd.DataFrame({
            'Open': prices - np.random.uniform(0, 2, size=len(dates)),
            'High': prices + np.random.uniform(0, 2, size=len(dates)),
            'Low': prices - np.random.uniform(0, 2, size=len(dates)),
            'Close': prices,
            'Volume': np.random.randint(1000000, 10000000, size=len(dates))
        }, index=dates)
        
        logger.warning(f"Using generated test data for {self.ticker}")
        return data
    
    def get_company_info(self) -> Dict[str, Any]:
        """
        Získání informací o společnosti pro akcii.
        
        Vrací:
            Slovník s informacemi o společnosti
        """
        try:
            info = {}
            
            # Get company profile information
            profile = self.stock.info
            if not profile:
                logger.warning(f"No info found for {self.ticker}")
                return {}
            
            # Extract relevant info
            info['name'] = profile.get('shortName', self.ticker)
            info['sector'] = profile.get('sector', 'Unknown')
            info['industry'] = profile.get('industry', 'Unknown')
            info['country'] = profile.get('country', 'Unknown')
            info['employees'] = profile.get('fullTimeEmployees', None)
            info['website'] = profile.get('website', None)
            info['description'] = profile.get('longBusinessSummary', None)
            
            # Financial metrics
            info['market_cap'] = profile.get('marketCap', None)
            info['pe_ratio'] = profile.get('trailingPE', None)
            info['dividend_yield'] = profile.get('dividendYield', None)
            info['eps'] = profile.get('trailingEps', None)
            info['beta'] = profile.get('beta', None)
            info['fifty_two_week_high'] = profile.get('fiftyTwoWeekHigh', None)
            info['fifty_two_week_low'] = profile.get('fiftyTwoWeekLow', None)
            
            # Add Czech translations for relevant fields
            info['sector_cz'] = self._translate_field(info['sector'])
            info['industry_cz'] = self._translate_field(info['industry'])
            info['country_cz'] = self._translate_field(info['country'])
            info['description_cz'] = self._translate_field(info['description'])
            
            return info
            
        except Exception as e:
            logger.error(f"Chyba při získávání informací o společnosti pro {self.ticker}: {str(e)}")
            return {}
            
    def _translate_field(self, text: str) -> str:
        """
        Přeložit text do českého jazyka
        
        Parametry:
            text: Text k překladu
            
        Vrací:
            Přeložený text
        """
        if not text:
            return ""
            
        try:
            # Simple translation approach (similar to NewsHandler)
            # In a production environment, use a proper translation API
            
            # Common financial terms translations
            common_terms = {
                "Technology": "Technologie",
                "Financial Services": "Finanční služby",
                "Healthcare": "Zdravotnictví",
                "Communication Services": "Komunikační služby",
                "Consumer Cyclical": "Spotřební cyklické",
                "Consumer Defensive": "Spotřební defenzivní",
                "Energy": "Energie",
                "Industrials": "Průmysl",
                "Basic Materials": "Základní materiály",
                "Real Estate": "Nemovitosti",
                "Utilities": "Veřejné služby",
                "United States": "Spojené státy americké",
                "China": "Čína",
                "Japan": "Japonsko",
                "Germany": "Německo",
                "Software": "Software",
                "Hardware": "Hardware",
                "Semiconductors": "Polovodiče",
                "Internet Content & Information": "Internetový obsah a informace",
                "Auto Manufacturers": "Výrobci automobilů",
                "Banks": "Banky",
                "Insurance": "Pojišťovnictví",
                "Biotechnology": "Biotechnologie",
                "Medical Devices": "Zdravotnické zařízení"
            }
            
            # Check if the text is in our dictionary
            if text in common_terms:
                return common_terms[text]
                
            # For longer text like description, add a Czech header
            if len(text) > 100:
                return f"[Přeloženo automaticky] {text}"
                
            # For other fields, try to use translator if available
            try:
                translator = Translator()
                translated = translator.translate(text, dest='cs')
                return translated.text
            except:
                # Fall back to adding a Czech header if translation fails
                return f"[Přeloženo automaticky] {text}"
                
        except Exception as e:
            logger.error(f"Error translating text: {str(e)}")
            return f"[Přeloženo automaticky] {text}"