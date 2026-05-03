from uuid import UUID
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


from . import schemas, services
from .database import get_db

app = FastAPI(
    title="Neighborhood Library Service",
    version="1.0.0",
    description="REST API for managing books, members, and lending operations.",
)

app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"],
allow_credentials=False,
allow_methods=["*"],
allow_headers=["*"],
)

@app.get("/health", response_model=schemas.HealthResponse)
def health_check() -> schemas.HealthResponse:
    return schemas.HealthResponse(status="ok")


@app.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)) -> dict[str, int]:
    return services.dashboard_counts(db)


@app.post("/books", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(payload: schemas.BookCreate, db: Session = Depends(get_db)) -> schemas.BookResponse:
    try:
        return services.create_book(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise unique_violation("Book could not be created. ISBN might already exist.") from exc


@app.get("/books", response_model=list[schemas.BookResponse])
def list_books(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[schemas.BookResponse]:
    return services.list_books(db, skip, limit)


@app.get("/books/{book_id}", response_model=schemas.BookResponse)
def get_book(book_id: UUID, db: Session = Depends(get_db)) -> schemas.BookResponse:
    return services.get_book_or_404(db, book_id)


@app.put("/books/{book_id}", response_model=schemas.BookResponse)
def update_book(book_id: UUID, payload: schemas.BookUpdate, db: Session = Depends(get_db)) -> schemas.BookResponse:
    try:
        return services.update_book(db, book_id, payload)
    except IntegrityError as exc:
        db.rollback()
        raise unique_violation("Book could not be updated. ISBN might already exist.") from exc


@app.post("/members", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(payload: schemas.MemberCreate, db: Session = Depends(get_db)) -> schemas.MemberResponse:
    try:
        return services.create_member(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise unique_violation("Member could not be created. Email might already exist.") from exc


@app.get("/members", response_model=list[schemas.MemberResponse])
def list_members(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[schemas.MemberResponse]:
    return services.list_members(db, skip, limit)


@app.get("/members/{member_id}", response_model=schemas.MemberResponse)
def get_member(member_id: UUID, db: Session = Depends(get_db)) -> schemas.MemberResponse:
    return services.get_member_or_404(db, member_id)


@app.put("/members/{member_id}", response_model=schemas.MemberResponse)
def update_member(
    member_id: UUID, payload: schemas.MemberUpdate, db: Session = Depends(get_db)
) -> schemas.MemberResponse:
    try:
        return services.update_member(db, member_id, payload)
    except IntegrityError as exc:
        db.rollback()
        raise unique_violation("Member could not be updated. Email might already exist.") from exc


@app.post("/loans/borrow", response_model=schemas.LoanResponse, status_code=status.HTTP_201_CREATED)
def borrow_book(payload: schemas.LoanBorrowRequest, db: Session = Depends(get_db)) -> schemas.LoanResponse:
    loan = services.borrow_book(db, payload)
    hydrated_loan = services.get_loan_or_404(db, loan.id)
    return services.build_loan_response(hydrated_loan)


@app.post("/loans/{loan_id}/return", response_model=schemas.LoanResponse)
def return_book(
    loan_id: UUID, payload: schemas.LoanReturnRequest, db: Session = Depends(get_db)
) -> schemas.LoanResponse:
    loan = services.return_book(db, loan_id, payload)
    return services.build_loan_response(loan)


@app.get("/loans", response_model=list[schemas.LoanResponse])
def list_loans(
    active_only: bool = Query(default=False),
    member_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[schemas.LoanResponse]:
    loans = services.list_loans(db, active_only, member_id, skip, limit)
    return [services.build_loan_response(loan) for loan in loans]


@app.get("/members/{member_id}/borrowed-books", response_model=list[schemas.LoanResponse])
def list_member_borrowed_books(member_id: UUID, db: Session = Depends(get_db)) -> list[schemas.LoanResponse]:
    loans = services.get_member_active_loans(db, member_id)
    return [services.build_loan_response(loan) for loan in loans]


def unique_violation(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)
