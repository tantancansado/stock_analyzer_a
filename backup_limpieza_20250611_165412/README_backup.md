if d_path and os.path.exists(d_path):
    insiders_df.loc[insiders_df["Ticker"] == ticker, "Chart_Daily"] = d_path
else:
    insiders_df.loc[insiders_df["Ticker"] == ticker, "Chart_Daily"] = ""

if w_path and os.path.exists(w_path):
    insiders_df.loc[insiders_df["Ticker"] == ticker, "Chart_Weekly"] = w_path
else:
    insiders_df.loc[insiders_df["Ticker"] == ticker, "Chart_Weekly"] = ""