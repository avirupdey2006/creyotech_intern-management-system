import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ApplicationStatus


class InternProfileCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: str = Field(..., min_length=7, max_length=25)
    college_name: str = Field(..., min_length=2, max_length=255)
    internship_role: str = Field(..., min_length=2, max_length=150)
    start_date: date
    end_date: date
    address: Optional[str] = Field(default="Sector V, Salt Lake", max_length=500)
    city: Optional[str] = Field(default="Kolkata", max_length=100)
    state: Optional[str] = Field(default="West Bengal", max_length=100)
    pin_code: Optional[str] = Field(default="700091", max_length=20)
    work_mode: Optional[str] = Field(default="Remote", max_length=50)
    work_schedule: Optional[str] = Field(
        default="Monday to Friday (10:00 AM - 6:00 PM IST)", max_length=150
    )
    reporting_manager: Optional[str] = Field(
        default="Technical Project Manager, CREYOTECH", max_length=150
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "InternProfileCreateRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class InternProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone_number: str
    college_name: str
    internship_role: str
    start_date: date
    end_date: date
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    work_mode: Optional[str] = None
    work_schedule: Optional[str] = None
    reporting_manager: Optional[str] = None
    application_status: ApplicationStatus
    created_at: datetime
    updated_at: datetime