import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Book(TimestampMixin, Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("published_year IS NULL OR published_year <= EXTRACT(YEAR FROM CURRENT_DATE)", name="ck_books_published_year_not_in_future"),
        CheckConstraint("total_copies >= 0", name="ck_books_total_copies_non_negative"),
        CheckConstraint("available_copies >= 0", name="ck_books_available_copies_non_negative"),
        CheckConstraint("available_copies <= total_copies", name="ck_books_available_le_total"),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isbn: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    loans: Mapped[list["Loan"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Member(TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_full_name", "full_name"),
        Index("ix_members_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    loans: Mapped[list["Loan"]] = relationship(back_populates="member", cascade="all, delete-orphan")


class Loan(TimestampMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("due_at IS NULL OR due_at >= borrowed_at", name="ck_loans_due_at_gte_borrowed_at"),
        Index("ix_loans_member_id_returned_at", "member_id", "returned_at"),
        Index("ix_loans_book_id_returned_at", "book_id", "returned_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="RESTRICT"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("members.id", ondelete="RESTRICT"), nullable=False
    )
    borrowed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    book: Mapped[Book] = relationship(back_populates="loans")
    member: Mapped[Member] = relationship(back_populates="loans")
