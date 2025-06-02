import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def scrape_openinsider():
    """
    Analiza oportunidades de inversión basadas en compras de insiders
    Versión mejorada con más criterios de filtrado
    """
    try:
        # Cargar compras recientes de insiders
        insiders_df = pd.read_csv("reports/insiders_daily.csv")
        print(f"📊 Datos de insiders cargados: {len(insiders_df)} transacciones")

        # Cargar dataset fundamental más reciente
        try:
            # Probar diferentes ubicaciones del archivo
            fundamentals_paths = [
                "reports/finviz_ml_dataset_with_fundamentals.csv",
                "finviz_ml_dataset_with_fundamentals.csv",
                "reports/finviz_ml_dataset.csv"
            ]
            
            fundamentals_df = None
            for path in fundamentals_paths:
                if os.path.exists(path):
                    fundamentals_df = pd.read_csv(path)
                    print(f"📈 Datos fundamentales cargados desde: {path} ({len(fundamentals_df)} empresas)")
                    break
            
            if fundamentals_df is None:
                raise FileNotFoundError("No se encontró archivo de fundamentales")
                
        except FileNotFoundError:
            print("⚠️ Archivo de datos fundamentales no encontrado")
            print("   Rutas buscadas:", fundamentals_paths)
            fundamentals_df = pd.DataFrame()

        # Limpiar y preparar datos de insiders
        insiders_df = preparar_datos_insiders(insiders_df)
        
        # Análisis de actividad de insiders
        insider_signals = analizar_actividad_insiders(insiders_df)
        
        # Si hay datos fundamentales, hacer análisis completo
        if not fundamentals_df.empty:
            fundamentals_df = preparar_datos_fundamentales(fundamentals_df)
            oportunidades = analizar_oportunidades_completas(insider_signals, fundamentals_df)
        else:
            oportunidades = insider_signals
        
        # Generar reporte final
        output_path = generar_reporte_oportunidades(oportunidades)
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error en análisis de oportunidades: {e}")
        import traceback
        traceback.print_exc()
        return None

def preparar_datos_insiders(df):
    """
    Limpia y prepara los datos de insiders - CORREGIDO para estructura real de OpenInsider
    """
    print("🔧 Preparando datos de insiders...")
    
    # Mostrar estructura original para debugging
    print(f"Columnas originales: {list(df.columns)}")
    print(f"Primeras filas:")
    for i in range(min(3, len(df))):
        print(f"  Fila {i}: {dict(df.iloc[i])}")
    
    # Limpiar datos - La estructura real es diferente a la asumida
    df_clean = df.copy()
    
    # MAPEO CORRECTO según la estructura real del CSV:
    # Ticker,Insider,Title,Date,Type,Price,Qty,Owned,Value,Source,ScrapedAt,Chart_Daily,Chart_Weekly
    # donde:
    # - Ticker = Timestamp de transacción  
    # - Insider = Ticker real de la empresa (LYFT, EMYB, etc.)
    # - Title = Nombre de la empresa
    # - Date = Título del insider (CEO, etc.)
    # - Type = Tipo de transacción
    
    df_clean = df_clean.rename(columns={
        'Ticker': 'TransactionTimestamp',    # Timestamp original
        'Insider': 'Ticker',                 # Este es el ticker real
        'Title': 'CompanyName',              # Nombre de empresa
        'Date': 'InsiderTitle',              # Título del insider
        'Type': 'TransactionType',           # Tipo de transacción
        'Price': 'Price',                    # Precio (ya correcto)
        'Qty': 'Quantity',                   # Cantidad
        'Owned': 'SharesOwned',              # Acciones en propiedad
        'Value': 'OwnershipPct',             # Porcentaje de propiedad
        'ScrapedAt': 'ScrapedAt'             # Fecha de scraping
    })
    
    print(f"Columnas después del mapeo: {list(df_clean.columns)}")
    
    # Convertir tipos de datos
    df_clean["Ticker"] = df_clean["Ticker"].astype(str).str.upper().str.strip()
    df_clean["Price"] = pd.to_numeric(df_clean["Price"], errors='coerce')
    df_clean["Quantity"] = pd.to_numeric(df_clean["Quantity"], errors='coerce')
    df_clean["SharesOwned"] = pd.to_numeric(df_clean["SharesOwned"], errors='coerce')
    
    # Procesar fechas - usar el timestamp de transacción como fecha de filing
    df_clean["FilingDate"] = pd.to_datetime(df_clean["TransactionTimestamp"], errors="coerce")
    df_clean["ScrapedAt"] = pd.to_datetime(df_clean["ScrapedAt"], errors="coerce")
    
    # Para la fecha de compra, usar filing date como proxy
    df_clean["PurchaseDate"] = df_clean["FilingDate"]
    
    # Calcular valor de transacción
    df_clean["TransactionValue"] = df_clean["Price"] * df_clean["Quantity"]
    
    # Limpiar CompanyName si está disponible
    if "CompanyName" not in df_clean.columns:
        df_clean["CompanyName"] = df_clean["Ticker"] + " Corp"
    
    # Filtrar solo compras (P - Purchase)
    if "TransactionType" in df_clean.columns:
        purchases_only = df_clean[df_clean["TransactionType"].str.contains("P - Purchase", na=False)]
        print(f"Filtrando solo compras: {len(df_clean)} → {len(purchases_only)} transacciones")
        df_clean = purchases_only
    
    # Filtrar datos válidos
    df_clean = df_clean.dropna(subset=["Ticker", "Price", "Quantity"])
    df_clean = df_clean[df_clean["Ticker"] != "NAN"]
    df_clean = df_clean[df_clean["Price"] > 0]
    df_clean = df_clean[df_clean["Quantity"] > 0]
    
    # Mostrar muestra de datos limpios
    print(f"\n✅ Datos limpios: {len(df_clean)} transacciones válidas")
    if len(df_clean) > 0:
        print("Muestra de datos procesados:")
        sample = df_clean[['Ticker', 'CompanyName', 'InsiderTitle', 'Price', 'Quantity', 'TransactionValue', 'FilingDate']].head(3)
        for i, row in sample.iterrows():
            print(f"  {row['Ticker']}: ${row['Price']:.2f} x {row['Quantity']} = ${row['TransactionValue']:,.0f} ({row['InsiderTitle']})")
    
    return df_clean

