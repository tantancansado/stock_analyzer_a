#!/usr/bin/env python3
"""
ENRICH 5D - Añade sector enhancement y fundamentales al CSV existente
Toma el CSV 4D y lo enriquece con las nuevas dimensiones
"""
import pandas as pd
import time
from pathlib import Path
from sector_enhancement import SectorEnhancement
from fundamental_analyzer import FundamentalAnalyzer

# Configuración
FUNDAMENTAL_TOP_N = 100   # Solo obtener fundamentales de los top N tickers
RATE_LIMIT_DELAY = 0.3    # Segundos entre llamadas a la API

def _enrich_sector(ticker, se, new_cols):
    """Enriquece con datos de sector (sin API, rápido)"""
    try:
        sector_score = se.calculate_sector_score(ticker)
        sector_momentum = se.get_sector_momentum(ticker)
        tier_boost = se.calculate_tier_boost(sector_score, sector_momentum)
        sector_info = se.ticker_to_sector.get(ticker, {})

        new_cols['sector_name'].append(sector_info.get('sector', 'Unknown'))
        new_cols['sector_momentum'].append(sector_momentum)
        new_cols['tier_boost'].append(tier_boost)
        new_cols['dj_ticker'].append(sector_info.get('dj_ticker', ''))
        print(f"📊 {sector_info.get('sector', 'N/A')} ({sector_momentum})", end=" ")
    except Exception:
        new_cols['sector_name'].append('Unknown')
        new_cols['sector_momentum'].append('stable')
        new_cols['tier_boost'].append(0)
        new_cols['dj_ticker'].append('')
        print("⚠️  sector error", end=" ")


def _enrich_fundamentals(ticker, fa, new_cols):
    """Enriquece con datos fundamentales (API, lento)"""
    try:
        fund_data = fa.get_fundamental_data(ticker)

        if fund_data:
            pt = fa.calculate_custom_price_target(ticker)
            new_cols['current_price'].append(fund_data['current_price'])
            new_cols['pe_ratio'].append(fund_data['valuation']['pe_ratio'])
            new_cols['peg_ratio'].append(fund_data['valuation']['peg_ratio'])
            new_cols['fcf_yield'].append(fund_data['cashflow']['fcf_yield'])
            new_cols['roe'].append(fund_data['profitability']['roe'])
            new_cols['revenue_growth'].append(fund_data['growth']['revenue_growth'])
            new_cols['analyst_target'].append(fund_data['analysts']['target_mean'])
            new_cols['analyst_upside'].append(fund_data['analysts']['upside_analysts'])
            new_cols['num_analysts'].append(fund_data['analysts']['num_analysts'])
            new_cols['fundamental_score'].append(fa.get_fundamental_score(ticker))

            entry_score = fa.calculate_entry_score(ticker)
            new_cols['entry_score'].append(entry_score)
            new_cols['entry_bonus'].append(fa.get_entry_bonus(entry_score))

            if pt:
                new_cols['price_target'].append(pt['custom_target'])
                new_cols['upside_percent'].append(pt['upside_percent'])
                print(f"🎯 ${pt['custom_target']:.0f} ({pt['upside_percent']:+.0f}%)", end="")
            else:
                new_cols['price_target'].append(None)
                new_cols['upside_percent'].append(None)
                print("⚠️  sin target", end="")
        else:
            _fill_empty_fundamentals(new_cols)
            print("⚠️  sin datos", end="")

    except Exception as e:
        _fill_empty_fundamentals(new_cols)
        print(f"❌ {str(e)[:25]}", end="")


def _fill_empty_fundamentals(new_cols):
    """Rellena con None cuando no hay datos fundamentales"""
    for col in ['current_price', 'pe_ratio', 'peg_ratio', 'fcf_yield',
                'roe', 'revenue_growth', 'analyst_target', 'analyst_upside',
                'price_target', 'upside_percent', 'entry_score']:
        new_cols[col].append(None)
    new_cols['num_analysts'].append(0)
    new_cols['fundamental_score'].append(None)
    new_cols['entry_bonus'].append(0)


