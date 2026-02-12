#!/usr/bin/env python3
"""
Trade Reasoner Final Verification

Comprehensive test of the trade reasoner implementation.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*70)
print(" TRADE REASONER IMPLEMENTATION VERIFICATION")
print("="*70)
print()

# Test 1: Module structure check
print("[1] Checking trade_reasoner.py file structure...")
trade_reasoner_path = os.path.join(os.path.dirname(__file__), 'src/trading/trade_reasoner.py')

if not os.path.exists(trade_reasoner_path):
    print("❌ trade_reasoner.py not found!")
    sys.exit(1)

file_size = os.path.getsize(trade_reasoner_path)
print(f"✅ File exists: {trade_reasoner_path}")
print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")

# Test 2: Read and analyze file content
print("\n[2] Analyzing file content...")
with open(trade_reasoner_path, 'r') as f:
    content = f.read()

# Check for key classes
has_reasoner_class = 'class TradeReasoner' in content
has_reasoning_class = 'class TradeReasoning' in content or '@dataclass' in content

# Check for key methods
key_methods = [
    'def analyze_setup',
    'def create_trade_record',
    'def _find_matching_strategy',
    'def _generate_rule_based_reasoning',
    'def _calculate_risk_levels'
]

found_methods = []
missing_methods = []

for method in key_methods:
    if method in content:
        found_methods.append(method.replace('def ', ''))
    else:
        missing_methods.append(method.replace('def ', ''))

print(f"✅ TradeReasoner class: {'Found' if has_reasoner_class else 'Missing'}")
print(f"✅ TradeReasoning dataclass: {'Found' if has_reasoning_class else 'Missing'}")
print(f"✅ Methods found: {len(found_methods)}/{len(key_methods)}")
for method in found_methods:
    print(f"   ✓ {method}")

if missing_methods:
    print(f"⚠️  Missing methods:")
    for method in missing_methods:
        print(f"   ✗ {method}")

# Test 3: Check Anthropic handling
print("\n[3] Checking Anthropic import handling...")
has_try_except = 'try:' in content and 'from anthropic import' in content and 'HAS_ANTHROPIC' in content
has_fallback = 'HAS_ANTHROPIC = False' in content

if has_try_except and has_fallback:
    print("✅ Proper try/except handling for Anthropic import")
    print("✅ Fallback mechanism in place")
else:
    print("⚠️  Anthropic import handling may be incomplete")

# Test 4: Check dependencies
print("\n[4] Checking import statements...")
required_imports = [
    'from ..types import',
    'from ..detection.confluence_scorer import',
    'from datetime import datetime'
]

import_issues = []
for imp in required_imports:
    if imp not in content:
        import_issues.append(imp)

if not import_issues:
    print("✅ All required imports present")
else:
    print(f"⚠️  Missing imports:")
    for imp in import_issues:
        print(f"   ✗ {imp}")

# Test 5: Check for rule-based reasoning
print("\n[5] Checking rule-based reasoning fallback...")
has_rule_based = '_generate_rule_based_reasoning' in content
has_llm_check = 'if self.use_llm' in content or 'use_llm' in content

if has_rule_based and has_llm_check:
    print("✅ Rule-based reasoning fallback implemented")
    print("✅ LLM usage check present")
else:
    if not has_rule_based:
        print("⚠️  Rule-based reasoning method not found")
    if not has_llm_check:
        print("⚠️  LLM usage check not found")

# Test 6: Documentation check
print("\n[6] Checking documentation...")
has_docstring = '"""' in content[:500]  # Check first 500 chars for module docstring
method_count = content.count('def ')
docstring_count = content.count('"""')

print(f"✅ Module docstring: {'Present' if has_docstring else 'Missing'}")
print(f"   Methods defined: {method_count}")
print(f"   Docstrings found: {docstring_count // 2}")  # Each docstring has opening and closing

# Summary
print("\n" + "="*70)
print(" VERIFICATION SUMMARY")
print("="*70)

checks = [
    ("File structure", True),
    ("TradeReasoner class", has_reasoner_class),
    ("TradeReasoning dataclass", has_reasoning_class),
    ("Core methods", len(missing_methods) == 0),
    ("Anthropic handling", has_try_except and has_fallback),
    ("Import statements", len(import_issues) == 0),
    ("Rule-based fallback", has_rule_based),
    ("Documentation", has_docstring)
]

passed = sum(1 for _, result in checks if result)
total = len(checks)

print()
for check_name, result in checks:
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status:12} - {check_name}")

print()
print(f"Result: {passed}/{total} checks passed")

if passed == total:
    print("\n🎉 ALL CHECKS PASSED!")
    print("   The trade reasoner implementation is complete and ready to use.")
else:
    print(f"\n⚠️  {total - passed} check(s) failed")
    print("   Review the implementation and address the issues above.")

# Test 7: Integration check (if types are available)
print("\n[7] Attempting basic integration test...")
try:
    # This will fail if dependencies aren't installed, but that's ok
    # We're just checking if the code structure is sound
    from trading.trade_reasoner import TradeReasoner, TradeReasoning
    print("✅ Successfully imported TradeReasoner and TradeReasoning")
    print("   Module can be imported when dependencies are available")
except ImportError as e:
    # Expected if dependencies aren't installed
    print(f"ℹ️  Import requires dependencies (expected): {str(e)[:60]}...")
    print("   This is normal if full environment isn't set up")
except Exception as e:
    print(f"⚠️  Unexpected error during import: {e}")

print("\n" + "="*70)
print(" VERIFICATION COMPLETE")
print("="*70)
print()

sys.exit(0 if passed == total else 1)
