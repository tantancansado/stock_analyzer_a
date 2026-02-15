#!/usr/bin/env python3
"""
CHART DATA SERVER
Simple Flask server to proxy Yahoo Finance chart data and avoid CORS issues
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/chart/<ticker>')
def get_chart_data(ticker):
    """Get historical chart data for a ticker"""
    try:
        # Get data for last 60 days
        stock = yf.Ticker(ticker)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            return jsonify({'error': 'No data available'}), 404

        # Format data for Chart.js
        chart_data = {
            'labels': [date.strftime('%Y-%m-%d') for date in hist.index],
            'prices': hist['Close'].tolist(),
            'high': hist['High'].tolist(),
            'low': hist['Low'].tolist(),
            'volume': hist['Volume'].tolist()
        }

        return jsonify(chart_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/info/<ticker>')
def get_ticker_info(ticker):
    """Get basic ticker information"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return jsonify({
            'current_price': info.get('currentPrice', 0),
            'market_cap': info.get('marketCap', 0),
            'sector': info.get('sector', ''),
            'industry': info.get('industry', '')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 CHART DATA SERVER")
    print("="*80)
    print("\nStarting server on http://localhost:5001")
    print("\nEndpoints:")
    print("  GET /api/chart/<ticker>  - Get chart data")
    print("  GET /api/info/<ticker>   - Get ticker info")
    print("\n" + "="*80 + "\n")

    app.run(host='0.0.0.0', port=5001, debug=False)
