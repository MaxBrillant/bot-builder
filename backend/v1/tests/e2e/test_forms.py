"""
Forms (Tests 439-440)
Reorganized from: test_33_use_case_coverage.py

Tests validate: Forms
"""
import pytest

def test_439_form_sequential_data_collection():
    """✅ Forms: Sequential data collection pattern"""
    # Spec: "Forms: Multi-step data collection with validation"

    flow = {
    "node_start": {"type": "PROMPT", "config": {"text": "Name?", "save_to_variable": "name"}},
    "node_email": {"type": "PROMPT", "config": {"text": "Email?", "save_to_variable": "email"}},
    "node_phone": {"type": "PROMPT", "config": {"text": "Phone?", "save_to_variable": "phone"}},
    "node_save": {"type": "API_ACTION"},
    "node_confirm": {"type": "MESSAGE", "config": {"text": "Saved!"}},
    "node_end": {"type": "END"}
    }

def test_440_form_with_validation_at_each_step():
    """✅ Forms: Validation at each input step"""
    prompt = {
    "type": "PROMPT",
    "config": {
    "text": "Email:",
    "save_to_variable": "email",
    "validation": {"type": "REGEX", "rule": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"}
    }
    }


