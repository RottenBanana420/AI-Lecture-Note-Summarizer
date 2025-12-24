"""
User model for authentication and user management.

This module defines the User model which stores user identification,
authentication information, and manages relationships with documents.
"""

from sqlalchemy import Column, String, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base_model import BaseModelMixin


class User(Base, BaseModelMixin):
    """
    User model for storing user authentication and profile information.
    
    Attributes:
        id: Primary key (inherited from BaseModelMixin)
        username: Unique username for login
        email: Unique email address
        hashed_password: Bcrypt hashed password
        full_name: User's full name (optional)
        is_active: Whether the user account is active
        is_superuser: Whether the user has admin privileges
        created_at: Account creation timestamp (inherited)
        updated_at: Last update timestamp (inherited)
        
    Relationships:
        documents: One-to-many relationship with Document model
    """
    
    __tablename__ = "users"
    
    # User identification and authentication
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username for authentication"
    )
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address"
    )
    hashed_password = Column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password"
    )
    
    # User profile information
    full_name = Column(
        String(100),
        nullable=True,
        comment="User's full name"
    )
    
    # User status flags
    is_active = Column(
        String(1),  # Using String for boolean to ensure compatibility
        nullable=False,
        server_default="1",
        comment="Whether the user account is active"
    )
    is_superuser = Column(
        String(1),  # Using String for boolean to ensure compatibility
        nullable=False,
        server_default="0",
        comment="Whether the user has admin privileges"
    )
    
    # Relationships
    documents = relationship(
        "Document",
        back_populates="owner",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="dynamic",
        doc="Documents uploaded by this user"
    )
    
    # Indexes and constraints for performance and data integrity
    __table_args__ = (
        Index("ix_users_username_email", "username", "email"),
        # CHECK constraints to prevent empty strings
        CheckConstraint("length(username) > 0", name="ck_users_username_not_empty"),
        CheckConstraint("length(email) > 0", name="ck_users_email_not_empty"),
        # CHECK constraints for boolean fields (must be '0' or '1')
        CheckConstraint("is_active IN ('0', '1')", name="ck_users_is_active_valid"),
        CheckConstraint("is_superuser IN ('0', '1')", name="ck_users_is_superuser_valid"),
        {"comment": "Users table for authentication and user management"},
    )
    
    def __repr__(self):
        """String representation of the User instance."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def is_active_bool(self):
        """Convert is_active string to boolean."""
        return self.is_active == "1"
    
    @property
    def is_superuser_bool(self):
        """Convert is_superuser string to boolean."""
        return self.is_superuser == "1"
