from pydantic import BaseModel, ConfigDict, field_validator
import re

DEFAULT_COLOR = "#be185d"

def color(value):
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value.strip()):
        raise ValueError("Màu phải có dạng HEX #RRGGBB, ví dụ #2563eb")
    return value.strip().lower()

class BrandingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theme_color: str
    _color = field_validator("theme_color")(color)

class BrandingOut(BaseModel):
    theme_color: str
    configured: bool
