from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
import hashlib
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="WATCHTOWER - Victoria Police Fatigue & Fairness Module", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
JWT_SECRET = "watchtower_secret_key_2025"  # In production, use environment variable

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

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vp_number: str
    name: str
    email: str
    role: UserRole
    station: Station
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

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

class Member(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vp_number: str
    name: str
    email: str
    station: Station
    rank: str = "Constable"
    seniority_years: int = 0
    preferences: MemberPreferences = Field(default_factory=MemberPreferences)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Shift(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    member_id: str
    shift_type: ShiftType
    date: datetime
    start_time: str
    end_time: str
    overtime_hours: float = 0.0
    was_recalled: bool = False
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    action: str
    target_type: str  # "member", "shift", "preference"
    target_id: str
    changes: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EBACompliance(BaseModel):
    member_id: str
    fortnight_hours: float
    consecutive_shifts_without_break: int
    last_break_duration: Optional[float] = None  # Hours between shifts
    compliance_status: str  # "compliant", "warning", "violation"
    violations: List[str] = []
    warnings: List[str] = []
    last_check: datetime = Field(default_factory=datetime.utcnow)

class RosterPublication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    station: Station
    roster_period_start: datetime
    roster_period_end: datetime
    publication_date: datetime
    published_by: str
    days_in_advance: int
    compliance_status: str  # "compliant", "warning", "violation"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PublicationAlert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    station: Station
    roster_period_start: datetime
    alert_type: str  # "approaching_deadline", "deadline_missed"
    days_remaining: int
    message: str
    acknowledged: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LeaveRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    member_id: str
    request_type: str  # "annual_leave", "rest_day", "sick_leave"
    start_date: datetime
    end_date: datetime
    is_urgent: bool = False
    reason: Optional[str] = None
    status: str = "pending"  # "pending", "approved", "denied"
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Automated Roster Producer Models
class RosterPeriod(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_date: datetime
    end_date: datetime
    status: str = "draft"  # "draft", "published", "approved", "archived"
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    station: Station

class ShiftAssignment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    roster_period_id: str
    member_id: str
    date: datetime
    shift_type: ShiftType
    start_time: str  # "06:00", "14:00", "22:00"
    end_time: str
    hours: float = 8.0
    is_overtime: bool = False
    assigned_by: str = "system"  # "system" or user_id
    assignment_reason: str = "automatic"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RosterConstraint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    roster_period_id: str
    constraint_type: str  # "min_coverage", "max_hours", "rest_requirement"
    shift_type: Optional[ShiftType] = None
    date: Optional[datetime] = None
    minimum_staff: Optional[int] = None
    maximum_hours: Optional[float] = None
    description: str
    is_mandatory: bool = True

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
def calculate_shift_hours(shift):
    """Calculate hours for a shift"""
    # Simple calculation - in reality would parse start/end times properly
    base_hours = 8  # Standard shift length
    return base_hours + shift.get("overtime_hours", 0)

def check_10_hour_break(shifts_sorted):
    """Check if there's at least 10 hours between consecutive shifts"""
    violations = []
    for i in range(1, len(shifts_sorted)):
        prev_shift = shifts_sorted[i-1]
        curr_shift = shifts_sorted[i]
        
        # Calculate time between shifts (simplified)
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
        
        # Get shifts in this 14-day window
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
            
            # Flag if approaching 7 consecutive nights
            if consecutive_nights == 6:
                warnings.append(f"Approaching 7 consecutive night shifts - recovery period required after next night shift")
            
            # Violation if exceeding 7 consecutive nights without recovery
            if consecutive_nights >= 7:
                # Check if next shift provides 24-hour recovery
                if i + 1 < len(shifts_sorted):
                    next_shift = shifts_sorted[i + 1]
                    time_to_next = (next_shift["date"] - shift["date"]).total_seconds() / 3600
                    
                    if time_to_next < 24:
                        violations.append(f"7+ consecutive night shifts without 24h recovery - ended {shift['date'].strftime('%Y-%m-%d')}")
                else:
                    # Currently in violation - still working nights without recovery
                    violations.append(f"Currently working {consecutive_nights} consecutive night shifts - immediate 24h recovery required")
        else:
            # Reset counter when not a night shift
            consecutive_nights = 0
    
    return violations, warnings

def check_rest_days_compliance(member_id, shifts):
    """Check rest day compliance - 4 rest days per fortnight, 2 consecutive at least 15 times per year"""
    violations = []
    warnings = []
    
    # Create a full calendar of worked days vs rest days
    if not shifts:
        return violations, warnings
    
    shifts_sorted = sorted(shifts, key=lambda x: x["date"])
    start_date = shifts_sorted[0]["date"]
    end_date = shifts_sorted[-1]["date"]
    
    # Create set of worked days
    worked_days = set()
    for shift in shifts:
        worked_days.add(shift["date"].date())
    
    # Check fortnightly rest days (every 14-day period)
    current_date = start_date.date()
    while current_date <= end_date.date():
        fortnight_end = current_date + timedelta(days=13)
        
        # Count rest days in this fortnight
        rest_days_count = 0
        for day_offset in range(14):
            check_date = current_date + timedelta(days=day_offset)
            if check_date not in worked_days and check_date <= end_date.date():
                rest_days_count += 1
        
        if rest_days_count < 4:
            violations.append(f"Only {rest_days_count} rest days in fortnight starting {current_date.strftime('%Y-%m-%d')} (minimum: 4)")
        
        current_date += timedelta(days=14)
    
    # Check for consecutive rest days (simplified check for last 8 weeks)
    consecutive_rest_periods = 0
    consecutive_days = 0
    
    current_date = start_date.date()
    while current_date <= end_date.date():
        if current_date not in worked_days:
            consecutive_days += 1
        else:
            if consecutive_days >= 2:
                consecutive_rest_periods += 1
            consecutive_days = 0
        current_date += timedelta(days=1)
    
    # Final check for any remaining consecutive days
    if consecutive_days >= 2:
        consecutive_rest_periods += 1
    
    # Calculate expected consecutive rest periods for the period
    weeks_covered = (end_date.date() - start_date.date()).days / 7
    expected_periods = int((weeks_covered / 52) * 15)  # 15 per year, scaled to period
    
    if consecutive_rest_periods < expected_periods and weeks_covered > 4:
        warnings.append(f"Only {consecutive_rest_periods} periods of 2+ consecutive rest days (expected ~{expected_periods} for this period)")
    
    return violations, warnings

def check_maximum_working_hours(shifts_sorted):
    """Check 60 hours in 7 days and 48-hour break requirements"""
    violations = []
    warnings = []
    
    for i in range(len(shifts_sorted)):
        week_start = shifts_sorted[i]["date"]
        week_end = week_start + timedelta(days=7)
        
        # Get shifts in this 7-day window
        week_shifts = [s for s in shifts_sorted if week_start <= s["date"] < week_end]
        total_hours = sum(calculate_shift_hours(s) for s in week_shifts)
        
        if total_hours > 60:
            violations.append(f"Exceeded 60h in 7 days: {total_hours:.1f}h starting {week_start.strftime('%Y-%m-%d')}")
            
            # Check if 48-hour break follows
            next_shifts = [s for s in shifts_sorted if s["date"] >= week_end]
            if next_shifts:
                time_to_next = (next_shifts[0]["date"] - week_end).total_seconds() / 3600
                if time_to_next < 48:
                    violations.append(f"No 48h break after exceeding 60h weekly limit")
    
    return violations, warnings

async def check_eba_compliance(member_id):
    """Check all EBA compliance rules for a member"""
    # Get last 4 weeks of shifts
    four_weeks_ago = datetime.utcnow() - timedelta(weeks=4)
    shifts = await db.shifts.find({
        "member_id": member_id,
        "date": {"$gte": four_weeks_ago}
    }).to_list(1000)
    
    if not shifts:
        return EBACompliance(
            member_id=member_id,
            fortnight_hours=0,
            consecutive_shifts_without_break=0,
            compliance_status="compliant",
            violations=[],
            warnings=[]
        )
    
    shifts_sorted = sorted(shifts, key=lambda x: x["date"])
    
    # Check all EBA compliance rules
    fortnight_violations = check_76_hour_fortnight(member_id, shifts)
    break_violations = check_10_hour_break(shifts_sorted)
    
    # NEW Sprint 2 checks
    night_violations, night_warnings = check_night_shift_recovery(shifts_sorted)
    rest_violations, rest_warnings = check_rest_days_compliance(member_id, shifts)
    hours_violations, hours_warnings = check_maximum_working_hours(shifts_sorted)
    
    # Calculate current fortnight hours (last 14 days)
    two_weeks_ago = datetime.utcnow() - timedelta(days=14)
    recent_shifts = [s for s in shifts if s["date"] >= two_weeks_ago]
    current_fortnight_hours = sum(calculate_shift_hours(s) for s in recent_shifts)
    
    # Count consecutive night shifts currently
    consecutive_nights = 0
    for shift in reversed(shifts_sorted):
        if shift.get("shift_type") == "night":
            consecutive_nights += 1
        else:
            break
    
    # Combine all violations and warnings
    all_violations = (fortnight_violations + break_violations + 
                     night_violations + rest_violations + hours_violations)
    all_warnings = (night_warnings + rest_warnings + hours_warnings)
    
    # Add existing warnings for approaching limits
    if current_fortnight_hours > 65:  # Warning at 65+ hours
        all_warnings.append(f"Approaching 76h limit: currently at {current_fortnight_hours:.1f}h this fortnight")
    
    if current_fortnight_hours > 80:  # Severe warning
        all_warnings.append("URGENT: Exceeding safe working hours")
    
    # Add night shift warnings
    if consecutive_nights >= 5:
        all_warnings.append(f"Currently working {consecutive_nights} consecutive night shifts - monitor for recovery needs")
    
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
        consecutive_shifts_without_break=consecutive_nights if consecutive_nights > 0 else len([s for s in shifts_sorted[-5:] if s.get("overtime_hours", 0) > 0]),
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
        
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Authentication routes
@api_router.post("/auth/login")
async def login(user_login: UserLogin):
    # Make VP number case-insensitive
    vp_number = user_login.vp_number.upper()
    user = await db.users.find_one({"vp_number": vp_number})
    if not user or not verify_password(user_login.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user["id"], user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "role": user["role"],
            "station": user["station"]
        }
    }

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"vp_number": user_data.vp_number})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user = User(
        vp_number=user_data.vp_number,
        name=user_data.name,
        email=user_data.email,
        role=user_data.role,
        station=user_data.station,
        password_hash=hash_password(user_data.password)
    )
    
    await db.users.insert_one(user.dict())
    
    # Also create member profile
    member = Member(
        vp_number=user_data.vp_number,
        name=user_data.name,
        email=user_data.email,
        station=user_data.station,
        rank="Constable",
        seniority_years=0
    )
    await db.members.insert_one(member.dict())
    
    return {"message": "User created successfully"}

