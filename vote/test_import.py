#!/usr/bin/env python3
"""Test if Flask app can import"""
try:
    from app import app
    print("✓ Flask app imported successfully")
    print(f"✓ Flask app has {len(app.url_map._rules)} routes")
    for rule in app.url_map.iter_rules():
        print(f"  - {rule.rule} ({rule.methods})")
except Exception as e:
    print(f"✗ Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
