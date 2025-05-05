import yfinance as yf

class APIHandler:
    @staticmethod
    def get_stock_data(ticker: str):
        stock = yf.Ticker(ticker)
        return stock.history(period="1mo")
