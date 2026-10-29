import uuid
from datetime import date, time
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class AssignmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenant_id: uuid.UUID | None = None
    start_time: time | None = None
    end_time: time | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    day: date | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def local_clock(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError("Giờ làm tại Việt Nam không kèm offset")
        return value

    @model_validator(mode="after")
    def valid_hours(self):
        if self.tenant_id is None:
            if self.start_time is not None or self.end_time is not None:
                raise ValueError("Ngày nghỉ không có giờ làm")
        elif not self.start_time or not self.end_time or self.start_time >= self.end_time:
            raise ValueError("Chọn giờ bắt đầu và kết thúc trong cùng ngày")
        return self


class WeekIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_from: date
    days: list[AssignmentIn] = Field(min_length=7, max_length=7)

    @model_validator(mode="after")
    def valid_week(self):
        if {d.weekday for d in self.days} != set(range(7)) or any(d.day for d in self.days):
            raise ValueError("Cần bảy thứ khác nhau từ 0 (CN) tới 6 (Thứ Bảy)")
        return self
