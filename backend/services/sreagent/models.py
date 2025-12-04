"""Database models for SRE Agent."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ModelSettings(Base):
    """Model configuration settings stored in database."""
    
    __tablename__ = "model_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    model_provider = Column(String(50), nullable=False)  # e.g., "openai", "gemini"
    model_name = Column(String(100), nullable=False)  # e.g., "gpt-4", "gemini-2.0-flash"
    api_key = Column(Text, nullable=False)  # Encrypted API key
    max_tokens = Column(Integer, nullable=True)  # Optional token limit
    temperature = Column(Float, nullable=True)  # Optional temperature (0.0-2.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(100), nullable=True)  # Admin user who updated
    
    def __repr__(self):
        return f"<ModelSettings(id={self.id}, provider={self.model_provider}, model={self.model_name})>"


class User(Base):
    """User account for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hashed password
    role = Column(String(20), nullable=False, default="user")  # "admin" or "user"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    api_tokens = relationship("ApiToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class ApiToken(Base):
    """Long-lived API tokens for programmatic access."""
    
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)  # Hashed token value
    name = Column(String(100), nullable=False)  # User-friendly name for the token
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # None = no expiration
    
    # Relationship
    user = relationship("User", back_populates="api_tokens")
    
    def __repr__(self):
        return f"<ApiToken(id={self.id}, user_id={self.user_id}, name={self.name})>"


class Session(Base):
    """Session tokens for web authentication."""
    
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # Absolute expiration
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"

