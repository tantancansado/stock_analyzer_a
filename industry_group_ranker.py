#!/usr/bin/env python3
"""
INDUSTRY GROUP RANKER
Agrupa tickers por grupo industrial (columna 'industry' de yfinance)
y calcula un ranking basado en Relative Strength promedio del grupo.

Minervini/IBD: el 50% del movimiento de una acción viene de su sector o
grupo industrial. Comprar stocks en el grupo más fuerte del mercado.

Métrica de ranking: avg(rs_line_percentile) por grupo
  → grupos donde más stocks tienen su RS Line en máximos 52s = grupos más fuertes

Output: docs/industry_group_rankings.csv
"""
import pandas as pd
from pathlib import Path


def compute_industry_rankings(fund_csv_path: str = 'docs/fundamental_scores.csv') -> pd.DataFrame:
    """
    Lee fundamental_scores.csv, agrupa por industry, calcula ranking.

    Returns DataFrame con columnas:
      industry, sector, num_tickers, avg_rs_percentile, avg_rs_score,
      avg_fundamental_score, pct_at_new_high, rank, rank_total, percentile, label
    """
    path = Path(fund_csv_path)
    if not path.exists():
        print(f"⚠️  {fund_csv_path} no encontrado")
        return pd.DataFrame()

    df = pd.read_csv(path)

    required = ['ticker', 'industry', 'sector', 'relative_strength_score']
    if not all(c in df.columns for c in required):
        missing = [c for c in required if c not in df.columns]
        print(f"⚠️  Columnas requeridas no encontradas: {missing}")
        return pd.DataFrame()

    # Drop rows without industry data
    df = df[df['industry'].notna() & (df['industry'] != 'N/A') & (df['industry'] != '')].copy()
    if df.empty:
        return pd.DataFrame()

    # Primary ranking metric: rs_line_percentile (Minervini), fallback to relative_strength_score
    if 'rs_line_percentile' in df.columns:
        df['_rank_metric'] = df['rs_line_percentile'].fillna(df['relative_strength_score'])
    else:
        df['_rank_metric'] = df['relative_strength_score']

    # Aggregate by industry group
    agg_dict = {
        'sector':                 ('sector', 'first'),
        'num_tickers':            ('ticker', 'count'),
        'avg_rs_percentile':      ('_rank_metric', 'mean'),
        'avg_rs_score':           ('relative_strength_score', 'mean'),
        'avg_fundamental_score':  ('fundamental_score', 'mean'),
    }

    if 'rs_line_at_new_high' in df.columns:
        agg_dict['pct_at_new_high'] = ('rs_line_at_new_high', lambda x: round(x.eq(True).mean() * 100, 1))
    if 'eps_accelerating' in df.columns:
        agg_dict['pct_eps_accel'] = ('eps_accelerating', lambda x: round(x.eq(True).mean() * 100, 1))

    grp = df.groupby('industry').agg(**agg_dict).reset_index()

    # Rank only groups with ≥2 tickers (statistical validity)
    ranked = grp[grp['num_tickers'] >= 2].copy()
    ranked = ranked.sort_values('avg_rs_percentile', ascending=False).reset_index(drop=True)
    ranked['rank'] = ranked.index + 1
    ranked['rank_total'] = len(ranked)
    ranked['percentile'] = round((1 - (ranked['rank'] - 1) / ranked['rank_total']) * 100, 1)

    def _label(pct):
        if pct >= 90: return 'Top 10%'
        if pct >= 75: return 'Top 25%'
        if pct >= 50: return 'Medio'
        if pct >= 25: return 'Bajo 50%'
        return 'Bottom 25%'

    ranked['label'] = ranked['percentile'].apply(_label)

    # Single-ticker industries: include as informational (null rank)
    singles = grp[grp['num_tickers'] < 2].copy()
    singles['rank'] = None
    singles['rank_total'] = len(ranked)
    singles['percentile'] = None
    singles['label'] = 'Sin datos suficientes'

    # Align columns before concat to avoid FutureWarning with mixed types
    all_cols = ranked.columns.tolist()
    for col in all_cols:
        if col not in singles.columns:
            singles[col] = None
    singles = singles[all_cols]
    result = pd.concat([ranked, singles], ignore_index=True)

    # Round numeric cols
    for col in ['avg_rs_percentile', 'avg_rs_score', 'avg_fundamental_score']:
        if col in result.columns:
            result[col] = result[col].round(1)

    return result


def save_industry_rankings(df: pd.DataFrame, path: str = 'docs/industry_group_rankings.csv') -> None:
    """Guarda el ranking en CSV y muestra top 5."""
    df.to_csv(path, index=False)
    print(f"💾 Industry group rankings guardados: {path} ({len(df)} grupos)")

    ranked = df[df['rank'].notna()].copy()
    if not ranked.empty:
        ranked['rank'] = pd.to_numeric(ranked['rank'], errors='coerce')
        top5 = ranked.nsmallest(5, 'rank')[['rank', 'industry', 'avg_rs_percentile', 'num_tickers', 'label']]
        print("🏆 Top 5 grupos industriales:")
        print(top5.to_string(index=False))


if __name__ == '__main__':
    print("📊 INDUSTRY GROUP RANKER")
    print("=" * 60)
    df = compute_industry_rankings()
    if not df.empty:
        save_industry_rankings(df)
        print(f"\n✅ {len(df[df['rank'].notna()])} grupos rankeados (≥2 tickers)")
        print(f"   {len(df[df['rank'].isna()])} grupos con datos insuficientes (<2 tickers)")
    else:
        print("❌ No se pudo calcular el ranking")
