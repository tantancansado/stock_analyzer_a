#!/bin/bash
# Start Ticker Analyzer API Server

echo "🚀 Starting Ticker Analyzer API Server..."
echo ""

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ Flask not installed. Installing dependencies..."
    pip3 install --break-system-packages -r requirements.txt
fi

# Kill any existing server on port 5001
lsof -ti:5001 | xargs kill -9 2>/dev/null

# Start server
echo "📡 Server starting on http://localhost:5001"
echo "🌐 Frontend: docs/ticker_analyzer.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 ticker_analyzer_api.py
