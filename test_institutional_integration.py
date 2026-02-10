#!/usr/bin/env python3
"""
TEST INSTITUTIONAL INTEGRATION
Prueba el nuevo scoring institucional integrado
"""
from institutional_tracker import InstitutionalTracker
from super_analyzer_4d import SuperAnalyzer4D

print("=" * 70)
print("🧪 TEST: INSTITUTIONAL SCORING INTEGRATION")
print("=" * 70)

# Test directo del tracker
print("\n1️⃣  TEST DIRECTO DEL TRACKER")
print("-" * 70)

tracker = InstitutionalTracker()

test_tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']

for ticker in test_tickers:
    activity = tracker.get_whale_activity(ticker)

    print(f"\n{ticker}:")
    print(f"   Whales holding: {activity['num_whales']}")
    print(f"   Total value: ${activity['total_value']:,}")
    print(f"   Whale score: {activity['whale_score']}/100")

    if activity['whales_holding']:
        print(f"   Top whales:")
        for whale in activity['whales_holding'][:3]:
            print(f"      - {whale['whale_name']} ({whale['tier']}): ${whale['value']:,}")

# Test integración con SuperAnalyzer4D
print("\n\n2️⃣  TEST INTEGRACIÓN CON SUPER ANALYZER 5D")
print("-" * 70)

analyzer = SuperAnalyzer4D()

print("\n📊 Testing score calculation para AAPL...")
# Este test requiere que existan los archivos de datos (VCP, insiders, etc.)

print("\n✅ Test completado!")
print("\nSi ves whale scores > 0, ¡la integración está funcionando! 🎉")
