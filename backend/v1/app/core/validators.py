"""
Validators — backward-compatibility re-export shim.
For new code, import directly from input_validator or flow_validator.
"""
from app.core.input_validator import InputValidator
from app.core.flow_validator import FlowValidator, RouteConditionValidator, ValidationResult

# Alias used by engine.py, base_processor.py, factory.py
ValidationSystem = InputValidator

__all__ = [
    'InputValidator',
    'FlowValidator',
    'RouteConditionValidator',
    'ValidationResult',
    'ValidationSystem',
]
