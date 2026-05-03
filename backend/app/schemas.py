from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def current_utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


def normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def normalize_required_string(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("value cannot be blank")
    return value


def validate_published_year_not_in_future(value: int | None) -> int | None:
    if value is None:
        return None
    current_year = current_utc_datetime().year
    if value > current_year:
        raise ValueError(f"published_year must be less than or equal to {current_year}")
    return value


def validate_timezone_aware_datetime(value: datetime | None, field_name: str) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value


def validate_due_at_not_in_past(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value < current_utc_datetime():
        raise ValueError("due_at must be greater than or equal to the current datetime")
    return value


TrimmedRequiredStr = Annotated[str, Field(min_length=1, max_length=255)]
OptionalTrimmedStr20 = Annotated[str | None, Field(default=None, max_length=20)]
OptionalTrimmedStr30 = Annotated[str | None, Field(default=None, max_length=30)]


class BookBase(BaseModel):
    isbn: OptionalTrimmedStr20 = None
    title: TrimmedRequiredStr
    author: TrimmedRequiredStr
    description: str | None = None
    published_year: int | None = Field(default=None, ge=0, le=9999)
    total_copies: int = Field(default=1, ge=0)
    is_active: bool = True

    @field_validator("isbn", "description", mode="before")
    @classmethod
    def strip_optional_book_strings(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_required_book_strings(cls, value: str) -> str:
        return normalize_required_string(value)

    @field_validator("published_year")
    @classmethod
    def validate_published_year(cls, value: int | None) -> int | None:
        return validate_published_year_not_in_future(value)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    isbn: OptionalTrimmedStr20 = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    published_year: int | None = Field(default=None, ge=0, le=9999)
    total_copies: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("isbn", "description", mode="before")
    @classmethod
    def strip_optional_book_strings(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_optional_non_blank_book_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_string(value)

    @field_validator("published_year")
    @classmethod
    def validate_published_year(cls, value: int | None) -> int | None:
        return validate_published_year_not_in_future(value)


class BookResponse(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    available_copies: int
    created_at: datetime
    updated_at: datetime


class MemberBase(BaseModel):
    full_name: TrimmedRequiredStr
    email: EmailStr
    phone: OptionalTrimmedStr30 = None
    address: str | None = None
    is_active: bool = True

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_required_member_strings(cls, value: str) -> str:
        return normalize_required_string(value)

    @field_validator("phone", "address", mode="before")
    @classmethod
    def strip_optional_member_strings(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = None
    is_active: bool | None = None

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_optional_non_blank_member_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_required_string(value)

    @field_validator("phone", "address", mode="before")
    @classmethod
    def strip_optional_member_strings(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)


class MemberResponse(MemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class LoanBorrowRequest(BaseModel):
    book_id: UUID
    member_id: UUID
    due_at: datetime | None = None
    notes: str | None = None

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime | None:
        value = validate_timezone_aware_datetime(value, "due_at")
        return validate_due_at_not_in_past(value)

    @field_validator("notes", mode="before")
    @classmethod
    def strip_optional_notes(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)


class LoanReturnRequest(BaseModel):
    notes: str | None = None

    @field_validator("notes", mode="before")
    @classmethod
    def strip_optional_notes(cls, value: str | None) -> str | None:
        return normalize_optional_string(value)


class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    book_id: UUID
    member_id: UUID
    borrowed_at: datetime
    due_at: datetime | None
    returned_at: datetime | None
    notes: str | None
    status: Literal["BORROWED", "RETURNED", "OVERDUE"]
    book_title: str
    member_name: str


class HealthResponse(BaseModel):
    status: str


class MessageResponse(BaseModel):
    message: str
