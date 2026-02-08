#!/usr/bin/env python3
"""
Script para generar reportes VCP desde CSVs históricos
"""
import pandas as pd
import json
import shutil
from pathlib import Path
from datetime import datetime
from vcp_scanner_usa import VCPScannerEnhanced, VCPResult

def csv_to_vcp_results(csv_path):
    """Convierte un CSV de VCP a lista de VCPResult objects"""
    df = pd.read_csv(csv_path)
    results = []

    for _, row in df.iterrows():
        # Parsear contracciones
        contractions_str = str(row['contracciones'])
        contractions = []
        for part in contractions_str.split('→'):
            try:
                value = float(part.strip().replace('%', ''))
                contractions.append(value)
            except:
                pass

        # Crear VCPResult
        result = VCPResult(
            ticker=row['ticker'],
            current_price=float(row['precio']),
            vcp_score=float(row['vcp_score']),
            pattern_quality=row['calidad_patron'],
            contractions=contractions,
            base_depth=float(row['profundidad_base']),
            stage_analysis=row['etapa_analisis'],
            trend_score=float(row['trend_score']),
            volume_score=float(row['volumen_score']),
            breakout_potential=float(row['breakout_potential']),
            ready_to_buy=row['listo_comprar'] in [True, 'True', 'true', 1],
            sector=row.get('sector', 'Unknown'),
            market_cap=float(row.get('market_cap', 0)),
            reason=row['razon']
        )
        results.append(result)

    return results

def generate_vcp_report(csv_path, output_dir):
    """Genera un reporte VCP completo desde un CSV"""
    print(f"📊 Generando reporte VCP desde {csv_path}")

    # Leer CSV y convertir a VCPResult objects
    results = csv_to_vcp_results(csv_path)
    print(f"✅ Cargados {len(results)} patrones VCP")

    # Crear directorio de salida
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generar HTML usando VCPScannerEnhanced
    scanner = VCPScannerEnhanced()
    scanner.last_results = results
    scanner.scanner.processed_count = len(results) * 20  # Estimar total escaneado

    html_path = output_dir / "index.html"
    csv_output_path = output_dir / "data.csv"

    # Copiar CSV
    shutil.copy2(csv_path, csv_output_path)

    # Generar HTML
    scanner.generate_html(results, html_path)

    print(f"✅ Reporte generado en {output_dir}")

    return {
        'html_path': str(html_path),
        'csv_path': str(csv_output_path),
        'num_patterns': len(results),
        'buy_candidates': len([r for r in results if r.ready_to_buy]),
        'excellent': len([r for r in results if r.pattern_quality == "Excellent"]),
        'good': len([r for r in results if r.pattern_quality == "Good"])
    }

def update_manifest_with_vcp(manifest_path, vcp_report_info, report_id, report_date):
    """Actualiza manifest.json con el nuevo reporte VCP"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    # Crear sección vcp_reports si no existe
    if 'vcp_reports' not in manifest:
        manifest['vcp_reports'] = []
        manifest['total_vcp_reports'] = 0

    # Crear entrada de reporte VCP
    base_path = f"reports/vcp/{report_id}"
    vcp_report = {
        "id": report_id,
        "title": f"🚀 VCP Scanner - {vcp_report_info['num_patterns']} patrones detectados",
        "description": f"{vcp_report_info['buy_candidates']} listos para comprar • {vcp_report_info['excellent']} Excellent • {vcp_report_info['good']} Good",
        "timestamp": datetime.now().isoformat(),
        "date": report_date,
        "time": datetime.now().strftime('%H:%M:%S'),
        "html_url": f"{base_path}/index.html",
        "csv_url": f"{base_path}/data.csv",
        "full_url": f"https://tantancansado.github.io/stock_analyzer_a/{base_path}/index.html",
        "type": "vcp",
        "stats": {
            "total_patterns": vcp_report_info['num_patterns'],
            "buy_candidates": vcp_report_info['buy_candidates'],
            "excellent": vcp_report_info['excellent'],
            "good": vcp_report_info['good']
        }
    }

    # Agregar al inicio de la lista (más reciente primero)
    manifest['vcp_reports'].insert(0, vcp_report)
    manifest['total_vcp_reports'] = len(manifest['vcp_reports'])

    # Guardar manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Manifest actualizado con reporte VCP {report_id}")
    return manifest

def regenerate_vcp_page(manifest, templates_file):
    """Regenera la página VCP Scanner usando los templates"""
    from templates.github_pages_templates import GitHubPagesTemplates

    templates = GitHubPagesTemplates()
    vcp_html = templates.generate_vcp_scanner_page(manifest)

    vcp_page_path = Path('docs/vcp_scanner.html')
    with open(vcp_page_path, 'w', encoding='utf-8') as f:
        f.write(vcp_html)

    print(f"✅ Página VCP Scanner regenerada: {vcp_page_path}")

if __name__ == "__main__":
    # CSV histórico de VCP
    csv_path = "vcp_calibrated_results_20250711_103128.csv"

    # Extraer fecha del nombre del archivo
    report_date = "2025-07-11"
    report_id = "vcp_scan_20250711_103128"

    # Generar reporte
    output_dir = f"docs/reports/vcp/{report_id}"
    report_info = generate_vcp_report(csv_path, output_dir)

    # Actualizar manifest
    manifest_path = "docs/manifest.json"
    manifest = update_manifest_with_vcp(manifest_path, report_info, report_id, report_date)

    # Regenerar página VCP
    regenerate_vcp_page(manifest, "templates/github_pages_templates.py")

    print("\n🎉 PROCESO COMPLETADO")
    print(f"   📊 Reporte VCP: {output_dir}/index.html")
    print(f"   📈 Patrones: {report_info['num_patterns']}")
    print(f"   🟢 Listos comprar: {report_info['buy_candidates']}")
    print(f"   ⭐ Excellent: {report_info['excellent']}")
