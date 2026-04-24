"""
Scoring primitives — pure functions extracted from super_score_integrator.py.

Cada módulo aquí contiene lógica testeable en aislamiento:
  - Sin I/O (no lectura de CSVs, no prints, no yfinance)
  - Sin mutación oculta (recibe df, devuelve nuevo df)
  - Sin dependencias de MarketRegimeDetector/MovingAverageFilter (esos
    inyectan sus resultados como parámetros)

Esto permite tests unitarios rápidos sobre las reglas críticas que hoy
sólo se pueden validar corriendo el pipeline entero (~1-2 minutos).
"""