def preparar_datos_fundamentales(df):
    """
    Limpia y prepara los datos fundamentales
    """
    print("🔧 Preparando datos fundamentales...")
    
    df_clean = df.copy()
    df_clean["Ticker"] = df_clean["Ticker"].astype(str).str.upper().str.strip()
    
    # Convertir métricas numéricas de forma más robusta
    numeric_columns = ["Debt/Eq", "P/E", "ROE", "Gross Margin", "P/B", "P/S", "Market Cap"]
    
    for col in numeric_columns:
        if col in df_clean.columns:
            # Limpiar valores de string que pueden tener %, -, etc.
            df_clean[col] = df_clean[col].astype(str).str.replace('%', '').str.replace('-', '').str.replace('', '0')
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    # Crear alias para consistencia
    if "Debt/Eq" in df_clean.columns:
        df_clean["Debt/Equity"] = df_clean["Debt/Eq"]
    
    # Mostrar información de lo que encontramos
    print(f"✅ Datos fundamentales preparados: {len(df_clean)} empresas")
    print(f"🔍 Columnas numéricas disponibles:")
    for col in numeric_columns:
        if col in df_clean.columns:
            non_null = df_clean[col].notna().sum()
            print(f"   {col}: {non_null}/{len(df_clean)} valores válidos")
    
    return df_clean

def analizar_actividad_insiders(df):
    """
    Analiza la actividad de insiders con criterios estrictos
    """
    print("🔍 Analizando actividad de insiders (modo estricto)...")
    
    # Filtrar compras recientes (últimos 30 días para mayor relevancia)
    fecha_limite = datetime.now() - timedelta(days=30)
    recent = df[df["FilingDate"] >= fecha_limite]
    
    print(f"📅 Transacciones últimos 30 días: {len(recent)}")
    
    # Si no hay datos recientes suficientes, ampliar a 60 días
    if len(recent) < 5:
        print("⚠️ Ampliando búsqueda a 60 días...")
        fecha_limite = datetime.now() - timedelta(days=60)
        recent = df[df["FilingDate"] >= fecha_limite]
        print(f"📅 Transacciones últimos 60 días: {len(recent)}")
    
    # Si aún no hay datos, usar todos los datos disponibles
    if len(recent) == 0:
        print("⚠️ No hay transacciones recientes, usando todos los datos disponibles...")
        recent = df.copy()
        print(f"📅 Total transacciones disponibles: {len(recent)}")
    
    if len(recent) == 0:
        print("❌ No hay datos de transacciones disponibles")
        return pd.DataFrame(columns=[
            'Ticker', 'CompanyName', 'NumTransactions', 'TotalValue', 'AvgValue',
            'UniqueInsiders', 'FirstFilingDate', 'LastFilingDate', 'FirstPurchaseDate',
            'LastPurchaseDate', 'AvgPrice', 'DaysSinceLastActivity', 'InsiderConfidence',
            'ConfidenceLevel'
        ])
    
    # Agrupar por ticker y calcular métricas
    signals = recent.groupby("Ticker").agg({
        "TransactionType": "count",  # Número de transacciones
        "TransactionValue": ["sum", "mean", "count"],  # Valor total, promedio, número
        "Quantity": "sum",  # Total de acciones compradas
        "InsiderTitle": lambda x: len(x.unique()),  # Número de insiders únicos
        "FilingDate": ["min", "max"],  # Rango de fechas de filing
        "PurchaseDate": ["min", "max"],  # Rango de fechas de compra
        "CompanyName": "first",  # Nombre de la empresa
        "Price": "mean"  # Precio promedio
    }).round(2)
    
    # Aplanar columnas
    signals.columns = [
        "NumTransactions", "TotalValue", "AvgValue", "ValueCount", 
        "TotalShares", "UniqueInsiders", "FirstFilingDate", "LastFilingDate",
        "FirstPurchaseDate", "LastPurchaseDate", "CompanyName", "AvgPrice"
    ]
    
    signals = signals.reset_index()
    
    # Calcular días desde última actividad
    signals["DaysSinceLastActivity"] = (datetime.now() - pd.to_datetime(signals["LastFilingDate"])).dt.days
    
    # Aplicar filtros de calidad ANTES de calcular puntuaciones
    signals_filtered = aplicar_filtros_calidad_insider(signals)
    
    # Calcular puntuaciones solo para oportunidades de calidad
    if len(signals_filtered) > 0:
        signals_filtered = calcular_puntuaciones_insider_flexible(signals_filtered)
    else:
        print("⚠️ No hay señales que pasen los filtros de calidad")
        # Crear DataFrame vacío con las columnas necesarias
        signals_filtered = pd.DataFrame(columns=[
            'Ticker', 'CompanyName', 'NumTransactions', 'TotalValue', 'AvgValue',
            'UniqueInsiders', 'FirstFilingDate', 'LastFilingDate', 'FirstPurchaseDate',
            'LastPurchaseDate', 'AvgPrice', 'DaysSinceLastActivity', 'InsiderConfidence',
            'ConfidenceLevel'
        ])
    
    print(f"✅ Señales de calidad generadas para {len(signals_filtered)} tickers")
    return signals_filtered

def aplicar_filtros_calidad_insider(df):
    """
    Aplica filtros de calidad a la actividad de insiders - VERSION RELAJADA
    """
    print("🔍 Aplicando filtros de calidad a actividad de insiders...")
    
    antes = len(df)
    
    # Filtros de calidad MÁS RELAJADOS para permitir más oportunidades
    filtros_calidad = (
        # Mínimo 1 transacción (reducido de 2)
        (df["NumTransactions"] >= 1) &
        # Valor mínimo más bajo ($10k total en lugar de $50k)
        (df["TotalValue"] >= 10000) &
        # Actividad menos reciente (máximo 90 días en lugar de 45)
        (df["DaysSinceLastActivity"] <= 90) &
        # Valor promedio más bajo (mínimo $5k por transacción)
        (df["AvgValue"] >= 5000)
    )
    
    df_filtered = df[filtros_calidad].copy()
    despues = len(df_filtered)
    
    print(f"✅ Filtros de calidad insider: {antes} → {despues} empresas ({despues/antes*100:.1f}%)")
    
    return df_filtered

