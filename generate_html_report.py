import pandas as pd
import os

csv_path = "reports/insiders_daily.csv"
df = pd.read_csv(csv_path)

html_rows = []
for _, row in df.iterrows():
    ticker = row["Ticker"]
    daily_chart = row.get("Chart_Daily", "")
    weekly_chart = row.get("Chart_Weekly", "")

    daily_img_tag = f'<img src="{daily_chart}" width="300">' if pd.notna(daily_chart) and daily_chart else ""
    weekly_img_tag = f'<img src="{weekly_chart}" width="300">' if pd.notna(weekly_chart) and weekly_chart else ""

    html_rows.append(f"""
        <tr>
            <td>{ticker}</td>
            <td>{row.get("InsiderBuys", "")}</td>
            <td>{row.get("Date", "")}</td>
            <td>{daily_img_tag}</td>
            <td>{weekly_img_tag}</td>
        </tr>
    """)

html_content = f"""
<html>
<head>
    <title>Informe de Compras de Insiders</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>📊 Informe de Compras de Insiders</h1>
    <table>
        <tr>
            <th>Ticker</th>
            <th>InsiderBuys</th>
            <th>Date</th>
            <th>Gráfico Diario</th>
            <th>Gráfico Semanal</th>
        </tr>
        {''.join(html_rows)}
    </table>
</body>
</html>
"""

output_path = "reports/insiders_report.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ Informe HTML generado en: {output_path}")