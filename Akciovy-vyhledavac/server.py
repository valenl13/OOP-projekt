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

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Použití SQLite pro lokální vývoj místo PostgreSQL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portfolio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Inicializace databáze
with app.app_context():
    try:
        db.create_all()
        logger.info("Databázové tabulky byly úspěšně vytvořeny")
    except Exception as e:
        logger.error(f"Chyba při vytváření databázových tabulek: {str(e)}")

# Ukládání dat aktivního uživatele v paměti (v reálné aplikaci by byla uložena v databázi)
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
                
                # Načtení zpráv pro tento ticker
                news_items = APIHandler.fetch_news(ticker, limit=5)
                
                if not stock_data.empty:
                    try:
                        # Získání názvu souboru s obrázkem z GraphGenerator
                        image_filename = GraphGenerator.plot_stock(stock_data, ticker, selected_period)
                        if image_filename:
                            # Nastavení URL obrázku pro šablonu
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
    # V reálné aplikaci bychom načítali uživatele ze session a jeho portfolio
    # z databáze. Tady používáme active_user z paměti.
    
    # Také načteme data z databáze pro zachování kompatibility se stávajícím kódem
    db_portfolio = DB_Portfolio.query.first()
    if not db_portfolio:
        db_portfolio = DB_Portfolio(name="Moje Portfolio")
        db.session.add(db_portfolio)
        db.session.commit()
    
    # Vytvoření cache pro data akcií, aby se zabránilo opakovaným API voláním pro stejný ticker
    stock_cache = {}
    
    # Synchronizace portfolia v paměti s databází pro demonstrační účely
    portfolio_items = []
    tickers = []
    
    # První průchod - shromáždění všech ticker symbolů
    for item in db_portfolio.items:
        tickers.append(item.ticker)
        
        # Přidání do portfolia v paměti, pokud tam ještě není
        active_user.add_to_portfolio(
            item.ticker,
            item.quantity,
            item.purchase_price,
            item.purchase_date,
            item.notes
        )
    
    # Hromadné načtení všech dat akcií nejprve pro zlepšení výkonu
    for ticker in tickers:
        try:
            if ticker not in stock_cache:
                stock = StockData(ticker)
                # Uložení instance akcie a informací o společnosti do cache pro opakované použití
                stock_cache[ticker] = {
                    'stock': stock,
                    'price': stock.get_price(),
                    'company_info': stock.get_company_info()
                }
        except Exception as e:
            logger.error(f"Error pre-loading data for {ticker}: {str(e)}")
            # Vytvoření prázdného záznamu v cache, aby se zabránilo opakovaným neúspěšným API voláním
            stock_cache[ticker] = {
                'stock': None,
                'price': 0.0,
                'company_info': {'name': ticker}
            }
    
    # Druhý průchod - sestavení položek portfolia s využitím dat z cache
    for item in db_portfolio.items:
        try:
            ticker = item.ticker
            
            # Získání dat z cache
            cache_data = stock_cache.get(ticker, {})
            current_price = cache_data.get('price', 0.0)
            company_info = cache_data.get('company_info', {'name': ticker})
            
            # Výpočet hodnot
            current_value = item.quantity * current_price
            cost_basis = item.quantity * item.purchase_price
            gain_loss = current_value - cost_basis
            gain_loss_percent = (gain_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            # Získání názvu společnosti z informací v cache
            company_name = company_info.get('name', ticker)
            
            # Přidání do položek portfolia pro zobrazení
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
    
    # Výpočet výkonnosti portfolia pomocí dat z cache
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
    # Získání nebo vytvoření výchozího portfolia
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
        
        # Validace vstupů
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
            
            # Přidání jak do portfolia v paměti, tak do databáze
            success = active_user.add_to_portfolio(
                ticker, quantity, purchase_price, purchase_date, notes
            )
            
            if success:
                # Přidání do databáze
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
    
    # Pokud jde o GET požadavek nebo validace formuláře selhala, zobrazí se formulář
    # Získání aktuálního tickeru z URL, pokud přicházíme ze stránky s detailem akcie
    ticker = request.args.get("ticker", "")
    current_price = None
    
    # Pokud je ticker poskytnut, získat aktuální cenu
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
        # Nalezení položky v databázi
        portfolio_item = PortfolioItem.query.get_or_404(item_id)
        ticker = portfolio_item.ticker
        
        # Odstranění jak z paměti, tak z databáze
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
    Porovnání více akcií
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
        # Získání tickerů z formuláře
        ticker1 = request.form.get("ticker1", "").strip().upper()
        ticker2 = request.form.get("ticker2", "").strip().upper()
        ticker3 = request.form.get("ticker3", "").strip().upper()
        selected_period = request.form.get("period", "1mo")
        
        # Sestavení seznamu tickerů (pouze neprázdné)
        tickers = [t for t in [ticker1, ticker2, ticker3] if t]
        
        if tickers:
            try:
                # Generování srovnávacího grafu
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
    Zobrazení profilu uživatele
    """
    # V reálné aplikaci bychom získali uživatele ze session
    # Zde používáme active_user z paměti
    
    # Výpočet souhrnu portfolia přímo, namísto použití metody,
    # která by znovu spustila API volání pro všechny akcie
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
        # Získání vypočtených hodnot ze stránky portfolia, aby se zabránilo přepočítávání
        # V reálné aplikaci by tyto hodnoty mohly být uloženy v cache nebo v session
        portfolio_items = []
        total_value = 0.0
        total_cost = 0.0
        
        for item in db_portfolio.items:
            try:
                purchase_value = item.quantity * item.purchase_price
                total_cost += purchase_value
                # Výpočet simulované aktuální hodnoty (o 5 % vyšší než nákupní cena)
                # Toto je pouze pro demonstraci, aby se zobrazil nenulový zisk/ztráta
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