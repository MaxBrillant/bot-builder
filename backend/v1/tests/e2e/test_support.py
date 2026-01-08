"""
Support (Tests 445)
Reorganized from: test_33_use_case_coverage.py

Tests validate: Support
"""
import pytest

def test_445_support_ticket_flow():
    """✅ Support: Issue type → details → ticket creation"""
    flow = {
    "node_type": {"type": "MENU", "config": {"text": "Issue type?"}},
    "node_details": {"type": "PROMPT", "config": {"text": "Details?"}},
    "node_create": {"type": "API_ACTION"},
    "node_confirm": {"type": "MESSAGE"}
    }


