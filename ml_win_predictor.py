"""
ML Win Predictor — XGBoost sobre el historial de señales de Value US: probabilidad
de que una idea le gane al S&P a 90 días. Solo publica si pasa una validación
honesta; si no, publica que no hay modelo y por qué.

11-nov-2026. Antes predecía `win_14d` (subir a 14 días), cuando el horizonte
mínimo de la casa es 90 (`horizontes.py`): a 14 días se mide ruido. Publicaba un
ROC-AUC de 0,78 que no se reproduce: con los mismos valores en entrenamiento y
prueba y plazos que se solapan, el modelo reconoce la empresa, no la idea.
Entrenando solo con señales cuyo plazo ya había terminado antes de la prueba y
con una señal por empresa y mes, el AUC a 14 días era 0,51, una moneda al aire.
A 90 días no había ni con qué validar (señales de febrero a agosto de 2026).
Mientras tanto se enseñaba como «ML 72» en cada fila de Value US.

Outputs (se escriben SIEMPRE, también cuando no publica: un fichero viejo con
predicciones de otro modelo se seguiría leyendo como si fuera de hoy):
  docs/ml_win_probability.json  — predicciones por ticker, o vacío con el motivo
  docs/ml_model_report.json     — validación, importancias y muestra
"""
import json
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from value_bands import UPSIDE_ALTO

warnings.filterwarnings('ignore')

DOCS      = Path(__file__).parent / 'docs'
RECS_CSV  = DOCS / 'portfolio_tracker' / 'recommendations.csv'
VALUE_CSV = DOCS / 'value_opportunities.csv'
OUT_PROBS  = DOCS / 'ml_win_probability.json'
OUT_REPORT = DOCS / 'ml_model_report.json'

HORIZONTE_DIAS = 90
TARGET = 'gana_al_sp_90d'          # alpha_90d > 0: lo mismo que mide el tracker
# Para publicar. Una señal por empresa y mes, que señales del mismo valor en días
# seguidos comparten casi todo el plazo y no son casos distintos.
MIN_MUESTRAS = 300
MIN_MESES = 12                     # de fechas de señal: más de un régimen de mercado
MIN_PLIEGUES = 3
AUC_MINIMO = 0.60                  # de media fuera de muestra
AUC_PEOR_PLIEGUE = 0.55            # y ningún mes por debajo de esto

REGIME_MAP = {
    'CONFIRMED_UPTREND': 2,
    'UPTREND':           1,
    'UPTREND_PRESSURE':  0,
    'NEUTRAL':           0,
    'CORRECTION':       -1,
    'BEAR':             -2,
}

# Mutable globals filled at train time, used at inference time
_SECTOR_WIN_RATES: dict = {}
_GLOBAL_MEDIAN_FEATURES: dict = {}


def _regime_num(series: pd.Series) -> pd.Series:
    return series.fillna('NEUTRAL').astype(str).str.upper().map(
        lambda x: REGIME_MAP.get(x, 0)
    )


def _build_features(df: pd.DataFrame, fit: bool) -> pd.DataFrame:
    global _SECTOR_WIN_RATES, _GLOBAL_MEDIAN_FEATURES

    out = pd.DataFrame(index=df.index)

    up = pd.to_numeric(df.get('analyst_upside_pct'), errors='coerce')
    rr = pd.to_numeric(df.get('risk_reward_ratio'), errors='coerce')
    fc = pd.to_numeric(df.get('fcf_yield_pct'), errors='coerce')

    if fit:
        _GLOBAL_MEDIAN_FEATURES = {
            'analyst_upside_pct':  float(up.median()),
            'risk_reward_ratio':   float(rr.median()),
            'fcf_yield_pct':       float(fc.median()),
        }
        wr = df.groupby('sector')[TARGET].apply(lambda x: float(x.mean())).to_dict()
        _SECTOR_WIN_RATES = {k: v for k, v in wr.items() if df['sector'].eq(k).sum() >= 10}

    m = _GLOBAL_MEDIAN_FEATURES
    up = up.fillna(m.get('analyst_upside_pct', 15.0))
    rr = rr.fillna(m.get('risk_reward_ratio', 2.0))
    fc = fc.fillna(0.0)

    global_wr = float(np.mean(list(_SECTOR_WIN_RATES.values()))) if _SECTOR_WIN_RATES else 0.28
    sec_wr = df.get('sector', pd.Series('Unknown', index=df.index)).fillna('Unknown').map(
        lambda x: _SECTOR_WIN_RATES.get(str(x), global_wr)
    )
    reg = _regime_num(df.get('market_regime', pd.Series('NEUTRAL', index=df.index)))

    out['analyst_upside_pct'] = up
    out['risk_reward_ratio']  = rr
    out['fcf_yield_pct']      = fc
    out['sector_wr']          = sec_wr
    out['regime_num']         = reg
    out['regime_x_sector']    = reg * sec_wr
    out['rr_gte_2']           = (rr >= 2).astype(float)
    out['rr_gte_3']           = (rr >= 3).astype(float)
    # El NOMBRE de la variable se queda (el modelo está entrenado con él),
    # pero el corte sale de value_bands, no de un 30 escrito a mano.
    out['upside_gte_30']      = (up >= UPSIDE_ALTO).astype(float)
    out['fcf_positive']       = (fc > 0).astype(float)
    out['fcf_gte_5']          = (fc >= 5).astype(float)

    return out.fillna(0)


