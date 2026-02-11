"""
Node Processors
Handle execution logic for different node types
"""

from app.processors.base_processor import BaseProcessor, ProcessResult
from app.processors.prompt_processor import PromptProcessor
from app.processors.menu_processor import MenuProcessor
from app.processors.api_action_processor import APIActionProcessor
from app.processors.logic_processor import LogicProcessor
from app.processors.text_processor import TextProcessor
from app.processors.end_processor import EndProcessor

__all__ = [
    "BaseProcessor",
    "ProcessResult",
    "PromptProcessor",
    "MenuProcessor",
    "APIActionProcessor",
    "LogicProcessor",
    "TextProcessor",
    "EndProcessor"
]