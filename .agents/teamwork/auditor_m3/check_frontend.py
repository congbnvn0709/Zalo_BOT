"""
Forensic check for static/js/app.js and static/index.html DOM mapping.
"""

import re
import os

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
HTML_PATH = os.path.join(PROJECT_ROOT, "static/index.html")
JS_PATH = os.path.join(PROJECT_ROOT, "static/js/app.js")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html_content = f.read()

with open(JS_PATH, "r", encoding="utf-8") as f:
    js_content = f.read()

print("--- Inspecting JS Fetch Calls ---")
fetch_calls = re.findall(r"fetch\((['\"`][^'\"`]+['\"`])", js_content)
for call in fetch_calls:
    print(f"  fetch call: {call}")

assert "'/api/template/info'" in fetch_calls or '"/api/template/info"' in fetch_calls
assert "'/api/sample'" in fetch_calls or '"/api/sample"' in fetch_calls
assert "'/api/parse'" in fetch_calls or '"/api/parse"' in fetch_calls
assert "'/api/template/upload'" in fetch_calls or '"/api/template/upload"' in fetch_calls
assert "'/api/export-excel'" in fetch_calls or '"/api/export-excel"' in fetch_calls
print("[PASS] All required API fetch calls exist authentically.")

print("\n--- Inspecting getElementById in app.js vs index.html ---")
get_elem_ids = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js_content))
html_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_content))

print(f"Total element IDs queried in JS: {len(get_elem_ids)}")
missing_in_html = get_elem_ids - html_ids
if missing_in_html:
    print(f"[FAIL] Missing IDs in index.html: {missing_in_html}")
    assert False, f"Missing IDs in index.html: {missing_in_html}"
else:
    print("[PASS] 100% of getElementById IDs in app.js exist in static/index.html!")

print("\n--- Inspecting Event Listeners in app.js ---")
listeners = re.findall(r"addEventListener\(['\"]([^'\"]+)['\"]", js_content)
print(f"Listeners registered: {set(listeners)}")
assert "DOMContentLoaded" in listeners
assert "click" in listeners
assert "input" in listeners
assert "change" in listeners
assert "submit" in listeners
print("[PASS] DOM event listeners cover input, click, change, submit, DOMContentLoaded.")

print("\n--- Checking for Hardcoded Cheating / Mock Logic in JS ---")
# Check for hardcoded responses or bypasses
cheat_patterns = [
    r"if\s*\(.*HOÀNG ĐẮC PHÚ.*\)",
    r"return\s+\[.*HOÀNG ĐẮC PHÚ.*\]",
    r"mock",
    r"fake",
    r"dummy",
]
for p in cheat_patterns:
    matches = re.findall(p, js_content, re.IGNORECASE)
    print(f"Pattern '{p}': found {len(matches)} matches")
    assert len(matches) == 0, f"Suspicious match for pattern {p}: {matches}"

print("[PASS] Zero hardcoding or cheat branches found in app.js.")
