from fastapi import APIRouter

from app.api.v1 import auth, bookings, customers, notifications, reports, services, staff, tenants, payments

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tenants.public_router)
api_router.include_router(tenants.tenants_router)
api_router.include_router(services.router)
api_router.include_router(staff.router)
api_router.include_router(staff.public_router)
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

from app.api.v1 import branding
api_router.include_router(branding.router)

from app.api.v1 import experience
api_router.include_router(experience.router)

from app.api.v1 import workforce, spas
api_router.include_router(workforce.router)
api_router.include_router(spas.router)

from app.api.v1 import guest_requests
api_router.include_router(guest_requests.router)
