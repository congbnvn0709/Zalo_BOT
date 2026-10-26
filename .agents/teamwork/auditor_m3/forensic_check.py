"""
Forensic Audit Script for Milestone 3
Auditing: api/routes.py, main.py, run.py, static/js/app.js
"""

import ast
import inspect
import sys
import os
import re
import socket
import unittest

PROJECT_ROOT = "/Users/congcm/CODE/Vibe_Code/Zalo_BOT"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def check_ast_hardcoding(filepath):
    print(f"\n--- Checking AST for: {filepath} ---")
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=filepath)
    
    # Check for suspicious branches (e.g., if text == 'HOÀNG ĐẮC PHÚ' or if 'test' in text)
    suspicious_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_source = ast.unparse(node.test)
            if any(suspicious in test_source for suspicious in ["HOÀNG ĐẮC PHÚ", "TEST", "test", "24/10", "sdv", "magic"]):
                suspicious_nodes.append((node.lineno, test_source))
        elif isinstance(node, ast.Compare):
            cmp_source = ast.unparse(node)
            if any(suspicious in cmp_source for suspicious in ["HOÀNG ĐẮC PHÚ", "TEST", "test"]):
                suspicious_nodes.append((node.lineno, cmp_source))
                
    print(f"Suspicious comparison nodes found: {len(suspicious_nodes)}")
    for lineno, src in suspicious_nodes:
        print(f"  Line {lineno}: {src}")
    return suspicious_nodes

def check_routes_authenticity():
    print("\n--- Checking api/routes.py Authenticity ---")
    from api import routes
    from core.parser import parse_attendance_messages
    from core.excel_integrator import ExcelIntegrator
    
    # 1. Inspect parse_messages
    parse_source = inspect.getsource(routes.parse_messages)
    assert "parse_attendance_messages(" in parse_source, "parse_messages does not call parse_attendance_messages!"
    print("[PASS] parse_messages calls parse_attendance_messages dynamically.")
    
    # 2. Inspect export_excel
    export_source = inspect.getsource(routes.export_excel)
    assert "ExcelIntegrator(" in export_source, "export_excel does not instantiate ExcelIntegrator!"
    assert "apply_records(" in export_source, "export_excel does not call apply_records!"
    assert "uuid.uuid4().hex" in export_source, "export_excel does not generate dynamic uuid token!"
    print("[PASS] export_excel instantiates ExcelIntegrator and calls apply_records with dynamic uuid token.")
    
    # 3. Inspect download_excel
    dl_source = inspect.getsource(routes.download_excel)
    assert "_EXPORT_TOKEN_STORE.get(token)" in dl_source, "download_excel does not lookup token in _EXPORT_TOKEN_STORE!"
    print("[PASS] download_excel checks dynamic token store.")

def check_run_authenticity():
    print("\n--- Checking run.py Authenticity ---")
    import run
    
    # 1. Test is_port_in_use
    port_in_use_src = inspect.getsource(run.is_port_in_use)
    assert "socket.socket" in port_in_use_src
    assert "connect_ex" in port_in_use_src
    print("[PASS] run.is_port_in_use uses genuine socket.connect_ex.")
    
    # 2. Test find_free_port
    find_free_src = inspect.getsource(run.find_free_port)
    assert "socket.socket" in find_free_src
    assert "bind" in find_free_src
    print("[PASS] run.find_free_port uses genuine socket bind checks.")
    
    # 3. Dynamic test of find_free_port
    free_port = run.find_free_port(start_port=59000, max_port=59010)
    print(f"Dynamic probe found free port: {free_port}")
    assert 59000 <= free_port <= 59010
    
    # Occupy a port and see if find_free_port skips it
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_sock.bind(("127.0.0.1", free_port))
    test_sock.listen(1)
    
    next_port = run.find_free_port(start_port=free_port, max_port=59010)
    print(f"With port {free_port} busy, found next port: {next_port}")
    assert next_port != free_port, "find_free_port did not skip busy port!"
    test_sock.close()
    print("[PASS] run.find_free_port dynamically avoids occupied ports.")

def check_main_authenticity():
    print("\n--- Checking main.py Authenticity ---")
    import main
    assert hasattr(main, "app"), "main.py has no app object!"
    paths = []
    for r in main.app.routes:
        if hasattr(r, "path"):
            paths.append(r.path)
        elif hasattr(r, "name"):
            paths.append(f"mount:{r.name}")
    print(f"Registered route paths in app: {paths}")
    assert "/" in paths
    assert any("/api" in p or "api" in p for p in paths)
    print("[PASS] main.py mounts router and static files correctly.")

if __name__ == "__main__":
    check_ast_hardcoding(os.path.join(PROJECT_ROOT, "api/routes.py"))
    check_ast_hardcoding(os.path.join(PROJECT_ROOT, "main.py"))
    check_ast_hardcoding(os.path.join(PROJECT_ROOT, "run.py"))
    check_routes_authenticity()
    check_run_authenticity()
    check_main_authenticity()
    print("\nALL SCRIPT CHECKS COMPLETED SUCCESSFULLY.")