def _prob_label(prob: float) -> str:
    """Etiqueta anclada al 50% real, no al ranking relativo del lote.

    Antes ALTA empezaba en 0.45: el 31-jul-2026 NDAQ (0.476), SPGI (0.476),
    MCO (0.459) y EXPN.L (0.492) se mostraban como "ALTA" junto al ticker, sin
    contexto, cuando la probabilidad de ganar era peor que una moneda al aire.
    Que 0.47 sea bueno *comparado con el resto del lote* no lo convierte en
    alto: quien lee la app lee "alta probabilidad de acierto".
    """
    if prob >= 0.55:
        return 'ALTA'
    if prob >= 0.45:
        return 'MEDIA'
    return 'BAJA'


# `sector_wr` y `regime_x_sector` NO están: eran FUGA DE TARGET. `sector_wr` se
# calculaba promediando el propio TARGET por sector sobre todo el dataset
# (_build_features, rama fit) y se usaba luego como feature, así que el modelo
# veía el resultado medio de las filas con las que se le evaluaba. Eran, además,
# las features nº1 y nº3 por importancia — el modelo se apoyaba justo en el
# atajo. Medido entrenando en el periodo contaminado y probando en el limpio:
#     con sector_wr    ROC-AUC 0,589   (moneda al aire es 0,50)
#     sin sector_wr    ROC-AUC 0,677
# O sea que la fuga no solo inflaba la métrica publicada: empeoraba el modelo
# de verdad, porque los win-rates sectoriales del pasado NO transfieren (medido
# aparte: correlación +0,26 entre el win-rate sectorial de ambos periodos).
FEATURE_COLS = [
    # Sin value_score: se entrena con señales de la nota vieja y se predice con la
    # de grupos (7-nov-2026). Son escalas distintas y el resultado no significaría nada.
    'analyst_upside_pct', 'risk_reward_ratio',
    'fcf_yield_pct', 'regime_num',
    'rr_gte_2', 'rr_gte_3', 'upside_gte_30',
    'fcf_positive', 'fcf_gte_5',
]


def _load_training_data() -> pd.DataFrame:
    """Señales de Value US con su resultado a 90 días contra el S&P, una por empresa y mes."""
    df = pd.read_csv(RECS_CSV, low_memory=False)
    if 'strategy' in df.columns:
        df = df[df['strategy'] == 'VALUE']
    df = df[~df['ticker'].astype(str).str.contains(r'\.', regex=True)].copy()
    df['fecha'] = pd.to_datetime(df.get('signal_date'), errors='coerce')
    alpha = pd.to_numeric(df.get('alpha_90d'), errors='coerce')
    df = df[alpha.notna() & df['fecha'].notna()].copy()
    df[TARGET] = (alpha[df.index] > 0).astype(int)
    df['mes'] = df['fecha'].dt.to_period('M')
    return (df.sort_values('fecha').drop_duplicates(['ticker', 'mes'])
              .drop(columns='mes').reset_index(drop=True))


def pliegues(fechas: pd.Series, plazo_dias: int = HORIZONTE_DIAS):
    """Cortes mensuales hacia delante. Se entrena solo con señales cuyo plazo YA
    había terminado antes del corte, y se prueba con el mes siguiente.

    Es más estricto que un TimeSeriesSplit a secas: con plazos de 90 días que se
    solapan, la señal de ayer y la de hoy comparten el resultado, y dejarlas a los
    dos lados del corte es enseñarle la respuesta al modelo.
    """
    fechas = pd.to_datetime(fechas)
    plazo = pd.Timedelta(days=plazo_dias)
    for corte in pd.date_range(fechas.min() + plazo + pd.Timedelta(days=30), fechas.max(), freq='30D'):
        entreno = (fechas < corte - plazo).values
        prueba = ((fechas >= corte) & (fechas < corte + pd.Timedelta(days=30))).values
        yield corte, entreno, prueba


def _modelo(y):
    from xgboost import XGBClassifier
    return XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
                         colsample_bytree=0.8, eval_metric='logloss', random_state=42, verbosity=0,
                         scale_pos_weight=float((y == 0).sum()) / max(float((y == 1).sum()), 1))