def _save_and_report(df, new_cols, se):
    """Añade columnas al df, guarda CSV y muestra estadísticas"""
    for col, values in new_cols.items():
        df[col] = values

    df['sector_score'] = df['ticker'].apply(se.calculate_sector_score)
    df['super_score_5d'] = (
        df['super_score_4d'] + df['tier_boost'] + df['entry_bonus'].fillna(0)
    ).clip(upper=100).round(1)
    df = df.sort_values('super_score_5d', ascending=False).reset_index(drop=True)

    out_path = Path("docs/super_opportunities_5d_complete.csv")
    df.to_csv(out_path, index=False)
    print(f"\n✅ CSV 5D guardado: {out_path}")

    if 'days_to_earnings' in df.columns:
        out_earnings = Path("docs/super_opportunities_5d_complete_with_earnings.csv")
        df.to_csv(out_earnings, index=False)
        print(f"✅ CSV 5D+Earnings guardado: {out_earnings}")

    print("\n📈 RESULTADO:")
    print(f"   Total tickers: {len(df)}")
    print(f"   Con sector identificado: {(df['sector_name'] != 'Unknown').sum()}")
    print(f"   Con price target: {df['price_target'].notna().sum()}")
    print(f"   Con upside >20%: {(df['upside_percent'].fillna(0) > 20).sum()}")

    print("\n🏆 TOP 5 OPORTUNIDADES 5D:")
    for idx, row in df.head(5).iterrows():
        if pd.notna(row.get('price_target')):
            target_str = f"${row['price_target']:.0f} ({row['upside_percent']:+.0f}%)"
        else:
            target_str = "N/A"
        print(f"   {idx+1}. {row['ticker']:6} - Score: {row['super_score_5d']:5.1f} | "
              f"Sector: {row['sector_name']:15} | Target: {target_str}")

    return df


def enrich_csv():
    print("🔄 ENRICH 5D - Enriqueciendo CSV con sector y fundamentales")
    print("=" * 70)

    csv_path = Path("docs/super_opportunities_4d_complete_with_earnings.csv")
    if not csv_path.exists():
        csv_path = Path("docs/super_opportunities_4d_complete.csv")

    df = pd.read_csv(csv_path)
    print(f"✅ CSV cargado: {len(df)} tickers")

    print("\n🔍 Cargando Sector Enhancement...")
    se = SectorEnhancement()
    se.load_dj_sectorial()
    # Pre-cargar sectores en lotes (usa caché si ya están)
    se.prefetch_sectors(df['ticker'].tolist(), batch_size=20, delay=1.5)

    print("💰 Cargando Fundamental Analyzer...")
    fa = FundamentalAnalyzer()

    new_cols = {
        'sector_name': [], 'sector_momentum': [], 'tier_boost': [], 'dj_ticker': [],
        'current_price': [], 'price_target': [], 'upside_percent': [],
        'analyst_target': [], 'analyst_upside': [], 'num_analysts': [],
        'fundamental_score': [], 'pe_ratio': [], 'peg_ratio': [],
        'fcf_yield': [], 'roe': [], 'revenue_growth': [],
        'entry_score': [], 'entry_bonus': [],
    }

    total = len(df)
    print(f"\n📊 Enriqueciendo {total} tickers (fundamentales top {FUNDAMENTAL_TOP_N})...")
    print("-" * 70)

    for i, row in df.iterrows():
        ticker = row['ticker']
        print(f"   [{i+1}/{total}] {ticker}...", end=" ", flush=True)

        _enrich_sector(ticker, se, new_cols)

        if i < FUNDAMENTAL_TOP_N:
            _enrich_fundamentals(ticker, fa, new_cols)
            time.sleep(RATE_LIMIT_DELAY)
        else:
            _fill_empty_fundamentals(new_cols)
            print("(skipped)", end="")

        print()

    return _save_and_report(df, new_cols, se)


if __name__ == "__main__":
    enrich_csv()
