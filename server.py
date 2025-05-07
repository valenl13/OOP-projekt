from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import logging
import os
from datetime import datetime
from stock_data import StockData
from api_handler import APIHandler
from graph_generator import GraphGenerator
from portfolio import Portfolio
from user import User
from models import db, Portfolio as DB_Portfolio, PortfolioItem

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # Use SQLite as fallback if DATABASE_URL is not set
    database_url = "sqlite:///portfolio.db"
    logger.warning("DATABASE_URL not set, using SQLite database as fallback")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Initialize DB
with app.app_context():
    db.create_all()

# Store the active user's data in memory (in a real app, this would be stored in the DB)
active_user = User(username="Demo User", email="demo@example.com")

@app.route("/", methods=["GET", "POST"])
def index():
    chart = None
    error = None
    ticker = ""
    selected_period = "1mo"
    company_info = None
    news_items = []
    periods = [
        {"value": "1mo", "label": "1 měsíc"},
        {"value": "3mo", "label": "3 měsíce"},
        {"value": "6mo", "label": "6 měsíců"},
        {"value": "1y", "label": "1 rok"},
        {"value": "2y", "label": "2 roky"},
        {"value": "5y", "label": "5 let"},
    ]

    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip().upper()
        selected_period = request.form.get("period", "1mo")

        if ticker:
            try:
                logger.debug(f"Fetching stock data for {ticker} with period {selected_period}")
                stock_data = APIHandler.fetch_stock_data(ticker, period=selected_period)
                company_info = APIHandler.fetch_company_info(ticker)
                
                # Fetch news for this ticker
                news_items = APIHandler.fetch_news(ticker, limit=5)
                
                if not stock_data.empty:
                    try:
                        # Get image filename from GraphGenerator
                        image_filename = GraphGenerator.plot_stock(stock_data, ticker, selected_period)
                        if image_filename:
                            # Set the image URL for the template
                            chart = url_for('static', filename=f'images/{image_filename}')
                            logger.debug(f"Generated chart at: {chart}")
                        else:
                            error = f"Nepodařilo se vytvořit graf pro {ticker}"
                    except Exception as e:
                        logger.error(f"Error generating plot: {str(e)}")
                        error = f"Chyba při generování grafu: {str(e)}"
                else:
                    error = f"Nepodařilo se načíst data pro {ticker}"
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                error = f"Chyba při zpracování požadavku: {str(e)}"
        else:
            error = "Zadejte prosím symbol akcie"

    return render_template("index.html",
                           chart=chart,
                           error=error,
                           ticker=ticker,
                           selected_period=selected_period,
                           periods=periods,
                           company_info=company_info,
                           news_items=news_items)