def calcular_puntuaciones_insider_flexible(df):
    """
    Calcula puntuaciones de confianza más estrictas para oportunidades reales
    """
    print("📊 Calculando puntuaciones de confianza (modo estricto)...")
    
    # Normalizar métricas de forma más exigente
    df["TransactionScore"] = np.clip((df["NumTransactions"] - 0.5) * 40, 0, 100)  # Ajustado
    df["ValueScore"] = np.clip(np.log10(df["TotalValue"].fillna(1) + 1) * 20, 0, 100)  # Ajustado
    df["DiversityScore"] = np.clip((df["UniqueInsiders"] - 0.5) * 50, 0, 100)  # Ajustado
    
    # Bonus por alta inversión individual (insider pone mucho dinero)
    df["HighValueBonus"] = np.clip((df["AvgValue"] / 25000) * 15, 0, 25)  # Ajustado
    
    # Penalty por actividad muy antigua
    df["RecencyPenalty"] = np.clip(df["DaysSinceLastActivity"] / 45 * 20, 0, 30)  # Ajustado
    
    # Puntuación compuesta más exigente
    df["InsiderConfidence"] = np.maximum(0, (
        df["TransactionScore"] * 0.30 +
        df["ValueScore"] * 0.25 + 
        df["DiversityScore"] * 0.25 +
        df["HighValueBonus"] * 0.20 -
        df["RecencyPenalty"]  # Resta puntos por ser antigua
    )).round(1)
    
    # Categorías de confianza más estrictas
    def asignar_nivel_confianza(score):
        if score >= 80:
            return "Muy Alta"
        elif score >= 60:
            return "Alta"
        elif score >= 40:
            return "Media"
        else:
            return "Baja"
    
    df["ConfidenceLevel"] = df["InsiderConfidence"].apply(asignar_nivel_confianza)
    
    return df

def analizar_oportunidades_completas(insider_signals, fundamentals_df):
    """
    Combina señales de insiders con análisis fundamental
    """
    print("🎯 Combinando análisis de insiders con fundamentales...")
    
    # Verificar que insider_signals tiene las columnas necesarias
    if 'InsiderConfidence' not in insider_signals.columns:
        print("⚠️ Recalculando puntuaciones de insider...")
        insider_signals = calcular_puntuaciones_insider_flexible(insider_signals)
    
    # Unir datasets
    merged = insider_signals.merge(fundamentals_df, on="Ticker", how="left")
    
    # Aplicar filtros de calidad fundamental
    filtered = aplicar_filtros_fundamentales(merged)
    
    # Si no pasan filtros fundamentales, usar solo insiders
    if len(filtered) == 0:
        print("⚠️ Ninguna empresa pasó filtros fundamentales, usando solo análisis de insiders")
        return calcular_puntuacion_solo_insiders(insider_signals)
    
    # Calcular puntuación final
    filtered = calcular_puntuacion_final(filtered)
    
    return filtered

def calcular_puntuacion_solo_insiders(df):
    """
    Calcula puntuación final usando solo datos de insiders
    """
    print("🎯 Calculando puntuación final solo con insiders...")
    
    df = df.copy()
    
    # Asegurar que tenemos InsiderConfidence
    if 'InsiderConfidence' not in df.columns:
        print("⚠️ Calculando InsiderConfidence faltante...")
        df = calcular_puntuaciones_insider_flexible(df)
    
    df["FinalScore"] = df["InsiderConfidence"]
    df["FundamentalScore"] = 0
    
    # Ranking
    df["Rank"] = df["FinalScore"].rank(method="dense", ascending=False).astype(int)
    
    return df

def aplicar_filtros_fundamentales(df):
    """
    Aplica filtros de calidad fundamental MÁS RELAJADOS
    """
    print("🔍 Aplicando filtros fundamentales relajados...")
    
    # Verificar que tenemos InsiderConfidence
    if 'InsiderConfidence' not in df.columns:
        print("⚠️ Recalculando InsiderConfidence en filtros fundamentales...")
        df = calcular_puntuaciones_insider_flexible(df)
    
    # Verificar que existen datos fundamentales
    fundamental_columns = ["Debt/Equity", "Debt/Eq", "ROE", "Gross Margin", "P/E"]
    available_columns = []
    
    for col in fundamental_columns:
        if col in df.columns and not df[col].isna().all():
            available_columns.append(col)
    
    if not available_columns:
        print("❌ No hay datos fundamentales suficientes")
        return pd.DataFrame()
    
    print(f"✅ Columnas fundamentales disponibles: {available_columns}")
    
    antes = len(df)
    
    # Usar Debt/Eq si Debt/Equity no está disponible
    debt_column = "Debt/Equity" if "Debt/Equity" in df.columns else "Debt/Eq"
    
    # Filtros MÁS RELAJADOS
    conditions = []
    
    if debt_column in df.columns:
        conditions.append(df[debt_column].fillna(999) < 3.0)  # Más relajado: <3.0
        print(f"   Filtro deuda ({debt_column}): <3.0")
    
    if "ROE" in df.columns:
        conditions.append(df["ROE"].fillna(-999) > 0)  # Más relajado: >0%
        print(f"   Filtro ROE: >0%")
    
    if "Gross Margin" in df.columns:
        conditions.append(df["Gross Margin"].fillna(-999) > 5)  # Más relajado: >5%
        print(f"   Filtro Gross Margin: >5%")
    
    if "P/E" in df.columns:
        conditions.append((df["P/E"].fillna(999) > 0) & (df["P/E"].fillna(999) < 50))  # Más relajado: <50
        print(f"   Filtro P/E: 0-50")
    
    # Combinar todas las condiciones
    if conditions:
        combined_filter = conditions[0]
        for condition in conditions[1:]:
            combined_filter = combined_filter & condition
        
        df_filtered = df[combined_filter].copy()
    else:
        print("⚠️ No hay condiciones fundamentales, usando todos los datos")
        df_filtered = df.copy()
    
    despues = len(df_filtered)
    
    print(f"✅ Filtros relajados aplicados: {antes} → {despues} empresas ({despues/antes*100:.1f}%)")
    
    return df_filtered

