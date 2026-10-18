from sqlalchemy import select, text
from app.models.models import DeploymentBranding
from app.schemas.branding import BrandingOut, DEFAULT_COLOR

async def get_branding(db):
    row = (await db.execute(select(DeploymentBranding).where(DeploymentBranding.slot == 1))).scalar_one_or_none()
    return BrandingOut(theme_color=row.theme_color if row else DEFAULT_COLOR, configured=row is not None)

async def save_branding(db, operator_id, theme_color):
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('spaos:deployment-brand',0))"))
    row = (await db.execute(select(DeploymentBranding).where(DeploymentBranding.slot == 1).with_for_update())).scalar_one_or_none()
    if row is None:
        row = DeploymentBranding(slot=1, theme_color=theme_color, updated_by=operator_id)
        db.add(row)
    else:
        row.theme_color, row.updated_by = theme_color, operator_id
    await db.flush()
    return BrandingOut(theme_color=row.theme_color, configured=True)