def validar(df: pd.DataFrame) -> list[dict]:
    from sklearn.metrics import roc_auc_score
    y = df[TARGET].values
    resultado = []
    for corte, entreno, prueba in pliegues(df['fecha']):
        if entreno.sum() < 100 or prueba.sum() < 20:
            continue
        if len(set(y[entreno])) < 2 or len(set(y[prueba])) < 2:
            continue
        # Las medianas de relleno salen solo del entrenamiento: con todo el
        # histórico, el modelo vería algo de la prueba.
        x_entreno = _build_features(df[entreno], fit=True)[FEATURE_COLS].values
        x_prueba = _build_features(df[prueba], fit=False)[FEATURE_COLS].values
        m = _modelo(y[entreno]).fit(x_entreno, y[entreno])
        auc = roc_auc_score(y[prueba], m.predict_proba(x_prueba)[:, 1])
        resultado.append({'corte': str(corte.date()), 'entreno': int(entreno.sum()),
                          'prueba': int(prueba.sum()), 'auc': round(float(auc), 3)})
    return resultado


def motivo_para_no_publicar(df: pd.DataFrame, validacion: list[dict] | None) -> str | None:
    if len(df) < MIN_MUESTRAS:
        return f'{len(df)} señales con resultado a 90 días; hacen falta {MIN_MUESTRAS}'
    meses = (df['fecha'].max() - df['fecha'].min()).days / 30.4
    if meses < MIN_MESES:
        return f'las señales cubren {meses:.0f} meses; hacen falta {MIN_MESES}'
    if validacion is None or len(validacion) < MIN_PLIEGUES:
        return f'{len(validacion or [])} meses de prueba fuera de muestra; hacen falta {MIN_PLIEGUES}'
    aucs = [v['auc'] for v in validacion]
    if np.mean(aucs) < AUC_MINIMO or min(aucs) < AUC_PEOR_PLIEGUE:
        return (f'fuera de muestra acierta {np.mean(aucs):.2f} de media (peor mes {min(aucs):.2f}); '
                f'hace falta {AUC_MINIMO:.2f} y ningún mes bajo {AUC_PEOR_PLIEGUE:.2f}')
    return None


def _escribir(predicciones: dict, informe: dict) -> None:
    base = {'generated_at': datetime.now().isoformat(), 'horizonte_dias': HORIZONTE_DIAS,
            'objetivo': 'ganar al S&P 500 a 90 días'}
    OUT_PROBS.write_text(json.dumps({**base, 'publica': bool(predicciones),
                                     'motivo': informe.get('motivo'),
                                     'auc_fuera_de_muestra': informe.get('auc_fuera_de_muestra'),
                                     'predictions': predicciones}, indent=2, ensure_ascii=False))
    OUT_REPORT.write_text(json.dumps({**base, **informe}, indent=2, ensure_ascii=False, default=str))


def run():
    print('[ML] Probabilidad de ganarle al S&P a 90 días...')
    if not RECS_CSV.exists():
        _escribir({}, {'motivo': 'no hay recommendations.csv'})
        return
    df = _load_training_data()
    try:
        validacion = validar(df) if len(df) >= MIN_MUESTRAS else None
    except ImportError:
        _escribir({}, {'motivo': 'xgboost/sklearn no instalados'})
        return
    motivo = motivo_para_no_publicar(df, validacion)
    informe = {'n_muestras': int(len(df)), 'validacion': validacion or [],
               'gana_al_sp_base': round(float(df[TARGET].mean()), 3) if len(df) else None,
               'muestra_desde': str(df['fecha'].min().date()) if len(df) else None,
               'muestra_hasta': str(df['fecha'].max().date()) if len(df) else None,
               'motivo': motivo}
    if motivo:
        print(f'  No publica: {motivo}')
        _escribir({}, informe)
        return

    from sklearn.calibration import CalibratedClassifierCV
    X = _build_features(df, fit=True)[FEATURE_COLS]
    y = df[TARGET].values
    model = CalibratedClassifierCV(_modelo(y), cv=3, method='isotonic').fit(X, y)
    informe['auc_fuera_de_muestra'] = round(float(np.mean([v['auc'] for v in validacion])), 3)
    try:
        imps = np.array([e.estimator.feature_importances_ for e in model.calibrated_classifiers_])
        informe['feature_importance'] = dict(zip(FEATURE_COLS, np.round(imps.mean(axis=0), 4).tolist()))
    except Exception:
        pass

    val_df = pd.read_csv(VALUE_CSV) if VALUE_CSV.exists() else pd.DataFrame()
    if val_df.empty or 'ticker' not in val_df:
        _escribir({}, {**informe, 'motivo': 'no hay lista de Value US que puntuar'})
        return
    val_df = val_df.drop_duplicates('ticker').reset_index(drop=True)
    probs = model.predict_proba(_build_features(val_df, fit=False)[FEATURE_COLS])[:, 1]
    orden = sorted(probs, reverse=True)
    predicciones = {}
    for ticker, prob in zip(val_df['ticker'].astype(str).str.upper(), probs):
        rank = sum(1 for p in orden if p > prob) + 1
        predicciones[ticker] = {'probability': round(float(prob), 4),
                                'percentile': int(round((1 - rank / len(orden)) * 100)),
                                'label': _prob_label(float(prob))}
    _escribir(predicciones, informe)
    print(f'  {len(predicciones)} tickers puntuados · AUC fuera de muestra {informe["auc_fuera_de_muestra"]}')


if __name__ == '__main__':
    run()
