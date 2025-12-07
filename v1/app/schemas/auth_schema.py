"""
Authentication Schemas
Pydantic models for user authentication and authorization
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
import re


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,  # Bcrypt limit
        description="Password (8-72 characters, must contain uppercase, lowercase, and digit)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength requirements
        
        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - Maximum 72 characters (bcrypt limit)
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if len(v) > 72:
            raise ValueError('Password must not exceed 72 characters (bcrypt limit)')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123"
            }
        }
    }


class UserResponse(BaseModel):
    """Schema for user data in responses"""
    user_id: UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "is_active": True,
                "created_at": "2024-11-30T10:00:00",
                "updated_at": "2024-11-30T10:00:00"
            }
        }
    }


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    }


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    token_type: str = "bearer"
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }
    }


class LoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "is_active": True,
                    "created_at": "2024-11-30T10:00:00",
                    "updated_at": "2024-11-30T10:00:00"
                }
            }
        }
    }


class TokenData(BaseModel):
    """Schema for decoded token data"""
    user_id: Optional[str] = None