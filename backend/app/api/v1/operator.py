"""Private deployment provisioning; tokens cannot authenticate tenant APIs."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import bearer_scheme
from app.core.config import settings
from app.core.database import get_db, set_tenant_context
from app.core.security import hash_password, verify_password, JWT_CLOCK_SKEW_SECONDS
from app.models.models import DeploymentOperator, OwnerProvision, Tenant, User, UserRole
from app.schemas.operator import OperatorLogin, OperatorOut, OperatorToken, OwnerCreate, ProvisionOut
from app.services.branch_service import provision_account
from app.services.audit_service import audit

from app.schemas.branding import BrandingOut, BrandingUpdate
from app.services.branding_service import get_branding, save_branding
from app.schemas.operator import OwnerVerify, OwnerUpdate
from app.schemas.experience import RecoveryClaim
from app.services.owner_service import resolve_owner, owner_view, owner_memberships
from app.models.models import OwnerRecoveryGrant, AuditLog
from sqlalchemy import delete
import secrets

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
            algorithms=[settings.JWT_ALGORITHM], audience=AUDIENCE, leeway=JWT_CLOCK_SKEW_SECONDS, options={"require": ["sub", "exp", "version", "scope"]})
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


@router.get("/system")
async def system_info(response: Response, operator=Depends(get_operator)):
    from app.core.release import BUILD_INFO
    response.headers["Cache-Control"] = "no-store"
    return BUILD_INFO

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
    payload = body.model_dump(mode="json", exclude={"password", "theme_color"}, exclude_none=True)
    if body.theme_color is not None:
        payload["theme_color"] = body.theme_color
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
    from app.services.spa_service import new_spa
    spa = await new_spa(db, body.spa_name or body.branch_name, operator_id=operator.id, theme_color=body.theme_color)
    spa.logo_url, spa.cover_url = body.logo_url, body.cover_url
    from app.api.v1.spas import apply_images
    apply_images(spa, body.logo_data, body.cover_data)
    tenant = Tenant(name=body.branch_name, slug="cn-"+uuid.uuid4().hex, spa_id=spa.id)
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

@router.get("/branding", response_model=BrandingOut)
async def read_branding(operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    return await get_branding(db)

@router.post("/branding", response_model=BrandingOut)
async def update_branding(body: BrandingUpdate, operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    result = await save_branding(db, operator.id, body.theme_color)
    await db.commit()
    return result


def verify_operator_password(operator, body):
    if not verify_password(body.current_password.get_secret_value(), operator.password_hash):
        raise HTTPException(403, "Mật khẩu xác nhận không đúng")


@router.get("/owners/{provision_id}")
async def owner_detail(provision_id: uuid.UUID, operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    return await owner_view(db, operator.id, provision_id)


@router.patch("/owners/{provision_id}")
async def update_owner(provision_id: uuid.UUID, body: OwnerUpdate, operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    verify_operator_password(operator, body)
    record, account, rows = await resolve_owner(db, operator.id, provision_id)
    try:
        account.phone_number = body.phone_number
        await db.flush()
        for _, user, tenant in rows:
            await set_tenant_context(db, tenant.id)
            user.full_name, user.phone_number = body.full_name, body.phone_number
            user.auth_version += 1
            audit(db, tenant.id, None, "OWNER_ACCOUNT_UPDATED", "user", user.id,
                {"operator_id": str(operator.id), "fields": ["full_name", "phone_number"], "sessions_revoked": True})
            await db.flush()
        result = await owner_view(db, operator.id, provision_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Số điện thoại đã được sử dụng; chưa thay đổi tài khoản")
    return result


@router.post("/owners/{provision_id}/recovery-link")
async def owner_recovery_link(provision_id: uuid.UUID, body: OwnerVerify, operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    verify_operator_password(operator, body)
    record, account, rows = await resolve_owner(db, operator.id, provision_id)
    primary = next(u for _, u, _ in rows if u.id == record.owner_user_id)
    if not primary.is_active:
        raise HTTPException(409, "Tài khoản đang ngưng hoạt động")
    await set_tenant_context(db, record.tenant_id)
    await db.execute(delete(OwnerRecoveryGrant).where(OwnerRecoveryGrant.tenant_id == record.tenant_id,
        OwnerRecoveryGrant.account_id == account.id, OwnerRecoveryGrant.operator_id == operator.id))
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.add(OwnerRecoveryGrant(tenant_id=record.tenant_id, operator_id=operator.id, account_id=account.id,
        user_id=primary.id, auth_version=primary.auth_version, token_hash=hashlib.sha256(token.encode()).hexdigest(), expires_at=expiry))
    audit(db, record.tenant_id, None, "OWNER_RECOVERY_ISSUED", "user", primary.id,
        {"operator_id": str(operator.id), "identity_verified": True})
    await db.commit()
    return {"token": token, "expires_at": expiry}


@router.get("/owners/{provision_id}/events")
async def owner_events(provision_id: uuid.UUID, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
    operator=Depends(get_operator), db: AsyncSession = Depends(get_db)):
    record, _, _ = await resolve_owner(db, operator.id, provision_id)
    await set_tenant_context(db, record.tenant_id)
    rows = (await db.execute(select(AuditLog).where(AuditLog.tenant_id == record.tenant_id,
        AuditLog.entity_id == record.owner_user_id, AuditLog.action.in_([
            "OWNER_PROVISIONED", "OWNER_ACCOUNT_UPDATED", "OWNER_RECOVERY_ISSUED", "OWNER_RECOVERY_COMPLETED"]))
        .order_by(AuditLog.created_at.desc(), AuditLog.id).limit(limit).offset(offset))).scalars().all()
    return [{"id": r.id, "action": r.action, "created_at": r.created_at,
        "operator_id": r.details.get("operator_id")} for r in rows]


@router.post("/recovery", tags=["owner recovery"])
async def recover_owner(body: RecoveryClaim, db: AsyncSession = Depends(get_db)):
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    await db.execute(text("SELECT set_config('app.owner_recovery_hash',:hash,true)"), {"hash": digest})
    invalid = HTTPException(400, "Liên kết không còn hiệu lực. Vui lòng liên hệ đơn vị triển khai.")
    grant = (await db.execute(select(OwnerRecoveryGrant).where(OwnerRecoveryGrant.token_hash == digest))).scalar_one_or_none()
    if not grant:
        raise invalid
    # Account lock serializes issue/update/claim and normal credentials changes.
    account, rows = await owner_memberships(db, grant.account_id)
    primary = next((u for link, u, _ in rows if u.id == grant.user_id and link.is_active and u.is_active), None)
    await set_tenant_context(db, grant.tenant_id)
    grant = (await db.execute(select(OwnerRecoveryGrant).where(OwnerRecoveryGrant.tenant_id == grant.tenant_id,
        OwnerRecoveryGrant.token_hash == digest).execution_options(populate_existing=True).with_for_update())).scalar_one_or_none()
    if not grant or not primary or grant.consumed_at or grant.expires_at <= datetime.now(timezone.utc) or grant.auth_version != primary.auth_version:
        raise invalid
    password_hash = hash_password(body.password)
    account.password_hash = password_hash
    for _, user, tenant in rows:
        await set_tenant_context(db, tenant.id)
        user.password_hash = password_hash
        user.auth_version += 1
        audit(db, tenant.id, None, "OWNER_RECOVERY_COMPLETED", "user", user.id,
            {"operator_id": str(grant.operator_id), "sessions_revoked": True})
        await db.flush()
    await set_tenant_context(db, grant.tenant_id)
    grant.consumed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"updated": True}
