#!/usr/bin/env python3
"""
Sistema de Reportes Históricos - Mantiene un historial organizado de análisis diarios
"""

import os
import shutil
import pandas as pd
from datetime import datetime, timedelta
import json

class HistorialReportes:
    def __init__(self):
        self.base_dir = "reports"
        self.historical_dir = "reports/historical"
        self.daily_dir = "reports/historical/daily"
        self.summary_dir = "reports/historical/summaries"
        
        # Crear directorios si no existen
        os.makedirs(self.daily_dir, exist_ok=True)
        os.makedirs(self.summary_dir, exist_ok=True)
    
    def archivar_reporte_diario(self):
        """
        Archiva los reportes del día actual con timestamp
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        fecha_str = datetime.now().strftime('%Y-%m-%d')
        
        print(f"📦 Archivando reportes del {fecha_str}...")
        
        # Crear directorio para el día
        day_dir = os.path.join(self.daily_dir, datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(day_dir, exist_ok=True)
        
        archivos_archivados = []
        
        # Archivos a archivar
        archivos_principales = [
            ("reports/insiders_daily.csv", f"insiders_daily_{timestamp}.csv"),
            ("reports/insiders_opportunities.csv", f"insiders_opportunities_{timestamp}.csv"),
            ("reports/insiders_opportunities.html", f"insiders_opportunities_{timestamp}.html"),
            ("reports/insiders_report_completo.html", f"insiders_report_completo_{timestamp}.html"),
            ("reports/insiders_report_bundle.zip", f"insiders_report_bundle_{timestamp}.zip")
        ]
        
        for archivo_origen, archivo_destino in archivos_principales:
            if os.path.exists(archivo_origen):
                destino_completo = os.path.join(day_dir, archivo_destino)
                try:
                    shutil.copy2(archivo_origen, destino_completo)
                    size = os.path.getsize(destino_completo)
                    archivos_archivados.append({
                        'archivo': archivo_destino,
                        'size': size,
                        'timestamp': timestamp
                    })
                    print(f"✅ {archivo_destino}: {size:,} bytes")
                except Exception as e:
                    print(f"⚠️ Error archivando {archivo_origen}: {e}")
        
        # Crear metadata del día
        metadata = {
            'fecha': fecha_str,
            'timestamp': timestamp,
            'archivos': archivos_archivados,
            'total_archivos': len(archivos_archivados),
            'directorio': day_dir
        }
        
        # Guardar metadata
        metadata_path = os.path.join(day_dir, f"metadata_{timestamp}.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Archivos guardados en: {day_dir}")
        print(f"📄 Metadata: {metadata_path}")
        
        return day_dir, len(archivos_archivados)
    
    def generar_resumen_semanal(self):
        """
        Genera un resumen de la semana pasada
        """
        print("📊 Generando resumen semanal...")
        
        # Calcular fechas de la semana pasada
        hoy = datetime.now()
        inicio_semana = hoy - timedelta(days=7)
        fin_semana = hoy - timedelta(days=1)
        
        fecha_inicio = inicio_semana.strftime('%Y-%m-%d')
        fecha_fin = fin_semana.strftime('%Y-%m-%d')
        
        print(f"📅 Período: {fecha_inicio} a {fecha_fin}")
        
        # Buscar reportes de la semana
        reportes_semana = []
        total_oportunidades = 0
        empresas_unicas = set()
        
        for dia in range(7):
            fecha_dia = (inicio_semana + timedelta(days=dia)).strftime('%Y-%m-%d')
            day_dir = os.path.join(self.daily_dir, fecha_dia)
            
            if os.path.exists(day_dir):
                # Buscar CSV de oportunidades del día
                for archivo in os.listdir(day_dir):
                    if archivo.startswith('insiders_opportunities_') and archivo.endswith('.csv'):
                        csv_path = os.path.join(day_dir, archivo)
                        try:
                            df = pd.read_csv(csv_path)
                            if len(df) > 0 and 'Mensaje' not in df.columns:
                                num_oportunidades = len(df)
                                total_oportunidades += num_oportunidades
                                
                                # Obtener tickers únicos
                                if 'Ticker' in df.columns:
                                    empresas_unicas.update(df['Ticker'].dropna().unique())
                                
                                reportes_semana.append({
                                    'fecha': fecha_dia,
                                    'oportunidades': num_oportunidades,
                                    'archivo': archivo,
                                    'top_ticker': df.iloc[0]['Ticker'] if len(df) > 0 and 'Ticker' in df.columns else 'N/A'
                                })
                                break
                        except Exception as e:
                            print(f"⚠️ Error leyendo {csv_path}: {e}")
        
        # Crear resumen
        resumen = {
            'periodo': f"{fecha_inicio} a {fecha_fin}",
            'dias_con_reportes': len(reportes_semana),
            'total_oportunidades': total_oportunidades,
            'empresas_unicas': len(empresas_unicas),
            'promedio_diario': round(total_oportunidades / max(len(reportes_semana), 1), 1),
            'reportes_diarios': reportes_semana,
            'empresas_mas_activas': list(empresas_unicas)[:10],
            'generado': datetime.now().isoformat()
        }
        
        # Guardar resumen semanal
        semana_str = f"semana_{inicio_semana.strftime('%Y%m%d')}_{fin_semana.strftime('%Y%m%d')}"
        resumen_path = os.path.join(self.summary_dir, f"resumen_{semana_str}.json")
        
        with open(resumen_path, 'w', encoding='utf-8') as f:
            json.dump(resumen, f, indent=2, ensure_ascii=False)
        
        # Crear HTML del resumen
        html_path = self.crear_html_resumen_semanal(resumen, semana_str)
        
        print(f"✅ Resumen semanal generado: {resumen_path}")
        print(f"🌐 HTML resumen: {html_path}")
        print(f"📊 Total oportunidades: {total_oportunidades}")
        print(f"🏢 Empresas únicas: {len(empresas_unicas)}")
        
        return resumen_path, html_path
    
    def crear_html_resumen_semanal(self, resumen, semana_str):
        """
        Crea un HTML del resumen semanal
        """
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>📊 Resumen Semanal - Insider Trading</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f7fa; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                .stats {{ display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; }}
                .stat {{ text-align: center; padding: 20px; background: #ecf0f1; border-radius: 10px; margin: 10px; min-width: 150px; }}
                .stat-number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
                .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: center; border: 1px solid #ddd; }}
                th {{ background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%); color: white; }}
                tr:nth-child(even) {{ background: #f8f9fa; }}
                tr:hover {{ background: #e3f2fd; }}
                .empresas-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 10px; margin: 20px 0; }}
                .empresa-tag {{ background: #3498db; color: white; padding: 5px 10px; border-radius: 15px; text-align: center; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Resumen Semanal de Insider Trading</h1>
                <p style="text-align: center; color: #7f8c8d; font-size: 1.1em;">{resumen['periodo']}</p>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-number">{resumen['dias_con_reportes']}</div>
                        <div class="stat-label">Días con Reportes</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{resumen['total_oportunidades']}</div>
                        <div class="stat-label">Total Oportunidades</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{resumen['empresas_unicas']}</div>
                        <div class="stat-label">Empresas Únicas</div>
                    </div>
                    <div class="stat">
                        <div class="stat-number">{resumen['promedio_diario']}</div>
                        <div class="stat-label">Promedio Diario</div>
                    </div>
                </div>
                
                <h2>📅 Reportes Diarios</h2>
                <table>
                    <tr>
                        <th>Fecha</th>
                        <th>Oportunidades</th>
                        <th>Top Ticker</th>
                        <th>Estado</th>
                    </tr>
        """
        
        for reporte in resumen['reportes_diarios']:
            estado = "✅ Activo" if reporte['oportunidades'] > 0 else "💤 Sin actividad"
            html_content += f"""
                    <tr>
                        <td>{reporte['fecha']}</td>
                        <td><strong>{reporte['oportunidades']}</strong></td>
                        <td>{reporte['top_ticker']}</td>
                        <td>{estado}</td>
                    </tr>
            """
        
        html_content += f"""
                </table>
                
                <h2>🏢 Empresas Más Activas ({len(resumen['empresas_mas_activas'])} tickers)</h2>
                <div class="empresas-grid">
        """
        
        for empresa in resumen['empresas_mas_activas']:
            html_content += f'<div class="empresa-tag">{empresa}</div>'
        
        html_content += f"""
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #e8f5e8; border-radius: 10px; text-align: center;">
                    <h3>📈 Análisis de Tendencias</h3>
                    <p><strong>Actividad promedio:</strong> {resumen['promedio_diario']} oportunidades por día</p>
                    <p><strong>Diversificación:</strong> {resumen['empresas_unicas']} empresas diferentes detectadas</p>
                    <p><strong>Cobertura:</strong> {resumen['dias_con_reportes']}/7 días con actividad de insiders</p>
                </div>
                
                <div style="margin-top: 20px; text-align: center; color: #7f8c8d; font-size: 0.9em;">
                    <p>Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>🤖 Sistema de Análisis de Insider Trading</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        html_path = os.path.join(self.summary_dir, f"resumen_{semana_str}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_path
    
    def limpiar_archivos_antiguos(self, dias_mantener=30):
        """
        Limpia archivos más antiguos que X días
        """
        print(f"🧹 Limpiando archivos anteriores a {dias_mantener} días...")
        
        fecha_limite = datetime.now() - timedelta(days=dias_mantener)
        archivos_eliminados = 0
        
        # Limpiar reportes diarios antiguos
        if os.path.exists(self.daily_dir):
            for dia_dir in os.listdir(self.daily_dir):
                dia_path = os.path.join(self.daily_dir, dia_dir)
                if os.path.isdir(dia_path):
                    try:
                        fecha_dir = datetime.strptime(dia_dir, '%Y-%m-%d')
                        if fecha_dir < fecha_limite:
                            shutil.rmtree(dia_path)
                            archivos_eliminados += 1
                            print(f"🗑️ Eliminado: {dia_dir}")
                    except ValueError:
                        # Nombre de directorio no válido, ignorar
                        continue
        
        print(f"✅ Limpieza completada: {archivos_eliminados} directorios eliminados")
        return archivos_eliminados
    
    def mostrar_estadisticas_historico(self):
        """
        Muestra estadísticas del histórico actual
        """
        print("📊 ESTADÍSTICAS DEL HISTÓRICO")
        print("=" * 35)
        
        if not os.path.exists(self.daily_dir):
            print("❌ No hay histórico disponible")
            return
        
        # Contar días con reportes
        dias_total = 0
        oportunidades_total = 0
        empresas_todas = set()
        
        for dia_dir in os.listdir(self.daily_dir):
            dia_path = os.path.join(self.daily_dir, dia_dir)
            if os.path.isdir(dia_path):
                dias_total += 1
                
                # Buscar CSV de oportunidades
                for archivo in os.listdir(dia_path):
                    if archivo.startswith('insiders_opportunities_') and archivo.endswith('.csv'):
                        csv_path = os.path.join(dia_path, archivo)
                        try:
                            df = pd.read_csv(csv_path)
                            if len(df) > 0 and 'Mensaje' not in df.columns:
                                oportunidades_total += len(df)
                                if 'Ticker' in df.columns:
                                    empresas_todas.update(df['Ticker'].dropna().unique())
                        except:
                            continue
                        break
        
        # Contar resúmenes semanales
        resumenes_semanales = 0
        if os.path.exists(self.summary_dir):
            resumenes_semanales = len([f for f in os.listdir(self.summary_dir) if f.endswith('.json')])
        
        print(f"📅 Días con reportes: {dias_total}")
        print(f"🎯 Total oportunidades: {oportunidades_total:,}")
        print(f"🏢 Empresas únicas: {len(empresas_todas)}")
        print(f"📊 Promedio por día: {oportunidades_total/max(dias_total, 1):.1f}")
        print(f"📑 Resúmenes semanales: {resumenes_semanales}")
        
        if dias_total > 0:
            fecha_mas_antigua = min([d for d in os.listdir(self.daily_dir) 
                                   if os.path.isdir(os.path.join(self.daily_dir, d))])
            fecha_mas_reciente = max([d for d in os.listdir(self.daily_dir) 
                                    if os.path.isdir(os.path.join(self.daily_dir, d))])
            print(f"📆 Período: {fecha_mas_antigua} a {fecha_mas_reciente}")

def main():
    """
    Función principal del sistema de histórico
    """
    import sys
    
    historial = HistorialReportes()
    
    if len(sys.argv) > 1:
        comando = sys.argv[1]
        
        if comando == "--archivar":
            day_dir, archivos = historial.archivar_reporte_diario()
            print(f"✅ {archivos} archivos archivados en {day_dir}")
            
        elif comando == "--resumen-semanal":
            historial.generar_resumen_semanal()
            
        elif comando == "--limpiar":
            dias = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            historial.limpiar_archivos_antiguos(dias)
            
        elif comando == "--estadisticas":
            historial.mostrar_estadisticas_historico()
            
        elif comando == "--completo":
            # Archivar día actual
            historial.archivar_reporte_diario()
            
            # Generar resumen semanal si es domingo o lunes
            dia_semana = datetime.now().weekday()  # 0 = lunes, 6 = domingo
            if dia_semana in [0, 6]:  # Lunes o domingo
                print("\n📊 Generando resumen semanal...")
                historial.generar_resumen_semanal()
            
            # Limpiar archivos antiguos (mantener 30 días)
            print("\n🧹 Limpiando archivos antiguos...")
            historial.limpiar_archivos_antiguos(30)
            
            # Mostrar estadísticas
            print("\n")
            historial.mostrar_estadisticas_historico()
            
        elif comando == "--help":
            print("""
📊 SISTEMA DE REPORTES HISTÓRICOS

Uso: python sistema_reportes_historicos.py [comando]

Comandos:
  --archivar          Archivar reportes del día actual
  --resumen-semanal   Generar resumen de la semana pasada
  --limpiar [días]    Limpiar archivos anteriores a X días (defecto: 30)
  --estadisticas      Mostrar estadísticas del histórico
  --completo          Ejecutar todo (archivar + resumen + limpiar + stats)
  --help              Mostrar esta ayuda

Ejemplos:
  python sistema_reportes_historicos.py --archivar
  python sistema_reportes_historicos.py --limpiar 60
  python sistema_reportes_historicos.py --completo
            """)
        else:
            print(f"❌ Comando no reconocido: {comando}")
            print("   Usa --help para ver comandos disponibles")
    else:
        # Por defecto: archivar día actual
        historial.archivar_reporte_diario()

if __name__ == "__main__":
    main()