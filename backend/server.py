from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, or_, func
from database import (
    CONFIG, init_database, get_db, AsyncSessionLocal,
    User, Member, Shift, AuditLog, RosterPeriod, ShiftAssignment, 
    RosterPublication, PublicationAlert, LeaveRequest,
    model_to_dict, dict_to_model
)
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
import hashlib
from enum import Enum
import json
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the main app
app = FastAPI(title="WATCHTOWER - Victoria Police Fatigue & Fairness Module", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
JWT_SECRET = CONFIG.get('JWT_SECRET', 'watchtower_secret_key_2025')

# Enums
class UserRole(str, Enum):
    GENERAL_DUTIES = "general_duties"
    SERGEANT = "sergeant"
    INSPECTOR = "inspector"
    ADMIN = "admin"

class ShiftType(str, Enum):
    EARLY = "early"
    LATE = "late"
    NIGHT = "night"
    VAN = "van"
    WATCHHOUSE = "watchhouse"
    CORRO = "corro"

class Station(str, Enum):
    GEELONG = "geelong"
    CORIO = "corio"

# Pydantic Models
class UserLogin(BaseModel):
    vp_number: str
    password: str

class UserCreate(BaseModel):
    vp_number: str
    name: str
    email: str
    role: UserRole
    station: Station
    password: str

class MemberPreferences(BaseModel):
    night_shift_tolerance: int = Field(default=2, description="Max night shifts per month")
    recall_willingness: bool = Field(default=True, description="Willing for out-of-hours recall")
    avoid_consecutive_doubles: bool = Field(default=True)
    avoid_four_earlies: bool = Field(default=True)
    medical_limitations: Optional[str] = None
    welfare_notes: Optional[str] = None
    preferred_rest_days: List[str] = Field(default_factory=list)
    emergency_contact: Optional[str] = None

class MemberResponse(BaseModel):
    id: str
    vp_number: str
    name: str
    email: str
    station: str
    rank: str = "Constable"
    seniority_years: int = 0
    preferences: MemberPreferences = Field(default_factory=MemberPreferences)
    active: bool = True
    created_at: datetime
    updated_at: datetime

class ShiftResponse(BaseModel):
    id: str
    member_id: str
    shift_type: ShiftType
    date: datetime
    start_time: str
    end_time: str
    overtime_hours: float = 0.0
    was_recalled: bool = False
    notes: Optional[str] = None
    created_at: datetime

class EBACompliance(BaseModel):
    member_id: str
    fortnight_hours: float
    consecutive_shifts_without_break: int
    last_break_duration: Optional[float] = None
    compliance_status: str  # "compliant", "warning", "violation"
    violations: List[str] = []
    warnings: List[str] = []
    last_check: datetime = Field(default_factory=datetime.utcnow)

class RosterGenerationConfig(BaseModel):
    station: Station
    period_weeks: int = 2
    min_van_coverage: int = 2
    min_watchhouse_coverage: int = 1
    max_consecutive_nights: int = 7
    min_rest_days_per_fortnight: int = 4
    max_fortnight_hours: float = 76.0
    enable_fatigue_balancing: bool = True
    enable_preference_weighting: bool = True
    corro_rotation_priority: bool = True

# Authentication functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(user_id: str, role: str):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# EBA Compliance functions
def calculate_shift_hours(shift_dict):
    """Calculate hours for a shift"""
    base_hours = 8  # Standard shift length
    return base_hours + shift_dict.get("overtime_hours", 0)

def check_10_hour_break(shifts_sorted):
    """Check if there's at least 10 hours between consecutive shifts"""
    violations = []
    for i in range(1, len(shifts_sorted)):
        prev_shift = shifts_sorted[i-1]
        curr_shift = shifts_sorted[i]
        
        time_diff = (curr_shift["date"] - prev_shift["date"]).total_seconds() / 3600
        
        if time_diff < 10:
            violations.append(f"Only {time_diff:.1f}h break between shifts on {curr_shift['date'].strftime('%Y-%m-%d')}")
    
    return violations

def check_76_hour_fortnight(member_id, shifts):
    """Check if member exceeds 76 hours in any 14-day period"""
    violations = []
    shifts_sorted = sorted(shifts, key=lambda x: x["date"])
    
    for i in range(len(shifts_sorted)):
        start_date = shifts_sorted[i]["date"]
        end_date = start_date + timedelta(days=14)
        
        fortnight_shifts = [s for s in shifts_sorted if start_date <= s["date"] < end_date]
        total_hours = sum(calculate_shift_hours(s) for s in fortnight_shifts)
        
        if total_hours > 76:
            violations.append(f"Exceeded 76h limit: {total_hours:.1f}h in fortnight starting {start_date.strftime('%Y-%m-%d')}")
    
    return violations

def check_night_shift_recovery(shifts_sorted):
    """Check if member needs recovery after 7 consecutive night shifts"""
    violations = []
    warnings = []
    consecutive_nights = 0
    
    for i, shift in enumerate(shifts_sorted):
        if shift.get("shift_type") == "night":
            consecutive_nights += 1
            
            if consecutive_nights == 6:
                warnings.append(f"Approaching 7 consecutive night shifts - recovery period required after next night shift")
            
            if consecutive_nights >= 7:
                if i + 1 < len(shifts_sorted):
                    next_shift = shifts_sorted[i + 1]
                    time_to_next = (next_shift["date"] - shift["date"]).total_seconds() / 3600
                    
                    if time_to_next < 24:
                        violations.append(f"7+ consecutive night shifts without 24h recovery - ended {shift['date'].strftime('%Y-%m-%d')}")
                else:
                    violations.append(f"Currently working {consecutive_nights} consecutive night shifts - immediate 24h recovery required")
        else:
            consecutive_nights = 0
    
    return violations, warnings

async def check_eba_compliance(member_id: str, session):
    """Check all EBA compliance rules for a member"""
    four_weeks_ago = datetime.utcnow() - timedelta(weeks=4)
    
    # Get shifts from database
    result = await session.execute(
        select(Shift).where(
            and_(
                Shift.member_id == member_id,
                Shift.date >= four_weeks_ago
            )
        )
    )
    shift_records = result.scalars().all()
    
    if not shift_records:
        return EBACompliance(
            member_id=member_id,
            fortnight_hours=0,
            consecutive_shifts_without_break=0,
            compliance_status="compliant",
            violations=[],
            warnings=[]
        )
    
    # Convert to dict format for existing logic
    shifts = [model_to_dict(shift) for shift in shift_records]
    
    # Convert string dates to datetime objects if needed
    for shift in shifts:
        if isinstance(shift['date'], str):
            shift['date'] = datetime.fromisoformat(shift['date'].replace('Z', '+00:00'))
    
    shifts_sorted = sorted(shifts, key=lambda x: x["date"])
    
    # Check all EBA compliance rules
    fortnight_violations = check_76_hour_fortnight(member_id, shifts)
    break_violations = check_10_hour_break(shifts_sorted)
    night_violations, night_warnings = check_night_shift_recovery(shifts_sorted)
    
    # Calculate current fortnight hours (last 14 days)
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    recent_shifts = [s for s in shifts if s["date"] >= two_weeks_ago]
    current_fortnight_hours = sum(calculate_shift_hours(s) for s in recent_shifts)
    
    # Combine all violations and warnings
    all_violations = fortnight_violations + break_violations + night_violations
    all_warnings = night_warnings
    
    # Add existing warnings for approaching limits
    if current_fortnight_hours > 65:
        all_warnings.append(f"Approaching 76h limit: currently at {current_fortnight_hours:.1f}h this fortnight")
    
    if current_fortnight_hours > 80:
        all_warnings.append("URGENT: Exceeding safe working hours")
    
    # Determine status
    if all_violations:
        status = "violation"
    elif all_warnings:
        status = "warning"
    else:
        status = "compliant"
    
    return EBACompliance(
        member_id=member_id,
        fortnight_hours=current_fortnight_hours,
        consecutive_shifts_without_break=0,
        compliance_status=status,
        violations=all_violations,
        warnings=all_warnings
    )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            return model_to_dict(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Authentication routes
@api_router.post("/auth/login")
async def login(user_login: UserLogin):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.vp_number == user_login.vp_number.upper())
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(user_login.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_access_token(user.id, user.role)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role,
                "station": user.station
            }
        }

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.vp_number == user_data.vp_number)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create new user
        new_user = User(
            id=str(uuid.uuid4()),
            vp_number=user_data.vp_number,
            name=user_data.name,
            email=user_data.email,
            role=user_data.role.value,
            station=user_data.station.value,
            password_hash=hash_password(user_data.password)
        )
        
        session.add(new_user)
        
        # Also create member profile
        new_member = Member(
            id=str(uuid.uuid4()),
            vp_number=user_data.vp_number,
            name=user_data.name,
            email=user_data.email,
            station=user_data.station.value,
            rank="Constable",
            seniority_years=0,
            preferences_json=json.dumps(MemberPreferences().dict())
        )
        
        session.add(new_member)
        await session.commit()
        
        return {"message": "User created successfully"}

