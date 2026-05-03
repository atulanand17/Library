from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def compute_status(loan: models.Loan) -> str:
    if loan.returned_at is not None:
        return "RETURNED"
    if loan.due_at and loan.due_at < datetime.now(timezone.utc):
        return "OVERDUE"
    return "BORROWED"


# Book operations

def create_book(db: Session, payload: schemas.BookCreate) -> models.Book:
    book = models.Book(
        isbn=payload.isbn,
        title=payload.title,
        author=payload.author,
        description=payload.description,
        published_year=payload.published_year,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
        is_active=payload.is_active,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book



def list_books(db: Session, skip: int, limit: int) -> list[models.Book]:
    stmt = select(models.Book).order_by(models.Book.title.asc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())



def get_book_or_404(db: Session, book_id: UUID) -> models.Book:
    book = db.get(models.Book, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book



def update_book(db: Session, book_id: UUID, payload: schemas.BookUpdate) -> models.Book:
    book = get_book_or_404(db, book_id)
    data = payload.model_dump(exclude_unset=True)

    if "total_copies" in data:
        new_total = data["total_copies"]
        active_loans = book.total_copies - book.available_copies
        if new_total < active_loans:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="total_copies cannot be lower than currently borrowed copies",
            )
        book.available_copies = new_total - active_loans

    for field, value in data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


# Member operations

def create_member(db: Session, payload: schemas.MemberCreate) -> models.Member:
    member = models.Member(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member



def list_members(db: Session, skip: int, limit: int) -> list[models.Member]:
    stmt = select(models.Member).order_by(models.Member.full_name.asc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())



def get_member_or_404(db: Session, member_id: UUID) -> models.Member:
    member = db.get(models.Member, member_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return member



def update_member(db: Session, member_id: UUID, payload: schemas.MemberUpdate) -> models.Member:
    member = get_member_or_404(db, member_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


# Loan operations

def borrow_book(db: Session, payload: schemas.LoanBorrowRequest) -> models.Loan:
    member = get_member_or_404(db, payload.member_id)
    if not member.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Member is inactive")

    stmt = select(models.Book).where(models.Book.id == payload.book_id).with_for_update()
    book = db.scalar(stmt)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if not book.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book is inactive")
    if book.available_copies <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No copies available for borrowing")

    loan = models.Loan(
        book_id=payload.book_id,
        member_id=payload.member_id,
        due_at=payload.due_at,
        notes=payload.notes,
    )
    book.available_copies -= 1
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan



def get_loan_or_404(db: Session, loan_id: UUID) -> models.Loan:
    stmt = (
        select(models.Loan)
        .where(models.Loan.id == loan_id)
        .options(joinedload(models.Loan.book), joinedload(models.Loan.member))
    )
    loan = db.scalar(stmt)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


def return_book(db: Session, loan_id: UUID, payload: schemas.LoanReturnRequest | None = None) -> models.Loan:
    loan = get_loan_or_404(db, loan_id)
    if loan.returned_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book has already been returned")

    book_stmt = select(models.Book).where(models.Book.id == loan.book_id).with_for_update()
    book = db.scalar(book_stmt)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated book not found")

    loan.returned_at = datetime.now(timezone.utc)
    if payload and payload.notes:
        loan.notes = payload.notes
    book.available_copies += 1
    db.commit()
    db.refresh(loan)
    return loan



def list_loans(db: Session, active_only: bool, member_id: UUID | None, skip: int, limit: int) -> list[models.Loan]:
    stmt = select(models.Loan).options(joinedload(models.Loan.book), joinedload(models.Loan.member))
    if active_only:
        stmt = stmt.where(models.Loan.returned_at.is_(None))
    if member_id:
        stmt = stmt.where(models.Loan.member_id == member_id)
    stmt = stmt.order_by(models.Loan.borrowed_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).unique().all())



def get_member_active_loans(db: Session, member_id: UUID) -> list[models.Loan]:
    get_member_or_404(db, member_id)
    stmt = (
        select(models.Loan)
        .where(models.Loan.member_id == member_id, models.Loan.returned_at.is_(None))
        .options(joinedload(models.Loan.book), joinedload(models.Loan.member))
        .order_by(models.Loan.borrowed_at.desc())
    )
    return list(db.scalars(stmt).unique().all())



def build_loan_response(loan: models.Loan) -> schemas.LoanResponse:
    return schemas.LoanResponse(
        id=loan.id,
        book_id=loan.book_id,
        member_id=loan.member_id,
        borrowed_at=loan.borrowed_at,
        due_at=loan.due_at,
        returned_at=loan.returned_at,
        notes=loan.notes,
        status=compute_status(loan),
        book_title=loan.book.title,
        member_name=loan.member.full_name,
    )



def dashboard_counts(db: Session) -> dict[str, int]:
    total_books = db.scalar(select(func.count()).select_from(models.Book)) or 0
    total_members = db.scalar(select(func.count()).select_from(models.Member)) or 0
    active_loans = db.scalar(select(func.count()).select_from(models.Loan).where(models.Loan.returned_at.is_(None))) or 0
    return {
        "total_books": int(total_books),
        "total_members": int(total_members),
        "active_loans": int(active_loans),
    }
