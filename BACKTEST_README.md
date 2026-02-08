# 📊 BACKTEST SYSTEM - Guía Completa

Sistema de backtesting para validar la efectividad de las señales del Super Analyzer 4D.

---

## 🎯 ¿Qué hace?

El sistema de backtesting:
1. **Crea snapshots** diarios de las oportunidades detectadas con sus precios de entrada
2. **Calcula returns** a diferentes timeframes (7d, 30d, 60d, 90d)
3. **Genera estadísticas** de performance: win rate, average return, mejores/peores trades
4. **Valida el sistema** para saber si las señales LEGENDARY realmente funcionan

---

## 🚀 Quick Start

### 1. Crear Snapshot de Oportunidades Actuales

```bash
python3 backtest_system.py
```

Esto crea un snapshot con:
- Todos los tickers de super_opportunities_4d_complete.csv
- Precio de entrada actual
- Fecha del snapshot
- Scores de las 4 dimensiones

### 2. Analizar Snapshot Anterior (Después de X días)

```python
from backtest_system import BacktestSystem

backtest = BacktestSystem()

# Analizar snapshot más reciente
# (calcula returns a 7d, 30d, 60d, 90d)
results = backtest.analyze_latest_snapshot()
```

### 3. Ver Resultados

```python
# Analizar snapshot específico
results = backtest.calculate_returns('20260208_180834')

# Ver stats
backtest.print_stats(results, [7, 30, 60, 90])
```

---

## 📁 Estructura de Datos

```
data/backtest/
├── snapshots/          # Snapshots históricos con precios de entrada
│   ├── snapshot_20260208_180834.csv
│   ├── snapshot_20260209_180000.csv
│   └── ...
└── results/            # Resultados de backtest con returns calculados
    ├── backtest_20260208_180834.csv
    ├── backtest_20260209_180000.csv
    └── ...
```

### Formato de Snapshot

| ticker | super_score_4d | tier | vcp_score | ... | entry_price | entry_date | snapshot_id |
|--------|----------------|------|-----------|-----|-------------|------------|-------------|
| NCLH   | 61.9          | ⭐   | 89.6      | ... | 24.50       | 2026-02-08 | 20260208... |

### Formato de Results

| ticker | entry_price | return_7d | return_30d | return_60d | return_90d | exit_price_7d | ... |
|--------|-------------|-----------|------------|------------|------------|---------------|-----|
| NCLH   | 24.50       | +5.2%     | +12.3%     | +18.5%     | +25.0%     | 25.77         | ... |

---

## 📈 Métricas Calculadas

### Por Timeframe (7d, 30d, 60d, 90d)

- **Average Return**: Retorno promedio de todas las señales
- **Median Return**: Retorno mediano (más robusto que la media)
- **Win Rate**: % de trades ganadores
- **Best Return**: Mejor trade del periodo
- **Worst Return**: Peor trade del periodo

### Por Tier

- **LEGENDARY (≥85)**: Estadísticas solo para señales LEGENDARY
- **ÉPICAS (≥75)**: Estadísticas solo para señales ÉPICAS
- **EXCELENTES (≥65)**: Estadísticas solo para señales EXCELENTES

Esto permite validar si scores más altos = mejores returns.

---

## 🤖 Automatización

### Opción 1: Snapshot Diario Manual

```bash
# Añadir al crontab (después del daily scan)
0 19 * * 1-5 cd /path/to/stock_analyzer_a && python3 -c "from backtest_system import BacktestSystem; BacktestSystem().create_snapshot('docs/super_opportunities_4d_complete.csv')" >> logs/backtest.log 2>&1
```

### Opción 2: Integrar en run_all_scanners.py

Añadir al final de `run_all_scanners.py`:

```python
# Crear snapshot para backtesting
from backtest_system import BacktestSystem
backtest = BacktestSystem()
backtest.create_snapshot('docs/super_opportunities_4d_complete.csv')
```

### Opción 3: GitHub Actions

Añadir a `.github/workflows/daily-scan.yml`:

```yaml
- name: Create backtest snapshot
  run: |
    python3 -c "from backtest_system import BacktestSystem; BacktestSystem().create_snapshot('docs/super_opportunities_4d_complete.csv')"
```

---

## 📊 Ejemplo de Output

```
📊 BACKTEST SYSTEM
================================================================================

📸 Creando snapshot: 2026-02-08
   Oportunidades: 685
   Obteniendo precios...
✅ Snapshot guardado: data/backtest/snapshots/snapshot_20260208_180834.csv
   Tickers con precio: 674/685

================================================================================
📈 ESTADÍSTICAS DE PERFORMANCE
================================================================================

🎯 7 DÍAS:
   Samples: 650
   Avg Return: +3.2%
   Median Return: +2.1%
   Win Rate: 62.3%
   Best: +45.2%
   Worst: -18.5%

   📊 Por Tier:
      ⭐⭐⭐⭐ LEGENDARY: +8.5% avg, 75% win rate (12 samples)
      ⭐⭐⭐ ÉPICAS: +5.2% avg, 68% win rate (45 samples)
      ⭐⭐ EXCELENTES: +2.8% avg, 58% win rate (98 samples)

🎯 30 DÍAS:
   Samples: 650
   Avg Return: +7.8%
   Median Return: +5.4%
   Win Rate: 65.2%
   Best: +89.3%
   Worst: -32.1%

   📊 Por Tier:
      ⭐⭐⭐⭐ LEGENDARY: +18.2% avg, 83% win rate (12 samples)
      ⭐⭐⭐ ÉPICAS: +12.1% avg, 72% win rate (45 samples)
      ⭐⭐ EXCELENTES: +6.5% avg, 61% win rate (98 samples)
```