def calcular_puntuacion_final(df):
    """
    Calcula puntuación final combinando insiders y fundamentales
    """
    print("🎯 Calculando puntuación final...")
    
    # Puntuaciones fundamentales (0-100) - más generosas
    if "Debt/Equity" in df.columns:
        df["DebtScore"] = np.clip(100 - df["Debt/Equity"].fillna(1) * 20, 0, 100)
    else:
        df["DebtScore"] = 50  # Puntuación neutral
    
    if "ROE" in df.columns:
        df["ROEScore"] = np.clip((df["ROE"].fillna(5) + 10) * 3, 0, 100)
    else:
        df["ROEScore"] = 50
    
    if "Gross Margin" in df.columns:
        df["MarginScore"] = np.clip((df["Gross Margin"].fillna(15) + 20) * 2, 0, 100)
    else:
        df["MarginScore"] = 50
    
    if "P/E" in df.columns:
        df["ValuationScore"] = np.clip(100 - df["P/E"].fillna(20) * 2, 0, 100)
    else:
        df["ValuationScore"] = 50
    
    # Puntuación fundamental compuesta
    df["FundamentalScore"] = (
        df["DebtScore"] * 0.25 +
        df["ROEScore"] * 0.3 +
        df["MarginScore"] * 0.25 +
        df["ValuationScore"] * 0.2
    ).round(1)
    
    # Puntuación final (priorizando insiders)
    df["FinalScore"] = (
        df["InsiderConfidence"] * 0.7 +
        df["FundamentalScore"] * 0.3
    ).round(1)
    
    # Ranking
    df["Rank"] = df["FinalScore"].rank(method="dense", ascending=False).astype(int)
    
    return df

