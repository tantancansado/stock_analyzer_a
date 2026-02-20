#!/usr/bin/env python3
"""
THESIS GENERATOR
Genera tesis de inversión completas para cada ticker candidato
basándose en análisis técnico, fundamental, sector, y catalizadores
"""
import pandas as pd
import json
from pathlib import Path
from datetime import datetime


class ThesisGenerator:
    """Genera tesis de inversión narrativas a partir de datos"""

    def __init__(self, use_ai=False):
        self.csv_5d = None
        self.vcp_data = None
        self.ai_client = None
        if use_ai:
            try:
                import os
                if not os.environ.get('ANTHROPIC_API_KEY'):
                    print("⚠️ ANTHROPIC_API_KEY not set, using templates")
                else:
                    import anthropic
                    self.ai_client = anthropic.Anthropic()
                    print("✅ AI narratives enabled (Claude Haiku)")
            except Exception as e:
                print(f"⚠️ AI not available ({e}), using templates")

    def load_data(self):
        """Carga datos del CSV 5D y VCP scan"""
        # Cargar 5D CSV
        csv_path = Path("docs/super_opportunities_5d_complete.csv")
        if csv_path.exists():
            self.csv_5d = pd.read_csv(csv_path)
            print(f"✅ CSV 5D cargado: {len(self.csv_5d)} tickers")
        else:
            print("❌ CSV 5D no encontrado")
            return False

        # Cargar VCP data (buscar el scan más reciente)
        vcp_dir = Path("docs/reports/vcp")
        if vcp_dir.exists():
            scan_dirs = sorted([d for d in vcp_dir.iterdir() if d.is_dir() and d.name.startswith("vcp_scan_")])
            if scan_dirs:
                latest_scan = scan_dirs[-1]
                vcp_csv = latest_scan / "data.csv"
                if vcp_csv.exists():
                    self.vcp_data = pd.read_csv(vcp_csv)
                    print(f"✅ VCP data cargado: {len(self.vcp_data)} tickers ({latest_scan.name})")

        return True

    def generate_thesis(self, ticker):
        """Genera tesis completa para un ticker desde CSV 5D"""
        if self.csv_5d is None:
            self.load_data()

        # Buscar ticker en datos 5D
        row_5d = self.csv_5d[self.csv_5d['ticker'] == ticker]
        if row_5d.empty:
            return {"error": f"Ticker {ticker} no encontrado en 5D data"}

        row_5d = row_5d.iloc[0].to_dict()

        # Buscar en VCP data
        vcp_row = None
        if self.vcp_data is not None:
            vcp_match = self.vcp_data[self.vcp_data['ticker'] == ticker]
            if not vcp_match.empty:
                vcp_row = vcp_match.iloc[0].to_dict()

        return self.generate_thesis_from_row(row_5d, vcp_row)

    def generate_thesis_from_row(self, row_dict, vcp_row=None):
        """Genera tesis a partir de un dict normalizado (no requiere CSV 5D)"""
        ticker = row_dict.get('ticker', '')
        return {
            "ticker": ticker,
            "generated_at": datetime.now().isoformat(),
            "overview": self._generate_overview(row_dict),
            "technical": self._analyze_technical(row_dict, vcp_row),
            "fundamental": self._analyze_fundamental(row_dict),
            "catalysts": self._analyze_catalysts(row_dict),
            "thesis_narrative": self._generate_narrative(row_dict, vcp_row),
            "rating": self._calculate_rating(row_dict, vcp_row),
            "raw_data": {"5d": row_dict, "vcp": vcp_row}
        }

    def _normalize_value_row(self, record, fund_row=None):
        """Convierte un record de value/momentum_opportunities al formato esperado por los métodos de análisis"""
        import ast

        # Parsear detail blobs de fundamental_scores (son Python dicts, no JSON)
        health, earnings, growth = {}, {}, {}
        if fund_row is not None:
            for col, target in [('health_details', health), ('earnings_details', earnings), ('growth_details', growth)]:
                raw = fund_row.get(col, '')
                if raw and str(raw) not in ('', 'nan'):
                    try:
                        target.update(ast.literal_eval(str(raw)))
                    except (ValueError, SyntaxError):
                        pass

        roe_pct = health.get('roe_pct')
        rev_growth = growth.get('revenue_growth_yoy')
        profit_margin = earnings.get('profit_margin_pct')
        op_margin = health.get('operating_margin_pct')
        debt_eq = health.get('debt_to_equity')
        current_ratio = health.get('current_ratio')

        value_score = float(record.get('value_score', record.get('momentum_score', 0)) or 0)
        sector_bonus = float(record.get('sector_bonus', 0) or 0)
        source = record.get('_source', 'value')

        def _safe_float(val, default=0):
            if val is None or str(val).lower() in ('nan', 'none', ''):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Cargar datos de insiders detallados
        insider_detail = self._load_insider_detail(record.get('ticker', ''))

        return {
            'ticker': record.get('ticker', ''),
            '_source': source,
            'super_score_5d': value_score,
            'value_score': value_score,
            'vcp_score': _safe_float(record.get('vcp_score')),
            'entry_score': None,
            'fundamental_score': _safe_float(record.get('fundamental_score'), 50),
            'pe_ratio': None,
            'peg_ratio': None,
            'fcf_yield': None,
            'roe': roe_pct / 100 if roe_pct is not None else None,
            'roe_pct': roe_pct,
            'revenue_growth': rev_growth / 100 if rev_growth is not None else None,
            'revenue_growth_pct': rev_growth,
            'profit_margin_pct': profit_margin,
            'operating_margin_pct': op_margin,
            'debt_to_equity': debt_eq,
            'current_ratio': current_ratio,
            'sector_name': record.get('sector', ''),
            'sector_momentum': 'improving' if sector_bonus > 0 else '',
            'sector_score': None,
            'tier_boost': sector_bonus,
            'num_whales': int(_safe_float(record.get('num_whales'))),
            'top_whales': str(record.get('top_whales', '') or ''),
            'insiders_score': _safe_float(record.get('insiders_score')),
            'insider_detail': insider_detail,
            'days_to_earnings': None,
            'analyst_upside': None,
            'num_analysts': 0,
            'price_target': None,
            'upside_percent': None,
            'current_price': record.get('current_price'),
            # Target prices (from fundamental_scores)
            'target_price_analyst': _safe_float(fund_row.get('target_price_analyst')) if fund_row and _safe_float(fund_row.get('target_price_analyst')) > 0 else None,
            'target_price_analyst_high': _safe_float(fund_row.get('target_price_analyst_high')) if fund_row and _safe_float(fund_row.get('target_price_analyst_high')) > 0 else None,
            'target_price_analyst_low': _safe_float(fund_row.get('target_price_analyst_low')) if fund_row and _safe_float(fund_row.get('target_price_analyst_low')) > 0 else None,
            'analyst_count': int(_safe_float(fund_row.get('analyst_count'))) if fund_row and _safe_float(fund_row.get('analyst_count')) > 0 else None,
            'analyst_recommendation': fund_row.get('analyst_recommendation') if fund_row else None,
            'analyst_upside_pct': _safe_float(fund_row.get('analyst_upside_pct')) if fund_row and _safe_float(fund_row.get('analyst_upside_pct')) != 0 else None,
            'target_price_dcf': _safe_float(fund_row.get('target_price_dcf')) if fund_row and _safe_float(fund_row.get('target_price_dcf')) > 0 else None,
            'target_price_pe': _safe_float(fund_row.get('target_price_pe')) if fund_row and _safe_float(fund_row.get('target_price_pe')) > 0 else None,
            'entry_bonus': 0,
            'sentiment': record.get('sentiment', ''),
            'mr_bonus': _safe_float(record.get('mr_bonus')),
            'eps_growth_yoy': _safe_float(record.get('eps_growth_yoy')) or None,
            'rev_growth_yoy': _safe_float(record.get('rev_growth_yoy')) or None,
            'eps_accelerating': record.get('eps_accelerating', False),
            'rev_accelerating': record.get('rev_accelerating', False),
            'eps_accel_quarters': _safe_float(record.get('eps_accel_quarters')),
            'rev_accel_quarters': _safe_float(record.get('rev_accel_quarters')),
            'financial_health_score': _safe_float(record.get('financial_health_score')),
            'earnings_quality_score': _safe_float(record.get('earnings_quality_score')),
            'growth_acceleration_score': _safe_float(record.get('growth_acceleration_score')),
            'short_percent_float': _safe_float(record.get('short_percent_float')),
            'proximity_to_52w_high': _safe_float(record.get('proximity_to_52w_high')),
            'company_name': record.get('company_name', ''),
        }

    def _load_insider_detail(self, ticker: str) -> dict:
        """Carga datos detallados de insiders para un ticker, con recencia"""
        import json as _json

        detail = {'purchases': 0, 'recurring': False, 'recurring_count': 0,
                  'unique_insiders': 0, 'transactions': [], 'last_purchase_date': None,
                  'days_since_last': None, 'recent': False}

        today = datetime.now()

        # Recurring insiders
        recurring_path = Path("docs/recurring_insiders.csv")
        if recurring_path.exists():
            try:
                rdf = pd.read_csv(recurring_path)
                match = rdf[rdf['ticker'] == ticker]
                if not match.empty:
                    row = match.iloc[0]
                    detail['recurring'] = True
                    detail['recurring_count'] = int(row.get('purchase_count', 0))
                    detail['unique_insiders'] = int(row.get('unique_insiders', 0))
                    detail['confidence_score'] = int(row.get('confidence_score', 0))
                    last = row.get('last_purchase', '')
                    if last and str(last) != 'nan':
                        detail['last_purchase_date'] = str(last)
            except Exception:
                pass

        # Insider index (transacciones individuales)
        idx_path = Path("docs/insider_index.json")
        if idx_path.exists():
            try:
                idx = _json.load(open(idx_path))
                if ticker in idx:
                    data = idx[ticker]
                    detail['purchases'] = data.get('purchases', 0)
                    detail['sales'] = data.get('sales', 0)
                    # Solo compras (tipo P)
                    buy_txs = [t for t in data.get('transactions', [])
                               if 'P' in str(t.get('type', ''))]
                    detail['transactions'] = buy_txs[:5]
                    # Fecha más reciente
                    if buy_txs and buy_txs[0].get('date'):
                        detail['last_purchase_date'] = buy_txs[0]['date']
            except Exception:
                pass

        # Calcular recencia
        if detail['last_purchase_date']:
            try:
                last_dt = datetime.strptime(detail['last_purchase_date'], '%Y-%m-%d')
                days = (today - last_dt).days
                detail['days_since_last'] = days
                detail['recent'] = days <= 60  # < 2 meses = reciente
            except Exception:
                pass

        return detail

    def _generate_overview(self, row):
        """Overview/resumen ejecutivo"""
        source = row.get('_source', '5d')
        score = row.get('super_score_5d', 0) or 0
        tier = row.get('tier', 'N/A')
        sector = row.get('sector_name', 'N/A')
        current_price = row.get('current_price')
        target = row.get('price_target')
        upside = row.get('upside_percent')

        # Clasificación profesional por score
        if source in ('value', 'momentum'):
            if score >= 50:
                classification = "Muy atractiva"
            elif score >= 40:
                classification = "Atractiva"
            elif score >= 30:
                classification = "Moderada"
            else:
                classification = "En observación"
            score_label = "value_score" if source == 'value' else "momentum_score"
        else:
            if score >= 80:
                classification = "Excelente"
            elif score >= 65:
                classification = "Muy buena"
            elif score >= 55:
                classification = "Buena"
            else:
                classification = "Moderada"
            score_label = "score_5d"

        return {
            "score": score,
            "score_5d": score,
            "score_label": score_label,
            "classification": classification,
            "source": source,
            "tier": tier,
            "sector": sector,
            "sector_momentum": row.get('sector_momentum', 'N/A'),
            "current_price": current_price,
            "price_target": target,
            "upside_percent": upside,
            "tier_boost": row.get('tier_boost', 0),
            "entry_bonus": row.get('entry_bonus', 0)
        }

    def _analyze_technical(self, row, vcp_row):
        """Análisis técnico detallado"""
        analysis = {
            "vcp_score": row.get('vcp_score', 0),
            "entry_score": row.get('entry_score', 0),
            "strengths": [],
            "concerns": [],
            "signals": []
        }

        # VCP Pattern Analysis
        vcp_score = row.get('vcp_score', 0)
        if vcp_score >= 85:
            analysis['strengths'].append("Patrón VCP de calidad excepcional")
            analysis['signals'].append("🟢 Setup técnico muy fuerte")
        elif vcp_score >= 70:
            analysis['strengths'].append("Buen patrón VCP")
            analysis['signals'].append("🟢 Setup técnico sólido")
        else:
            analysis['concerns'].append("Patrón VCP moderado")

        # Entry Timing
        entry_score = row.get('entry_score')
        if entry_score and entry_score >= 80:
            analysis['strengths'].append("Momento de entrada óptimo (cerca de 52w high, encima de SMAs)")
            analysis['signals'].append("🟢 Timing ideal para entrada")
        elif entry_score and entry_score >= 60:
            analysis['strengths'].append("Buen momento de entrada")
        elif entry_score and entry_score < 40:
            analysis['concerns'].append("Timing de entrada no ideal (lejos de máximos)")

        # VCP Details (si disponible)
        if vcp_row:
            stage = vcp_row.get('etapa_analisis', '')
            listo_comprar = vcp_row.get('listo_comprar', False)
            breakout = vcp_row.get('breakout_potential', 0)
            contracciones = vcp_row.get('num_contracciones', 0)

            analysis['stage'] = stage
            analysis['ready_to_buy'] = listo_comprar
            analysis['breakout_potential'] = breakout
            analysis['num_contractions'] = contracciones

            if stage == "Stage 2 Strong":
                analysis['strengths'].append("En Stage 2 (fase de tendencia alcista ideal)")
                analysis['signals'].append("🟢 Stage 2 confirmado")

            if listo_comprar:
                analysis['signals'].append("✅ SEÑAL DE COMPRA activada")

            if contracciones >= 15:
                analysis['strengths'].append(f"Patrón maduro ({contracciones} contracciones)")
            elif contracciones >= 10:
                analysis['strengths'].append(f"Buen número de contracciones ({contracciones})")

        return analysis

    def _analyze_fundamental(self, row):
        """Análisis fundamental detallado"""
        analysis = {
            "valuation_rating": "N/A",
            "profitability_rating": "N/A",
            "growth_rating": "N/A",
            "health_rating": "N/A",
            "strengths": [],
            "concerns": []
        }

        # Valoración
        peg = row.get('peg_ratio')
        pe = row.get('pe_ratio')
        if peg and peg < 1.0:
            analysis['valuation_rating'] = "⭐⭐⭐⭐⭐ Infravalorada"
            analysis['strengths'].append(f"PEG {peg:.2f} - muy atractiva según crecimiento")
        elif peg and peg < 2.0:
            analysis['valuation_rating'] = "⭐⭐⭐ Razonable"
            analysis['strengths'].append(f"PEG {peg:.2f} - valoración justa")
        elif peg and peg >= 2.5:
            analysis['valuation_rating'] = "⭐ Cara"
            analysis['concerns'].append(f"PEG {peg:.2f} - cara respecto a crecimiento")

        # Rentabilidad
        roe = row.get('roe')
        if roe:
            roe_pct = roe * 100
            if roe_pct > 20:
                analysis['profitability_rating'] = "⭐⭐⭐⭐⭐ Excelente"
                analysis['strengths'].append(f"ROE {roe_pct:.1f}% - rentabilidad excepcional")
            elif roe_pct > 15:
                analysis['profitability_rating'] = "⭐⭐⭐⭐ Buena"
                analysis['strengths'].append(f"ROE {roe_pct:.1f}% - buena rentabilidad")
            elif roe_pct > 10:
                analysis['profitability_rating'] = "⭐⭐⭐ Moderada"
            else:
                analysis['profitability_rating'] = "⭐⭐ Baja"
                analysis['concerns'].append(f"ROE {roe_pct:.1f}% - rentabilidad baja")

        # Crecimiento
        rev_growth = row.get('revenue_growth')
        if rev_growth:
            growth_pct = rev_growth * 100
            if growth_pct > 20:
                analysis['growth_rating'] = "⭐⭐⭐⭐⭐ Fuerte"
                analysis['strengths'].append(f"Crecimiento de ingresos {growth_pct:.1f}% - muy fuerte")
            elif growth_pct > 10:
                analysis['growth_rating'] = "⭐⭐⭐⭐ Sólido"
                analysis['strengths'].append(f"Crecimiento de ingresos {growth_pct:.1f}% - sólido")
            elif growth_pct > 5:
                analysis['growth_rating'] = "⭐⭐⭐ Moderado"
            elif growth_pct > 0:
                analysis['growth_rating'] = "⭐⭐ Lento"
            else:
                analysis['concerns'].append("Ingresos en contracción")

        # Cash Flow
        fcf_yield = row.get('fcf_yield')
        if fcf_yield and fcf_yield > 5:
            analysis['strengths'].append(f"FCF Yield {fcf_yield:.1f}% - fuerte generación de caja")
        elif fcf_yield and fcf_yield > 2:
            analysis['strengths'].append(f"FCF Yield {fcf_yield:.1f}% - buena caja")

        # Analistas
        num_analysts = row.get('num_analysts', 0)
        analyst_upside = row.get('analyst_upside')
        if num_analysts > 10:
            if analyst_upside and analyst_upside > 15:
                analysis['strengths'].append(f"{num_analysts} analistas con upside medio de +{analyst_upside:.0f}%")
            elif analyst_upside and analyst_upside < -10:
                analysis['concerns'].append(f"{num_analysts} analistas ven downside de {analyst_upside:.0f}%")

        return analysis

    def _analyze_catalysts(self, row):
        """Catalizadores y contexto"""
        catalysts = {
            "sector": [],
            "institutional": [],
            "insiders": [],
            "earnings": []
        }

        # Sector
        sector_name = row.get('sector_name', '')
        sector_momentum = row.get('sector_momentum', '')
        sector_score = row.get('sector_score') or 0
        tier_boost = row.get('tier_boost', 0) or 0

        if sector_name:
            if sector_momentum == 'improving' and tier_boost > 0:
                catalysts['sector'].append(f"Sector {sector_name} con momentum mejorando (score {sector_score:.0f}, bonus +{tier_boost})")
            elif sector_momentum == 'improving':
                catalysts['sector'].append(f"Sector {sector_name} con momentum mejorando")
            elif sector_momentum == 'declining':
                catalysts['sector'].append(f"Sector {sector_name} con momentum declinando")

        # Institucionales
        num_whales = row.get('num_whales', 0)
        top_whales = row.get('top_whales', '')
        if num_whales > 0:
            catalysts['institutional'].append(f"{num_whales} grandes inversores institucionales: {top_whales}")
        else:
            catalysts['institutional'].append("Sin posiciones institucionales significativas identificadas")

        # Insiders — detalle real
        insider_score = row.get('insiders_score', 0) or 0
        insider_detail = row.get('insider_detail', {})
        purchases = insider_detail.get('purchases', 0)
        recurring = insider_detail.get('recurring', False)
        recurring_count = insider_detail.get('recurring_count', 0)
        unique_ins = insider_detail.get('unique_insiders', 0)
        transactions = insider_detail.get('transactions', [])

        if recurring and recurring_count > 0:
            catalysts['insiders'].append(
                f"Compras recurrentes: {recurring_count} compras de {unique_ins} insider(s) — patrón consistente de acumulación")
        if purchases > 0:
            catalysts['insiders'].append(f"{purchases} compras de insiders registradas")
            if transactions:
                for tx in transactions[:3]:
                    role = tx.get('insider', '')
                    qty = tx.get('qty', 0)
                    price = tx.get('price', 0)
                    date = tx.get('date', '')
                    if qty and price:
                        amount = qty * price
                        catalysts['insiders'].append(f"  → {role}: ${amount:,.0f} el {date}")
        if not catalysts['insiders']:
            if insider_score >= 60:
                catalysts['insiders'].append(f"Actividad de insiders positiva (score {insider_score:.0f}/100)")
            else:
                catalysts['insiders'].append("Sin compras significativas de insiders recientes")

        # Earnings
        days_to_earnings = row.get('days_to_earnings')
        if days_to_earnings and not pd.isna(days_to_earnings):
            days = int(days_to_earnings)
            if 0 <= days <= 7:
                catalysts['earnings'].append(f"Earnings en {days} días — evento cercano, considerar riesgo")
            elif days > 0:
                catalysts['earnings'].append(f"Próximo earnings en {days} días")

        return catalysts

    def _generate_narrative(self, row, vcp_row):
        """Genera la narrativa/tesis escrita — adaptada al tipo de oportunidad"""
        source = row.get('_source', '5d')
        if source == 'value':
            if self.ai_client:
                try:
                    return self._narrative_value_ai(row)
                except Exception as e:
                    print(f"  ⚠️ AI fallback para {row.get('ticker', '?')}: {e}")
            return self._narrative_value(row)
        elif source == 'momentum':
            return self._narrative_momentum(row, vcp_row)
        else:
            return self._narrative_5d(row, vcp_row)

    def _narrative_value_ai(self, row):
        """Narrativa VALUE generada por Claude — análisis real, no template"""
        ticker = row['ticker']

        # Construir contexto de datos (solo valores reales, None → "no disponible")
        def _fmt(val, suffix='', prefix=''):
            if val is None:
                return 'no disponible'
            return f'{prefix}{val}{suffix}'

        insider = row.get('insider_detail', {})
        transactions_str = ''
        for tx in insider.get('transactions', [])[:5]:
            qty = tx.get('qty', 0)
            price = tx.get('price', 0)
            if qty and price:
                transactions_str += f"\n  - {tx.get('insider', '?')}: ${qty * price:,.0f} ({tx.get('date', '?')})"

        data_context = f"""TICKER: {ticker}
EMPRESA: {_fmt(row.get('company_name'))}
SECTOR: {_fmt(row.get('sector_name'))}
PRECIO ACTUAL: {_fmt(row.get('current_price'), prefix='$')}
VALUE SCORE: {_fmt(row.get('value_score'), '/100')}

FUNDAMENTALES:
- Score fundamental: {_fmt(row.get('fundamental_score'), '/100')} (50.0 = sin datos reales)
- ROE: {_fmt(row.get('roe_pct'), '%')}
- Margen operativo: {_fmt(row.get('operating_margin_pct'), '%')}
- Margen neto: {_fmt(row.get('profit_margin_pct'), '%')}
- Deuda/Capital: {_fmt(row.get('debt_to_equity'))}
- Ratio corriente: {_fmt(row.get('current_ratio'))}
- Crecimiento ingresos YoY: {_fmt(row.get('rev_growth_yoy'), '%')}
- Crecimiento EPS YoY: {_fmt(row.get('eps_growth_yoy'), '%')}
- Ingresos acelerando: {row.get('rev_accelerating', False)} ({_fmt(row.get('rev_accel_quarters'))} trimestres)
- EPS acelerando: {row.get('eps_accelerating', False)} ({_fmt(row.get('eps_accel_quarters'))} trimestres)
- Salud financiera (sub-score): {_fmt(row.get('financial_health_score'), '/100')}
- Calidad beneficios (sub-score): {_fmt(row.get('earnings_quality_score'), '/100')}
- Aceleración crecimiento (sub-score): {_fmt(row.get('growth_acceleration_score'), '/100')}

INSIDERS:
- Score insiders: {_fmt(row.get('insiders_score'), '/100')}
- Compras totales: {insider.get('purchases', 0)}
- Patrón recurrente: {insider.get('recurring', False)} ({insider.get('recurring_count', 0)} compras, {insider.get('unique_insiders', 0)} insiders)
- Última compra: {insider.get('last_purchase_date', 'no disponible')}
- Días desde última compra: {_fmt(insider.get('days_since_last'))}
- Reciente (< 60 días): {insider.get('recent', False)}
- Transacciones:{transactions_str if transactions_str else ' ninguna registrada'}

VALORACIÓN / TARGETS:
- Target analistas (consenso): {_fmt(row.get('target_price_analyst'), prefix='$')}
- Target analistas alto: {_fmt(row.get('target_price_analyst_high'), prefix='$')}
- Target analistas bajo: {_fmt(row.get('target_price_analyst_low'), prefix='$')}
- Num. analistas: {_fmt(row.get('analyst_count'))}
- Recomendación: {_fmt(row.get('analyst_recommendation'))}
- Upside analistas: {_fmt(row.get('analyst_upside_pct'), '%')}
- Valor DCF: {_fmt(row.get('target_price_dcf'), prefix='$')}
- Valor P/E justo: {_fmt(row.get('target_price_pe'), prefix='$')}

CONTEXTO MERCADO:
- Distancia máx. 52 semanas: {_fmt(row.get('proximity_to_52w_high'), '%')}
- Short interest: {_fmt(row.get('short_percent_float'), '% del float')}
- Flujo opciones: {_fmt(row.get('sentiment'))}
- Bonus sector rotation: {float(row.get('tier_boost', 0) or 0):.1f}
- Señal mean reversion: {float(row.get('mr_bonus', 0) or 0) > 0}
"""

        system_prompt = """Eres un analista de inversión value/GARP profesional (estilo Peter Lynch).
Escribe una tesis de inversión breve y accionable en español basada EXCLUSIVAMENTE en los datos proporcionados.

REGLAS ESTRICTAS:
- Usa SOLO los datos proporcionados. NUNCA inventes cifras, ratios, o hechos.
- Si un dato dice "no disponible", menciónalo honestamente como limitación.
- Si fundamental_score = 50.0, indica que no hay datos fundamentales reales.
- Conecta las señales entre sí cuando sea posible (ej: insiders comprando + mejora de márgenes).
- Señala riesgos y preocupaciones, no solo lo positivo.
- Las compras de insiders > 6 meses son menos relevantes, señálalo.
- Tono profesional y directo. Sin hipérbole, sin emojis.

ESTRUCTURA (usa **negrita** para cada sección):
1. **Resumen** — Una frase sobre la empresa y la oportunidad
2. **Fundamentales** — Analiza ROE, márgenes, crecimiento, salud financiera
3. **Insiders** — Evalúa calidad y recencia de las compras
4. **Valoración** — Compara precio actual con targets (analistas, DCF, P/E)
5. **Riesgos** — Al menos 1-2 riesgos concretos
6. **Conclusión** — Veredicto claro: comprar, esperar, o evitar. Con justificación."""

        response = self.ai_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            messages=[{"role": "user", "content": data_context}],
            system=system_prompt,
        )

        return response.content[0].text

    def _narrative_value(self, row):
        """Narrativa para oportunidades VALUE — foco en fundamentales e insiders (template)"""
        ticker = row['ticker']
        score = row.get('value_score', row.get('super_score_5d', 0)) or 0
        sector = row.get('sector_name', '')
        roe_pct = row.get('roe_pct')
        op_margin = row.get('operating_margin_pct')
        profit_margin = row.get('profit_margin_pct')
        debt_eq = row.get('debt_to_equity')
        rev_growth = row.get('revenue_growth_pct')
        fund_score = row.get('fundamental_score', 0) or 0
        insiders_score = row.get('insiders_score', 0) or 0
        insider_detail = row.get('insider_detail', {})
        sentiment = row.get('sentiment', '')
        mr_bonus = row.get('mr_bonus', 0) or 0

        parts = []

        # Intro con puntuación value
        parts.append(f"**{ticker}** — Puntuación value: **{score:.1f}/100** | Sector: {sector}")

        # Fundamentales — datos detallados si disponibles, sub-scores como fallback
        fund_lines = []
        if fund_score is not None and abs(fund_score - 50.0) > 0.1:
            fund_lines.append(f"Score fundamental: {fund_score:.0f}/100")
        if roe_pct is not None:
            label = "excelente" if roe_pct > 20 else "buena" if roe_pct > 15 else "moderada" if roe_pct > 10 else "baja"
            fund_lines.append(f"ROE: {roe_pct:.1f}% ({label})")
        if op_margin is not None:
            fund_lines.append(f"Margen operativo: {op_margin:.1f}%")
        if profit_margin is not None:
            fund_lines.append(f"Margen neto: {profit_margin:.1f}%")
        if debt_eq is not None:
            level = "conservador" if debt_eq < 0.5 else "moderado" if debt_eq < 1.5 else "elevado"
            fund_lines.append(f"Deuda/Capital: {debt_eq:.2f} ({level})")

        # Growth data (directamente de value CSV si no hay health_details)
        rev_growth_yoy = row.get('rev_growth_yoy')
        eps_growth_yoy = row.get('eps_growth_yoy')
        if rev_growth is not None:
            fund_lines.append(f"Crecimiento ingresos: {rev_growth:+.1f}%")
        elif rev_growth_yoy:
            fund_lines.append(f"Crecimiento ingresos: {rev_growth_yoy:+.1f}%")
        if eps_growth_yoy:
            fund_lines.append(f"Crecimiento EPS: {eps_growth_yoy:+.1f}%")
        if row.get('rev_accelerating'):
            q = row.get('rev_accel_quarters', 0)
            fund_lines.append(f"Ingresos acelerando ({int(q)} trimestres consecutivos)" if q else "Ingresos acelerando")

        # Sub-scores del scanner (cuando no hay datos granulares)
        health_sc = row.get('financial_health_score', 0)
        earn_sc = row.get('earnings_quality_score', 0)
        growth_sc = row.get('growth_acceleration_score', 0)
        if not roe_pct and not op_margin:
            # No hay datos granulares — mostrar sub-scores
            if health_sc:
                label = "excelente" if health_sc >= 80 else "buena" if health_sc >= 60 else "moderada"
                fund_lines.append(f"Salud financiera: {health_sc:.0f}/100 ({label})")
            if earn_sc:
                fund_lines.append(f"Calidad de beneficios: {earn_sc:.0f}/100")
            if growth_sc:
                fund_lines.append(f"Aceleración de crecimiento: {growth_sc:.0f}/100")

        # Proximidad a máximos
        prox = row.get('proximity_to_52w_high')
        if prox and prox != 0:
            fund_lines.append(f"Distancia a máx. 52 semanas: {prox:+.1f}%")
        short_float = row.get('short_percent_float')
        if short_float and short_float > 5:
            fund_lines.append(f"Short interest: {short_float:.1f}% del float")

        if fund_lines:
            parts.append("\n**Fundamentales:**\n" + "\n".join(f"• {l}" for l in fund_lines))
        else:
            parts.append("\n**Fundamentales:** Datos detallados no disponibles.")

        # Insiders — con recencia
        insider_lines = []
        recurring = insider_detail.get('recurring', False)
        recurring_count = insider_detail.get('recurring_count', 0)
        unique_ins = insider_detail.get('unique_insiders', 0)
        purchases = insider_detail.get('purchases', 0)
        transactions = insider_detail.get('transactions', [])
        days_since = insider_detail.get('days_since_last')
        is_recent = insider_detail.get('recent', False)

        if recurring and recurring_count > 0:
            insider_lines.append(f"Compras recurrentes: {recurring_count} compras de {unique_ins} insider(s)")
        if purchases > 0:
            insider_lines.append(f"Total compras registradas: {purchases}")

        # Recencia de última compra
        if days_since is not None:
            if days_since <= 30:
                insider_lines.append(f"Última compra: hace {days_since} días (muy reciente)")
            elif days_since <= 60:
                insider_lines.append(f"Última compra: hace {days_since} días (reciente)")
            elif days_since <= 180:
                meses = days_since // 30
                insider_lines.append(f"Última compra: hace {meses} meses (no reciente)")
            else:
                meses = days_since // 30
                insider_lines.append(f"Última compra: hace {meses} meses (antigua — menor relevancia)")

        for tx in transactions[:3]:
            role = tx.get('insider', '')
            qty = tx.get('qty', 0)
            price = tx.get('price', 0)
            date = tx.get('date', '')
            if qty and price:
                insider_lines.append(f"  → {role}: ${qty * price:,.0f} ({date})")

        if insider_lines:
            recency_flag = ""
            if days_since is not None and days_since > 180:
                recency_flag = " — ⚠️ compras antiguas"
            parts.append("\n**Actividad de insiders** (score {:.0f}/100{}):\n{}".format(
                insiders_score, recency_flag, "\n".join(f"• {l}" for l in insider_lines)))
        elif insiders_score >= 60:
            parts.append(f"\n**Actividad de insiders:** Score {insiders_score:.0f}/100 — actividad positiva detectada.")
        else:
            parts.append("\n**Actividad de insiders:** Sin compras significativas recientes.")

        # Puntos de entrada / Valoración
        entry_lines = []
        current_price = row.get('current_price')

        # Analyst targets
        t_analyst = row.get('target_price_analyst')
        t_analyst_high = row.get('target_price_analyst_high')
        t_analyst_low = row.get('target_price_analyst_low')
        analyst_count = row.get('analyst_count')
        analyst_rec = row.get('analyst_recommendation')
        analyst_upside = row.get('analyst_upside_pct')

        if t_analyst and current_price:
            rec_label = str(analyst_rec).replace('_', ' ').title() if analyst_rec and str(analyst_rec) != 'nan' else ''
            n_label = f" ({analyst_count} analistas)" if analyst_count else ""
            upside_str = f" ({analyst_upside:+.1f}%)" if analyst_upside is not None else ""
            entry_lines.append(f"Consenso analistas{n_label}: ${t_analyst:.2f}{upside_str}{' — ' + rec_label if rec_label else ''}")
            if t_analyst_low and t_analyst_high:
                entry_lines.append(f"  Rango: ${t_analyst_low:.2f} — ${t_analyst_high:.2f}")

        # DCF target
        t_dcf = row.get('target_price_dcf')
        if t_dcf and current_price:
            dcf_upside = (t_dcf / current_price - 1) * 100
            label = "infravalorada" if dcf_upside > 10 else "cerca de valor justo" if dcf_upside > -10 else "sobrevalorada"
            entry_lines.append(f"Valor intrínseco (DCF): ${t_dcf:.2f} ({dcf_upside:+.1f}% — {label})")

        # P/E fair value target
        t_pe = row.get('target_price_pe')
        if t_pe and current_price:
            pe_upside = (t_pe / current_price - 1) * 100
            entry_lines.append(f"Valor por P/E justo: ${t_pe:.2f} ({pe_upside:+.1f}%)")

        # Proximity to 52w high
        prox = row.get('proximity_to_52w_high')
        if prox and prox != 0 and current_price:
            if prox >= -5:
                entry_lines.append(f"A {abs(prox):.1f}% del máximo 52 semanas — zona de breakout")
            elif prox >= -15:
                entry_lines.append(f"A {abs(prox):.1f}% del máximo 52 semanas — cerca de máximos")
            elif prox < -30:
                entry_lines.append(f"A {abs(prox):.1f}% del máximo 52 semanas — lejos de máximos, mayor riesgo")

        # Mean reversion signal as potential entry
        if mr_bonus > 0:
            entry_lines.append("Señal de mean reversion: precio temporalmente deprimido en empresa de calidad")

        if entry_lines:
            parts.append("\n**Puntos de entrada / Valoración:**\n" + "\n".join(f"• {l}" for l in entry_lines))
        elif current_price:
            parts.append(f"\n**Puntos de entrada:** Precio actual: ${current_price:.2f}. Datos de valoración no disponibles — ejecutar análisis fundamental para obtener targets.")
        else:
            parts.append("\n**Puntos de entrada:** Datos de valoración no disponibles.")

        # Catalizadores adicionales
        extras = []
        if sentiment == 'BULLISH':
            extras.append("Flujo de opciones alcista (más calls que puts)")
        if row.get('sector_momentum') == 'improving':
            extras.append(f"Sector {sector} con momentum mejorando")
        if is_recent and insiders_score >= 60:
            extras.append("Compras de insiders recientes refuerzan la convicción")

        if extras:
            parts.append("\n**Catalizadores:**\n" + "\n".join(f"• {e}" for e in extras))

        # Conclusión
        has_targets = t_analyst or t_dcf or t_pe
        if score >= 45 and roe_pct and roe_pct > 15 and insiders_score >= 60 and is_recent:
            parts.append("\n**Conclusión:** Empresa con buenos fundamentales, respaldada por compras recientes de insiders. Candidata sólida para posición value.")
        elif score >= 45 and roe_pct and roe_pct > 15 and insiders_score >= 60:
            parts.append("\n**Conclusión:** Buenos fundamentales con actividad de insiders positiva (aunque no reciente). Candidata para posición value con seguimiento.")
        elif score >= 40:
            parts.append("\n**Conclusión:** Oportunidad interesante que requiere análisis adicional del timing de entrada.")
        else:
            parts.append("\n**Conclusión:** En observación. Monitorizar evolución de fundamentales y actividad de insiders.")

        return "\n".join(parts)

    def _narrative_momentum(self, row, vcp_row):
        """Narrativa para oportunidades MOMENTUM — foco en técnico"""
        ticker = row['ticker']
        score = row.get('super_score_5d', 0) or 0
        vcp_score = row.get('vcp_score') or 0
        sector = row.get('sector_name', 'N/A')

        parts = []
        parts.append(f"**{ticker}** — Puntuación momentum: **{score:.1f}/100** | Sector: {sector}")

        # Técnico
        tech_lines = []
        if vcp_score >= 85:
            tech_lines.append(f"Patrón VCP de alta calidad ({vcp_score:.0f}/100)")
        elif vcp_score >= 70:
            tech_lines.append(f"Patrón VCP sólido ({vcp_score:.0f}/100)")
        elif vcp_score > 0:
            tech_lines.append(f"Patrón VCP moderado ({vcp_score:.0f}/100)")

        if vcp_row:
            stage = vcp_row.get('etapa_analisis', '')
            if stage:
                tech_lines.append(f"Etapa: {stage}")
            if vcp_row.get('listo_comprar'):
                tech_lines.append("Señal de compra activada")
            contracciones = vcp_row.get('num_contracciones', 0)
            if contracciones:
                tech_lines.append(f"Contracciones: {contracciones}")

        if tech_lines:
            parts.append("\n**Análisis técnico:**\n" + "\n".join(f"• {l}" for l in tech_lines))

        # Fundamentales breves
        roe_pct = row.get('roe_pct')
        rev_growth = row.get('revenue_growth_pct')
        fund_lines = []
        if roe_pct is not None:
            fund_lines.append(f"ROE: {roe_pct:.1f}%")
        if rev_growth is not None:
            fund_lines.append(f"Crecimiento ingresos: {rev_growth:+.1f}%")
        if fund_lines:
            parts.append("\n**Fundamentales:** " + " | ".join(fund_lines))

        # Conclusión
        if vcp_score >= 80:
            parts.append("\n**Conclusión:** Setup técnico fuerte. Adecuada para operativa de momentum/swing.")
        else:
            parts.append("\n**Conclusión:** Setup moderado. Esperar confirmación de breakout antes de entrar.")

        return "\n".join(parts)

    def _narrative_5d(self, row, vcp_row):
        """Narrativa para oportunidades 5D (original)"""
        ticker = row['ticker']
        score_5d = row.get('super_score_5d', 0) or 0
        vcp_score = row.get('vcp_score') or 0
        entry_score = row.get('entry_score') or 0
        upside = row.get('upside_percent') or 0
        sector = row.get('sector_name', 'N/A')

        parts = []
        parts.append(f"**{ticker}** — Score combinado: **{score_5d:.1f}/100** | Sector: {sector}")

        # Technical
        if vcp_score >= 85:
            parts.append(f"\nPatrón VCP de alta calidad ({vcp_score:.0f}/100).")
            if vcp_row and vcp_row.get('listo_comprar'):
                parts[-1] += " Señal de compra activada."
        elif vcp_score >= 70:
            parts.append(f"\nPatrón VCP sólido ({vcp_score:.0f}/100).")

        if entry_score and entry_score >= 80:
            parts.append(f"Timing de entrada favorable ({entry_score:.0f}/100) — cerca de máximos de 52 semanas.")

        # Fundamental
        peg = row.get('peg_ratio')
        if peg and peg < 1.5:
            parts.append(f"Valoración atractiva (PEG {peg:.2f}).")
        if upside and upside > 20:
            parts.append(f"Precio objetivo sugiere upside de +{upside:.0f}%.")

        # Sector
        if sector and sector != 'N/A':
            momentum = row.get('sector_momentum', '')
            if momentum == 'improving':
                parts.append(f"Sector {sector} con momentum mejorando.")
            elif momentum == 'declining':
                parts.append(f"Sector {sector} con momentum declinando — viento en contra.")

        if score_5d >= 70:
            parts.append("\n**Conclusión:** Oportunidad de alta calidad que combina técnico y fundamental.")
        elif score_5d >= 55:
            parts.append("\n**Conclusión:** Oportunidad sólida. Considerar para diversificación.")
        else:
            parts.append("\n**Conclusión:** Oportunidad moderada. Requiere seguimiento.")

        return "\n".join(parts)

    def _calculate_rating(self, row, vcp_row):
        """Calcula rating de estrellas para diferentes aspectos"""
        import numpy as np
        rating = {}

        # Technical Setup (0-5 stars)
        vcp_score = row.get('vcp_score', 0) or 0
        entry_score = row.get('entry_score', 0)

        # Handle NaN/None in entry_score
        if entry_score is None or (isinstance(entry_score, float) and np.isnan(entry_score)):
            entry_score = 50  # Default neutral

        tech_avg = (vcp_score + entry_score) / 2
        rating['technical'] = min(5, int(tech_avg / 20) + 1)

        # Fundamental Value (0-5 stars)
        fund_score = row.get('fundamental_score', 50)
        if fund_score is None or (isinstance(fund_score, float) and np.isnan(fund_score)):
            fund_score = 50
        rating['fundamental'] = min(5, int(fund_score / 20) + 1)

        # Risk/Reward (0-5 stars) - basado en combinación
        score_5d = row.get('super_score_5d', 50) or 50
        upside = row.get('upside_percent', 0)
        if upside is None or (isinstance(upside, float) and np.isnan(upside)):
            upside = 0
        risk_reward = (score_5d + abs(upside)) / 2
        rating['risk_reward'] = min(5, int(risk_reward / 20) + 1)

        # Overall
        rating['overall'] = round((rating['technical'] + rating['fundamental'] + rating['risk_reward']) / 3, 1)

        return rating


