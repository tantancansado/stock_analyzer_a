#!/usr/bin/env python3
"""Valida sintaxis JavaScript en el dashboard antes de commit"""
import re
import sys
from pathlib import Path

def validate_dashboard():
    html_path = Path("docs/super_dashboard.html")
    if not html_path.exists():
        print("⚠️  Dashboard not found, skipping validation")
        return 0
    
    html = html_path.read_text()
    errors = []
    
    # Check for comma instead of semicolon in onclick
    onclicks = re.findall(r'onclick="([^"]+)"', html)
    for oc in onclicks:
        if '),var ' in oc or '),r.' in oc or '),d.' in oc:
            errors.append(f"❌ onclick uses comma instead of semicolon: {oc[:60]}...")
    
    # Check for $$ instead of $ in template literals (common f-string error)
    bad_dollar = re.findall(r'\$\$\{[^}]+\}', html)
    if bad_dollar:
        errors.append(f"❌ Found ${{...}} instead of ${{{{...}}}}: {len(bad_dollar)} occurrences")
    
    if errors:
        print("❌ DASHBOARD VALIDATION FAILED")
        for err in errors[:5]:
            print(f"  {err}")
        return 1
    else:
        print("✅ Dashboard JavaScript validation passed")
        return 0

if __name__ == "__main__":
    sys.exit(validate_dashboard())