def generar_reporte_oportunidades(df):
    """
    Genera reporte final de oportunidades
    """
    print("📄 Generando reporte de oportunidades...")
    
    if len(df) == 0:
        print("⚠️ No hay datos para generar reporte")
        # Crear reporte vacío
        reporte_vacio = pd.DataFrame({
            "Mensaje": ["No se encontraron transacciones válidas"],
            "Fecha_Analisis": [datetime.now().strftime('%Y-%m-%d %H:%M')]
        })
        
        output_path = "reports/insiders_opportunities.csv"
        os.makedirs("reports", exist_ok=True)
        reporte_vacio.to_csv(output_path, index=False)
        return output_path
    
    # Ordenar por puntuación final
    score_column = "FinalScore" if "FinalScore" in df.columns else "InsiderConfidence"
    df_sorted = df.sort_values(score_column, ascending=False)
    
    # Seleccionar top oportunidades (threshold más bajo)
    threshold = 30  # Más relajado
    top_opportunities = df_sorted[df_sorted[score_column] > threshold]
    
    print(f"🎯 Aplicando threshold: {threshold}")
    print(f"📊 Oportunidades que cumplen criterios: {len(top_opportunities)} de {len(df_sorted)}")
    
    # Si no hay oportunidades, tomar las mejores 10
    if len(top_opportunities) == 0:
        print("⚠️ Tomando las 10 mejores oportunidades disponibles")
        top_opportunities = df_sorted.head(10)
    
    # Preparar columnas para el reporte
    columnas_reporte = [
        "Ticker", "CompanyName", score_column, "ConfidenceLevel",
        "NumTransactions", "TotalValue", "UniqueInsiders", "AvgPrice",
        "FirstFilingDate", "LastFilingDate", "FirstPurchaseDate", "LastPurchaseDate",
        "DaysSinceLastActivity", "FundamentalScore", "ROE", "Debt/Equity", "Gross Margin", "P/E"
    ]
    
    # Filtrar columnas que existen
    columnas_existentes = [col for col in columnas_reporte if col in df_sorted.columns]
    reporte = top_opportunities[columnas_existentes].copy()
    
    # Añadir ranking
    reporte.insert(0, "Rank", range(1, len(reporte) + 1))
    
    # Formatear valores monetarios
    if "TotalValue" in reporte.columns:
        reporte["TotalValue"] = reporte["TotalValue"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "N/A")
    
    # Formatear fechas
    date_columns = ["FirstFilingDate", "LastFilingDate", "FirstPurchaseDate", "LastPurchaseDate"]
    for col in date_columns:
        if col in reporte.columns:
            reporte[col] = pd.to_datetime(reporte[col], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # Guardar reporte
    output_path = "reports/insiders_opportunities.csv"
    os.makedirs("reports", exist_ok=True)
    reporte.to_csv(output_path, index=False)
    
    # Mostrar resumen
    print(f"\n🎉 ANÁLISIS COMPLETADO")
    print(f"{'='*60}")
    print(f"📊 Total empresas analizadas: {len(df)}")
    print(f"🎯 Oportunidades encontradas: {len(top_opportunities)}")
    print(f"📄 Reporte guardado en: {output_path}")
    print(f"🎚️ Threshold aplicado: {threshold}")
    
    if len(top_opportunities) > 0:
        print(f"\n🏆 TOP OPORTUNIDADES:")
        print(f"{'='*60}")
        for i, row in reporte.head().iterrows():
            ticker = row.get("Ticker", "N/A")
            score = row.get(score_column, 0)
            confidence = row.get("ConfidenceLevel", "N/A")
            transactions = row.get("NumTransactions", 0)
            last_activity = row.get("DaysSinceLastActivity", "N/A")
            
            print(f"{row.get('Rank', 0):2d}. {ticker:6s} | Score: {score:5.1f} | {confidence:8s} | {transactions} trans | {last_activity} días")
    
    return output_path

def generar_reporte_html_oportunidades(csv_path):
    """
    Genera un reporte HTML de las oportunidades - CORREGIDO
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Verificar si el DataFrame está vacío o solo tiene mensaje de error
        if len(df) == 0 or 'Mensaje' in df.columns:
            # Generar HTML para caso sin oportunidades
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>🎯 Análisis de Oportunidades - Sin Resultados</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f7fa; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                    .no-results {{ background: #fff3cd; padding: 30px; border-radius: 10px; text-align: center; border: 2px solid #ffeaa7; }}
                    .info {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎯 Análisis de Oportunidades de Inversión</h1>
                    <div class="no-results">
                        <h2>📊 Análisis Completado</h2>
                        <p><strong>Resultado:</strong> No se encontraron transacciones válidas o datos suficientes</p>
                        <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                        <p><strong>Estado:</strong> ⚠️ Verificar archivos de datos</p>
                    </div>
                    <div class="info">
                        <h3>🔍 Posibles causas:</h3>
                        <ul>
                            <li>Archivo de datos de insiders vacío o mal formateado</li>
                            <li>No hay transacciones recientes (últimos 90 días)</li>
                            <li>Transacciones no cumplen criterios mínimos de valor</li>
                            <li>Problemas en el formato de fechas o datos numéricos</li>
                        </ul>
                        <p><strong>💡 Solución:</strong> Verificar que el archivo 'reports/insiders_daily.csv' existe y contiene datos válidos.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            # Verificar que existen las columnas necesarias
            score_column = "FinalScore" if "FinalScore" in df.columns else "InsiderConfidence"
            
            # CORREGIR EL CÁLCULO DEL PROMEDIO - ESTA ES LA LÍNEA PROBLEMÁTICA
            try:
                if score_column in df.columns:
                    # Convertir a numérico y filtrar valores válidos
                    score_values = pd.to_numeric(df[score_column], errors='coerce')
                    valid_scores = score_values.dropna()
                    
                    if len(valid_scores) > 0:
                        avg_score = valid_scores.mean()
                        avg_score_str = f"{avg_score:.1f}"
                    else:
                        avg_score_str = "N/A"
                else:
                    avg_score_str = "N/A"
            except Exception as e:
                print(f"⚠️ Error calculando promedio: {e}")
                avg_score_str = "N/A"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>🎯 Oportunidades de Inversión - Insider Trading</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; margin: 20px; background: #f5f7fa; }}
                    .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                    .summary {{ background: #ecf0f1; padding: 20px; border-radius: 10px; margin-bottom: 30px; display: flex; justify-content: space-around; flex-wrap: wrap; }}
                    .summary div {{ text-align: center; margin: 10px; }}
                    .summary strong {{ color: #2c3e50; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }}
                    th, td {{ padding: 8px; text-align: center; border: 1px solid #ddd; }}
                    th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; position: sticky; top: 0; }}
                    tr:nth-child(even) {{ background: #f8f9fa; }}
                    tr:hover {{ background: #e3f2fd; }}
                    .score-high {{ background: #c8e6c9 !important; font-weight: bold; }}
                    .score-medium {{ background: #fff3e0 !important; }}
                    .score-low {{ background: #ffebee !important; }}
                    .rank {{ font-weight: bold; color: #1976d2; }}
                    .ticker {{ font-weight: bold; color: #2e7d32; }}
                    .date {{ font-size: 0.8em; color: #666; }}
                    .days-ago {{ font-size: 0.8em; color: #ff5722; }}
                    .value {{ font-weight: bold; color: #1565c0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎯 Oportunidades de Inversión Basadas en Insider Trading</h1>
                    <div class="summary">
                        <div><strong>📊 Total de oportunidades:</strong><br>{len(df)}</div>
                        <div><strong>📅 Generado:</strong><br>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                        <div><strong>🎯 Tipo de análisis:</strong><br>Insiders + Fundamentales</div>
                        <div><strong>📈 Promedio Score:</strong><br>{avg_score_str}</div>
                    </div>
                    <table>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Empresa</th>
                            <th>Score</th>
                            <th>Nivel</th>
                            <th>Trans.</th>
                            <th>Valor Total</th>
                            <th>Insiders</th>
                            <th>Precio Prom.</th>
                            <th>Último Filing</th>
                            <th>Días Atrás</th>
                        </tr>
            """
            
            for _, row in df.iterrows():
                # CORREGIR TAMBIÉN EL PROCESAMIENTO DE CADA FILA
                try:
                    score = row.get(score_column, 0)
                    
                    # Convertir score de forma segura
                    try:
                        score_num = float(score) if pd.notna(score) else 0.0
                    except (ValueError, TypeError):
                        score_num = 0.0
                    
                    score_class = "score-high" if score_num > 60 else "score-medium" if score_num > 30 else "score-low"
                    
                    # Obtener datos de forma segura
                    ticker = row.get("Ticker", "N/A")
                    company = row.get("CompanyName", "N/A")
                    rank = row.get("Rank", "")
                    confidence = row.get("ConfidenceLevel", "N/A")
                    transactions = row.get("NumTransactions", 0)
                    total_value = row.get("TotalValue", "N/A")
                    insiders = row.get("UniqueInsiders", 0)
                    
                    # Convertir avg_price de forma segura
                    try:
                        avg_price = float(row.get("AvgPrice", 0)) if pd.notna(row.get("AvgPrice")) else 0.0
                    except (ValueError, TypeError):
                        avg_price = 0.0
                    
                    last_filing = row.get("LastFilingDate", "N/A")
                    days_ago = row.get("DaysSinceLastActivity", "N/A")
                    
                    html_content += f"""
                            <tr class="{score_class}">
                                <td class="rank">{rank}</td>
                                <td class="ticker">{ticker}</td>
                                <td style="text-align: left; max-width: 200px; font-size: 0.8em;">{company}</td>
                                <td><strong>{score_num:.1f}</strong></td>
                                <td style="font-size: 0.8em;">{confidence}</td>
                                <td>{transactions}</td>
                                <td class="value">{total_value}</td>
                                <td>{insiders}</td>
                                <td>${avg_price:.2f}</td>
                                <td class="date">{last_filing}</td>
                                <td class="days-ago">{days_ago}</td>
                            </tr>
                    """
                except Exception as e:
                    print(f"⚠️ Error procesando fila: {e}")
                    continue
            
            html_content += """
                    </table>
                    <div style="margin-top: 30px; padding: 20px; background: #e8f5e8; border-radius: 10px;">
                        <h3>📝 Interpretación de Resultados:</h3>
                        <ul>
                            <li><strong>Score:</strong> Puntuación combinada de actividad de insiders y fundamentales (0-100)</li>
                            <li><strong>🟢 Verde (>60):</strong> Alta confianza - Múltiples señales positivas</li>
                            <li><strong>🟡 Naranja (30-60):</strong> Media confianza - Algunas señales positivas</li>
                            <li><strong>🔴 Rojo (<30):</strong> Baja confianza - Pocas señales</li>
                            <li><strong>Trans.:</strong> Número de transacciones de insiders detectadas</li>
                            <li><strong>Insiders:</strong> Número de ejecutivos/directores únicos que compraron</li>
                            <li><strong>Días Atrás:</strong> Días desde la última actividad de insider reportada</li>
                        </ul>
                        <p><strong>⚠️ Disclaimer:</strong> Esta información es solo para fines educativos. No constituye asesoramiento de inversión. Siempre consulte con un asesor financiero profesional.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        
        html_path = "reports/insiders_opportunities.html"
        os.makedirs("reports", exist_ok=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ Reporte HTML generado: {html_path}")
        return html_path
        
    except Exception as e:
        print(f"❌ Error generando HTML de oportunidades: {e}")
        import traceback
        traceback.print_exc()
        return None

def enviar_reporte_telegram(csv_path, html_path):
    """
    Envía el reporte a Telegram si está configurado - VERSION MEJORADA
    """
    try:
        print("📱 Iniciando envío a Telegram...")
        
        # Obtener chat_id
        try:
            from config import TELEGRAM_CHAT_ID
            chat_id = TELEGRAM_CHAT_ID
            print(f"✅ Chat ID obtenido: {chat_id}")
        except ImportError:
            print("❌ No se pudo importar TELEGRAM_CHAT_ID desde config.py")
            return False
        
        if not chat_id:
            print("⚠️ TELEGRAM_CHAT_ID no configurado, saltando envío")
            return False
        
        # Importar utilidades de Telegram
        try:
            from alerts.telegram_utils import send_message, send_document_telegram
            print("✅ Utilidades de Telegram importadas correctamente")
        except ImportError as e:
            print(f"❌ No se pudieron importar utilidades de Telegram: {e}")
            return False
        
        # Verificar que los archivos existen
        if not os.path.exists(csv_path):
            print(f"❌ El archivo CSV no existe: {csv_path}")
            return False
            
        print(f"✅ Archivo CSV encontrado: {csv_path}")
        
        if html_path and not os.path.exists(html_path):
            print(f"⚠️ El archivo HTML no existe: {html_path}")
            html_path = None
        elif html_path:
            print(f"✅ Archivo HTML encontrado: {html_path}")
        
        # Leer el CSV para obtener estadísticas
        df = pd.read_csv(csv_path)
        print(f"📊 CSV leído: {len(df)} filas")
        
        if len(df) == 0 or 'Mensaje' in df.columns:
            # No hay oportunidades
            mensaje = f"""🎯 **REPORTE DIARIO - INSIDER TRADING**

📊 **Resultado:** Sin oportunidades detectadas
📅 **Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
✅ **Estado:** Filtros funcionando correctamente

🔍 **Criterios aplicados:**
• Actividad reciente de insiders
• Valores de transacción significativos  
• Análisis fundamental básico

💡 **Interpretación:** Los filtros estrictos están funcionando. Solo se mostrarán oportunidades cuando sean realmente prometedoras."""

            print("📝 Mensaje preparado (sin oportunidades)")
            
        else:
            # Hay oportunidades
            score_column = "FinalScore" if "FinalScore" in df.columns else "InsiderConfidence"
            
            # Calcular estadísticas de forma segura
            try:
                score_values = pd.to_numeric(df[score_column], errors='coerce').dropna()
                avg_score = score_values.mean() if len(score_values) > 0 else 0
                
                top_ticker = df.iloc[0]['Ticker'] if len(df) > 0 else "N/A"
                top_score_raw = df.iloc[0][score_column] if len(df) > 0 and score_column in df.columns else 0
                top_score = float(top_score_raw) if pd.notna(top_score_raw) else 0
                
            except Exception as e:
                print(f"⚠️ Error calculando estadísticas: {e}")
                avg_score = 0
                top_ticker = "N/A"  
                top_score = 0
            
            mensaje = f"""🎯 **REPORTE DIARIO - INSIDER TRADING**

📊 **Oportunidades encontradas:** {len(df)}
📈 **Score promedio:** {avg_score:.1f}
🏆 **Top oportunidad:** {top_ticker} (Score: {top_score:.1f})
📅 **Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

🔝 **Top 5 oportunidades:**"""
            
            # Agregar top 5
            for i, row in df.head(5).iterrows():
                try:
                    ticker = row.get('Ticker', 'N/A')
                    score_raw = row.get(score_column, 0)
                    confidence = row.get('ConfidenceLevel', 'N/A')
                    transactions = row.get('NumTransactions', 0)
                    days = row.get('DaysSinceLastActivity', 'N/A')
                    
                    # Convertir score de forma segura
                    try:
                        score_val = float(score_raw) if pd.notna(score_raw) else 0
                    except (ValueError, TypeError):
                        score_val = 0
                    
                    mensaje += f"\n{i+1}. **{ticker}** - Score: {score_val:.1f} ({confidence}) - {transactions} trans - {days} días"
                    
                except Exception as e:
                    print(f"⚠️ Error procesando fila {i}: {e}")
                    continue
            
            mensaje += "\n\n📄 **Archivo adjunto:** Reporte completo en HTML"
            print("📝 Mensaje preparado (con oportunidades)")
        
        # Enviar mensaje principal
        try:
            print("📤 Enviando mensaje principal...")
            send_message(chat_id, mensaje)
            print("✅ Mensaje principal enviado a Telegram")
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")
            return False
        
        # Enviar archivo HTML si existe y hay oportunidades
        if html_path and os.path.exists(html_path) and len(df) > 0 and 'Mensaje' not in df.columns:
            try:
                print("📎 Enviando archivo HTML...")
                send_document_telegram(chat_id, html_path, "📊 Reporte completo de oportunidades")
                print("✅ Archivo HTML enviado a Telegram")
            except Exception as e:
                print(f"⚠️ Error enviando archivo HTML: {e}")
                # No fallar completamente si solo falla el archivo
        else:
            print("ℹ️ No se envía archivo HTML (no existe o no hay oportunidades)")
        
        print("🎉 Envío a Telegram completado exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error general enviando a Telegram: {e}")
        import traceback
        traceback.print_exc()
        return False

# También vamos a mejorar la función principal para asegurar el envío
def generar_reporte_completo_integrado():
    """
    Función que integra el análisis de oportunidades con plot_utils.py - MEJORADA
    """
    print("🚀 GENERANDO REPORTE COMPLETO INTEGRADO")
    print("=" * 50)
    
    try:
        # Paso 1: Ejecutar análisis de oportunidades
        print("🎯 Paso 1: Análisis de oportunidades...")
        csv_path = scrape_openinsider()
        html_opportunities = None
        
        if csv_path:
            print(f"✅ CSV generado: {csv_path}")
            html_opportunities = generar_reporte_html_oportunidades(csv_path)
            if html_opportunities:
                print(f"✅ HTML oportunidades generado: {html_opportunities}")
            else:
                print("⚠️ No se pudo generar HTML de oportunidades")
        else:
            print("❌ No se pudo generar CSV de oportunidades")
        
        # Paso 2: Ejecutar plot_utils (si existe)
        print("\n📊 Paso 2: Generación de gráficos...")
        html_charts = None
        bundle_path = None
        
        try:
            from alerts.plot_utils import generar_reporte_completo
            result = generar_reporte_completo()
            
            if isinstance(result, tuple) and len(result) >= 2:
                html_charts, bundle_path = result[:2]
                print(f"✅ HTML gráficos: {html_charts}")
                print(f"✅ Bundle: {bundle_path}")
        except ImportError:
            print("⚠️ plot_utils no disponible, continuando sin gráficos")
        except Exception as e:
            print(f"⚠️ Error en plot_utils: {e}")
        
        # Paso 3: Enviar a Telegram - MEJORADO
        print("\n📱 Paso 3: Envío a Telegram...")
        telegram_success = False
        
        if csv_path:
            print(f"📊 Enviando reporte de oportunidades...")
            telegram_success = enviar_reporte_telegram(csv_path, html_opportunities)
            
            if telegram_success:
                print("✅ Reporte de oportunidades enviado a Telegram")
            else:
                print("❌ Falló el envío del reporte de oportunidades")
        else:
            print("⚠️ No hay CSV para enviar")
        
        print("\n" + "=" * 50)
        print("🎉 REPORTE COMPLETO FINALIZADO")
        print("=" * 50)
        print(f"📱 Telegram: {'✅ Enviado' if telegram_success else '❌ Falló'}")
        
        return {
            'csv_opportunities': csv_path,
            'html_opportunities': html_opportunities,
            'html_charts': html_charts,
            'bundle': bundle_path,
            'telegram_sent': telegram_success
        }
        
    except Exception as e:
        print(f"❌ Error en reporte completo: {e}")
        import traceback
        traceback.print_exc()
        return None
def generar_reporte_completo_integrado():
    """
    Función que integra el análisis de oportunidades con plot_utils.py
    """
    print("🚀 GENERANDO REPORTE COMPLETO INTEGRADO")
    print("=" * 50)
    
    try:
        # Paso 1: Ejecutar análisis de oportunidades
        print("🎯 Paso 1: Análisis de oportunidades...")
        csv_path = scrape_openinsider()
        html_opportunities = None
        
        if csv_path:
            html_opportunities = generar_reporte_html_oportunidades(csv_path)
            print(f"✅ Oportunidades: {csv_path}")
            if html_opportunities:
                print(f"✅ HTML oportunidades: {html_opportunities}")
        
        # Paso 2: Ejecutar plot_utils (si existe)
        print("\n📊 Paso 2: Generación de gráficos...")
        html_charts = None
        bundle_path = None
        
        try:
            from alerts.plot_utils import generar_reporte_completo
            result = generar_reporte_completo()
            
            if isinstance(result, tuple) and len(result) >= 2:
                html_charts, bundle_path = result[:2]
                print(f"✅ HTML gráficos: {html_charts}")
                print(f"✅ Bundle: {bundle_path}")
        except ImportError:
            print("⚠️ plot_utils no disponible, continuando sin gráficos")
        except Exception as e:
            print(f"⚠️ Error en plot_utils: {e}")
        
        # Paso 3: Enviar a Telegram
        print("\n📱 Paso 3: Envío a Telegram...")
        if csv_path and html_opportunities:
            enviar_reporte_telegram(csv_path, html_opportunities)
        
        print("\n" + "=" * 50)
        print("🎉 REPORTE COMPLETO FINALIZADO")
        print("=" * 50)
        
        return {
            'csv_opportunities': csv_path,
            'html_opportunities': html_opportunities,
            'html_charts': html_charts,
            'bundle': bundle_path
        }
        
    except Exception as e:
        print(f"❌ Error en reporte completo: {e}")
        import traceback
        traceback.print_exc()
        return None

# Función auxiliar para crear datos de prueba
def crear_datos_prueba():
    """
    Crea datos de prueba para testing del sistema
    """
    print("🧪 Creando datos de prueba...")
    
    # Crear directorio
    os.makedirs("reports", exist_ok=True)
    
    # Datos de insiders de prueba con la estructura CORRECTA
    insiders_data = {
        'Ticker': ['2025-05-30 08:44:19', '2025-05-30 08:38:55', '2025-05-30 06:04:21', '2025-05-29 16:23:10', '2025-05-29 15:15:35', '2025-05-29 14:22:48', '2025-05-28 11:30:22', '2025-05-28 10:45:17'],
        'Insider': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AAPL', 'MSFT', 'NVDA', 'META'],
        'Title': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Tesla Inc.', 'Apple Inc.', 'Microsoft Corp.', 'NVIDIA Corp.', 'Meta Platforms'],
        'Date': ['CEO', 'CEO', 'CEO', 'CEO', 'SVP', 'CFO', 'CEO', 'CEO'],
        'Type': ['P - Purchase', 'P - Purchase', 'P - Purchase', 'P - Purchase', 'P - Purchase', 'P - Purchase', 'P - Purchase', 'P - Purchase'],
        'Price': [180.50, 420.30, 2750.00, 185.20, 181.20, 421.50, 950.00, 485.30],
        'Qty': [1000, 500, 100, 2000, 1500, 750, 300, 800],
        'Owned': [50000, 25000, 5000, 100000, 30000, 15000, 8000, 40000],
        'Value': ['0%', '0%', '0%', '0%', '0%', '0%', '0%', '0%'],
        'Source': ['OpenInsider', 'OpenInsider', 'OpenInsider', 'OpenInsider', 'OpenInsider', 'OpenInsider', 'OpenInsider', 'OpenInsider'],
        'ScrapedAt': ['2025-05-30 15:22:28', '2025-05-30 15:22:28', '2025-05-30 15:22:28', '2025-05-29 20:30:15', '2025-05-29 20:30:15', '2025-05-29 20:30:15', '2025-05-28 18:45:22', '2025-05-28 18:45:22'],
        'Chart_Daily': ['reports/graphs/2025-05-30 08:44:19_d.png', 'reports/graphs/2025-05-30 08:38:55_d.png', 'reports/graphs/2025-05-30 06:04:21_d.png', 'reports/graphs/2025-05-29 16:23:10_d.png', 'reports/graphs/2025-05-29 15:15:35_d.png', 'reports/graphs/2025-05-29 14:22:48_d.png', 'reports/graphs/2025-05-28 11:30:22_d.png', 'reports/graphs/2025-05-28 10:45:17_d.png'],
        'Chart_Weekly': ['reports/graphs/2025-05-30 08:44:19_w.png', 'reports/graphs/2025-05-30 08:38:55_w.png', 'reports/graphs/2025-05-30 06:04:21_w.png', 'reports/graphs/2025-05-29 16:23:10_w.png', 'reports/graphs/2025-05-29 15:15:35_w.png', 'reports/graphs/2025-05-29 14:22:48_w.png', 'reports/graphs/2025-05-28 11:30:22_w.png', 'reports/graphs/2025-05-28 10:45:17_w.png']
    }
    
    insiders_df = pd.DataFrame(insiders_data)
    insiders_df.to_csv("reports/insiders_daily.csv", index=False)
    
    # Datos fundamentales de prueba
    fundamentals_data = {
        'Ticker': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMZN', 'NFLX'],
        'Company': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Tesla Inc.', 'NVIDIA Corp.', 'Meta Platforms', 'Amazon.com', 'Netflix Inc.'],
        'Debt/Eq': [1.2, 0.8, 0.1, 0.3, 0.2, 0.0, 1.1, 1.5],
        'P/E': [25.5, 28.2, 22.1, 45.2, 55.8, 18.9, 35.4, 28.7],
        'ROE': [15.2, 18.5, 14.8, 12.3, 22.1, 16.7, 13.9, 20.2],
        'Gross Margin': [38.2, 42.1, 25.6, 18.9, 73.2, 35.4, 28.1, 31.5],
        'P/B': [8.5, 7.2, 5.1, 9.8, 12.1, 4.2, 6.8, 5.9],
        'P/S': [6.2, 8.1, 4.8, 7.9, 18.2, 4.1, 2.8, 5.2],
        'Market Cap': [2800000, 2900000, 1750000, 580000, 2100000, 750000, 1400000, 180000]
    }
    
    fundamentals_df = pd.DataFrame(fundamentals_data)
    fundamentals_df.to_csv("reports/finviz_ml_dataset_with_fundamentals.csv", index=False)
    
    print("✅ Datos de prueba creados exitosamente")
    print("   - reports/insiders_daily.csv")
    print("   - reports/finviz_ml_dataset_with_fundamentals.csv")

if __name__ == "__main__":
    import sys
    
    # Opción para crear datos de prueba
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        crear_datos_prueba()
        print("\n" + "="*60)
        print("🧪 EJECUTANDO ANÁLISIS CON DATOS DE PRUEBA")
        print("="*60)
    
    # Opción para reporte completo integrado
    if len(sys.argv) > 1 and sys.argv[1] == "--completo":
        generar_reporte_completo_integrado()
    else:
        # Ejecutar análisis principal
        output_path = scrape_openinsider()
        
        if output_path:
            print(f"\n✅ Análisis completado exitosamente")
            print(f"📄 Archivo CSV: {output_path}")
            
            # Generar reporte HTML
            html_path = generar_reporte_html_oportunidades(output_path)
            if html_path:
                print(f"🌐 Reporte HTML: {html_path}")
            
            # Enviar a Telegram si está configurado
            telegram_enviado = enviar_reporte_telegram(output_path, html_path)
            
            print(f"\n🎯 PRÓXIMOS PASOS:")
            print(f"1. Revisar el archivo CSV para análisis detallado")
            print(f"2. Abrir el HTML en navegador para vista amigable")  
            print(f"3. Considerar las oportunidades con score >60 como prioritarias")
            print(f"4. Realizar investigación adicional antes de invertir")
            
            if telegram_enviado:
                print(f"5. ✅ Reporte enviado a Telegram automáticamente")
            else:
                print(f"5. ⚠️ Telegram no configurado o falló el envío")
                
        else:
            print(f"\n❌ El análisis no se completó correctamente")
            print(f"💡 Sugerencias:")
            print(f"   - Ejecutar con --test para probar con datos ficticios")
            print(f"   - Verificar que existen los archivos de datos")
            print(f"   - Revisar el formato de los archivos CSV")