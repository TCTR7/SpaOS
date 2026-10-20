"""Seed ONLY the private deployment operator from secret configuration.
Demo data is opt-in: python -m app.seed_demo (development only).
"""
import asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.security import hash_password
from app.models.models import DeploymentOperator
from app.schemas.auth import _check_phone

async def seed(db):
    phone = settings.OPERATOR_PHONE.strip()
    password = settings.OPERATOR_PASSWORD.get_secret_value()
    if not phone and not password:
        return "Chưa cấu hình OPERATOR_PHONE/OPERATOR_PASSWORD; không tạo tài khoản mặc định."
    phone = _check_phone(phone)
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise ValueError("OPERATOR_PASSWORD cần ít nhất 12 ký tự, tối đa 72 byte UTF-8.")
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('spaos:operator-seed',0))"))
    await db.execute(text("SELECT set_config('app.operator_phone',:phone,true)"), {"phone": phone})
    old = (await db.execute(select(DeploymentOperator).where(DeploymentOperator.phone_number == phone))).scalar_one_or_none()
    if old:
        return "Tài khoản quản trị triển khai đã tồn tại; giữ nguyên mật khẩu và quyền."
    db.add(DeploymentOperator(phone_number=phone, full_name=settings.OPERATOR_NAME,
                              password_hash=hash_password(password), slot=1))
    await db.commit()
    return "Đã tạo tài khoản quản trị triển khai. Mở /operator/login để đăng nhập."

async def main():
    try:
        async with AsyncSessionLocal() as db:
            print(await seed(db))
    except IntegrityError:
        raise SystemExit("Hệ thống đã có tài khoản quản trị khác. Không tạo thêm hoặc tự đổi thông tin đăng nhập.")
    except (ValueError, UnicodeError):
        raise SystemExit("Cấu hình quản trị chưa hợp lệ. Kiểm tra OPERATOR_PHONE, OPERATOR_PASSWORD và lưu file cấu hình UTF-8.")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
