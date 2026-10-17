"""Private deployment provisioning; tokens cannot authenticate tenant APIs."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import bearer_scheme
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.core.security import hash_password, verify_password
from app.models.models import DeploymentOperator, OwnerProvision, Tenant, User, UserRole
from app.schemas.operator import OperatorLogin, OperatorOut, OperatorToken, OwnerCreate, ProvisionOut
from app.services.branch_service import provision_account
from app.services.audit_service import audit

router = APIRouter(prefix="/operator", tags=["operator"])
AUDIENCE = "spaos-operator"
DUMMY_HASH = hash_password("not-a-valid-operator-password")

async def operator_context(db, operator_id):
    await db.execute(text("SELECT set_config('app.current_operator_id',:id,true)"), {"id": str(operator_id)})

async def get_operator(credentials=Depends(bearer_scheme), db: AsyncSession = Depends(get_db)):
    if credentials is None:
        raise HTTPException(401, "Cần đăng nhập quản trị triển khai")
    try:
        claims = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM], audience=AUDIENCE, options={"require": ["sub", "exp", "version", "scope"]})
        if claims["scope"] != "operator":
            raise ValueError()
        operator_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise HTTPException(401, "Phiên quản trị không hợp lệ hoặc hết hạn")
    await operator_context(db, operator_id)
    row = (await db.execute(select(DeploymentOperator).where(DeploymentOperator.id == operator_id,
                          DeploymentOperator.is_active.is_(True)))).scalar_one_or_none()
    if row is None or row.token_version != claims["version"]:
        raise HTTPException(401, "Phiên quản trị đã bị thu hồi")
    return row

@router.post("/login", response_model=OperatorToken)
async def login(body: OperatorLogin, db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT set_config('app.operator_phone',:phone,true)"), {"phone": body.phone_number})
    row = (await db.execute(select(DeploymentOperator).where(DeploymentOperator.phone_number == body.phone_number)
                           .with_for_update())).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row and row.locked_until and row.locked_until > now:
        raise HTTPException(429, "Đã thử quá nhiều lần. Vui lòng thử lại sau 5 phút.")
    valid = verify_password(body.password.get_secret_value(), row.password_hash if row else DUMMY_HASH)
    if not row or not row.is_active or not valid:
        if row:
            row.failed_attempts = (0 if row.locked_until else row.failed_attempts) + 1
            row.locked_until = now + timedelta(minutes=5) if row.failed_attempts >= 5 else None
            await db.commit()
        raise HTTPException(401, "Sai số điện thoại hoặc mật khẩu")
    row.failed_attempts, row.locked_until = 0, None
    token = jwt.encode({"sub": str(row.id), "scope": "operator", "aud": AUDIENCE,
        "version": row.token_version, "iat": now, "exp": now+timedelta(minutes=30)},
        settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    result = OperatorToken(access_token=token, expires_in=1800, operator=OperatorOut.model_validate(row))
    await db.commit()
    return result

@router.get("/me", response_model=OperatorOut)
async def me(operator=Depends(get_operator)):
    return operator

@router.post("/logout")
async def logout(operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    # Atomic increment also revokes other open sessions for this installation identity.
    await db.execute(text("UPDATE deployment_operators SET token_version=token_version+1 WHERE id=:id"),
                     {"id": operator.id})
    await db.commit()
    return {"logged_out": True}

@router.get("/owners", response_model=list[ProvisionOut])
async def owners(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    return list((await db.execute(select(OwnerProvision).where(OwnerProvision.operator_id == operator.id)
        .order_by(OwnerProvision.created_at.desc(), OwnerProvision.id).limit(limit).offset(offset))).scalars().all())

def request_digest(body):
    payload = body.model_dump(mode="json", exclude={"password"})
    payload["password"] = body.password.get_secret_value()
    return hmac.new(settings.JWT_SECRET_KEY.encode(), json.dumps(payload, ensure_ascii=False,
                   sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()

@router.post("/owners", response_model=ProvisionOut, status_code=201)
async def create_owner(body: OwnerCreate, operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    # Serializes idempotency and initial owner checks across all operator sessions.
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('spaos:owner-provision',0))"))
    digest = request_digest(body)
    old = (await db.execute(select(OwnerProvision).where(OwnerProvision.operator_id == operator.id,
                                                       OwnerProvision.request_id == body.request_id))).scalar_one_or_none()
    if old:
        if not hmac.compare_digest(old.request_digest, digest):
            raise HTTPException(409, "Mã yêu cầu đã được dùng với nội dung khác")
        return old
    if settings.ENVIRONMENT == "production" and (await db.execute(select(Tenant.id).limit(1))).first():
        raise HTTPException(409, "Hệ thống đã có chi nhánh. Mỗi khách hàng dùng một deployment riêng; không tạo chủ mới trên dữ liệu hiện có.")
    tenant = Tenant(name=body.branch_name, slug="cn-"+uuid.uuid4().hex)
    db.add(tenant)
    try:
        await db.flush()
        await set_tenant_context(db, tenant.id)
        owner = User(tenant_id=tenant.id, role=UserRole.ADMIN, full_name=body.owner_full_name,
            phone_number=body.phone_number, password_hash=hash_password(body.password.get_secret_value()))
        db.add(owner)
        await db.flush()
        await provision_account(db, owner, owner=True)
        record = OwnerProvision(tenant_id=tenant.id, operator_id=operator.id, owner_user_id=owner.id,
            request_id=body.request_id, request_digest=digest, owner_name=owner.full_name,
            phone_number=owner.phone_number, branch_name=tenant.name)
        db.add(record)
        await db.flush()
        audit(db, tenant.id, None, "OWNER_PROVISIONED", "user", owner.id, {"operator_id": str(operator.id)})
        result = ProvisionOut.model_validate(record)
        await db.commit()
        return result
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Không thể tạo tài khoản trùng. Vui lòng đối chiếu lại thông tin.")
