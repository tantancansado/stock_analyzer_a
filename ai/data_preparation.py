import yfinance as yf
import pandas as pd

def download_price_data(ticker):
    df = yf.download(ticker, start="2010-01-01")
    return df

def generate_features(df):
    df["return_1d"] = df["Close"].pct_change()
    df["return_5d"] = df["Close"].pct_change(5)
    df["ma_10"] = df["Close"].rolling(10).mean()
    df["ma_50"] = df["Close"].rolling(50).mean()
    df["rsi_14"] = compute_rsi(df["Close"], 14)
    df["volume_change"] = df["Volume"].pct_change()
    df.dropna(inplace=True)
    return df

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def label_data(df, future_days=30, threshold=0.10):
    future_returns = df["Close"].pct_change(periods=future_days).shift(-future_days)
    df["label"] = (future_returns > threshold).astype(int)
    df.dropna(inplace=True)
    return df