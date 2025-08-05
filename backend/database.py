"""
SQLite Database Configuration and Models for WATCHTOWER
"""
import sqlite3
import aiosqlite
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime
import uuid
import json
import os
from pathlib import Path

# Configuration loader
def load_config():
    """Load configuration from config.txt file"""
    config = {}
    config_file = Path(__file__).parent.parent / 'config.txt'
    
    if not config_file.exists():
        raise FileNotFoundError("config.txt file not found")
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    
    return config

# Load configuration
CONFIG = load_config()

# Database setup
DATABASE_PATH = CONFIG.get('DB_PATH', 'watchtower.db')
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base class for models
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vp_number = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String)
    role = Column(String)  # general_duties, sergeant, inspector, admin
    station = Column(String)  # geelong, corio
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Member(Base):
    __tablename__ = "members"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    vp_number = Column(String, unique=True, index=True)
    name = Column(String)
    email = Column(String)
    station = Column(String)
    rank = Column(String, default="Constable")
    seniority_years = Column(Integer, default=0)
    special_qualifications = Column(Text)  # JSON string of qualifications
    ostt_qualification_date = Column(DateTime)  # OSTT qualification date
    ada_driver_authority = Column(Boolean, default=False)  # ADA driver authority
    preferences_json = Column(Text)  # JSON string of preferences
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    shifts = relationship("Shift", back_populates="member")

class Shift(Base):
    __tablename__ = "shifts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(String, ForeignKey("members.id"))
    shift_type = Column(String)  # early, late, night, van, watchhouse, corro
    date = Column(DateTime)
    start_time = Column(String)
    end_time = Column(String)
    overtime_hours = Column(Float, default=0.0)
    was_recalled = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="shifts")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String)
    action = Column(String)
    target_type = Column(String)
    target_id = Column(String)
    changes_json = Column(Text)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)

class RosterPeriod(Base):
    __tablename__ = "roster_periods"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String, default="draft")  # draft, published, approved, archived
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)
    station = Column(String)
    
    # Relationships
    assignments = relationship("ShiftAssignment", back_populates="roster_period")

class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    roster_period_id = Column(String, ForeignKey("roster_periods.id"))
    member_id = Column(String)
    date = Column(DateTime)
    shift_type = Column(String)
    start_time = Column(String)
    end_time = Column(String)
    hours = Column(Float, default=8.0)
    is_overtime = Column(Boolean, default=False)
    assigned_by = Column(String, default="system")
    assignment_reason = Column(String, default="automatic")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    roster_period = relationship("RosterPeriod", back_populates="assignments")

class RosterPublication(Base):
    __tablename__ = "roster_publications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    station = Column(String)
    roster_period_start = Column(DateTime)
    roster_period_end = Column(DateTime)
    publication_date = Column(DateTime)
    published_by = Column(String)
    days_in_advance = Column(Integer)
    compliance_status = Column(String)  # compliant, warning, violation
    created_at = Column(DateTime, default=datetime.utcnow)

class PublicationAlert(Base):
    __tablename__ = "publication_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    station = Column(String)
    roster_period_start = Column(DateTime)
    alert_type = Column(String)  # approaching_deadline, deadline_missed
    days_remaining = Column(Integer)
    message = Column(String)
    acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = Column(String)
    request_type = Column(String)  # annual_leave, rest_day, sick_leave
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    is_urgent = Column(Boolean, default=False)
    reason = Column(Text)
    status = Column(String, default="pending")  # pending, approved, denied
    approved_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database session management
async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Helper functions for data conversion
def dict_to_model(model_class, data_dict):
    """Convert dictionary to SQLAlchemy model instance"""
    # Filter out keys that don't exist in the model
    valid_keys = {c.name for c in model_class.__table__.columns}
    filtered_data = {k: v for k, v in data_dict.items() if k in valid_keys}
    return model_class(**filtered_data)

def model_to_dict(model_instance):
    """Convert SQLAlchemy model instance to dictionary"""
    result = {}
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        result[column.name] = value
    return result