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
        """Genera tesis completa para un ticker"""
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

        # Construir tesis
        thesis = {
            "ticker": ticker,
            "generated_at": datetime.now().isoformat(),
            "overview": self._generate_overview(row_5d),
            "technical": self._analyze_technical(row_5d, vcp_row),
            "fundamental": self._analyze_fundamental(row_5d),
            "catalysts": self._analyze_catalysts(row_5d),
            "thesis_narrative": self._generate_narrative(row_5d, vcp_row),
            "rating": self._calculate_rating(row_5d, vcp_row),
            "raw_data": {
                "5d": row_5d,
                "vcp": vcp_row
            }
        }

        return thesis

    def _generate_overview(self, row):
        """Overview/resumen ejecutivo"""
        score_5d = row.get('super_score_5d', 0)
        tier = row.get('tier', 'N/A')
        sector = row.get('sector_name', 'N/A')
        current_price = row.get('current_price')
        target = row.get('price_target')
        upside = row.get('upside_percent')

        # Clasificación por score
        if score_5d >= 85:
            classification = "⭐⭐⭐⭐ LEGENDARY"
        elif score_5d >= 75:
            classification = "⭐⭐⭐ ÉPICA"
        elif score_5d >= 65:
            classification = "⭐⭐ EXCELENTE"
        elif score_5d >= 55:
            classification = "⭐ BUENA"
        else:
            classification = "MODERADA"

        return {
            "score_5d": score_5d,
            "classification": classification,
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
        sector_score = row.get('sector_score', 0)
        tier_boost = row.get('tier_boost', 0)

        if sector_name:
            if sector_momentum == 'improving' and tier_boost > 0:
                catalysts['sector'].append(f"✅ Sector {sector_name} con momentum mejorando (score {sector_score:.0f}, boost +{tier_boost})")
            elif sector_momentum == 'improving':
                catalysts['sector'].append(f"Sector {sector_name} con momentum mejorando")
            elif sector_momentum == 'declining':
                catalysts['sector'].append(f"⚠️ Sector {sector_name} con momentum declinando")

        # Institucionales
        num_whales = row.get('num_whales', 0)
        top_whales = row.get('top_whales', '')
        if num_whales > 0:
            catalysts['institutional'].append(f"🐋 {num_whales} whale investors: {top_whales}")
        else:
            catalysts['institutional'].append("Sin posiciones de whale investors identificadas")

        # Insiders
        insider_score = row.get('insiders_score', 0)
        if insider_score >= 80:
            catalysts['insiders'].append(f"✅ Compras de insiders muy fuertes (score {insider_score:.0f})")
        elif insider_score >= 60:
            catalysts['insiders'].append(f"Compras de insiders sólidas (score {insider_score:.0f})")
        elif insider_score < 30:
            catalysts['insiders'].append(f"Compras de insiders débiles (score {insider_score:.0f})")

        # Earnings
        days_to_earnings = row.get('days_to_earnings')
        if days_to_earnings and not pd.isna(days_to_earnings):
            days = int(days_to_earnings)
            if 0 <= days <= 7:
                catalysts['earnings'].append(f"⚠️ Earnings en {days} días - evento cercano")
            elif days > 0:
                catalysts['earnings'].append(f"Próximo earnings en {days} días")

        return catalysts

    def _generate_narrative(self, row, vcp_row):
        """Genera la narrativa/tesis escrita"""
        ticker = row['ticker']
        score_5d = row.get('super_score_5d', 0)
        vcp_score = row.get('vcp_score', 0)
        entry_score = row.get('entry_score', 0)
        upside = row.get('upside_percent', 0)
        sector = row.get('sector_name', 'N/A')

        # Determinar tipo de oportunidad
        if vcp_score >= 80 and entry_score >= 70:
            opp_type = "momentum técnico"
        elif upside and upside > 30:
            opp_type = "value con catalizador técnico"
        elif vcp_score >= 70:
            opp_type = "setup técnico"
        else:
            opp_type = "oportunidad mixta"

        # Intro
        narrative = f"{ticker} representa una oportunidad de **{opp_type}** "

        if score_5d >= 70:
            narrative += f"con score 5D excepcional de {score_5d:.1f}/100. "
        elif score_5d >= 60:
            narrative += f"con score 5D sólido de {score_5d:.1f}/100. "
        else:
            narrative += f"con score 5D moderado de {score_5d:.1f}/100. "

        # Technical highlights
        if vcp_score >= 85:
            narrative += f"El patrón VCP es de calidad excepcional ({vcp_score:.0f}/100)"
            if vcp_row and vcp_row.get('listo_comprar'):
                narrative += " y muestra señal de compra activada. "
            else:
                narrative += ". "
        elif vcp_score >= 70:
            narrative += f"Presenta un sólido patrón VCP ({vcp_score:.0f}/100). "

        # Entry timing
        if entry_score and entry_score >= 80:
            narrative += f"El timing de entrada es óptimo ({entry_score:.0f}/100) - el precio está cerca de máximos de 52 semanas, por encima de medias móviles clave, y muestra fuerte momentum. "
        elif entry_score and entry_score >= 60:
            narrative += f"El momento de entrada es favorable ({entry_score:.0f}/100). "
        elif entry_score and entry_score < 40:
            narrative += f"El timing de entrada no es ideal actualmente ({entry_score:.0f}/100). "

        # Fundamental context
        peg = row.get('peg_ratio')
        if peg and peg < 1.5:
            narrative += f"Desde el punto de vista fundamental, la valoración es atractiva (PEG {peg:.2f}). "
        elif peg and peg > 2.5:
            narrative += f"La valoración fundamental es elevada (PEG {peg:.2f}), sugiriendo que el upside viene más del momentum que del value. "

        if upside and upside > 20:
            narrative += f"El precio objetivo sugiere un upside de +{upside:.0f}%. "
        elif upside and upside < 0:
            narrative += f"Los fundamentales sugieren sobrevaloración ({upside:.0f}% desde niveles actuales). "

        # Sector context
        if sector and sector != 'N/A':
            momentum = row.get('sector_momentum', '')
            if momentum == 'improving':
                narrative += f"El sector {sector} muestra momentum mejorando, proporcionando vientos de cola. "
            elif momentum == 'declining':
                narrative += f"El sector {sector} está en decline, lo cual puede ser un viento en contra. "

        # Conclusion
        if score_5d >= 70 and vcp_score >= 80:
            narrative += "\n\n**Conclusión:** Setup de alta calidad para traders de momentum. El patrón técnico es fuerte y el timing es favorable."
        elif vcp_score >= 70 and (upside and upside > 20):
            narrative += "\n\n**Conclusión:** Combinación interesante de setup técnico y upside fundamental. Adecuada para posiciones swing."
        elif score_5d >= 65:
            narrative += "\n\n**Conclusión:** Oportunidad sólida que combina múltiples factores positivos. Considerar para diversificación."
        else:
            narrative += "\n\n**Conclusión:** Oportunidad moderada. Requiere seguimiento cercano antes de tomar posición."

        # Best for
        if vcp_score >= 80 and entry_score >= 70:
            narrative += "\n\n**Mejor para:** Traders de momentum buscando breakouts de alta probabilidad."
        elif upside and upside > 30:
            narrative += "\n\n**Mejor para:** Inversores value con tolerancia a volatilidad técnica."
        else:
            narrative += "\n\n**Mejor para:** Inversores híbridos que buscan balance técnico-fundamental."

        return narrative

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

    # Guardar JSON (convertir NaN a null para compatibilidad con JavaScript)
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
