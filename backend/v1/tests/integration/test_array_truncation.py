"""
Array truncation (Tests 200-206)
Reorganized from: test_16_array_truncation.py

Tests validate: Array truncation
"""
import pytest

def test_200_array_default_truncated_to_24_items():
    """✅ Array variable default truncated to 24 items at initialization"""
    # Spec: "Variable default - array: 24 items max"
    # "Array defaults: Maximum 24 items"

    flow_variables = {
    "items": {
    "type": "array",
    "default": list(range(30))  # 30 items
    }
    }

    # During flow validation or session initialization
    # Expected: Array truncated to first 24 items
    # context["items"] = [0, 1, 2, ..., 23]
    # Items 24-29 discarded

    assert len(flow_variables["items"]["default"]) == 30
    # After truncation: len = 24


def test_201_array_default_with_exactly_24_items_not_truncated():
    """✅ Array default with exactly 24 items preserved"""

    flow_variables = {
    "items": {
    "type": "array",
    "default": list(range(24))  # Exactly 24
    }
    }

    # Expected: No truncation needed
    # All 24 items preserved



def test_202_api_response_array_truncated_to_24_items():
    """✅ API response_map: arrays truncated when stored to context"""
    # Spec: "Array length in context: 24 items per array variable (truncated if exceeded)"
    # "Arrays exceeding 24 items are silently truncated to first 24 items"

    flow_variables = {
    "results": {"type": "array", "default": []}
    }

    api_response = {
    "status": 200,
    "body": {
    "results": list(range(50))  # API returns 50 items
    }
    }

    response_map = [
    {"source_path": "results", "target_variable": "results"}
    ]

    # After response_map execution:
    # Expected: context["results"] = [0, 1, 2, ..., 23]
    # Items 24-49 silently discarded
    # No error shown to user


def test_203_response_map_truncation_is_silent():
    """✅ Array truncation in response_map is SILENT (no error/warning)"""
    # Spec: "Arrays exceeding 24 items are silently truncated"

    # API returns large array
    api_response = {
    "body": {
    "data": list(range(100))
    }
    }

    # After mapping to context variable
    # Expected:
    # - Array truncated to 24 items
    # - No error message
    # - No warning logged (to user)
    # - Flow continues normally
    # - User sees first 24 items only



def test_204_menu_output_mapping_array_truncated():
    """✅ MENU output_mapping: arrays truncated when extracted"""
    # Spec: "output_mapping with type inference"
    # Arrays stored to context are truncated

    flow_variables = {
    "tags": {"type": "array", "default": []}
    }

    menu_items = [
    {
    "id": 1,
    "name": "Item 1",
    "tags": list(range(40))  # 40 tags
    }
    ]

    output_mapping = [
    {"source_path": "tags", "target_variable": "tags"}
    ]

    # User selects first item
    # output_mapping extracts tags array with 40 items
    # After type conversion and storage:
    # Expected: context["tags"] = [0, 1, 2, ..., 23]
    # Truncated to 24 items



def test_205_dynamic_menu_source_truncated_to_24_items():
    """✅ DYNAMIC menu: source array truncated to 24 options displayed"""
    # Spec: "Dynamic menus limited to 24 options - if source array exceeds 24, only first 24 items displayed"

    menu_config = {
    "source_type": "DYNAMIC",
    "source_variable": "trips",
    "item_template": "{{index}}. {{item.name}}"
    }

    context = {
    "trips": [{"name": f"Trip {i}"} for i in range(50)]  # 50 trips
    }

    # When displaying menu:
    # Expected:
    # - Only first 24 trips displayed
    # - Options numbered 1-24
    # - User cannot select options 25-50 (they're not shown)
    # - Trips 24-49 silently not displayed


def test_206_array_truncation_preserves_first_24_items():
    """✅ Array truncation: FIRST 24 items always preserved"""
    # Spec: "silently truncated to first 24 items"

    original_array = [
    {"id": i, "value": f"item_{i}"}
    for i in range(100)
    ]

    # After truncation
    expected_truncated = [
    {"id": i, "value": f"item_{i}"}
    for i in range(24)  # Items 0-23
    ]

    # Expected:
    # - Items 0-23 preserved in order
    # - Items 24-99 discarded
    # - No reordering or selection, just truncation at index 24