@app.route("/api/stock-data", methods=["GET"])
def get_stock_data():
    ticker = request.args.get("ticker", "").strip().upper()
    period = request.args.get("period", "1mo")
    
    if not ticker:
        return jsonify({"error": "Ticker symbol is required"}), 400
    
    try:
        data = APIHandler.fetch_stock_data(ticker, period=period)
        return jsonify({
            "ticker": ticker,
            "period": period,
            "data": data.to_dict(orient="records")
        })
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/portfolio", methods=["GET"])
def portfolio():
    """
    View user's portfolio
    """
    # In a real app, we would get the user from the session and load their portfolio
    # from the database. Here we're using the active_user from memory.
    
    # We'll also load from the database to maintain compatibility with the existing code
    db_portfolio = DB_Portfolio.query.first()
    if not db_portfolio:
        db_portfolio = DB_Portfolio(name="Moje Portfolio")
        db.session.add(db_portfolio)
        db.session.commit()
    
    # Create a cache for stock data to prevent multiple API calls for the same ticker
    stock_cache = {}
    
    # Sync memory portfolio with database for demo purposes
    portfolio_items = []
    tickers = []
    
    # First pass - collect all tickers
    for item in db_portfolio.items:
        tickers.append(item.ticker)
        
        # Add to memory portfolio if not already there
        active_user.add_to_portfolio(
            item.ticker,
            item.quantity,
            item.purchase_price,
            item.purchase_date,
            item.notes
        )
    
    # Batch load all stock data first to improve performance
    for ticker in tickers:
        try:
            if ticker not in stock_cache:
                stock = StockData(ticker)
                # Cache the stock instance and company info to reuse
                stock_cache[ticker] = {
                    'stock': stock,
                    'price': stock.get_price(),
                    'company_info': stock.get_company_info()
                }
        except Exception as e:
            logger.error(f"Error pre-loading data for {ticker}: {str(e)}")
            # Create empty cache entry to avoid repeated failed API calls
            stock_cache[ticker] = {
                'stock': None,
                'price': 0.0,
                'company_info': {'name': ticker}
            }
    
    # Second pass - build portfolio items using cached data
    for item in db_portfolio.items:
        try:
            ticker = item.ticker
            
            # Get data from cache
            cache_data = stock_cache.get(ticker, {})
            current_price = cache_data.get('price', 0.0)
            company_info = cache_data.get('company_info', {'name': ticker})
            
            # Calculate values
            current_value = item.quantity * current_price
            cost_basis = item.quantity * item.purchase_price
            gain_loss = current_value - cost_basis
            gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            # Get company name from cached info
            company_name = company_info.get('name', ticker)
            
            # Add to portfolio items for display
            portfolio_items.append({
                'id': item.id,
                'ticker': item.ticker,
                'company_name': company_name,
                'quantity': item.quantity,
                'purchase_price': item.purchase_price,
                'purchase_date': item.purchase_date,
                'current_price': current_price,
                'current_value': current_value,
                'cost_basis': cost_basis,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent,
                'notes': item.notes
            })
        except Exception as e:
            logger.error(f"Error processing portfolio item {item.ticker}: {str(e)}")
    
    # Calculate portfolio performance using the cached data
    total_value = sum(item['current_value'] for item in portfolio_items)
    total_cost = sum(item['cost_basis'] for item in portfolio_items)
    total_gain_loss = total_value - total_cost
    total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
    
    portfolio_summary = {
        'total_value': total_value,
        'total_cost': total_cost,
        'total_gain_loss': total_gain_loss,
        'total_gain_loss_percent': total_gain_loss_percent
    }
    
    return render_template("portfolio.html", 
                           portfolio=db_portfolio,
                           portfolio_items=portfolio_items,
                           total_value=portfolio_summary['total_value'],
                           total_cost=portfolio_summary['total_cost'],
                           total_gain_loss=portfolio_summary['total_gain_loss'],
                           total_gain_loss_percent=portfolio_summary['total_gain_loss_percent'])

@app.route("/portfolio/add", methods=["GET", "POST"])
def add_to_portfolio():
    """
    Add stock to portfolio
    """
    # Get or create default portfolio
    db_portfolio = DB_Portfolio.query.first()
    if not db_portfolio:
        db_portfolio = DB_Portfolio(name="Moje Portfolio")
        db.session.add(db_portfolio)
        db.session.commit()
    
    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip().upper()
        quantity_str = request.form.get("quantity", "")
        purchase_price_str = request.form.get("purchase_price", "")
        purchase_date_str = request.form.get("purchase_date", "")
        notes = request.form.get("notes", "")
        
        # Validate inputs
        if not ticker or not quantity_str or not purchase_price_str:
            flash("Prosím vyplňte všechna povinná pole", "danger")
            return redirect(url_for("add_to_portfolio"))
        
        try:
            quantity = float(quantity_str)
            purchase_price = float(purchase_price_str)
            
            if purchase_date_str:
                purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d")
            else:
                purchase_date = datetime.utcnow()
            
            # Add to both memory portfolio and database
            success = active_user.add_to_portfolio(
                ticker, quantity, purchase_price, purchase_date, notes
            )
            
            if success:
                # Add to database
                portfolio_item = PortfolioItem(
                    portfolio_id=db_portfolio.id,
                    ticker=ticker,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    purchase_date=purchase_date,
                    notes=notes
                )
                
                db.session.add(portfolio_item)
                db.session.commit()
                
                flash(f"{ticker} úspěšně přidán do portfolia", "success")
                return redirect(url_for("portfolio"))
            else:
                flash(f"Chyba při přidávání akcie {ticker} do portfolia", "danger")
                
        except ValueError:
            flash("Neplatné hodnoty. Množství a cena musí být čísla.", "danger")
        except Exception as e:
            flash(f"Chyba při přidávání do portfolia: {str(e)}", "danger")
    
    # If GET request or form validation failed, display form
    # Get current ticker from the URL if coming from stock detail page
    ticker = request.args.get("ticker", "")
    current_price = None
    
    # If ticker is provided, get current price
    if ticker:
        try:
            stock = StockData(ticker)
            current_price = stock.get_price()
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {str(e)}")
    
    return render_template("add_to_portfolio.html", 
                          ticker=ticker, 
                          current_price=current_price,
                          today=datetime.now().strftime("%Y-%m-%d"))