# Member management routes
@api_router.get("/members", response_model=List[MemberResponse])
async def get_members(current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Member))
        members = result.scalars().all()
        
        response_members = []
        for member in members:
            member_dict = model_to_dict(member)
            if member.preferences_json:
                try:
                    member_dict['preferences'] = json.loads(member.preferences_json)
                except:
                    member_dict['preferences'] = MemberPreferences().dict()
            else:
                member_dict['preferences'] = MemberPreferences().dict()
            response_members.append(MemberResponse(**member_dict))
        
        return response_members

@api_router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(member_id: str, current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        member_dict = model_to_dict(member)
        if member.preferences_json:
            try:
                member_dict['preferences'] = json.loads(member.preferences_json)
            except:
                member_dict['preferences'] = MemberPreferences().dict()
        else:
            member_dict['preferences'] = MemberPreferences().dict()
            
        return MemberResponse(**member_dict)

@api_router.put("/members/{member_id}/preferences")
async def update_member_preferences(
    member_id: str, 
    preferences: MemberPreferences, 
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        member.preferences_json = json.dumps(preferences.dict())
        member.updated_at = datetime.utcnow()
        
        await session.commit()
        
        # Log the change
        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=current_user["id"],
            action="update_preferences",
            target_type="member",
            target_id=member_id,
            changes_json=json.dumps(preferences.dict())
        )
        session.add(audit_log)
        await session.commit()
        
        return {"message": "Preferences updated successfully"}

@api_router.get("/shifts", response_model=List[ShiftResponse])
async def get_shifts(
    member_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user)
):
    async with AsyncSessionLocal() as session:
        query = select(Shift)
        conditions = []
        
        if member_id:
            conditions.append(Shift.member_id == member_id)
        if start_date:
            conditions.append(Shift.date >= start_date)
        if end_date:
            conditions.append(Shift.date <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        result = await session.execute(query)
        shifts = result.scalars().all()
        
        return [ShiftResponse(**model_to_dict(shift)) for shift in shifts]

@api_router.post("/shifts", response_model=ShiftResponse)
async def create_shift(
    shift_data: dict,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    async with AsyncSessionLocal() as session:
        new_shift = Shift(
            id=str(uuid.uuid4()),
            **shift_data
        )
        
        session.add(new_shift)
        await session.commit()
        
        return ShiftResponse(**model_to_dict(new_shift))

# Initialize sample data
@api_router.post("/init-sample-data")
async def initialize_sample_data():
    """Initialize the database with sample data for demo purposes"""
    try:
        async with AsyncSessionLocal() as session:
            # Check if data already exists
            result = await session.execute(select(func.count(User.id)))
            user_count = result.scalar()
            
            if user_count > 0:
                return {"message": "Sample data already exists"}
            
            # Parse demo users from config
            
            # Parse demo users
            demo_users = []
            for i in range(1, 4):
                user_key = f'DEMO_USER_{i}'
                if user_key in CONFIG:
                    parts = CONFIG[user_key].split(':')
                    if len(parts) >= 8:
                        demo_users.append({
                            'vp_number': parts[0],
                            'password': parts[1],
                            'name': parts[2],
                            'email': parts[3],
                            'role': parts[4],
                            'station': parts[5],
                            'rank': parts[6],
                            'seniority_years': int(parts[7])
                        })
            
            # Create users and members
            for user_data in demo_users:
                # Create user
                user = User(
                    id=str(uuid.uuid4()),
                    vp_number=user_data['vp_number'],
                    name=user_data['name'],
                    email=user_data['email'],
                    role=user_data['role'],
                    station=user_data['station'],
                    password_hash=hash_password(user_data['password'])
                )
                session.add(user)
                
                # Create member
                member = Member(
                    id=str(uuid.uuid4()),
                    vp_number=user_data['vp_number'],
                    name=user_data['name'],
                    email=user_data['email'],
                    station=user_data['station'],
                    rank=user_data['rank'],
                    seniority_years=user_data['seniority_years'],
                    preferences_json=json.dumps(MemberPreferences().dict())
                )
                session.add(member)
            
            await session.commit()
            
            # Create sample shifts for demonstration
            await create_sample_shifts(session)
            await session.commit()
            
            logger.info("Sample data initialized successfully")
            return {"message": "Sample data initialized successfully"}
            
    except Exception as e:
        logger.error(f"Failed to initialize sample data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize sample data: {str(e)}")

async def create_sample_shifts(session):
    """Create sample shifts for demo purposes"""
    # Get members
    result = await session.execute(select(Member))
    members = result.scalars().all()
    
    if not members:
        return
    
    # Create shifts for the last 4 weeks
    import random
    
    shift_types = ["early", "late", "night", "van", "watchhouse", "corro"]
    start_date = datetime.utcnow() - timedelta(weeks=4)
    
    for member in members:
        for week in range(4):
            for day in range(7):
                # Create some shifts (not every day)
                if random.random() < 0.7:  # 70% chance of having a shift
                    shift_date = start_date + timedelta(weeks=week, days=day)
                    shift_type = random.choice(shift_types)
                    
                    # Create shift
                    shift = Shift(
                        id=str(uuid.uuid4()),
                        member_id=member.id,
                        shift_type=shift_type,
                        date=shift_date,
                        start_time="06:00" if shift_type == "early" else "14:00" if shift_type == "late" else "22:00",
                        end_time="14:00" if shift_type == "early" else "22:00" if shift_type == "late" else "06:00",
                        overtime_hours=random.uniform(0, 4) if random.random() < 0.3 else 0,
                        was_recalled=random.random() < 0.1  # 10% chance of recall
                    )
                    session.add(shift)

# Analytics routes (continuing from the MongoDB version but adapted for SQLite)
@api_router.get("/analytics/workload-summary")
async def get_workload_summary(current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
        
        # Get all members
        members_result = await session.execute(select(Member))
        members = members_result.scalars().all()
        
        result = []
        for member in members:
            # Get shifts for this member
            shifts_result = await session.execute(
                select(Shift).where(
                    and_(
                        Shift.member_id == member.id,
                        Shift.date >= eight_weeks_ago
                    )
                )
            )
            shifts = shifts_result.scalars().all()
            
            if not shifts:
                continue
            
            # Calculate statistics
            total_shifts = len(shifts)
            van_shifts = len([s for s in shifts if s.shift_type == "van"])
            watchhouse_shifts = len([s for s in shifts if s.shift_type == "watchhouse"])
            night_shifts = len([s for s in shifts if s.shift_type == "night"])
            corro_shifts = len([s for s in shifts if s.shift_type == "corro"])
            overtime_hours = sum(s.overtime_hours for s in shifts)
            recall_count = len([s for s in shifts if s.was_recalled])
            
            # Get EBA compliance
            compliance = await check_eba_compliance(member.id, session)
            
            result.append({
                "member_id": member.id,
                "member_name": member.name,
                "station": member.station,
                "rank": member.rank,
                "seniority_years": member.seniority_years,
                "stats": {
                    "total_shifts": total_shifts,
                    "van_shifts_pct": round((van_shifts / total_shifts) * 100, 1) if total_shifts > 0 else 0,
                    "watchhouse_shifts_pct": round((watchhouse_shifts / total_shifts) * 100, 1) if total_shifts > 0 else 0,
                    "night_shifts_pct": round((night_shifts / total_shifts) * 100, 1) if total_shifts > 0 else 0,
                    "corro_shifts": corro_shifts,
                    "overtime_hours": overtime_hours,
                    "recall_count": recall_count
                },
                "compliance": {
                    "status": compliance.compliance_status,
                    "fortnight_hours": compliance.fortnight_hours,
                    "violations": compliance.violations,
                    "warnings": compliance.warnings
                }
            })
        
        return result

# Continue with other analytics endpoints... (truncated for length)

@api_router.get("/analytics/corro-distribution")
async def get_corro_distribution(current_user: dict = Depends(get_current_user)):
    async with AsyncSessionLocal() as session:
        four_weeks_ago = datetime.utcnow() - timedelta(weeks=4)
        
        # Get all active members
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        result = []
        for member in members:
            # Get corro shifts for this member
            corro_result = await session.execute(
                select(Shift).where(
                    and_(
                        Shift.member_id == member.id,
                        Shift.shift_type == "corro",
                        Shift.date >= four_weeks_ago
                    )
                ).order_by(Shift.date.desc())
            )
            corro_shifts = corro_result.scalars().all()
            
            last_corro = corro_shifts[0].date if corro_shifts else None
            days_since_corro = None
            if last_corro:
                days_since_corro = (datetime.utcnow() - last_corro).days
            
            result.append({
                "member_id": member.id,
                "member_name": member.name,
                "station": member.station,
                "corro_count_4weeks": len(corro_shifts),
                "last_corro_date": last_corro,
                "days_since_corro": days_since_corro,
                "overdue": days_since_corro is None or days_since_corro > 28
            })
        
        return sorted(result, key=lambda x: x["days_since_corro"] or 999, reverse=True)

@api_router.get("/analytics/eba-violations-detail")
async def get_eba_violations_detail(current_user: dict = Depends(get_current_user)):
    """Get detailed EBA violations breakdown"""
    async with AsyncSessionLocal() as session:
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        violations = []
        for member in members:
            compliance = await check_eba_compliance(member.id, session)
            if compliance.compliance_status == "violation":
                violations.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "station": member.station,
                    "rank": member.rank,
                    "fortnight_hours": compliance.fortnight_hours,
                    "violations": compliance.violations,
                    "urgency": "🚨 URGENT" if compliance.fortnight_hours > 85 else "#1 priority" if compliance.fortnight_hours > 80 else "#2 priority"
                })
        
        # Sort by urgency (highest hours first)
        return sorted(violations, key=lambda x: x["fortnight_hours"], reverse=True)

@api_router.get("/analytics/eba-warnings-detail")
async def get_eba_warnings_detail(current_user: dict = Depends(get_current_user)):
    """Get detailed EBA warnings breakdown"""
    async with AsyncSessionLocal() as session:
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        warnings = []
        for member in members:
            compliance = await check_eba_compliance(member.id, session)
            if compliance.compliance_status == "warning":
                warnings.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "station": member.station,
                    "rank": member.rank,
                    "fortnight_hours": compliance.fortnight_hours,
                    "warnings": compliance.warnings,
                    "urgency": "🚨 URGENT" if compliance.fortnight_hours > 70 else "#1 priority" if compliance.fortnight_hours > 68 else "#2 priority"
                })
        
        return sorted(warnings, key=lambda x: x["fortnight_hours"], reverse=True)

