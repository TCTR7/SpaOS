import uuid
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.auth import TenantOut, UserOut

class BranchOut(BaseModel):
    tenant: TenantOut
    user: UserOut
    is_owner: bool

class BranchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)

class StaffGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_staff_id: uuid.UUID

class DashboardMetrics(BaseModel):
    appointments: int = 0
    in_progress: int = 0
    completed: int = 0
    cash: Decimal = Decimal(0)
    bank_transfer: Decimal = Decimal(0)
    net_received: Decimal = Decimal(0)
    completed_value: Decimal = Decimal(0)
    outstanding: Decimal = Decimal(0)
    unknown_prices: int = 0
    active_packages: int = 0

class DashboardBranch(BaseModel):
    branch_id: uuid.UUID
    name: str
    metrics: DashboardMetrics

class DashboardOut(BaseModel):
    date: date
    timezone: str = "Asia/Ho_Chi_Minh"
    branches: list[DashboardBranch]
    totals: DashboardMetrics
