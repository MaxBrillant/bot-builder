"""
Flow Schemas
Pydantic models for flow management
"""

from pydantic import BaseModel, Field, field_serializer, field_validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from app.models.node_configs import FlowNode, VariableDefinition, FlowDefaults


class FlowCreate(BaseModel):
    """Schema for creating a flow"""
    name: str = Field(..., min_length=1, max_length=96, description="User-provided flow name (unique per bot)")
    trigger_keywords: List[str] = Field(default_factory=list)
    variables: Optional[Dict[str, VariableDefinition]] = Field(default_factory=dict)
    defaults: Optional[FlowDefaults] = None
    start_node_id: str = Field(..., min_length=1, max_length=96)
    nodes: Dict[str, FlowNode] = Field(...)
    
    @field_validator('trigger_keywords')
    @classmethod
    def validate_trigger_keywords(cls, v: List[str]) -> List[str]:
        """Validate trigger keywords - must have at least one non-empty keyword"""
        if not v or len(v) == 0:
            raise ValueError("At least one trigger keyword is required")
        
        # Validate each keyword
        valid_keywords = []
        for i, keyword in enumerate(v):
            if not isinstance(keyword, str):
                raise ValueError(f"Trigger keyword at index {i} must be a string")
            
            # Strip whitespace
            cleaned = keyword.strip()
            
            if not cleaned:
                raise ValueError(f"Trigger keyword at index {i} cannot be empty or whitespace only")
            
            valid_keywords.append(cleaned)
        
        if not valid_keywords:
            raise ValueError("At least one trigger keyword is required")
        
        # Check for duplicate keywords within the same flow (case-insensitive)
        normalized_keywords = [kw.upper() for kw in valid_keywords]
        seen = set()
        duplicates = []
        for kw in normalized_keywords:
            if kw in seen:
                duplicates.append(kw)
            seen.add(kw)
        
        if duplicates:
            raise ValueError(f"Duplicate trigger keywords found: {', '.join(set(duplicates))}")
        
        return valid_keywords
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "checkout_flow",
                "trigger_keywords": ["START", "BEGIN"],
                "variables": {
                    "user_name": {"type": "string", "default": None}
                },
                "defaults": {
                    "retry_logic": {
                        "max_attempts": 3,
                        "fail_route": "node_error"
                    }
                },
                "start_node_id": "node_welcome",
                "nodes": {
                    "node_welcome": {
                        "id": "node_welcome",
                        "type": "MESSAGE",
                        "config": {"text": "Welcome!"},
                        "routes": [{"condition": "true", "target_node": "node_end"}]
                    },
                    "node_end": {
                        "id": "node_end",
                        "type": "END",
                        "config": {}
                    }
                }
            }
        }
    }


class FlowUpdate(BaseModel):
    """Schema for updating a flow"""
    trigger_keywords: Optional[List[str]] = None
    variables: Optional[Dict[str, VariableDefinition]] = None
    defaults: Optional[FlowDefaults] = None
    start_node_id: Optional[str] = None
    nodes: Optional[Dict[str, FlowNode]] = None
    
    @field_validator('trigger_keywords')
    @classmethod
    def validate_trigger_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate trigger keywords when provided - must have at least one non-empty keyword"""
        # If None, it means no update to trigger_keywords
        if v is None:
            return v
        
        # If provided, must have at least one keyword
        if len(v) == 0:
            raise ValueError("At least one trigger keyword is required")
        
        # Validate each keyword
        valid_keywords = []
        for i, keyword in enumerate(v):
            if not isinstance(keyword, str):
                raise ValueError(f"Trigger keyword at index {i} must be a string")
            
            # Strip whitespace
            cleaned = keyword.strip()
            
            if not cleaned:
                raise ValueError(f"Trigger keyword at index {i} cannot be empty or whitespace only")
            
            valid_keywords.append(cleaned)
        
        if not valid_keywords:
            raise ValueError("At least one trigger keyword is required")
        
        # Check for duplicate keywords within the same flow (case-insensitive)
        normalized_keywords = [kw.upper() for kw in valid_keywords]
        seen = set()
        duplicates = []
        for kw in normalized_keywords:
            if kw in seen:
                duplicates.append(kw)
            seen.add(kw)
        
        if duplicates:
            raise ValueError(f"Duplicate trigger keywords found: {', '.join(set(duplicates))}")
        
        return valid_keywords
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "trigger_keywords": ["START", "BEGIN", "HELLO"]
            }
        }
    }


class FlowResponse(BaseModel):
    """Schema for flow data in responses - returns both UUID and name"""
    flow_id: str = Field(..., description="Flow UUID (system-generated)")
    flow_name: str = Field(..., description="Flow name (user-provided)")
    bot_id: str = Field(..., description="Bot UUID")
    trigger_keywords: List[str]
    flow_definition: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "flow_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
                "flow_name": "checkout_flow",
                "bot_id": "550e8400-e29b-41d4-a716-446655440000",
                "trigger_keywords": ["START"],
                "flow_definition": {
                    "name": "checkout_flow",
                    "start_node_id": "node_welcome",
                    "nodes": {}
                },
                "created_at": "2024-11-30T10:00:00",
                "updated_at": "2024-11-30T10:00:00"
            }
        }
    }


class FlowListResponse(BaseModel):
    """Schema for listing flows with pagination"""
    flows: List[FlowResponse]
    total: int
    skip: int = Field(default=0, ge=0, description="Number of flows skipped")
    limit: int = Field(default=100, ge=1, le=100, description="Maximum flows returned")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "flows": [],
                "total": 0,
                "skip": 0,
                "limit": 100
            }
        }
    }


class FlowValidationError(BaseModel):
    """Schema for flow validation error details"""
    type: str
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


class FlowValidationResponse(BaseModel):
    """Schema for flow validation response - returns both UUID and name"""
    status: str
    flow_id: Optional[str] = None  # UUID as string
    flow_name: Optional[str] = None  # User-provided name
    bot_id: Optional[str] = None
    message: Optional[str] = None
    errors: Optional[List[FlowValidationError]] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "success",
                    "flow_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
                    "flow_name": "checkout_flow",
                    "bot_id": "550e8400-e29b-41d4-a716-446655440000",
                    "message": "Flow validated and stored successfully"
                },
                {
                    "status": "error",
                    "errors": [
                        {
                            "type": "missing_node",
                            "message": "start_node_id 'node_start' does not exist in nodes",
                            "location": "start_node_id"
                        }
                    ]
                }
            ]
        }
    }