@app.route("/portfolio/delete/<int:item_id>", methods=["POST"])
def delete_from_portfolio(item_id):
    """
    Delete stock from portfolio
    """
    try:
        # Find the item in database
        portfolio_item = PortfolioItem.query.get_or_404(item_id)
        ticker = portfolio_item.ticker
        
        # Remove from both memory and database
        active_user.remove_from_portfolio(ticker)
        
        db.session.delete(portfolio_item)
        db.session.commit()
        
        flash(f"{ticker} byl odebrán z portfolia", "success")
    except Exception as e:
        flash(f"Chyba při odebírání z portfolia: {str(e)}", "danger")
    
    return redirect(url_for("portfolio"))

@app.route("/compare", methods=["GET", "POST"])
def compare_stocks():
    """
    Compare multiple stocks
    """
    chart = None
    error = None
    tickers = []
    selected_period = "1mo"
    
    periods = [
        {"value": "1mo", "label": "1 měsíc"},
        {"value": "3mo", "label": "3 měsíce"},
        {"value": "6mo", "label": "6 měsíců"},
        {"value": "1y", "label": "1 rok"},
        {"value": "2y", "label": "2 roky"},
        {"value": "5y", "label": "5 let"},
    ]
    
    if request.method == "POST":
        # Get tickers from form
        ticker1 = request.form.get("ticker1", "").strip().upper()
        ticker2 = request.form.get("ticker2", "").strip().upper()
        ticker3 = request.form.get("ticker3", "").strip().upper()
        selected_period = request.form.get("period", "1mo")
        
        # Build ticker list (only non-empty)
        tickers = [t for t in [ticker1, ticker2, ticker3] if t]
        
        if tickers:
            try:
                # Generate comparison chart
                image_filename = GraphGenerator.plot_comparison(tickers, selected_period)
                if image_filename:
                    chart = url_for('static', filename=f'images/{image_filename}')
                    logger.debug(f"Generated comparison chart at: {chart}")
            except Exception as e:
                logger.error(f"Error generating comparison chart: {str(e)}")
                error = f"Chyba při generování grafu: {str(e)}"
        else:
            error = "Zadejte prosím alespoň jeden symbol akcie"
    
    return render_template("compare.html",
                           chart=chart,
                           error=error,
                           tickers=tickers,
                           selected_period=selected_period,
                           periods=periods)

@app.route("/user/profile", methods=["GET"])
def user_profile():
    """
    View user profile
    """
    # In a real app, we would get the user from the session
    # Here we're using the active_user from memory
    
    # Calculate portfolio summary directly instead of using the method
    # which would trigger API calls for all stocks again
    db_portfolio = DB_Portfolio.query.first()
    if not db_portfolio:
        portfolio_summary = {
            'total_value': 0.0,
            'total_cost': 0.0,
            'total_gain_loss': 0.0,
            'total_gain_loss_percent': 0.0,
            'cash_balance': 0.0
        }
    else:
        # Get the calculated values from the portfolio page to avoid recalculating
        # In a real app, these values might be cached or stored in the session
        portfolio_items = []
        total_value = 0.0
        total_cost = 0.0
        
        for item in db_portfolio.items:
            try:
                purchase_value = item.quantity * item.purchase_price
                total_cost += purchase_value
                # Calculate a simulated current value (5% higher than purchase price)
                # This is just for demonstration to show non-zero profit/loss
                current_value = item.quantity * (item.purchase_price * 1.05)
                total_value += current_value
            except Exception as e:
                logger.error(f"Error processing portfolio item: {str(e)}")
        
        total_gain_loss = total_value - total_cost
        total_gain_loss_percent = (total_gain_loss / total_cost) * 100 if total_cost > 0 else 0
        
        portfolio_summary = {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain_loss': total_gain_loss,
            'total_gain_loss_percent': total_gain_loss_percent,
            'cash_balance': 0.0  # Placeholder for actual balance
        }
    
    return render_template("user_profile.html", 
                          user=active_user,
                          portfolio_summary=portfolio_summary)

if __name__ == "__main__":
    app.run(debug=True)