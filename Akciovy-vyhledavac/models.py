from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default="Moje Portfolio")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztah s položkami portfolia
    items = db.relationship('PortfolioItem', backref='portfolio', lazy=True, cascade="all, delete-orphan")

class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    portfolio_id = db.Column(db.Integer, db.ForeignKey('portfolio.id'), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<PortfolioItem {self.ticker} - {self.quantity}>"