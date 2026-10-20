from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.branding import BrandingOut
from app.services.branding_service import get_branding

router = APIRouter(tags=["branding"])

@router.get("/branding", response_model=BrandingOut)
async def public_branding(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return await get_branding(db)
