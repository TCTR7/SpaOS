from fastapi import APIRouter

from app.api.v1 import auth, bookings, customers, notifications, reports, services, staff, tenants, payments

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tenants.public_router)
api_router.include_router(tenants.tenants_router)
api_router.include_router(services.router)
api_router.include_router(staff.router)
api_router.include_router(customers.customers_router)
api_router.include_router(customers.packages_router)

api_router.include_router(bookings.router)
api_router.include_router(notifications.router)
api_router.include_router(reports.router)

api_router.include_router(payments.router)

from app.api.v1 import branches
api_router.include_router(branches.router)

from app.api.v1 import operator
api_router.include_router(operator.router)