---

## 🎨 Visualización

### CSV para Excel/Sheets

```bash
# Copiar resultados a docs/ para fácil acceso
cp data/backtest/results/backtest_YYYYMMDD_HHMMSS.csv docs/backtest_results.csv
```

Luego abrir en Excel/Google Sheets para crear gráficos.

### Dashboard HTML (Próximamente)

Página HTML con:
- Gráfico de equity curve
- Win rate por tier
- Distribution de returns
- Top 10 mejores/peores trades

---

## 💡 Casos de Uso

### 1. Validar el Sistema

```python
# Después de 30 días con snapshots diarios
backtest = BacktestSystem()

# Analizar todos los snapshots
for snapshot in sorted(backtest.snapshots_dir.glob("snapshot_*.csv")):
    snapshot_id = snapshot.stem.replace('snapshot_', '')
    results = backtest.calculate_returns(snapshot_id, [30])
```

Si LEGENDARY tiene consistentemente mejor performance que otras tiers → **Sistema validado** ✅

### 2. Optimizar Scoring

Si descubres que:
- VCP alto pero insiders bajo = mal resultado
- Institutional alto siempre gana

Puedes ajustar los pesos del scoring en `super_analyzer_4d.py`.

### 3. Entry Timing

Ver si es mejor entrar:
- El mismo día de la señal
- Esperar 1-2 días para confirmación
- En pullbacks

### 4. Exit Strategy

Descubrir el timeframe óptimo:
- ¿7d es mejor que 30d?
- ¿LEGENDARY necesita más tiempo (90d)?

---

## ⚠️ Limitaciones

1. **Survivorship Bias**: Tickers que se delistan no aparecen en resultados
2. **Slippage**: Precios reales pueden diferir ligeramente
3. **Comisiones**: No incluidas en cálculos (añadir -0.1% por trade)
4. **Market Conditions**: Bull vs Bear markets afectan todos los resultados

---

## 🔧 Personalización

### Cambiar Timeframes

```python
# Usar solo 7d y 14d
results = backtest.calculate_returns(snapshot_id, [7, 14])
```

### Filtrar por Score

```python
# Solo backtest LEGENDARY
df = pd.read_csv('snapshot.csv')
df_legendary = df[df['super_score_4d'] >= 85]
df_legendary.to_csv('temp.csv')
backtest.create_snapshot('temp.csv')
```

### Añadir Métricas Custom

Editar `backtest_system.py` → `print_stats()`:

```python
# Añadir Sharpe Ratio, Max Drawdown, etc.
sharpe = avg_return / std_return
print(f"Sharpe Ratio: {sharpe:.2f}")
```

---

## 🎯 Roadmap

- [ ] Dashboard HTML interactivo
- [ ] Equity curve visualization
- [ ] Monte Carlo simulation
- [ ] Portfolio optimization
- [ ] Risk-adjusted returns (Sharpe, Sortino)
- [ ] Comparison vs SPY benchmark

---

## 📖 Ejemplos

### Ejemplo 1: Crear Snapshot y Analizar

```python
from backtest_system import BacktestSystem
from pathlib import Path

backtest = BacktestSystem()

# Crear snapshot
backtest.create_snapshot('docs/super_opportunities_4d_complete.csv')

# Esperar 7 días...

# Analizar
results = backtest.analyze_latest_snapshot()
```

### Ejemplo 2: Backtest Específico

```python
# Analizar snapshot del 1 de febrero
results = backtest.calculate_returns('20260201_180000', [7, 14, 30])

# Ver solo LEGENDARY
legendary = results[results['tier'] == '⭐⭐⭐⭐ LEGENDARY']
print(legendary[['ticker', 'return_7d', 'return_30d']])
```

### Ejemplo 3: Export para Análisis

```python
# Combinar todos los resultados
import pandas as pd

all_results = []
for result_file in backtest.results_dir.glob("backtest_*.csv"):
    df = pd.read_csv(result_file)
    all_results.append(df)

combined = pd.concat(all_results, ignore_index=True)
combined.to_csv('docs/all_backtests.csv', index=False)
```

---

## ✅ Checklist

- [ ] Crear primer snapshot
- [ ] Configurar snapshots automáticos diarios
- [ ] Esperar 30 días para primera validación
- [ ] Analizar resultados
- [ ] Ajustar scoring si es necesario
- [ ] Crear dashboard de visualización

---

**Nota**: El backtesting es una herramienta de validación, NO garantía de performance futura. Siempre hacer risk management adecuado.
