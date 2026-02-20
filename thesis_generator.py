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

    def __init__(self):
        self.csv_5d = None
        self.vcp_data = None

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
        import json as _json

        # Parsear JSON blobs de fundamental_scores si están disponibles
        health, earnings, growth = {}, {}, {}
        if fund_row is not None:
            for col, target in [('health_details', health), ('earnings_details', earnings), ('growth_details', growth)]:
                raw = fund_row.get(col, '')
                if raw and str(raw) not in ('', 'nan'):
                    try:
                        target.update(_json.loads(str(raw)))
                    except Exception:
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
        """Carga datos detallados de insiders para un ticker"""
        import json as _json
        detail = {'purchases': 0, 'recurring': False, 'recurring_count': 0,
                  'unique_insiders': 0, 'transactions': []}

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
                    detail['transactions'] = data.get('transactions', [])[:5]
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
            return self._narrative_value(row)
        elif source == 'momentum':
            return self._narrative_momentum(row, vcp_row)
        else:
            return self._narrative_5d(row, vcp_row)

    def _narrative_value(self, row):
        """Narrativa para oportunidades VALUE — foco en fundamentales e insiders"""
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
        if fund_score and abs(fund_score - 50.0) > 0.1:
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

        # Insiders
        insider_lines = []
        recurring = insider_detail.get('recurring', False)
        recurring_count = insider_detail.get('recurring_count', 0)
        unique_ins = insider_detail.get('unique_insiders', 0)
        purchases = insider_detail.get('purchases', 0)
        transactions = insider_detail.get('transactions', [])

        if recurring and recurring_count > 0:
            insider_lines.append(f"Compras recurrentes: {recurring_count} compras de {unique_ins} insider(s)")
        if purchases > 0:
            insider_lines.append(f"Total compras registradas: {purchases}")
        for tx in transactions[:3]:
            role = tx.get('insider', '')
            qty = tx.get('qty', 0)
            price = tx.get('price', 0)
            date = tx.get('date', '')
            if qty and price:
                insider_lines.append(f"  → {role}: ${qty * price:,.0f} ({date})")

        if insider_lines:
            parts.append("\n**Actividad de insiders** (score {:.0f}/100):\n{}".format(
                insiders_score, "\n".join(f"• {l}" for l in insider_lines)))
        elif insiders_score >= 60:
            parts.append(f"\n**Actividad de insiders:** Score {insiders_score:.0f}/100 — actividad positiva detectada.")
        else:
            parts.append("\n**Actividad de insiders:** Sin compras significativas recientes.")

        # Catalizadores adicionales
        extras = []
        if sentiment == 'BULLISH':
            extras.append("Flujo de opciones alcista (más calls que puts)")
        if mr_bonus > 0:
            extras.append("Señal de mean reversion: precio temporalmente deprimido en empresa de calidad")
        if row.get('sector_momentum') == 'improving':
            extras.append(f"Sector {sector} con momentum mejorando")

        if extras:
            parts.append("\n**Catalizadores:**\n" + "\n".join(f"• {e}" for e in extras))

        # Conclusión
        if score >= 45 and roe_pct and roe_pct > 15 and insiders_score >= 60:
            parts.append("\n**Conclusión:** Empresa con buenos fundamentales y respaldada por compras de insiders. Candidata sólida para posición value.")
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

    # Permitir pasar número como argumento
    num_stocks = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    gen = ThesisGenerator()
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
        print(f"\n📊 Generando tesis para tickers {label} no cubiertos...")
        for _, rec in opp_df.iterrows():
            ticker = str(rec.get('ticker', ''))
            if not ticker or ticker in theses:
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
            rec_dict['_source'] = 'value' if label == 'VALUE' else 'momentum'
            row_dict = gen._normalize_value_row(rec_dict, fund_row)
            thesis = gen.generate_thesis_from_row(row_dict, vcp_row)
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
