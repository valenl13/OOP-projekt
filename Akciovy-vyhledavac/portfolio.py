import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from stock_data import StockData
from graph_generator import GraphGenerator

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Portfolio:
    """
    Třída reprezentující akciové portfolio uživatele.
    """
    
    def __init__(self, name: str = "My Portfolio", balance: float = 0.0):
        """
        Inicializace nového portfolia.
        
        Parametry:
            name: Název portfolia
            balance: Hotovostní zůstatek v portfoliu
        """
        self.name: str = name
        self.stocks: Dict[str, Dict[str, Any]] = {}  # Slovník ticker -> detaily akcie
        self.balance: float = balance
        logger.debug(f"Portfolio '{name}' inicializováno")
    
    def add_stock(self, ticker: str, quantity: float, purchase_price: float, 
                  purchase_date: datetime = None, notes: str = None) -> bool:
        """
        Přidání akcie do portfolia nebo aktualizace existující.
        
        Parametry:
            ticker: Symbol akcie
            quantity: Počet akcií
            purchase_price: Nákupní cena za akcii
            purchase_date: Datum nákupu
            notes: Volitelné poznámky k této akcii
            
        Vrací:
            True pokud úspěšné, jinak False
        """
        try:
            if not purchase_date:
                purchase_date = datetime.now()
                
            # Check if stock already exists
            if ticker in self.stocks:
                # Calculate new average purchase price
                current = self.stocks[ticker]
                total_shares = current['quantity'] + quantity
                total_cost = (current['quantity'] * current['purchase_price']) + (quantity * purchase_price)
                avg_price = total_cost / total_shares if total_shares > 0 else 0
                
                # Update stock entry
                self.stocks[ticker]['quantity'] = total_shares
                self.stocks[ticker]['purchase_price'] = avg_price
                self.stocks[ticker]['notes'] = notes or current['notes']
                
                logger.debug(f"Updated {ticker} in portfolio, new quantity: {total_shares}")
            else:
                # Add new stock
                self.stocks[ticker] = {
                    'ticker': ticker,
                    'quantity': quantity,
                    'purchase_price': purchase_price,
                    'purchase_date': purchase_date,
                    'notes': notes
                }
                logger.debug(f"Added {ticker} to portfolio, quantity: {quantity}")
                
            return True
        except Exception as e:
            logger.error(f"Error adding stock to portfolio: {str(e)}")
            return False
    
    def remove_stock(self, ticker: str, quantity: float = None) -> bool:
        """
        Remove a stock or reduce quantity from the portfolio.
        
        Args:
            ticker: The stock ticker symbol
            quantity: Quantity to remove (None = all)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if ticker not in self.stocks:
                logger.warning(f"{ticker} not found in portfolio")
                return False
                
            if quantity is None or quantity >= self.stocks[ticker]['quantity']:
                # Remove entire position
                del self.stocks[ticker]
                logger.debug(f"Removed {ticker} from portfolio")
            else:
                # Reduce position
                self.stocks[ticker]['quantity'] -= quantity
                logger.debug(f"Reduced {ticker} in portfolio by {quantity}")
                
            return True
        except Exception as e:
            logger.error(f"Error removing stock from portfolio: {str(e)}")
            return False
    
    def get_portfolio(self) -> List[Dict[str, Any]]:
        """
        Get all stocks in the portfolio with current prices and performance.
        
        Returns:
            List of portfolio items with performance metrics
        """
        try:
            portfolio_items = []
            
            for ticker, stock_data in self.stocks.items():
                try:
                    # Get current data
                    stock = StockData(ticker)
                    current_price = stock.get_price()
                    company_info = stock.get_company_info()
                    
                    # Calculate performance
                    quantity = stock_data['quantity']
                    purchase_price = stock_data['purchase_price']
                    current_value = quantity * current_price
                    cost_basis = quantity * purchase_price
                    gain_loss = current_value - cost_basis
                    gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
                    
                    # Create portfolio item with all information
                    item = {
                        'ticker': ticker,
                        'company_name': company_info.get('name', ticker),
                        'quantity': quantity,
                        'purchase_price': purchase_price,
                        'purchase_date': stock_data['purchase_date'],
                        'current_price': current_price,
                        'current_value': current_value,
                        'cost_basis': cost_basis,
                        'gain_loss': gain_loss,
                        'gain_loss_percent': gain_loss_percent,
                        'notes': stock_data['notes']
                    }
                    
                    portfolio_items.append(item)
                except Exception as e:
                    logger.error(f"Error processing portfolio item {ticker}: {str(e)}")
            
            return portfolio_items
        except Exception as e:
            logger.error(f"Error getting portfolio: {str(e)}")
            return []
    
    def get_total_value(self) -> Dict[str, float]:
        """
        Calculate the total value and performance of the portfolio.
        
        Returns:
            Dictionary with total value, cost, and performance metrics
        """
        try:
            total_value = 0.0
            total_cost = 0.0
            
            portfolio_items = self.get_portfolio()
            for item in portfolio_items:
                total_value += item['current_value']
                total_cost += item['cost_basis']
            
            # Add cash balance
            total_value += self.balance
            
            # Calculate performance
            total_gain_loss = total_value - total_cost - self.balance
            total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
            
            return {
                'total_value': total_value,
                'total_cost': total_cost,
                'total_gain_loss': total_gain_loss,
                'total_gain_loss_percent': total_gain_loss_percent,
                'cash_balance': self.balance
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio total value: {str(e)}")
            return {
                'total_value': 0.0,
                'total_cost': 0.0,
                'total_gain_loss': 0.0,
                'total_gain_loss_percent': 0.0,
                'cash_balance': self.balance
            }