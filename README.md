# Neighborhood Library Service

This solution uses:
- **Python + FastAPI** for the REST API
- **PostgreSQL** for data store
- **Next.js (App Router)** for a minimal frontend
- **Docker Compose** for one-command local setup

---

## 1) Project Structure

```text
numino-library-app/
├── backend/
│   ├── app/
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── services.py
│   ├── .env
│   ├── Dockerfile
│   ├── requirements.txt
├── database/
│   └── init.sql
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── Dockerfile
│   ├── next.config.ts
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
└── README.md
```

---

## 2) Functional Coverage

### Core requirements covered
- Create and update books
- Create and update members
- Record book borrowing
- Record book return
- List/query borrowed books, including all books currently borrowed by a given member

### Additional improvements
- Tracks total copies and available copies per book
- Supports optional due dates
- Identifies overdue loans in API responses
- Prevents borrowing when no copies are available
- Prevents returning the same loan twice
- Uses row locking during borrow/return to reduce race-condition risk

### Design notes
- A loan is the transactional record that links a member to a book.
- Instead of assuming one physical copy per title, `books.total_copies` and `books.available_copies` support a more realistic library inventory model.
- `returned_at IS NULL` means the loan is currently active.
- Additional indexes are added for common access patterns around titles, members, and active loans.
- Validation is layered. FastAPI/Pydantic validates request shape and field constraints, the service layer validates business rules, and PostgreSQL enforces final data integrity through constraints.

---

## 3) How to Run

Docker Compose. From the project root:

### Build and start all containers in the background

```bash
docker compose up -d --build
```

### Follow logs for all services

```bash
docker compose logs -f
```

### Stop containers

```bash
docker compose down -v
```

---

## 4) Services:
- PostgreSQL: `localhost:5432`
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

> The database schema is initialized automatically from `database/init.sql`.

---

## 5) API Design

Base URL: `http://localhost:8000`

### Health and dashboard
- `GET /health`
- `GET /dashboard`

### Books
- `POST /books`
- `GET /books`
- `GET /books/{book_id}`

### Members
- `POST /members`
- `GET /members`
- `GET /members/{member_id}`

### Loans
- `POST /loans/borrow`
- `POST /loans/{loan_id}/return`
- `GET /loans`
- `GET /members/{member_id}/borrowed-books`

---

## 6) Sample API Calls

### Create a book

```bash
curl -X POST http://localhost:8000/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Pragmatic Programmer",
    "author": "Andrew Hunt",
    "isbn": "9780201616224",
    "published_year": 1999,
    "total_copies": 3,
    "description": "Classic software engineering book."
  }'
```

### Create a member

```bash
curl -X POST http://localhost:8000/members \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Aarav Mehta",
    "email": "aarav@example.com",
    "phone": "+91-9999999999",
    "address": "Bengaluru"
  }'
```

### Borrow a book

```bash
curl -X POST http://localhost:8000/loans/borrow \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "<BOOK_UUID>",
    "member_id": "<MEMBER_UUID>",
    "due_at": "2026-05-01T18:30:00Z"
  }'
```

### Return a book

```bash
curl -X POST http://localhost:8000/loans/<LOAN_UUID>/return \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Returned in good condition"
  }'
```

### GET /health

```bash
curl http://localhost:8000/health
```

### GET /dashboard

```bash
curl http://localhost:8000/dashboard
```

### GET /books

```bash
curl http://localhost:8000/books
```

### GET /books/{book_id}

```bash
curl http://localhost:8000/books/<BOOK_UUID>
```

### GET /members

```bash
curl http://localhost:8000/members
```

### GET /members/{member_id}

```bash
curl http://localhost:8000/members/<MEMBER_UUID>
```

### GET /loans

```bash
curl http://localhost:8000/loans
```

### GET /loans for active loans only

```bash
curl "http://localhost:8000/loans?active_only=true"
```

### GET /loans filtered by member_id

```bash
curl "http://localhost:8000/loans?member_id=<MEMBER_UUID>"
```

### GET /members/{member_id}/borrowed-books

```bash
curl http://localhost:8000/members/<MEMBER_UUID>/borrowed-books
```
---

## 7) Flow Summary

This takes the example of creating/adding a new book using curl.

- curl sends HTTP request. The request goes to uvicorn on port 8000.
- Uvicorn hands it to FastAPI. FastAPI looks at method and path.
- FastAPI parses request body into Pydantic model. The JSON body is converted into schemas.BookCreate.
- FastAPI resolves dependencies(uses get_db() to create a db connection). 
- Control goes to service layer(services.create_book(db, payload)).
- Service layer builds SQLAlchemy model.
- SQLAlchemy persists to PostgreSQL.
- If success, FastAPI serializes the SQLAlchemy object into schemas.BookResponse. That is what gets returned as JSON.
- DB session closes

curl -> uvicorn -> FastAPI route in main.py -> Pydantic validation -> get_db() -> services.create_book() -> SQLAlchemy -> PostgreSQL -> response model -> curl output

---


## 8) Frontend Notes

The frontend is intentionally minimal, but it demonstrates the end-to-end flow required in the assignment:
- create books
- create members
- issue books
- record returns
- view inventory and active loans

It uses the **Next.js App Router** and simple client-side fetching against the REST API.

---

## 9) Error Handling Examples

The API returns meaningful errors for common failure cases:
- `404` when book/member/loan is missing
- `409` when ISBN/email uniqueness is violated
- `409` when a book has no available copies
- `409` when a loan is returned twice
- `400` when an inactive book/member is used or when total copies would become inconsistent

---

## 10) Future Improvements

- Configuration and Secrets Management(e.g: DB Credentials)
- authentication/authorization for  users
- migrations using Alembic(Reference : https://medium.com/@evembijo/beginners-guide-to-alembic-and-sqlalchemy-in-python-manage-your-database-like-a-pro-9395b5b5080d)
- audit logs
- automated tests with pytest
- fine calculation / overdue reminders
- richer search and filtering
