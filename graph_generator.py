import matplotlib.pyplot as plt
import io
import base64

class GraphGenerator:
    @staticmethod
    def create_stock_plot(data):
        plt.figure(figsize=(10, 5))
        data['Close'].plot(title="Vývoj ceny akcie", color='blue')
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