def main():
    """Genera tesis para top N oportunidades"""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Genera tesis de inversión')
    parser.add_argument('num_stocks', nargs='?', type=int, default=50, help='Top N tickers 5D')
    parser.add_argument('--ai', action='store_true', help='Usar Claude AI para narrativas VALUE')
    args = parser.parse_args()
    num_stocks = args.num_stocks

    gen = ThesisGenerator(use_ai=args.ai)
    gen.load_data()

    # Generar tesis para top N
    top_n = gen.csv_5d.nlargest(num_stocks, 'super_score_5d')['ticker'].tolist()

    print("\n" + "="*80)
    print(f"📝 GENERANDO TESIS PARA TOP {num_stocks} OPORTUNIDADES")
    print("="*80)

    theses = {}
    for idx, ticker in enumerate(top_n, 1):
        print(f"\n🔍 [{idx}/{num_stocks}] Generando tesis para {ticker}...", end=" ")
        thesis = gen.generate_thesis(ticker)
        theses[ticker] = thesis

        # Mostrar resumen
        if 'error' not in thesis:
            print(f"✅ Score: {thesis['overview']['score_5d']:.1f} | Tech: {'⭐' * thesis['rating']['technical']} | Fund: {'⭐' * thesis['rating']['fundamental']}")
        else:
            print(f"❌ {thesis['error']}")

    # ── Generar tesis para tickers VALUE + MOMENTUM no cubiertos por 5D ────────
    fund_df = None
    fund_path = Path("docs/fundamental_scores.csv")
    if fund_path.exists():
        fund_df = pd.read_csv(fund_path)

    for opp_csv, score_col, label in [
        ("docs/value_opportunities.csv", "value_score", "VALUE"),
        ("docs/momentum_opportunities.csv", "momentum_score", "MOMENTUM"),
    ]:
        opp_path = Path(opp_csv)
        if not opp_path.exists():
            continue
        opp_df = pd.read_csv(opp_path)
        source_key = 'value' if label == 'VALUE' else 'momentum'
        print(f"\n📊 Generando tesis {label} para todos los tickers...")
        for _, rec in opp_df.iterrows():
            ticker = str(rec.get('ticker', ''))
            if not ticker:
                continue
            # fundamental_scores row para datos adicionales
            fund_row = None
            if fund_df is not None:
                match = fund_df[fund_df['ticker'] == ticker]
                if not match.empty:
                    fund_row = match.iloc[0].to_dict()
            # VCP row
            vcp_row = None
            if gen.vcp_data is not None:
                vcp_match = gen.vcp_data[gen.vcp_data['ticker'] == ticker]
                if not vcp_match.empty:
                    vcp_row = vcp_match.iloc[0].to_dict()

            rec_dict = rec.to_dict()
            rec_dict['_source'] = source_key
            row_dict = gen._normalize_value_row(rec_dict, fund_row)
            thesis = gen.generate_thesis_from_row(row_dict, vcp_row)
            # Guardar con clave específica por fuente (TICKER__value, TICKER__momentum)
            # para que cada tabla tenga su propia narrativa adaptada
            theses[f"{ticker}__{source_key}"] = thesis
            # Si no existe ya como 5D, guardar también como clave simple
            if ticker not in theses:
                theses[ticker] = thesis
            score = row_dict['super_score_5d']
            print(f"  ✅ [{label}] {ticker} → score {score:.1f}")

    # ── Guardar JSON (convertir NaN a null para compatibilidad con JavaScript) ─
    import numpy as np
    def convert_nan_to_none(obj):
        """Convierte NaN/Inf a None recursivamente para compatibilidad JSON"""
        if isinstance(obj, dict):
            return {k: convert_nan_to_none(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_nan_to_none(item) for item in obj]
        elif isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj
        return obj

    theses_clean = convert_nan_to_none(theses)

    output_file = Path("docs/theses.json")
    with open(output_file, 'w') as f:
        json.dump(theses_clean, f, indent=2, default=str)

    print(f"\n{'='*80}")
    print(f"✅ {len(theses)} tesis guardadas en: {output_file}")
    print(f"📊 Tamaño del archivo: {output_file.stat().st_size / 1024:.1f} KB")

    # Stats
    ratings = [t['rating']['overall'] for t in theses.values() if 'error' not in t]
    if ratings:
        print(f"\n📈 Rating promedio: {sum(ratings)/len(ratings):.1f}/5")
        print(f"⭐ Mejor rating: {max(ratings):.1f}/5")
        print(f"📉 Peor rating: {min(ratings):.1f}/5")

    # Mostrar una tesis completa como ejemplo (top 1)
    if top_n:
        example = top_n[0]
        print(f"\n{'='*80}")
        print(f"📄 EJEMPLO DE TESIS COMPLETA: {example}")
        print('='*80)
        thesis = theses[example]
        if 'error' not in thesis:
            print(f"\n{thesis['thesis_narrative']}")
            print(f"\n⭐ Rating Overall: {thesis['rating']['overall']}/5")


if __name__ == "__main__":
    main()
