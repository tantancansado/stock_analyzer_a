import yfinance as yf

def get_fundamental_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        pe = info.get('trailingPE', 0)
        roe = info.get('returnOnEquity', 0)
        debt = info.get('debtToEquity', 0)

        score = 0
        if pe and pe < 20: score += 1
        if roe and roe > 0.15: score += 1
        if debt and debt < 100: score += 1

        data = {
            "Ticker": ticker,
            "Price": info.get('currentPrice'),
            "P/E": pe,
            "P/S": info.get('priceToSalesTrailing12Months'),
            "ROE": roe,
            "Debt/Equity": debt,
            "Revenue Growth": info.get('revenueGrowth'),
            "Gross Margin": info.get('grossMargins'),
            "Net Margin": info.get('netMargins'),
            "EBITDA Margin": info.get('ebitdaMargins'),
            "Score": score
        }

        return data

    except Exception as e:
        print(f"❌ Error con {ticker}: {e}")
        return {"Ticker": ticker, "Error": str(e)}