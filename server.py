from flask import Flask, render_template, request
from api_handler import APIHandler
from graph_generator import GraphGenerator

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    chart = None
    if request.method == "POST":
        ticker = request.form["ticker"]
        data = APIHandler.get_stock_data(ticker)
        if not data.empty:
            chart = GraphGenerator.create_stock_plot(data)
    return render_template("index.html", chart=chart)

if __name__ == "__main__":
    app.run(debug=True)