@api_router.get("/analytics/eba-compliant-members")
async def get_eba_compliant_members(current_user: dict = Depends(get_current_user)):
    """Get members who are EBA compliant"""
    async with AsyncSessionLocal() as session:
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        compliant = []
        for member in members:
            compliance = await check_eba_compliance(member.id, session)
            if compliance.compliance_status == "compliant":
                compliant.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "station": member.station,
                    "rank": member.rank,
                    "fortnight_hours": compliance.fortnight_hours
                })
        
        return sorted(compliant, key=lambda x: x["member_name"])

@api_router.get("/analytics/over-76-hours")
async def get_over_76_hours(current_user: dict = Depends(get_current_user)):
    """Get members over 76 hours"""
    async with AsyncSessionLocal() as session:
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        over_76 = []
        for member in members:
            compliance = await check_eba_compliance(member.id, session)
            if compliance.fortnight_hours > 76:
                over_76.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "station": member.station,
                    "rank": member.rank,
                    "fortnight_hours": compliance.fortnight_hours,
                    "urgency": "🚨 URGENT" if compliance.fortnight_hours > 85 else "#1 priority"
                })
        
        return sorted(over_76, key=lambda x: x["fortnight_hours"], reverse=True)

@api_router.get("/analytics/approaching-76-hours")
async def get_approaching_76_hours(current_user: dict = Depends(get_current_user)):
    """Get members approaching 76 hours (65-76h range)"""
    async with AsyncSessionLocal() as session:
        members_result = await session.execute(select(Member).where(Member.active == True))
        members = members_result.scalars().all()
        
        approaching = []
        for member in members:
            compliance = await check_eba_compliance(member.id, session)
            if 65 <= compliance.fortnight_hours <= 76:
                approaching.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "station": member.station,
                    "rank": member.rank,
                    "fortnight_hours": compliance.fortnight_hours,
                    "urgency": "#1 priority" if compliance.fortnight_hours > 72 else "#2 priority"
                })
        
        return sorted(approaching, key=lambda x: x["fortnight_hours"], reverse=True)

