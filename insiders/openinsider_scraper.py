import requests
import pandas as pd
from bs4 import BeautifulSoup
import time

def get_insider_summary(ticker):
    url = f"https://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=365&fdr=&td=0&tdr=&xp=1"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return {"Ticker": ticker, "Recent Insider Buys": 0, "Recent Insider Sells": 0}

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="tinytable")
        if not table:
            return {"Ticker": ticker, "Recent Insider Buys": 0, "Recent Insider Sells": 0}

        rows = table.find_all("tr")[1:]  # skip header
        buys, sells = 0, 0
        for row in rows:
            cols = [td.text.strip() for td in row.find_all("td")]
            if len(cols) < 10:
                continue
            trans_type = cols[3]  # "Buy" or "Sale"
            if trans_type.lower() == "buy":
                buys += 1
            elif trans_type.lower() in ["sale", "sell"]:
                sells += 1

        return {
            "Ticker": ticker,
            "Recent Insider Buys": buys,
            "Recent Insider Sells": sells,
            "Net Insider Activity": buys - sells
        }
    except Exception as e:
        print(f"❌ Error con {ticker}: {e}")
        return {"Ticker": ticker, "Recent Insider Buys": 0, "Recent Insider Sells": 0, "Net Insider Activity": 0}

if __name__ == "__main__":
    df = pd.read_csv("reports/finviz_ml_dataset.csv")
    tickers = df["Ticker"].dropna().unique()

    all_data = []
    for t in tickers:
        print(f"🔍 Scrapeando OpenInsider para {t}...")
        data = get_insider_summary(t)
        all_data.append(data)
        time.sleep(1.5)  # para evitar bloqueo por rate limit

    insider_df = pd.DataFrame(all_data)
    merged = df.merge(insider_df, on="Ticker", how="left")

    output_path = "reports/finviz_insider_dataset.csv"
    merged.to_csv(output_path, index=False)
    print(f"✅ Dataset combinado guardado en: {output_path}")