import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from portfolio import Portfolio

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class User:
    """
    Class representing a user of the application.
    """
    
    def __init__(self, username: str, email: str):
        """
        Initialize a new user.
        
        Args:
            username: The user's username
            email: The user's email address
        """
        self.username: str = username
        self.email: str = email
        self.portfolio: Portfolio = Portfolio(name=f"{username}'s Portfolio")
        logger.debug(f"User {username} initialized")
    
    def add_to_portfolio(self, ticker: str, quantity: float, purchase_price: float, 
                         purchase_date: datetime = None, notes: str = None) -> bool:
        """
        Add a stock to the user's portfolio.
        
        Args:
            ticker: The stock ticker symbol
            quantity: Number of shares
            purchase_price: Price per share at purchase
            purchase_date: Date of purchase
            notes: Optional notes about this stock
            
        Returns:
            True if successful, False otherwise
        """
        return self.portfolio.add_stock(ticker, quantity, purchase_price, purchase_date, notes)
    
    def remove_from_portfolio(self, ticker: str, quantity: float = None) -> bool:
        """
        Remove a stock from the user's portfolio.
        
        Args:
            ticker: The stock ticker symbol
            quantity: Quantity to remove (None = all)
            
        Returns:
            True if successful, False otherwise
        """
        return self.portfolio.remove_stock(ticker, quantity)
    
    def view_portfolio(self) -> Dict[str, Any]:
        """
        Get a view of the user's portfolio with performance metrics.
        
        Returns:
            Dictionary with portfolio items and summary metrics
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