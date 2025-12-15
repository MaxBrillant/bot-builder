"""
Flow Model
Stores flow definitions with ownership
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from app.database import Base


class Flow(Base):
    """
    Flow definition model
    
    Table: flows
    
    Identity System:
        id: UUID - System-generated primary key (immutable, globally unique)
        name: string - User-provided name (mutable, unique per bot, max 96 chars)
    
    Fields:
        id: System-generated UUID (primary key, globally unique)
        name: User-provided flow name (unique per bot)
        bot_id: Bot this flow belongs to (FK to bots)
        flow_definition: Complete flow JSON (JSONB)
        trigger_keywords: Array of keywords that activate flow (JSONB)
        created_at: Flow creation timestamp
        updated_at: Last update timestamp
    
    Indexes:
        - id (primary key index)
        - name (for querying by user-provided name)
        - bot_id (for querying bot's flows)
        - trigger_keywords (GIN index for keyword search)
        - updated_at (for sorting)
    
    Constraints:
        - Primary key on 'id' (UUID)
        - Unique (name, bot_id) - name unique per bot
        - Foreign key to bots(bot_id) with CASCADE delete
    """
    
    __tablename__ = "flows"
    
    # PRIMARY KEY: System-generated UUID (immutable, globally unique)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # USER-PROVIDED NAME: Unique per bot (mutable)
    name = Column(String(96), nullable=False, index=True)
    
    # Bot relationship
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.bot_id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Flow definition and metadata
    flow_definition = Column(JSONB, nullable=False)
    trigger_keywords = Column(JSONB, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)
    
    __table_args__ = (
        # Name must be unique within bot (not globally)
        UniqueConstraint('name', 'bot_id', name='unique_flow_name_per_bot'),
        # GIN index for trigger keyword searches
        Index('idx_flows_keywords', 'trigger_keywords', postgresql_using='gin'),
    )

    # Relationships
    bot = relationship("Bot", back_populates="flows")
    sessions = relationship(
        "Session",
        back_populates="flow",
        lazy="noload"  # Don't load by default (too many)
    )

    def __repr__(self):
        return f"<Flow(id='{self.id}', name='{self.name}', bot_id='{self.bot_id}')>"
    
    def to_dict(self, include_definition: bool = True):
        """
        Convert model to dictionary
        
        Args:
            include_definition: Whether to include full flow definition
        
        Returns:
            Dictionary representation
        """
        result = {
            "flow_id": str(self.id),
            "flow_name": self.name,
            "bot_id": str(self.bot_id) if self.bot_id else None,
            "trigger_keywords": self.trigger_keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_definition:
            result["flow_definition"] = self.flow_definition
        
        return result