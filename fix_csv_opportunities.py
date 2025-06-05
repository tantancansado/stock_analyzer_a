#!/usr/bin/env python3
"""
Fix específico para el problema del CSV de oportunidades
Depura paso a paso para ver dónde falla exactamente
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

def debug_csv_insiders():
    """
    Depura el CSV de insiders paso a paso
    """
    print("🔍 DEPURANDO CSV DE INSIDERS")
    print("=" * 35)
    
    csv_path = "reports/insiders_daily.csv"
    
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} no existe")
        return None
    
    try:
        # Leer CSV
        df = pd.read_csv(csv_path)
        print(f"✅ CSV leído: {len(df)} filas")
        
        # Mostrar estructura completa
        print(f"\n📋 ESTRUCTURA DEL CSV:")
        print(f"Columnas: {list(df.columns)}")
        print(f"Shape: {df.shape}")
        print(f"Tipos de datos:")
        for col in df.columns:
            print(f"  {col}: {df[col].dtype}")
        
        # Mostrar primeras filas completas
        print(f"\n📊 PRIMERAS 3 FILAS COMPLETAS:")
        for i in range(min(3, len(df))):
            print(f"\nFila {i}:")
            for col in df.columns:
                print(f"  {col}: '{df.iloc[i][col]}'")
        
        # Verificar datos críticos
        print(f"\n🔍 VERIFICACIONES:")
        
        # 1. Verificar columna Insider (ticker)
        if 'Insider' in df.columns:
            tickers_unicos = df['Insider'].dropna().unique()
            print(f"✅ Tickers únicos: {len(tickers_unicos)}")
            print(f"   Muestra: {list(tickers_unicos[:5])}")
        else:
            print(f"❌ Columna 'Insider' no encontrada")
        
        # 2. Verificar precios
        if 'Price' in df.columns:
            precios_validos = pd.to_numeric(df['Price'], errors='coerce').dropna()
            print(f"✅ Precios válidos: {len(precios_validos)} de {len(df)}")
            if len(precios_validos) > 0:
                print(f"   Rango: ${precios_validos.min():.2f} - ${precios_validos.max():.2f}")
        else:
            print(f"❌ Columna 'Price' no encontrada")
        
        # 3. Verificar cantidades
        if 'Qty' in df.columns:
            cantidades_validas = pd.to_numeric(df['Qty'], errors='coerce').dropna()
            print(f"✅ Cantidades válidas: {len(cantidades_validas)} de {len(df)}")
            if len(cantidades_validas) > 0:
                print(f"   Rango: {int(cantidades_validas.min())} - {int(cantidades_validas.max())}")
        else:
            print(f"❌ Columna 'Qty' no encontrada")
        
        # 4. Verificar tipos de transacción
        if 'Type' in df.columns:
            tipos = df['Type'].value_counts()
            print(f"✅ Tipos de transacción:")
            for tipo, count in tipos.items():
                print(f"   {tipo}: {count}")
        else:
            print(f"❌ Columna 'Type' no encontrada")
        
        return df
        
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_preparacion_datos(df):
    """
    Depura la preparación de datos paso a paso
    """
    print(f"\n🔧 DEPURANDO PREPARACIÓN DE DATOS")
    print("=" * 40)
    
    if df is None:
        print("❌ No hay datos para procesar")
        return None
    
    try:
        print(f"📊 Datos originales: {len(df)} filas")
        
        # Paso 1: Mapeo de columnas
        print(f"\n📋 PASO 1: Mapeo de columnas")
        df_clean = df.copy()
        
        # Mapeo según la estructura real
        mapeo = {
            'Ticker': 'TransactionTimestamp',
            'Insider': 'Ticker',  # Este es el ticker real
            'Title': 'CompanyName',
            'Date': 'InsiderTitle',
            'Type': 'TransactionType',
            'Price': 'Price',
            'Qty': 'Quantity',
            'Owned': 'SharesOwned',
            'Value': 'OwnershipPct',
            'ScrapedAt': 'ScrapedAt'
        }
        
        print(f"Aplicando mapeo:")
        for old, new in mapeo.items():
            if old in df_clean.columns:
                print(f"  {old} → {new}")
            else:
                print(f"  ❌ {old} no encontrada")
        
        df_clean = df_clean.rename(columns=mapeo)
        print(f"✅ Mapeo completado")
        
        # Paso 2: Conversión de tipos
        print(f"\n📋 PASO 2: Conversión de tipos")
        
        # Ticker
        if 'Ticker' in df_clean.columns:
            df_clean["Ticker"] = df_clean["Ticker"].astype(str).str.upper().str.strip()
            tickers_validos = df_clean[df_clean["Ticker"] != "NAN"]["Ticker"].dropna()
            print(f"✅ Tickers válidos: {len(tickers_validos)} de {len(df_clean)}")
        
        # Precio
        if 'Price' in df_clean.columns:
            precios_originales = len(df_clean)
            df_clean["Price"] = pd.to_numeric(df_clean["Price"], errors='coerce')
            precios_validos = df_clean["Price"].dropna()
            print(f"✅ Precios: {len(precios_validos)} de {precios_originales} válidos")
        
        # Cantidad
        if 'Quantity' in df_clean.columns:
            cantidades_originales = len(df_clean)
            df_clean["Quantity"] = pd.to_numeric(df_clean["Quantity"], errors='coerce')
            cantidades_validas = df_clean["Quantity"].dropna()
            print(f"✅ Cantidades: {len(cantidades_validas)} de {cantidades_originales} válidas")
        
        # Paso 3: Filtrar solo compras
        print(f"\n📋 PASO 3: Filtrar solo compras")
        if 'TransactionType' in df_clean.columns:
            antes_filtro = len(df_clean)
            compras = df_clean[df_clean["TransactionType"].str.contains("P - Purchase", na=False)]
            print(f"✅ Compras: {len(compras)} de {antes_filtro} transacciones")
            df_clean = compras
        else:
            print(f"⚠️ No se puede filtrar por tipo de transacción")
        
        # Paso 4: Filtros de validez
        print(f"\n📋 PASO 4: Filtros de validez")
        antes = len(df_clean)
        
        # Filtrar datos inválidos
        df_clean = df_clean.dropna(subset=["Ticker", "Price", "Quantity"])
        despues_na = len(df_clean)
        print(f"Después de eliminar NA: {despues_na} de {antes}")
        
        df_clean = df_clean[df_clean["Ticker"] != "NAN"]
        despues_nan = len(df_clean)
        print(f"Después de eliminar NAN: {despues_nan} de {despues_na}")
        
        df_clean = df_clean[df_clean["Price"] > 0]
        despues_precio = len(df_clean)
        print(f"Después de precio > 0: {despues_precio} de {despues_nan}")
        
        df_clean = df_clean[df_clean["Quantity"] > 0]
        final = len(df_clean)
        print(f"Después de cantidad > 0: {final} de {despues_precio}")
        
        print(f"\n🎯 RESULTADO FINAL: {final} transacciones válidas de {antes} originales")
        
        if final > 0:
            print(f"\n📊 MUESTRA DE DATOS LIMPIOS:")
            for i in range(min(3, final)):
                row = df_clean.iloc[i]
                ticker = row.get('Ticker', 'N/A')
                price = row.get('Price', 0)
                qty = row.get('Quantity', 0)
                print(f"  {i+1}. {ticker}: ${price:.2f} x {qty} = ${price*qty:,.0f}")
        
        return df_clean
        
    except Exception as e:
        print(f"❌ Error en preparación: {e}")
        import traceback
        traceback.print_exc()
        return None

def debug_analisis_actividad(df_clean):
    """
    Depura el análisis de actividad de insiders
    """
    print(f"\n🎯 DEPURANDO ANÁLISIS DE ACTIVIDAD")
    print("=" * 40)
    
    if df_clean is None or len(df_clean) == 0:
        print("❌ No hay datos limpios para analizar")
        return None
    
    try:
        # Preparar fechas
        print(f"📅 Procesando fechas...")
        
        # Usar TransactionTimestamp como fecha
        if 'TransactionTimestamp' in df_clean.columns:
            df_clean["FilingDate"] = pd.to_datetime(df_clean["TransactionTimestamp"], errors="coerce")
            fechas_validas = df_clean["FilingDate"].dropna()
            print(f"✅ Fechas válidas: {len(fechas_validas)} de {len(df_clean)}")
            
            if len(fechas_validas) > 0:
                fecha_min = fechas_validas.min()
                fecha_max = fechas_validas.max()
                print(f"   Rango: {fecha_min.strftime('%Y-%m-%d')} a {fecha_max.strftime('%Y-%m-%d')}")
        
        # Calcular valor de transacción
        df_clean["TransactionValue"] = df_clean["Price"] * df_clean["Quantity"]
        valores_validos = df_clean["TransactionValue"].dropna()
        print(f"✅ Valores calculados: {len(valores_validos)}")
        
        if len(valores_validos) > 0:
            valor_total = valores_validos.sum()
            valor_promedio = valores_validos.mean()
            print(f"   Total: ${valor_total:,.0f}")
            print(f"   Promedio: ${valor_promedio:,.0f}")
        
        # Filtrar transacciones recientes
        print(f"\n📅 Filtrando transacciones recientes...")
        fecha_limite = datetime.now() - timedelta(days=90)  # Más amplio para testing
        recent = df_clean[df_clean["FilingDate"] >= fecha_limite]
        print(f"✅ Transacciones últimos 90 días: {len(recent)} de {len(df_clean)}")
        
        if len(recent) == 0:
            print("⚠️ Usando todos los datos disponibles...")
            recent = df_clean.copy()
        
        # Agrupar por ticker
        print(f"\n📊 Agrupando por ticker...")
        
        if len(recent) > 0:
            signals = recent.groupby("Ticker").agg({
                "TransactionType": "count",
                "TransactionValue": ["sum", "mean"],
                "Quantity": "sum",
                "InsiderTitle": lambda x: len(x.unique()) if 'InsiderTitle' in recent.columns else 1,
                "FilingDate": ["min", "max"],
                "CompanyName": "first",
                "Price": "mean"
            }).round(2)
            
            # Aplanar columnas
            signals.columns = [
                "NumTransactions", "TotalValue", "AvgValue", 
                "TotalShares", "UniqueInsiders", "FirstFilingDate", "LastFilingDate",
                "CompanyName", "AvgPrice"
            ]
            
            signals = signals.reset_index()
            print(f"✅ Señales generadas para {len(signals)} tickers")
            
            # Mostrar muestra
            print(f"\n📋 TOP 5 SEÑALES:")
            top_signals = signals.sort_values('TotalValue', ascending=False).head()
            for i, row in top_signals.iterrows():
                ticker = row['Ticker']
                total_value = row['TotalValue']
                transactions = row['NumTransactions']
                print(f"  {ticker}: ${total_value:,.0f} ({transactions} trans)")
            
            return signals
        else:
            print("❌ No hay datos para agrupar")
            return None
            
    except Exception as e:
        print(f"❌ Error en análisis de actividad: {e}")
        import traceback
        traceback.print_exc()
        return None

def generar_csv_oportunidades_debug(signals):
    """
    Genera el CSV de oportunidades con debug
    """
    print(f"\n📄 GENERANDO CSV DE OPORTUNIDADES")
    print("=" * 40)
    
    if signals is None or len(signals) == 0:
        print("❌ No hay señales para generar CSV")
        
        # Crear CSV vacío como fallback
        reporte_vacio = pd.DataFrame({
            "Mensaje": ["No se encontraron transacciones válidas después de limpieza"],
            "Fecha_Analisis": [datetime.now().strftime('%Y-%m-%d %H:%M')],
            "Debug": ["Verificar estructura del CSV de insiders"]
        })
        
        output_path = "reports/insiders_opportunities.csv"
        os.makedirs("reports", exist_ok=True)
        reporte_vacio.to_csv(output_path, index=False)
        print(f"📄 CSV vacío generado: {output_path}")
        return output_path
    
    try:
        # Agregar ranking simple
        signals_ranked = signals.copy()
        signals_ranked['Rank'] = signals_ranked['TotalValue'].rank(method='dense', ascending=False).astype(int)
        signals_ranked = signals_ranked.sort_values('TotalValue', ascending=False)
        
        # Agregar puntuación básica
        max_value = signals_ranked['TotalValue'].max()
        signals_ranked['Score'] = (signals_ranked['TotalValue'] / max_value * 100).round(1)
        signals_ranked['ConfidenceLevel'] = signals_ranked['Score'].apply(
            lambda x: 'Alta' if x > 60 else 'Media' if x > 30 else 'Baja'
        )
        
        # Formatear fechas
        date_columns = ['FirstFilingDate', 'LastFilingDate']
        for col in date_columns:
            if col in signals_ranked.columns:
                signals_ranked[col] = pd.to_datetime(signals_ranked[col], errors='coerce').dt.strftime('%Y-%m-%d')
        
        # Formatear valores monetarios
        if 'TotalValue' in signals_ranked.columns:
            signals_ranked['TotalValueFormatted'] = signals_ranked['TotalValue'].apply(lambda x: f"${x:,.0f}")
        
        output_path = "reports/insiders_opportunities.csv"
        os.makedirs("reports", exist_ok=True)
        signals_ranked.to_csv(output_path, index=False)
        
        print(f"✅ CSV generado exitosamente: {output_path}")
        print(f"📊 Oportunidades: {len(signals_ranked)}")
        print(f"🎯 Rango de scores: {signals_ranked['Score'].min():.1f} - {signals_ranked['Score'].max():.1f}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error generando CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """
    Ejecuta debug completo del proceso de oportunidades
    """
    print("🔍 DEBUG COMPLETO - CSV DE OPORTUNIDADES")
    print("=" * 50)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Paso 1: Debug CSV insiders
    df = debug_csv_insiders()
    
    if df is None:
        print("\n❌ FALLO EN PASO 1: No se pudo leer CSV de insiders")
        return False
    
    # Paso 2: Debug preparación
    df_clean = debug_preparacion_datos(df)
    
    if df_clean is None or len(df_clean) == 0:
        print("\n❌ FALLO EN PASO 2: No se pudieron preparar los datos")
        return False
    
    # Paso 3: Debug análisis
    signals = debug_analisis_actividad(df_clean)
    
    if signals is None:
        print("\n❌ FALLO EN PASO 3: No se pudo analizar actividad")
        return False
    
    # Paso 4: Generar CSV
    csv_path = generar_csv_oportunidades_debug(signals)
    
    if csv_path:
        print(f"\n🎉 ¡DEBUG COMPLETADO EXITOSAMENTE!")
        print(f"✅ CSV de oportunidades generado: {csv_path}")
        return True
    else:
        print(f"\n❌ FALLO EN PASO 4: No se pudo generar CSV")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n💡 SIGUIENTE PASO:")
        print(f"   Ejecuta el análisis completo nuevamente")
        print(f"   python main.py → opción 1")
    else:
        print(f"\n🔧 RECOMENDACIONES:")
        print(f"   1. Verificar que openinsider_scraper.py genera datos válidos")
        print(f"   2. Revisar la estructura del CSV generado")
        print(f"   3. Ejecutar scraper manualmente: python openinsider_scraper.py")