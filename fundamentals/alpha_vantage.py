# fundamentals/alpha_vantage.py

import requests

API_KEY = "BQ249NDVSLFJ5KVI"

def get_fundamentals_alpha(ticker):
    try:
        # Overview
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={API_KEY}"
        overview = requests.get(overview_url).json()

        pe = float(overview.get("PERatio", 0) or 0)
        roe = float(overview.get("ReturnOnEquityTTM", 0) or 0) / 100  # % to ratio
        debt = float(overview.get("DebtEquityRatio", 0) or 0)
        rev_growth = float(overview.get("QuarterlyRevenueGrowthYOY", 0) or 0)
        gross_margin = float(overview.get("GrossProfitTTM", 0) or 0) / max(float(overview.get("RevenueTTM", 1) or 1), 1)
        net_margin = float(overview.get("NetIncomeTTM", 0) or 0) / max(float(overview.get("RevenueTTM", 1) or 1), 1)

        score = 0
        if pe > 0 and pe < 20: score += 1
        if roe > 0.15: score += 1
        if debt < 1: score += 1

        return {
            "Ticker": ticker,
            "P/E": pe,
            "ROE": roe,
            "Debt/Equity": debt,
            "Revenue Growth": rev_growth,
            "Gross Margin": gross_margin,
            "Net Margin": net_margin,
            "Score": score
        }

    except Exception as e:
        print(f"❌ Error AlphaVantage {ticker}: {e}")
        return {
            "Ticker": ticker,
            "Error": str(e)
        }