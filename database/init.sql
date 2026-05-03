CREATE TABLE IF NOT EXISTS books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isbn VARCHAR(20) UNIQUE,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    description TEXT,
    published_year INTEGER,
    total_copies INTEGER NOT NULL DEFAULT 1 CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1 CHECK (available_copies >= 0 AND available_copies <= total_copies),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_books_published_year_not_in_future
        CHECK (published_year IS NULL OR published_year <= EXTRACT(YEAR FROM CURRENT_DATE))
);

CREATE TABLE IF NOT EXISTS members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(30),
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    member_id UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    borrowed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_loans_due_at_gte_borrowed_at
        CHECK (due_at IS NULL OR due_at >= borrowed_at)
);

CREATE INDEX IF NOT EXISTS ix_books_title ON books(title);
CREATE INDEX IF NOT EXISTS ix_books_author ON books(author);
CREATE INDEX IF NOT EXISTS ix_members_full_name ON members(full_name);
CREATE INDEX IF NOT EXISTS ix_members_email ON members(email);
CREATE INDEX IF NOT EXISTS ix_loans_member_id_returned_at ON loans(member_id, returned_at);
CREATE INDEX IF NOT EXISTS ix_loans_book_id_returned_at ON loans(book_id, returned_at);

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_books_updated_at ON books;
CREATE TRIGGER trg_books_updated_at BEFORE UPDATE ON books
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_members_updated_at ON members;
CREATE TRIGGER trg_members_updated_at BEFORE UPDATE ON members
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_loans_updated_at ON loans;
CREATE TRIGGER trg_loans_updated_at BEFORE UPDATE ON loans
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
