import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from portfolio import Portfolio

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class User:
    """
    Třída reprezentující uživatele aplikace.
    """
    
    def __init__(self, username: str, email: str):
        """
        Inicializace nového uživatele.
        
        Parametry:
            username: Uživatelské jméno
            email: E-mailová adresa uživatele
        """
        self.username: str = username
        self.email: str = email
        self.portfolio: Portfolio = Portfolio(name=f"Portfolio uživatele {username}")
        logger.debug(f"Uživatel {username} inicializován")
    
    def add_to_portfolio(self, ticker: str, quantity: float, purchase_price: float, 
                         purchase_date: datetime = None, notes: str = None) -> bool:
        """
        Přidání akcie do portfolia uživatele.
        
        Parametry:
            ticker: Symbol akcie
            quantity: Počet akcií
            purchase_price: Nákupní cena za akcii
            purchase_date: Datum nákupu
            notes: Volitelné poznámky k této akcii
            
        Vrací:
            True pokud úspěšné, jinak False
        """
        return self.portfolio.add_stock(ticker, quantity, purchase_price, purchase_date, notes)
    
    def remove_from_portfolio(self, ticker: str, quantity: float = None) -> bool:
        """
        Odstranění akcie z portfolia uživatele.
        
        Parametry:
            ticker: Symbol akcie
            quantity: Množství k odstranění (None = vše)
            
        Vrací:
            True pokud úspěšné, jinak False
        """
        return self.portfolio.remove_stock(ticker, quantity)
    
    def view_portfolio(self) -> Dict[str, Any]:
        """
        Získání přehledu portfolia uživatele s ukazateli výkonnosti.
        
        Vrací:
            Slovník s položkami portfolia a souhrnnou metrikou
        """
        try:
            portfolio_items = self.portfolio.get_portfolio()
            portfolio_summary = self.portfolio.get_total_value()
            
            return {
                'user': {
                    'username': self.username,
                    'email': self.email
                },
                'portfolio_name': self.portfolio.name,
                'items': portfolio_items,
                'summary': portfolio_summary
            }
        except Exception as e:
            logger.error(f"Error viewing portfolio for {self.username}: {str(e)}")
            return {
                'user': {
                    'username': self.username,
                    'email': self.email
                },
                'portfolio_name': self.portfolio.name,
                'items': [],
                'summary': {
                    'total_value': 0.0,
                    'total_cost': 0.0,
                    'total_gain_loss': 0.0,
                    'total_gain_loss_percent': 0.0,
                    'cash_balance': 0.0
                }
            }