# Member management routes
@api_router.get("/members", response_model=List[Member])
async def get_members(current_user: dict = Depends(get_current_user)):
    members = await db.members.find().to_list(1000)
    return [Member(**member) for member in members]

@api_router.get("/members/{member_id}", response_model=Member)
async def get_member(member_id: str, current_user: dict = Depends(get_current_user)):
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return Member(**member)

@api_router.put("/members/{member_id}/preferences")
async def update_member_preferences(
    member_id: str, 
    preferences: MemberPreferences, 
    current_user: dict = Depends(get_current_user)
):
    # Check permissions - only sergeants and above can edit preferences
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.members.update_one(
        {"id": member_id},
        {
            "$set": {
                "preferences": preferences.dict(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Log the change
    audit_log = AuditLog(
        user_id=current_user["id"],
        action="update_preferences",
        target_type="member",
        target_id=member_id,
        changes=preferences.dict()
    )
    await db.audit_logs.insert_one(audit_log.dict())
    
    return {"message": "Preferences updated successfully"}

# Shift management routes
@api_router.get("/shifts", response_model=List[Shift])
async def get_shifts(
    member_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if member_id:
        query["member_id"] = member_id
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    shifts = await db.shifts.find(query).to_list(1000)
    return [Shift(**shift) for shift in shifts]

@api_router.post("/shifts", response_model=Shift)
async def create_shift(shift: Shift, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    await db.shifts.insert_one(shift.dict())
    return shift

# Dashboard analytics routes
@api_router.get("/analytics/workload-summary")
async def get_workload_summary(current_user: dict = Depends(get_current_user)):
    # Get last 8 weeks of data
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    
    pipeline = [
        {"$match": {"date": {"$gte": eight_weeks_ago}}},
        {"$group": {
            "_id": "$member_id",
            "total_shifts": {"$sum": 1},
            "van_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "van"]}, 1, 0]}},
            "watchhouse_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "watchhouse"]}, 1, 0]}},
            "night_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "night"]}, 1, 0]}},
            "corro_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "corro"]}, 1, 0]}},
            "overtime_hours": {"$sum": "$overtime_hours"},
            "recall_count": {"$sum": {"$cond": ["$was_recalled", 1, 0]}}
        }}
    ]
    
    workload_data = await db.shifts.aggregate(pipeline).to_list(1000)
    
    # Get member details
    member_ids = [item["_id"] for item in workload_data]
    members = await db.members.find({"id": {"$in": member_ids}}).to_list(1000)
    member_dict = {m["id"]: m for m in members}
    
    # Combine data and add compliance status
    result = []
    for item in workload_data:
        member = member_dict.get(item["_id"], {})
        
        # Get EBA compliance status for this member
        compliance = await check_eba_compliance(item["_id"])
        
        result.append({
            "member_id": item["_id"],
            "member_name": member.get("name", "Unknown"),
            "station": member.get("station", "Unknown"),
            "rank": member.get("rank", "Unknown"),
            "seniority_years": member.get("seniority_years", 0),
            "stats": {
                "total_shifts": item["total_shifts"],
                "van_shifts_pct": round((item["van_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "watchhouse_shifts_pct": round((item["watchhouse_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "night_shifts_pct": round((item["night_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "corro_shifts": item["corro_shifts"],
                "overtime_hours": item["overtime_hours"],
                "recall_count": item["recall_count"]
            },
            "compliance": {
                "status": compliance.compliance_status,
                "fortnight_hours": compliance.fortnight_hours,
                "violations": compliance.violations,
                "warnings": compliance.warnings
            }
        })
    
    return result

@api_router.get("/analytics/corro-distribution")
async def get_corro_distribution(current_user: dict = Depends(get_current_user)):
    # Get last 4 weeks of corro shifts
    four_weeks_ago = datetime.utcnow() - timedelta(weeks=4)
    
    pipeline = [
        {"$match": {"shift_type": "corro", "date": {"$gte": four_weeks_ago}}},
        {"$group": {
            "_id": "$member_id",
            "corro_count": {"$sum": 1},
            "last_corro": {"$max": "$date"}
        }}
    ]
    
    corro_data = await db.shifts.aggregate(pipeline).to_list(1000)
    
    # Get all members and check who hasn't had corro
    all_members = await db.members.find({"active": True}).to_list(1000)
    corro_dict = {item["_id"]: item for item in corro_data}
    
    result = []
    for member in all_members:
        corro_info = corro_dict.get(member["id"], {"corro_count": 0, "last_corro": None})
        days_since_corro = None
        if corro_info["last_corro"]:
            days_since_corro = (datetime.utcnow() - corro_info["last_corro"]).days
        
        result.append({
            "member_id": member["id"],
            "member_name": member["name"],
            "station": member["station"],
            "corro_count_4weeks": corro_info["corro_count"],
            "last_corro_date": corro_info["last_corro"],
            "days_since_corro": days_since_corro,
            "overdue": days_since_corro is None or days_since_corro > 28
        })
    
    return sorted(result, key=lambda x: x["days_since_corro"] or 999, reverse=True)
    
# EBA Compliance routes
@api_router.get("/compliance/{member_id}", response_model=EBACompliance)
async def get_member_compliance(member_id: str, current_user: dict = Depends(get_current_user)):
    """Get EBA compliance status for a specific member"""
    compliance = await check_eba_compliance(member_id)
    return compliance

@api_router.get("/compliance/summary/all")
async def get_compliance_summary(current_user: dict = Depends(get_current_user)):
    """Get compliance summary for all members"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    members = await db.members.find({"active": True}).to_list(1000)
    compliance_summary = []
    
    for member in members:
        compliance = await check_eba_compliance(member["id"])
        compliance_summary.append({
            "member_id": member["id"],
            "member_name": member["name"],
            "station": member["station"],
            "rank": member["rank"],
            "compliance_status": compliance.compliance_status,
            "fortnight_hours": compliance.fortnight_hours,
            "violations_count": len(compliance.violations),
            "warnings_count": len(compliance.warnings),
            "violations": compliance.violations,
            "warnings": compliance.warnings
        })
    
    return compliance_summary

# Roster Publication Tracking (Phase 2 Sprint 3)
@api_router.get("/roster-publications")
async def get_roster_publications(current_user: dict = Depends(get_current_user)):
    """Get roster publication history and compliance"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    publications = await db.roster_publications.find().sort("roster_period_start", -1).to_list(100)
    return [RosterPublication(**pub) for pub in publications]

@api_router.post("/roster-publications", response_model=RosterPublication)
async def create_roster_publication(
    publication: RosterPublication,
    current_user: dict = Depends(get_current_user)
):
    """Create a roster publication record"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    publication.published_by = current_user["id"]
    
    # Calculate days in advance
    days_in_advance = (publication.roster_period_start - publication.publication_date).days
    publication.days_in_advance = days_in_advance
    
    # Determine compliance status based on EBA requirement (4 weeks = 28 days)
    if days_in_advance >= 28:
        publication.compliance_status = "compliant"
    elif days_in_advance >= 21:  # 3 weeks
        publication.compliance_status = "warning"
    else:
        publication.compliance_status = "violation"
    
    await db.roster_publications.insert_one(publication.dict())
    
    # Log the publication
    audit_log = AuditLog(
        user_id=current_user["id"],
        action="publish_roster",
        target_type="roster",
        target_id=publication.id,
        changes={"station": publication.station, "days_in_advance": days_in_advance}
    )
    await db.audit_logs.insert_one(audit_log.dict())
    
    return publication

@api_router.get("/publication-alerts")
async def get_publication_alerts(current_user: dict = Depends(get_current_user)):
    """Get upcoming roster publication deadlines and alerts"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get current alerts from database
    alerts = await db.publication_alerts.find({"acknowledged": False}).to_list(100)
    
    # Generate new alerts for upcoming deadlines
    today = datetime.utcnow().date()
    
    # Check for upcoming 4-week periods that need roster publication
    upcoming_periods = []
    for weeks_ahead in range(1, 8):  # Check next 8 weeks
        period_start = today + timedelta(weeks=weeks_ahead * 4)  # Every 4 weeks
        period_end = period_start + timedelta(days=27)  # 4-week period
        
        # Check if roster already published for this period
        existing_publication = await db.roster_publications.find_one({
            "roster_period_start": {"$gte": datetime.combine(period_start, datetime.min.time())},
            "roster_period_end": {"$lte": datetime.combine(period_end, datetime.max.time())}
        })
        
        if not existing_publication:
            days_until_deadline = (period_start - today).days - 28  # 28 days before period starts
            
            if days_until_deadline <= 7:  # Alert if deadline is within 7 days
                alert_type = "deadline_missed" if days_until_deadline < 0 else "approaching_deadline"
                
                # Create alert if it doesn't exist
                existing_alert = await db.publication_alerts.find_one({
                    "roster_period_start": datetime.combine(period_start, datetime.min.time()),
                    "alert_type": alert_type
                })
                
                if not existing_alert:
                    alert = PublicationAlert(
                        station=Station.GEELONG,  # Default station
                        roster_period_start=datetime.combine(period_start, datetime.min.time()),
                        alert_type=alert_type,
                        days_remaining=max(0, days_until_deadline),
                        message=f"Roster publication {'overdue' if days_until_deadline < 0 else 'due'} for period starting {period_start.strftime('%d/%m/%Y')}"
                    )
                    await db.publication_alerts.insert_one(alert.dict())
                    alerts.append(alert.dict())
    
    return [PublicationAlert(**alert) for alert in alerts]

@api_router.put("/publication-alerts/{alert_id}/acknowledge")
async def acknowledge_publication_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge a publication alert"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    result = await db.publication_alerts.update_one(
        {"id": alert_id},
        {"$set": {"acknowledged": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert acknowledged"}

@api_router.get("/analytics/publication-compliance")
async def get_publication_compliance(current_user: dict = Depends(get_current_user)):
    """Get roster publication compliance analytics"""
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Get last 6 months of publications
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    publications = await db.roster_publications.find({
        "created_at": {"$gte": six_months_ago}
    }).to_list(1000)
    
    compliance_stats = {
        "total_publications": len(publications),
        "compliant": len([p for p in publications if p.get("compliance_status") == "compliant"]),
        "warnings": len([p for p in publications if p.get("compliance_status") == "warning"]),
        "violations": len([p for p in publications if p.get("compliance_status") == "violation"]),
        "average_days_advance": sum(p.get("days_in_advance", 0) for p in publications) / len(publications) if publications else 0
    }
    
    # Get active alerts
    active_alerts = await db.publication_alerts.find({"acknowledged": False}).to_list(100)
    
    return {
        "compliance_stats": compliance_stats,
        "active_alerts": len(active_alerts),
        "recent_publications": publications[-10:] if publications else []  # Last 10 publications
    }

# Dashboard category endpoints for clickable boxes
@api_router.get("/analytics/high-fatigue-members")
async def get_high_fatigue_members(current_user: dict = Depends(get_current_user)):
    """Get members with high fatigue risk"""
    workload_data = await get_workload_summary_internal()
    high_fatigue_members = []
    
    for member in workload_data:
        fatigue_score = (
            (member["stats"]["van_shifts_pct"] * 0.3) + 
            (member["stats"]["watchhouse_shifts_pct"] * 0.3) + 
            (member["stats"]["night_shifts_pct"] * 0.2) + 
            (member["stats"]["overtime_hours"] * 0.1) + 
            (member["stats"]["recall_count"] * 0.1)
        )
        
        if fatigue_score > 60:
            high_fatigue_members.append({
                **member,
                "fatigue_score": round(fatigue_score, 1),
                "risk_factors": []
            })
            
            # Add specific risk factors
            if member["stats"]["van_shifts_pct"] > 30:
                high_fatigue_members[-1]["risk_factors"].append(f"High van shifts: {member['stats']['van_shifts_pct']}%")
            if member["stats"]["watchhouse_shifts_pct"] > 30:
                high_fatigue_members[-1]["risk_factors"].append(f"High watchhouse shifts: {member['stats']['watchhouse_shifts_pct']}%")
            if member["stats"]["night_shifts_pct"] > 25:
                high_fatigue_members[-1]["risk_factors"].append(f"High night shifts: {member['stats']['night_shifts_pct']}%")
            if member["stats"]["overtime_hours"] > 20:
                high_fatigue_members[-1]["risk_factors"].append(f"Excessive overtime: {member['stats']['overtime_hours']:.1f}h")
            if member["stats"]["recall_count"] > 3:
                high_fatigue_members[-1]["risk_factors"].append(f"Frequent recalls: {member['stats']['recall_count']}")
    
    return high_fatigue_members

@api_router.get("/analytics/eba-violations-detail")
async def get_eba_violations_detail(current_user: dict = Depends(get_current_user)):
    """Get detailed EBA violations breakdown"""
    workload_data = await get_workload_summary_internal()
    violation_details = []
    
    for member in workload_data:
        if member.get("compliance", {}).get("status") == "violation":
            violation_details.append({
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "station": member["station"],
                "rank": member["rank"],
                "violations": member["compliance"]["violations"],
                "warnings": member["compliance"]["warnings"],
                "fortnight_hours": member["compliance"]["fortnight_hours"],
                "violation_types": {
                    "hours_exceeded": len([v for v in member["compliance"]["violations"] if "76h" in v or "60h" in v]),
                    "insufficient_breaks": len([v for v in member["compliance"]["violations"] if "break" in v.lower()]),
                    "night_recovery": len([v for v in member["compliance"]["violations"] if "consecutive night" in v]),
                    "rest_days": len([v for v in member["compliance"]["violations"] if "rest days" in v])
                }
            })
    
    return violation_details

@api_router.get("/analytics/night-recovery-issues")
async def get_night_recovery_issues(current_user: dict = Depends(get_current_user)):
    """Get members needing night shift recovery"""
    workload_data = await get_workload_summary_internal()
    night_issues = []
    
    for member in workload_data:
        if member.get("compliance", {}).get("violations"):
            night_violations = [v for v in member["compliance"]["violations"] if "consecutive night" in v]
            if night_violations:
                night_issues.append({
                    "member_id": member["member_id"],
                    "member_name": member["member_name"],
                    "station": member["station"],
                    "rank": member["rank"],
                    "violations": night_violations,
                    "consecutive_nights": len([v for v in night_violations if "consecutive" in v])
                })
    
    return night_issues

@api_router.get("/analytics/rest-day-issues")
async def get_rest_day_issues(current_user: dict = Depends(get_current_user)):
    """Get members with rest day compliance issues"""
    workload_data = await get_workload_summary_internal()
    rest_issues = []
    
    for member in workload_data:
        if member.get("compliance", {}).get("violations"):
            rest_violations = [v for v in member["compliance"]["violations"] if "rest days" in v]
            if rest_violations:
                rest_issues.append({
                    "member_id": member["member_id"],
                    "member_name": member["member_name"],
                    "station": member["station"],
                    "rank": member["rank"],
                    "violations": rest_violations,
                    "rest_day_deficit": sum([int(v.split("Only ")[1].split(" rest")[0]) for v in rest_violations if "Only " in v])
                })
    
    return rest_issues

@api_router.get("/analytics/eba-warnings-detail")
async def get_eba_warnings_detail(current_user: dict = Depends(get_current_user)):
    """Get detailed EBA warnings breakdown"""
    workload_data = await get_workload_summary_internal()
    warning_details = []
    
    for member in workload_data:
        if member.get("compliance", {}).get("status") == "warning":
            warning_details.append({
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "station": member["station"],
                "rank": member["rank"],
                "compliance": member["compliance"],
                "warnings": member["compliance"]["warnings"],
                "fortnight_hours": member["compliance"]["fortnight_hours"],
                "warning_types": {
                    "approaching_hours": len([w for w in member["compliance"]["warnings"] if "hours" in w.lower()]),
                    "fatigue_indicators": len([w for w in member["compliance"]["warnings"] if "fatigue" in w.lower()]),
                    "consecutive_shifts": len([w for w in member["compliance"]["warnings"] if "consecutive" in w.lower()])
                }
            })
    
    return warning_details

@api_router.get("/analytics/eba-compliant-members")
async def get_eba_compliant_members(current_user: dict = Depends(get_current_user)):
    """Get members in good EBA compliance standing"""
    workload_data = await get_workload_summary_internal()
    compliant_members = []
    
    for member in workload_data:
        if member.get("compliance", {}).get("status") == "compliant":
            compliant_members.append({
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "station": member["station"],
                "rank": member["rank"],
                "compliance": member["compliance"],
                "fortnight_hours": member["compliance"]["fortnight_hours"],
                "wellness_indicators": {
                    "hours_utilization": round((member["compliance"]["fortnight_hours"] / 76) * 100, 1),
                    "fatigue_score": member["compliance"].get("fatigue_score", 0),
                    "wellness_score": member["compliance"].get("wellness_score", 100)
                }
            })
    
    return compliant_members

@api_router.get("/analytics/over-76-hours")
async def get_over_76_hours_members(current_user: dict = Depends(get_current_user)):
    """Get members exceeding 76-hour fortnight limit"""
    workload_data = await get_workload_summary_internal()
    over_limit_members = []
    
    for member in workload_data:
        fortnight_hours = member.get("compliance", {}).get("fortnight_hours", 0)
        if fortnight_hours > 76:
            over_limit_members.append({
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "station": member["station"],
                "rank": member["rank"],
                "compliance": member["compliance"],
                "fortnight_hours": fortnight_hours,
                "overage_hours": round(fortnight_hours - 76, 1),
                "severity": "critical" if fortnight_hours > 80 else "high",
                "violations": [v for v in member["compliance"].get("violations", []) if "76h" in v or "60h" in v]
            })
    
    # Sort by overage hours (most critical first)
    over_limit_members.sort(key=lambda x: x["overage_hours"], reverse=True)
    return over_limit_members

@api_router.get("/analytics/approaching-76-hours")
async def get_approaching_76_hours_members(current_user: dict = Depends(get_current_user)):
    """Get members approaching 76-hour fortnight limit (65-76 hours)"""
    workload_data = await get_workload_summary_internal()
    approaching_members = []
    
    for member in workload_data:
        fortnight_hours = member.get("compliance", {}).get("fortnight_hours", 0)
        if 65 <= fortnight_hours <= 76:
            approaching_members.append({
                "member_id": member["member_id"],
                "member_name": member["member_name"],
                "station": member["station"],
                "rank": member["rank"],
                "compliance": member["compliance"],
                "fortnight_hours": fortnight_hours,
                "remaining_hours": round(76 - fortnight_hours, 1),
                "utilization_percent": round((fortnight_hours / 76) * 100, 1),
                "risk_level": "high" if fortnight_hours > 72 else "medium",
                "warnings": [w for w in member["compliance"].get("warnings", []) if "hour" in w.lower()]
            })
    
    # Sort by fortnight hours (highest first)
    approaching_members.sort(key=lambda x: x["fortnight_hours"], reverse=True)
    return approaching_members

@api_router.get("/members/{member_id}/detailed-view")
async def get_member_detailed_view(member_id: str, current_user: dict = Depends(get_current_user)):
    """Get comprehensive member details for detailed view"""
    
    # Get basic member information
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Get recent shifts (last 12 weeks)
    twelve_weeks_ago = datetime.utcnow() - timedelta(weeks=12)
    shifts = await db.shifts.find({
        "member_id": member_id, 
        "date": {"$gte": twelve_weeks_ago}
    }).sort("date", -1).to_list(500)
    
    # Calculate comprehensive shift breakdown
    shift_breakdown = {
        "total_shifts": len(shifts),
        "shift_types": {},
        "weekly_hours": [],
        "recent_patterns": []
    }
    
    # Group shifts by type
    shift_type_counts = {}
    for shift in shifts:
        shift_type = shift.get("shift_type", "unknown")
        shift_type_counts[shift_type] = shift_type_counts.get(shift_type, 0) + 1
    
    shift_breakdown["shift_types"] = shift_type_counts
    
    # Calculate weekly hours for trend analysis
    weeks = {}
    for shift in shifts:
        week_start = shift["date"] - timedelta(days=shift["date"].weekday())
        week_key = week_start.strftime("%Y-%W")
        if week_key not in weeks:
            weeks[week_key] = {"hours": 0, "shifts": 0, "week_start": week_start}
        weeks[week_key]["hours"] += shift.get("hours", 8)
        weeks[week_key]["shifts"] += 1
    
    shift_breakdown["weekly_hours"] = sorted(weeks.values(), key=lambda x: x["week_start"], reverse=True)[:12]
    
    # Get EBA compliance history
    compliance = await check_eba_compliance(member_id)
    
    # Get activity log (simulated - in real system would be from audit table)
    activity_log = [
        {
            "date": datetime.utcnow() - timedelta(days=1),
            "action": "Shift Assignment",
            "details": f"Assigned to {shifts[0].get('shift_type', 'shift').title()} shift" if shifts else "No recent shifts",
            "performed_by": "System"
        },
        {
            "date": datetime.utcnow() - timedelta(days=3),
            "action": "Preference Update",
            "details": "Night shift tolerance updated",
            "performed_by": current_user.get("name", "System")
        },
        {
            "date": datetime.utcnow() - timedelta(days=7),
            "action": "Compliance Check",
            "details": f"EBA compliance status: {compliance.compliance_status}",
            "performed_by": "System"
        }
    ]
    
    # Calculate fatigue risk projection
    recent_shifts = shifts[:14]  # Last 2 weeks
    consecutive_days = 0
    consecutive_nights = 0
    total_hours_2weeks = sum(shift.get("hours", 8) for shift in recent_shifts)
    
    for shift in recent_shifts:
        if shift.get("shift_type") == "night":
            consecutive_nights += 1
        else:
            consecutive_nights = 0
    
    fatigue_projection = {
        "current_fatigue_score": compliance.fatigue_score if hasattr(compliance, 'fatigue_score') else 0,
        "risk_factors": [],
        "projected_risk": "low",
        "recommendations": []
    }
    
    if total_hours_2weeks > 80:
        fatigue_projection["risk_factors"].append("High fortnightly hours")
        fatigue_projection["projected_risk"] = "high"
    
    if consecutive_nights > 3:
        fatigue_projection["risk_factors"].append("Consecutive night shifts")
        fatigue_projection["projected_risk"] = "high"
    
    if compliance.fortnight_hours > 70:
        fatigue_projection["risk_factors"].append("Approaching EBA limit")
        fatigue_projection["recommendations"].append("Limit additional shifts this fortnight")
    
    # Get leave/request history (simulated)
    schedule_history = [
        {
            "date": datetime.utcnow() - timedelta(days=5),
            "type": "Leave Request",
            "status": "Approved",
            "details": "Annual Leave - 2 days",
            "requested_by": member["name"]
        },
        {
            "date": datetime.utcnow() - timedelta(days=14),
            "type": "Shift Swap",
            "status": "Approved", 
            "details": "Night shift swapped with day shift",
            "requested_by": member["name"]
        }
    ]
    
    # Calculate equity tracking
    all_members_workload = await get_workload_summary_internal()
    member_workload = next((m for m in all_members_workload if m["member_id"] == member_id), None)
    
    equity_tracking = {
        "corro_allocation": {
            "member_count": member_workload.get("stats", {}).get("corro_shifts", 0) if member_workload else 0,
            "station_average": 2.5,  # Simulated average
            "percentile": 65  # Simulated percentile
        },
        "shift_distribution": {
            "van_shifts": member_workload.get("stats", {}).get("van_shifts_pct", 0) if member_workload else 0,
            "watchhouse_shifts": member_workload.get("stats", {}).get("watchhouse_shifts_pct", 0) if member_workload else 0,
            "night_shifts": member_workload.get("stats", {}).get("night_shifts_pct", 0) if member_workload else 0
        },
        "fairness_score": 75  # Simulated fairness score
    }
    
    return {
        "member_info": Member(**member),
        "shift_breakdown": shift_breakdown,
        "eba_compliance_history": {
            "current_status": compliance.compliance_status,
            "violations": compliance.violations,
            "warnings": compliance.warnings,
            "fortnight_hours": compliance.fortnight_hours,
            "compliance_trend": "stable"  # Would be calculated from historical data
        },
        "member_preferences": member.get("preferences", {}),
        "activity_log": activity_log,
        "fatigue_risk_projection": fatigue_projection,
        "schedule_request_history": schedule_history,
        "equity_tracking": equity_tracking
    }

# Helper function for internal use
async def get_workload_summary_internal():
    """Internal function to get workload data without authentication"""
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    
    pipeline = [
        {"$match": {"date": {"$gte": eight_weeks_ago}}},
        {"$group": {
            "_id": "$member_id",
            "total_shifts": {"$sum": 1},
            "van_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "van"]}, 1, 0]}},
            "watchhouse_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "watchhouse"]}, 1, 0]}},
            "night_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "night"]}, 1, 0]}},
            "corro_shifts": {"$sum": {"$cond": [{"$eq": ["$shift_type", "corro"]}, 1, 0]}},
            "overtime_hours": {"$sum": "$overtime_hours"},
            "recall_count": {"$sum": {"$cond": ["$was_recalled", 1, 0]}}
        }}
    ]
    
    workload_data = await db.shifts.aggregate(pipeline).to_list(1000)
    member_ids = [item["_id"] for item in workload_data]
    members = await db.members.find({"id": {"$in": member_ids}}).to_list(1000)
    member_dict = {m["id"]: m for m in members}
    
    result = []
    for item in workload_data:
        member = member_dict.get(item["_id"], {})
        compliance = await check_eba_compliance(item["_id"])
        
        result.append({
            "member_id": item["_id"],
            "member_name": member.get("name", "Unknown"),
            "station": member.get("station", "Unknown"),
            "rank": member.get("rank", "Unknown"),
            "seniority_years": member.get("seniority_years", 0),
            "stats": {
                "total_shifts": item["total_shifts"],
                "van_shifts_pct": round((item["van_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "watchhouse_shifts_pct": round((item["watchhouse_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "night_shifts_pct": round((item["night_shifts"] / item["total_shifts"]) * 100, 1) if item["total_shifts"] > 0 else 0,
                "corro_shifts": item["corro_shifts"],
                "overtime_hours": item["overtime_hours"],
                "recall_count": item["recall_count"]
            },
            "compliance": {
                "status": compliance.compliance_status,
                "fortnight_hours": compliance.fortnight_hours,
                "violations": compliance.violations,
                "warnings": compliance.warnings
            }
        })
    
    return result

# Initialize sample data
@api_router.post("/init-sample-data")
async def init_sample_data():
    # Clear existing data
    await db.users.delete_many({})
    await db.members.delete_many({})
    await db.shifts.delete_many({})
    
    # Create sample users and members
    sample_users = [
        {"vp_number": "VP12345", "name": "Sarah Connor", "email": "s.connor@vicpol.gov.au", "role": "inspector", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12346", "name": "John Smith", "email": "j.smith@vicpol.gov.au", "role": "sergeant", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12347", "name": "Emma Wilson", "email": "e.wilson@vicpol.gov.au", "role": "general_duties", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12348", "name": "Michael Brown", "email": "m.brown@vicpol.gov.au", "role": "general_duties", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12349", "name": "Lisa Davis", "email": "l.davis@vicpol.gov.au", "role": "general_duties", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12350", "name": "David Miller", "email": "d.miller@vicpol.gov.au", "role": "sergeant", "station": "corio", "password": "password123"},
        {"vp_number": "VP12351", "name": "Anna Taylor", "email": "a.taylor@vicpol.gov.au", "role": "general_duties", "station": "corio", "password": "password123"},
        {"vp_number": "VP12352", "name": "James Wilson", "email": "j.wilson@vicpol.gov.au", "role": "general_duties", "station": "corio", "password": "password123"},
        {"vp_number": "VP12353", "name": "Sophie Anderson", "email": "s.anderson@vicpol.gov.au", "role": "general_duties", "station": "corio", "password": "password123"},
        {"vp_number": "VP12354", "name": "Ryan Thomas", "email": "r.thomas@vicpol.gov.au", "role": "general_duties", "station": "corio", "password": "password123"},
        {"vp_number": "VP12355", "name": "Kate Martinez", "email": "k.martinez@vicpol.gov.au", "role": "general_duties", "station": "geelong", "password": "password123"},
        {"vp_number": "VP12356", "name": "Alex Johnson", "email": "a.johnson@vicpol.gov.au", "role": "general_duties", "station": "geelong", "password": "password123"}
    ]
    
    for user_data in sample_users:
        # Create user
        user = User(
            vp_number=user_data["vp_number"],
            name=user_data["name"],
            email=user_data["email"],
            role=UserRole(user_data["role"]),
            station=Station(user_data["station"]),
            password_hash=hash_password(user_data["password"])
        )
        await db.users.insert_one(user.dict())
        
        # Create member with varied preferences
        preferences = MemberPreferences(
            night_shift_tolerance=2 if user_data["name"] in ["Emma Wilson", "Lisa Davis"] else 4,
            recall_willingness=user_data["name"] not in ["Sophie Anderson", "Kate Martinez"],
            avoid_consecutive_doubles=True,
            avoid_four_earlies=user_data["name"] in ["Michael Brown", "Ryan Thomas"],
            medical_limitations="Lower back issues" if user_data["name"] == "James Wilson" else None,
            welfare_notes="Recently returned from leave" if user_data["name"] == "Anna Taylor" else None
        )
        
        member = Member(
            vp_number=user_data["vp_number"],
            name=user_data["name"],
            email=user_data["email"],
            station=Station(user_data["station"]),
            rank="Inspector" if user_data["role"] == "inspector" else "Sergeant" if user_data["role"] == "sergeant" else "Constable",
            seniority_years=15 if user_data["role"] == "inspector" else 8 if user_data["role"] == "sergeant" else 3,
            preferences=preferences
        )
        await db.members.insert_one(member.dict())
    
    # Create sample shifts for the last 8 weeks
    import random
    members = await db.members.find().to_list(1000)
    shift_types = ["early", "late", "night", "van", "watchhouse", "corro"]
    
    for week in range(8):
        week_start = datetime.utcnow() - timedelta(weeks=week)
        for day in range(7):
            shift_date = week_start - timedelta(days=day)
            
            for member in members:
                if member["rank"] not in ["Inspector"]:  # Inspectors don't do regular shifts
                    # Assign 4-5 shifts per week
                    if random.random() < 0.7:
                        shift_type = random.choice(shift_types)
                        
                        # Some members get more van/watchhouse shifts (fatigue risk)
                        if member["name"] in ["Michael Brown", "Ryan Thomas"]:
                            if random.random() < 0.4:
                                shift_type = random.choice(["van", "watchhouse"])
                        
                        # Some members get fewer corro shifts (inequity)
                        if member["name"] in ["Emma Wilson", "Lisa Davis"] and shift_type == "corro":
                            if random.random() < 0.3:  # Less likely to get corro
                                continue
                        
                        shift = Shift(
                            member_id=member["id"],
                            shift_type=ShiftType(shift_type),
                            date=shift_date,
                            start_time="06:00" if shift_type == "early" else "14:00" if shift_type == "late" else "22:00",
                            end_time="14:00" if shift_type == "early" else "22:00" if shift_type == "late" else "06:00",
                            overtime_hours=random.uniform(0, 3) if random.random() < 0.3 else 0,
                            was_recalled=random.random() < 0.1
                        )
                        await db.shifts.insert_one(shift.dict())
    
    return {"message": "Sample data initialized successfully"}

# ===== AUTOMATED ROSTER PRODUCER API ENDPOINTS =====

@api_router.post("/roster/generate", response_model=dict)
async def generate_roster(
    config: RosterGenerationConfig,
    start_date: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate an automated roster for the specified period"""
    
    # Only supervisors can generate rosters
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Parse start date or use next Monday
    if start_date:
        period_start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        # Default to next Monday
        today = datetime.utcnow()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target next Monday
            days_ahead += 7
        period_start = today + timedelta(days=days_ahead)
    
    period_end = period_start + timedelta(weeks=config.period_weeks)
    
    # Create roster period
    roster_period = RosterPeriod(
        start_date=period_start,
        end_date=period_end,
        station=config.station,
        created_by=current_user["id"],
        status="draft"
    )
    
    # Save roster period to database
    await db.roster_periods.insert_one(roster_period.dict())
    
    # Generate shift assignments
    assignments = await generate_shift_assignments(roster_period, config)
    
    # Save assignments to database
    for assignment in assignments:
        await db.shift_assignments.insert_one(assignment.dict())
    
    # Return summary
    return {
        "roster_period_id": roster_period.id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_assignments": len(assignments),
        "status": "draft",
        "compliance_summary": await validate_roster_compliance(roster_period.id),
        "assignments_by_member": await get_assignments_summary(assignments)
    }

@api_router.get("/roster/periods")
async def get_roster_periods(
    station: str = None,
    status: str = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all roster periods with optional filtering"""
    
    query = {}
    if station:
        query["station"] = station
    if status:
        query["status"] = status
    
    periods = await db.roster_periods.find(query).sort("start_date", -1).to_list(50)
    return [RosterPeriod(**period) for period in periods]

@api_router.get("/roster/{roster_period_id}")
async def get_roster_details(
    roster_period_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed roster with all assignments"""
    
    # Get roster period
    roster_period = await db.roster_periods.find_one({"id": roster_period_id})
    if not roster_period:
        raise HTTPException(status_code=404, detail="Roster period not found")
    
    # Get all assignments for this period
    assignments = await db.shift_assignments.find(
        {"roster_period_id": roster_period_id}
    ).sort("date", 1).to_list(1000)
    
    # Get member details for assignments
    member_ids = list(set(a["member_id"] for a in assignments))
    members = await db.members.find({"id": {"$in": member_ids}}).to_list(100)
    member_dict = {m["id"]: m for m in members}
    
    # Organize assignments by date and member
    assignments_by_date = {}
    for assignment in assignments:
        # Convert assignment to ShiftAssignment model to ensure proper serialization
        assignment_obj = ShiftAssignment(**assignment)
        assignment_dict = assignment_obj.dict()
        
        date_key = assignment_dict["date"].strftime("%Y-%m-%d")
        if date_key not in assignments_by_date:
            assignments_by_date[date_key] = []
        
        # Add member details to assignment
        assignment_dict["member_name"] = member_dict.get(assignment_dict["member_id"], {}).get("name", "Unknown")
        assignment_dict["member_rank"] = member_dict.get(assignment_dict["member_id"], {}).get("rank", "Unknown")
        
        assignments_by_date[date_key].append(assignment_dict)
    
    return {
        "roster_period": RosterPeriod(**roster_period),
        "assignments_by_date": assignments_by_date,
        "total_assignments": len(assignments),
        "compliance_status": await validate_roster_compliance(roster_period_id),
        "member_summary": await get_member_roster_summary(roster_period_id)
    }

@api_router.put("/roster/{roster_period_id}/publish")
async def publish_roster(
    roster_period_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Publish a draft roster (requires supervisor approval)"""
    
    # Only supervisors can publish rosters
    if current_user["role"] not in ["sergeant", "inspector", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Validate compliance before publishing
    compliance_status = await validate_roster_compliance(roster_period_id)
    if compliance_status["has_violations"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot publish roster with EBA violations: {compliance_status['violations']}"
        )
    
    # Update roster status
    await db.roster_periods.update_one(
        {"id": roster_period_id},
        {
            "$set": {
                "status": "published",
                "published_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Roster published successfully", "published_at": datetime.utcnow()}

# ===== ROSTER GENERATION CORE ALGORITHM =====

async def generate_shift_assignments(roster_period: RosterPeriod, config: RosterGenerationConfig) -> List[ShiftAssignment]:
    """Core algorithm to generate EBA-compliant shift assignments"""
    
    # Get all active members for the station
    members = await db.members.find({"station": config.station}).to_list(100)
    if not members:
        return []
    
    assignments = []
    current_date = roster_period.start_date
    
    # Define shift patterns (simplified for Phase 1)
    shift_patterns = [
        {"type": "early", "start": "06:00", "end": "14:00", "hours": 8.0},
        {"type": "late", "start": "14:00", "end": "22:00", "hours": 8.0},
        {"type": "night", "start": "22:00", "end": "06:00", "hours": 8.0},
        {"type": "van", "start": "06:00", "end": "14:00", "hours": 8.0},
        {"type": "watchhouse", "start": "06:00", "end": "14:00", "hours": 8.0},
        {"type": "corro", "start": "09:00", "end": "17:00", "hours": 8.0}
    ]
    
    # Track member assignments for EBA compliance
    member_assignments = {member["id"]: {"hours": 0, "shifts": [], "consecutive_nights": 0, "rest_days": 0} for member in members}
    
    # Generate assignments for each day in the period
    while current_date < roster_period.end_date:
        daily_assignments = []
        
        # Determine required coverage for the day
        required_coverage = {
            "early": 2,
            "late": 2,
            "night": 1,
            "van": config.min_van_coverage,
            "watchhouse": config.min_watchhouse_coverage,
            "corro": 1 if current_date.weekday() < 5 else 0  # Monday-Friday only
        }
        
        # Skip weekends for some shift types
        if current_date.weekday() >= 5:  # Weekend
            required_coverage["corro"] = 0
        
        # Assign shifts based on fairness and EBA compliance
        for shift_type, required_count in required_coverage.items():
            if required_count == 0:
                continue
                
            # Find the shift pattern
            shift_pattern = next((p for p in shift_patterns if p["type"] == shift_type), shift_patterns[0])
            
            # Select members for this shift type
            eligible_members = []
            for member in members:
                member_id = member["id"]
                member_data = member_assignments[member_id]
                
                # EBA compliance checks
                if member_data["hours"] + shift_pattern["hours"] > config.max_fortnight_hours:
                    continue  # Would exceed 76-hour limit
                
                if shift_type == "night" and member_data["consecutive_nights"] >= config.max_consecutive_nights:
                    continue  # Too many consecutive nights
                
                # Check if member has had adequate rest
                if len(member_data["shifts"]) > 0:
                    last_shift = member_data["shifts"][-1]
                    if last_shift["end_time"] == "06:00" and shift_pattern["start"] == "06:00":
                        continue  # Need 10-hour break after night shift
                
                # Add to eligible members with preference weighting
                preference_score = get_member_preference_score(member, shift_type, current_date)
                workload_score = get_workload_balance_score(member, shift_type)
                
                eligible_members.append({
                    "member": member,
                    "score": preference_score + workload_score,
                    "member_id": member_id
                })
            
            # Sort by score and select top members
            eligible_members.sort(key=lambda x: x["score"], reverse=True)
            selected_members = eligible_members[:required_count]
            
            # Create assignments
            for selected in selected_members:
                member = selected["member"]
                assignment = ShiftAssignment(
                    roster_period_id=roster_period.id,
                    member_id=member["id"],
                    date=current_date,
                    shift_type=shift_type,
                    start_time=shift_pattern["start"],
                    end_time=shift_pattern["end"],
                    hours=shift_pattern["hours"],
                    assignment_reason=f"automatic_allocation_score_{selected['score']:.1f}"
                )
                
                daily_assignments.append(assignment)
                
                # Update member tracking
                member_assignments[member["id"]]["hours"] += shift_pattern["hours"]
                member_assignments[member["id"]]["shifts"].append({
                    "date": current_date,
                    "type": shift_type,
                    "start_time": shift_pattern["start"],
                    "end_time": shift_pattern["end"]
                })
                
                # Track consecutive nights
                if shift_type == "night":
                    member_assignments[member["id"]]["consecutive_nights"] += 1
                else:
                    member_assignments[member["id"]]["consecutive_nights"] = 0
        
        assignments.extend(daily_assignments)
        current_date += timedelta(days=1)
    
    return assignments

def get_member_preference_score(member: dict, shift_type: str, date: datetime) -> float:
    """Calculate preference score for member and shift type"""
    preferences = member.get("preferences", {})
    score = 50.0  # Base score
    
    # Night shift tolerance
    if shift_type == "night":
        tolerance = preferences.get("night_shift_tolerance", 2)
        if tolerance == 0:
            score -= 30  # Strongly avoid
        elif tolerance >= 6:
            score += 20  # Prefer night shifts
    
    # Recall willingness
    if preferences.get("recall_willingness", True):
        score += 10
    
    # Preferred rest days
    preferred_rest_days = preferences.get("preferred_rest_days", [])
    day_name = date.strftime("%A")
    if day_name in preferred_rest_days:
        score -= 25  # Avoid scheduling on preferred rest days
    
    return score

def get_workload_balance_score(member: dict, shift_type: str) -> float:
    """Calculate workload balance score to promote fairness"""
    # This would integrate with existing workload data
    # For Phase 1, return a simple fairness score
    return 25.0  # Placeholder for workload balancing

async def validate_roster_compliance(roster_period_id: str) -> dict:
    """Validate roster against EBA compliance rules"""
    
    assignments = await db.shift_assignments.find(
        {"roster_period_id": roster_period_id}
    ).to_list(1000)
    
    violations = []
    warnings = []
    
    # Group assignments by member
    member_assignments = {}
    for assignment in assignments:
        member_id = assignment["member_id"]
        if member_id not in member_assignments:
            member_assignments[member_id] = []
        member_assignments[member_id].append(assignment)
    
    # Check each member's compliance
    for member_id, member_shifts in member_assignments.items():
        # Check 76-hour fortnight limit
        total_hours = sum(shift["hours"] for shift in member_shifts)
        if total_hours > 76:
            violations.append(f"Member {member_id}: {total_hours}h exceeds 76h limit")
        elif total_hours > 65:
            warnings.append(f"Member {member_id}: {total_hours}h approaching 76h limit")
        
        # Check consecutive night shifts
        consecutive_nights = 0
        max_consecutive = 0
        for shift in sorted(member_shifts, key=lambda x: x["date"]):
            if shift["shift_type"] == "night":
                consecutive_nights += 1
                max_consecutive = max(max_consecutive, consecutive_nights)
            else:
                consecutive_nights = 0
        
        if max_consecutive > 7:
            violations.append(f"Member {member_id}: {max_consecutive} consecutive night shifts")
        elif max_consecutive > 5:
            warnings.append(f"Member {member_id}: {max_consecutive} consecutive night shifts")
        
        # Check minimum rest days (simplified)
        total_shifts = len(member_shifts)
        expected_rest_days = 14 - total_shifts  # 14 days in fortnight minus shifts
        if expected_rest_days < 4:
            violations.append(f"Member {member_id}: Only {expected_rest_days} rest days")
    
    return {
        "has_violations": len(violations) > 0,
        "has_warnings": len(warnings) > 0,
        "violations": violations,
        "warnings": warnings,
        "total_members_checked": len(member_assignments)
    }

async def get_assignments_summary(assignments: List[ShiftAssignment]) -> dict:
    """Get summary of assignments by member"""
    
    member_summary = {}
    for assignment in assignments:
        member_id = assignment.member_id
        if member_id not in member_summary:
            member_summary[member_id] = {
                "total_shifts": 0,
                "total_hours": 0,
                "shift_types": {}
            }
        
        member_summary[member_id]["total_shifts"] += 1
        member_summary[member_id]["total_hours"] += assignment.hours
        
        shift_type = assignment.shift_type
        if shift_type not in member_summary[member_id]["shift_types"]:
            member_summary[member_id]["shift_types"][shift_type] = 0
        member_summary[member_id]["shift_types"][shift_type] += 1
    
    return member_summary

async def get_member_roster_summary(roster_period_id: str) -> dict:
    """Get detailed member summary for a roster period"""
    
    assignments = await db.shift_assignments.find(
        {"roster_period_id": roster_period_id}
    ).to_list(1000)
    
    member_ids = list(set(a["member_id"] for a in assignments))
    members = await db.members.find({"id": {"$in": member_ids}}).to_list(100)
    member_dict = {m["id"]: m for m in members}
    
    summary = {}
    for member_id in member_ids:
        member_assignments = [a for a in assignments if a["member_id"] == member_id]
        member_info = member_dict.get(member_id, {})
        
        summary[member_id] = {
            "name": member_info.get("name", "Unknown"),
            "rank": member_info.get("rank", "Unknown"),
            "total_shifts": len(member_assignments),
            "total_hours": sum(a["hours"] for a in member_assignments),
            "shift_breakdown": {},
            "compliance_status": "compliant"  # Would be calculated
        }
        
        # Count shift types
        for assignment in member_assignments:
            shift_type = assignment["shift_type"]
            if shift_type not in summary[member_id]["shift_breakdown"]:
                summary[member_id]["shift_breakdown"][shift_type] = 0
            summary[member_id]["shift_breakdown"][shift_type] += 1
    
    return summary

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()