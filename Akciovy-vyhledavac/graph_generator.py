import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import base64
from io import BytesIO
import logging
import os
import uuid
import time
from typing import Optional, List, Dict, Any
from stock_data import StockData

# Konfigurace logování
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class GraphGenerator:
    """
    Třída pro generování vizualizací a grafů akcií.
    """

    @staticmethod
    def plot_stock(data: pd.DataFrame, ticker: str, period: str) -> str:
        """
        Vytvoří graf ceny akcie na základě poskytnutých dat.
        
        Parametry:
            data: DataFrame obsahující data o ceně akcie
            ticker: Symbol akcie
            period: Zobrazené časové období
            
        Vrací:
            Cestu k uloženému souboru s obrázkem
        """
        logger.debug(f"Vytvářím graf pro {ticker} s {len(data)} datovými body")

        try:
            # změna barvy pro lepší vizualizaci
            plt.style.use('dark_background')

            # pro čitelnější graf a lepší rozlišení
            fig, ax = plt.subplots(figsize=(12, 7), dpi=100)

            # tohle zjistí proč se cena změnila a nastaví barvu
            if len(data) > 1:
                start_price = data['Close'].iloc[0]
                end_price = data['Close'].iloc[-1]
                price_change = end_price - start_price
                color = '#2ecc71' if price_change >= 0 else '#e74c3c'  #  zelena kdyz roste, cervena kdyz klesa
            else:
                color = '#3498db'  # modra pokud je jen jeden bod

            # finalni graf s lepšími stylovými prvky
            ax.plot(data.index, data['Close'], color=color, linewidth=2.5)

            # pridani plochy pod graf pro lepší vizualizaci
            ax.fill_between(data.index, data['Close'], alpha=0.2, color=color)

            # pridani titulku a popisku osy
            title = f"{ticker} - Cena akcie ({period})"
            if len(data) > 1:
                percent_change = (price_change / start_price) * 100
                change_text = f" | Změna: {price_change:.2f} ({percent_change:.2f}%)"
                title += change_text

            ax.set_title(title, fontsize=16, fontweight='bold', color='white')
            ax.set_xlabel('Datum', fontsize=14, color='white')
            ax.set_ylabel('Cena (USD)', fontsize=14, color='white')

            # formatovaní osy y
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, color='white')
            plt.yticks(color='white')

            # vylepšení grafu (mřížka)
            ax.grid(True, linestyle='--', alpha=0.3, color='gray')

            # ohraničení
            for spine in ax.spines.values():
                spine.set_edgecolor('gray')
                spine.set_linewidth(0.5)

            # Adjust layout
            plt.tight_layout()

            # Generate a unique filename
            filename = f"{ticker}_{period}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join('static', 'images', filename)

            # Save the figure to a file
            plt.savefig(filepath, format='png', dpi=120, bbox_inches='tight')
            plt.close()

            # Return the path to the saved image
            return filename

        except Exception as e:
            logger.error(f"Error creating plot: {str(e)}")
            return ""

    @staticmethod
    def plot_comparison(tickers: List[str], period: str = "1mo") -> str:
        """
        Vytvoří srovnávací graf více akcií.
        
        Parametry:
            tickers: Seznam symbolů akcií ke srovnání
            period: Časové období pro data
            
        Vrací:
            Cestu k uloženému souboru s obrázkem
        """
        logger.debug(f"Vytvářím srovnávací graf pro {tickers}")

        try:
            # Set styles for better appearance
            plt.style.use('dark_background')

            # Create a figure and axis with higher resolution
            fig, ax = plt.subplots(figsize=(12, 7), dpi=100)

            # Colors for different lines
            colors = [
                '#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6',
                '#1abc9c'
            ]

            # Create a data cache to avoid multiple StockData instances
            stock_data_cache = {}

            # Pre-fetch all stock data first (improves performance by batching API calls)
            for ticker in tickers:
                try:
                    stock = StockData(ticker)
                    data = stock.get_history(period)
                    if not data.empty:
                        stock_data_cache[ticker] = data
                except Exception as e:
                    logger.error(f"Error fetching data for {ticker}: {str(e)}")

            # For normalization
            first_values = {}

            # Plot each ticker using the cached data
            for i, ticker in enumerate(tickers):
                data = stock_data_cache.get(ticker)

                if data is not None and not data.empty:
                    # Normalize data to percentage change from first day
                    first_value = data['Close'].iloc[0]
                    first_values[ticker] = first_value
                    normalized_data = (data['Close'] / first_value - 1) * 100

                    # Plot normalized data with better styling
                    color = colors[i % len(colors)]
                    line, = ax.plot(data.index,
                                    normalized_data,
                                    color=color,
                                    linewidth=2.5,
                                    label=ticker)

                    # Add slight transparency for better visuals
                    ax.fill_between(data.index,
                                    normalized_data,
                                    alpha=0.1,
                                    color=color)

            # Add title and labels
            ax.set_title(f"Porovnání akcií - Procentuální změna ({period})",
                         fontsize=16,
                         fontweight='bold',
                         color='white')
            ax.set_xlabel('Datum', fontsize=14, color='white')
            ax.set_ylabel('Změna (%)', fontsize=14, color='white')

            # Format x-axis
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, color='white')
            plt.yticks(color='white')

            # Add grid and legend with better styling
            ax.grid(True, linestyle='--', alpha=0.3, color='gray')
            legend = ax.legend(loc='best', fancybox=True, framealpha=0.7)

            # Style the legend text
            for text in legend.get_texts():
                text.set_color('white')

            # Add border to the plot
            for spine in ax.spines.values():
                spine.set_edgecolor('gray')
                spine.set_linewidth(0.5)

            # Add horizontal line at 0%
            ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)

            # Adjust layout
            plt.tight_layout()

            # Generate a unique filename
            tickers_str = '_'.join(tickers)
            filename = f"compare_{tickers_str}_{period}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join('static', 'images', filename)

            # Save the figure to a file
            plt.savefig(filepath, format='png', dpi=120, bbox_inches='tight')
            plt.close()

            # Return the path to the saved image
            return filename

        except Exception as e:
            logger.error(f"Error creating comparison plot: {str(e)}")
            return ""