@api_router.get("/members/{member_id}/detailed-view")
async def get_detailed_member_view(member_id: str, current_user: dict = Depends(get_current_user)):
    """Get comprehensive detailed view for a member"""
    async with AsyncSessionLocal() as session:
        # Get member
        member_result = await session.execute(select(Member).where(Member.id == member_id))
        member = member_result.scalar_one_or_none()
        
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        # Get member's shifts (last 12 weeks for comprehensive view)
        twelve_weeks_ago = datetime.utcnow() - timedelta(weeks=12)
        shifts_result = await session.execute(
            select(Shift).where(
                and_(
                    Shift.member_id == member_id,
                    Shift.date >= twelve_weeks_ago
                )
            ).order_by(Shift.date.desc())
        )
        shifts = shifts_result.scalars().all()
        
        # Get EBA compliance
        compliance = await check_eba_compliance(member_id, session)
        
        # Parse preferences
        preferences = {}
        if member.preferences_json:
            try:
                preferences = json.loads(member.preferences_json)
            except:
                preferences = MemberPreferences().dict()
        
        # Calculate shift breakdown (weekly hours for last 12 weeks)
        shift_breakdown = []
        for week in range(12):
            week_start = datetime.utcnow() - timedelta(weeks=week+1)
            week_end = week_start + timedelta(days=7)
            
            week_shifts = [s for s in shifts if week_start <= s.date < week_end]
            total_hours = sum(calculate_shift_hours(model_to_dict(s)) for s in week_shifts)
            
            shift_breakdown.append({
                "week": f"Week {12-week}",
                "start_date": week_start.strftime('%Y-%m-%d'),
                "total_hours": total_hours,
                "shift_count": len(week_shifts),
                "shift_types": list(set(s.shift_type for s in week_shifts))
            })
        
        return {
            "member_info": {
                "id": member.id,
                "name": member.name,
                "vp_number": member.vp_number,
                "rank": member.rank,
                "station": member.station,
                "seniority_years": member.seniority_years,
                "email": member.email
            },
            "shift_breakdown": shift_breakdown,
            "eba_compliance_history": {
                "current_status": compliance.compliance_status,
                "fortnight_hours": compliance.fortnight_hours,
                "violations_count": len(compliance.violations),
                "warnings_count": len(compliance.warnings),
                "violations": compliance.violations,
                "warnings": compliance.warnings,
                "compliance_trend": "improving"  # Could be calculated from historical data
            },
            "member_preferences": preferences,
            "activity_log": [
                {
                    "date": shift.date.strftime('%Y-%m-%d'),
                    "action": f"Worked {shift.shift_type} shift",
                    "hours": calculate_shift_hours(model_to_dict(shift)),
                    "overtime": shift.overtime_hours > 0
                }
                for shift in shifts[:20]  # Last 20 activities
            ],
            "fatigue_risk_projection": {
                "current_risk_level": "high" if compliance.fortnight_hours > 70 else "medium" if compliance.fortnight_hours > 50 else "low",
                "risk_factors": [
                    f"Current fortnight hours: {compliance.fortnight_hours:.1f}h",
                    f"Recent overtime: {sum(s.overtime_hours for s in shifts[:14]):.1f}h",
                    f"Night shifts this month: {len([s for s in shifts if s.shift_type == 'night' and s.date >= datetime.utcnow() - timedelta(days=30)])}"
                ],
                "recommendations": [
                    "Monitor weekly hours closely",
                    "Ensure adequate rest periods",
                    "Consider reducing overtime assignments"
                ]
            },
            "schedule_request_history": [],  # Placeholder for leave requests
            "equity_tracking": {
                "corro_assignments_3months": len([s for s in shifts if s.shift_type == "corro" and s.date >= datetime.utcnow() - timedelta(days=90)]),
                "overtime_hours_3months": sum(s.overtime_hours for s in shifts if s.date >= datetime.utcnow() - timedelta(days=90)),
                "fairness_score": min(100, max(0, 100 - abs(compliance.fortnight_hours - 50))),  # Simple fairness calculation
                "weekend_assignments": len([s for s in shifts if s.date.weekday() >= 5])
            }
        }

# Add router to app
app.include_router(api_router)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_database()
    logger.info("Database initialized")

# Root endpoint
@app.get("/")
async def root():
    return {"message": "WATCHTOWER API v2.0 - SQLite Edition"}

@app.get("/config")
async def get_config():
    """Provide frontend configuration"""
    return {
        "backend_url": CONFIG.get('BACKEND_URL', 'http://localhost:8001')
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)