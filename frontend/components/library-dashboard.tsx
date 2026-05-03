'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';

import { apiRequest } from '@/lib/api';
import type { Book, Dashboard, Loan, Member } from '@/lib/types';

const currentYear = new Date().getFullYear();

const initialBookForm = {
  title: '',
  author: '',
  isbn: '',
  total_copies: 1,
  published_year: '',
  description: '',
};

const initialMemberForm = {
  full_name: '',
  email: '',
  phone: '',
  address: '',
};

function normalizeOptionalString(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function requireNonBlank(value: string, fieldName: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    throw new Error(`${fieldName} is required.`);
  }
  return trimmed;
}

function validateBookForm(form: typeof initialBookForm) {
  const title = requireNonBlank(form.title, 'Title');
  const author = requireNonBlank(form.author, 'Author');
  const totalCopies = Number(form.total_copies);

  if (!Number.isInteger(totalCopies) || totalCopies < 1) {
    throw new Error('Total copies must be at least 1.');
  }

  let publishedYear: number | null = null;
  if (String(form.published_year).trim()) {
    publishedYear = Number(form.published_year);
    if (!Number.isInteger(publishedYear) || publishedYear < 0) {
      throw new Error('Published year must be a valid positive year.');
    }
    if (publishedYear > currentYear) {
      throw new Error(`Published year cannot be greater than ${currentYear}.`);
    }
  }

  return {
    title,
    author,
    isbn: normalizeOptionalString(form.isbn),
    total_copies: totalCopies,
    published_year: publishedYear,
    description: normalizeOptionalString(form.description),
    is_active: true,
  };
}

function validateMemberForm(form: typeof initialMemberForm) {
  const fullName = requireNonBlank(form.full_name, 'Full name');
  const email = requireNonBlank(form.email, 'Email');

  return {
    full_name: fullName,
    email,
    phone: normalizeOptionalString(form.phone),
    address: normalizeOptionalString(form.address),
    is_active: true,
  };
}

function buildBorrowPayload(bookId: string, memberId: string, dueAt: string) {
  if (!bookId) {
    throw new Error('Please select a book.');
  }
  if (!memberId) {
    throw new Error('Please select a member.');
  }

  let isoDueAt: string | null = null;
  if (dueAt) {
    const dueDate = new Date(dueAt);
    if (Number.isNaN(dueDate.getTime())) {
      throw new Error('Due date must be a valid date and time.');
    }
    if (dueDate.getTime() < Date.now()) {
      throw new Error('Due date must be in the future.');
    }
    isoDueAt = dueDate.toISOString();
  }

  return {
    book_id: bookId,
    member_id: memberId,
    due_at: isoDueAt,
  };
}

export default function LibraryDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [bookForm, setBookForm] = useState(initialBookForm);
  const [memberForm, setMemberForm] = useState(initialMemberForm);
  const [borrowBookId, setBorrowBookId] = useState('');
  const [borrowMemberId, setBorrowMemberId] = useState('');
  const [dueAt, setDueAt] = useState('');
  const [feedback, setFeedback] = useState<string>('');
  const [pageError, setPageError] = useState<string>('');
  const [bookError, setBookError] = useState<string>('');
  const [memberError, setMemberError] = useState<string>('');
  const [borrowError, setBorrowError] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSubmittingBook, setIsSubmittingBook] = useState(false);
  const [isSubmittingMember, setIsSubmittingMember] = useState(false);
  const [isSubmittingBorrow, setIsSubmittingBorrow] = useState(false);
  const [returningLoanId, setReturningLoanId] = useState<string | null>(null);

  async function loadData(showRefreshingState = false) {
    if (showRefreshingState) {
      setIsRefreshing(true);
    } else {
      setLoading(true);
    }
    setPageError('');

    try {
      const [dashboardData, booksData, membersData, loansData] = await Promise.all([
        apiRequest<Dashboard>('/dashboard'),
        apiRequest<Book[]>('/books?limit=100'),
        apiRequest<Member[]>('/members?limit=100'),
        apiRequest<Loan[]>('/loans?active_only=true&limit=100'),
      ]);

      setDashboard(dashboardData);
      setBooks(booksData);
      setMembers(membersData);
      setLoans(loansData);

      if (booksData.length === 0) {
        setBorrowBookId('');
      } else if (!booksData.some((book) => book.id === borrowBookId)) {
        setBorrowBookId(booksData[0].id);
      }

      if (membersData.length === 0) {
        setBorrowMemberId('');
      } else if (!membersData.some((member) => member.id === borrowMemberId)) {
        setBorrowMemberId(membersData[0].id);
      }
    } catch (err) {
      setPageError(err instanceof Error ? err.message : 'Unable to load data.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const availableBooks = useMemo(() => books.filter((book) => book.available_copies > 0 && book.is_active), [books]);
  const activeMembers = useMemo(() => members.filter((member) => member.is_active), [members]);

  async function handleCreateBook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback('');
    setBookError('');
    setPageError('');
    setIsSubmittingBook(true);

    try {
      const payload = validateBookForm(bookForm);
      await apiRequest<Book>('/books', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setBookForm(initialBookForm);
      setFeedback('Book added successfully.');
      await loadData();
    } catch (err) {
      setBookError(err instanceof Error ? err.message : 'Unable to create book.');
    } finally {
      setIsSubmittingBook(false);
    }
  }

  async function handleCreateMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback('');
    setMemberError('');
    setPageError('');
    setIsSubmittingMember(true);

    try {
      const payload = validateMemberForm(memberForm);
      await apiRequest<Member>('/members', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setMemberForm(initialMemberForm);
      setFeedback('Member added successfully.');
      await loadData();
    } catch (err) {
      setMemberError(err instanceof Error ? err.message : 'Unable to create member.');
    } finally {
      setIsSubmittingMember(false);
    }
  }

  async function handleBorrow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback('');
    setBorrowError('');
    setPageError('');
    setIsSubmittingBorrow(true);

    try {
      const payload = buildBorrowPayload(borrowBookId, borrowMemberId, dueAt);
      await apiRequest<Loan>('/loans/borrow', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setFeedback('Borrowing recorded successfully.');
      setDueAt('');
      await loadData();
    } catch (err) {
      setBorrowError(err instanceof Error ? err.message : 'Unable to record borrowing.');
    } finally {
      setIsSubmittingBorrow(false);
    }
  }

  async function handleReturn(loanId: string) {
    setFeedback('');
    setBorrowError('');
    setPageError('');
    setReturningLoanId(loanId);

    try {
      await apiRequest<Loan>(`/loans/${loanId}/return`, {
        method: 'POST',
        body: JSON.stringify({ notes: 'Returned from frontend action' }),
      });
      setFeedback('Return recorded successfully.');
      await loadData();
    } catch (err) {
      setBorrowError(err instanceof Error ? err.message : 'Unable to record return.');
    } finally {
      setReturningLoanId(null);
    }
  }

  return (
    <main>
      <div className="card" style={{ marginBottom: 16 }}>
        <h1>Neighborhood Library Service</h1>
        <p>
          Minimal operational dashboard for staff to create books and members, issue books, and record returns.
        </p>
        <div className="inline-actions">
          <button
            className="ghost"
            onClick={() => void loadData(true)}
            type="button"
            disabled={loading || isRefreshing}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh data'}
          </button>
        </div>
        {pageError ? <div className="error-banner" style={{ marginTop: 12 }}>{pageError}</div> : null}
        {feedback ? <div className="success-banner" style={{ marginTop: 12 }}>{feedback}</div> : null}
      </div>

      <div className="grid grid-3">
        <div className="card">
          <div className="small">Books</div>
          <div className="metrics">{dashboard?.total_books ?? 0}</div>
        </div>
        <div className="card">
          <div className="small">Members</div>
          <div className="metrics">{dashboard?.total_members ?? 0}</div>
        </div>
        <div className="card">
          <div className="small">Active loans</div>
          <div className="metrics">{dashboard?.active_loans ?? 0}</div>
        </div>
      </div>

      <div className="section-grid">
        <div className="card">
          <h2>Create a Book</h2>
          <form className="grid" onSubmit={handleCreateBook}>
            <div className="row">
              <input
                value={bookForm.title}
                onChange={(e) => setBookForm((prev) => ({ ...prev, title: e.target.value }))}
                placeholder="Title"
                required
                disabled={isSubmittingBook}
              />
              <input
                value={bookForm.author}
                onChange={(e) => setBookForm((prev) => ({ ...prev, author: e.target.value }))}
                placeholder="Author"
                required
                disabled={isSubmittingBook}
              />
            </div>
            <div className="row">
              <input
                value={bookForm.isbn}
                onChange={(e) => setBookForm((prev) => ({ ...prev, isbn: e.target.value }))}
                placeholder="ISBN"
                disabled={isSubmittingBook}
              />
              <input
                type="number"
                min="1"
                value={bookForm.total_copies}
                onChange={(e) => setBookForm((prev) => ({ ...prev, total_copies: Number(e.target.value) }))}
                placeholder="Total copies"
                required
                disabled={isSubmittingBook}
              />
            </div>
            <input
              type="number"
              max={currentYear}
              value={bookForm.published_year}
              onChange={(e) => setBookForm((prev) => ({ ...prev, published_year: e.target.value }))}
              placeholder="Published year"
              disabled={isSubmittingBook}
            />
            <textarea
              value={bookForm.description}
              onChange={(e) => setBookForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Description"
              disabled={isSubmittingBook}
            />
            {bookError ? <div className="error">{bookError}</div> : null}
            <button type="submit" disabled={isSubmittingBook}>
              {isSubmittingBook ? 'Saving book...' : 'Save book'}
            </button>
          </form>
        </div>

        <div className="card">
          <h2>Create a Member</h2>
          <form className="grid" onSubmit={handleCreateMember}>
            <input
              value={memberForm.full_name}
              onChange={(e) => setMemberForm((prev) => ({ ...prev, full_name: e.target.value }))}
              placeholder="Full name"
              required
              disabled={isSubmittingMember}
            />
            <input
              type="email"
              value={memberForm.email}
              onChange={(e) => setMemberForm((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="Email"
              required
              disabled={isSubmittingMember}
            />
            <div className="row">
              <input
                value={memberForm.phone}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, phone: e.target.value }))}
                placeholder="Phone"
                disabled={isSubmittingMember}
              />
              <input
                value={memberForm.address}
                onChange={(e) => setMemberForm((prev) => ({ ...prev, address: e.target.value }))}
                placeholder="Address"
                disabled={isSubmittingMember}
              />
            </div>
            {memberError ? <div className="error">{memberError}</div> : null}
            <button type="submit" disabled={isSubmittingMember}>
              {isSubmittingMember ? 'Saving member...' : 'Save member'}
            </button>
          </form>
        </div>
      </div>

      <div className="section-grid">
        <div className="card">
          <h2>Issue a Book</h2>
          <form className="grid" onSubmit={handleBorrow}>
            <select value={borrowBookId} onChange={(e) => setBorrowBookId(e.target.value)} required disabled={isSubmittingBorrow}>
              <option value="">Select a book</option>
              {availableBooks.map((book) => (
                <option key={book.id} value={book.id}>
                  {book.title} — {book.author} ({book.available_copies} available)
                </option>
              ))}
            </select>
            <select value={borrowMemberId} onChange={(e) => setBorrowMemberId(e.target.value)} required disabled={isSubmittingBorrow}>
              <option value="">Select a member</option>
              {activeMembers.map((member) => (
                <option key={member.id} value={member.id}>
                  {member.full_name}
                </option>
              ))}
            </select>
            <input type="datetime-local" value={dueAt} onChange={(e) => setDueAt(e.target.value)} disabled={isSubmittingBorrow} />
            {borrowError ? <div className="error">{borrowError}</div> : null}
            <button type="submit" disabled={isSubmittingBorrow || availableBooks.length === 0 || activeMembers.length === 0}>
              {isSubmittingBorrow ? 'Recording borrowing...' : 'Record borrowing'}
            </button>
          </form>
        </div>

        <div className="card">
          <h2>Active Loans</h2>
          {loading ? <p>Loading...</p> : null}
          <div className="list">
            {!loading && loans.length === 0 ? <p>No active loans yet.</p> : null}
            {loans.map((loan) => (
              <div key={loan.id} className="card" style={{ padding: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
                  <div>
                    <strong>{loan.book_title}</strong>
                    <div className="small">Borrowed by {loan.member_name}</div>
                    <div className="small">Borrowed at {new Date(loan.borrowed_at).toLocaleString()}</div>
                    {loan.due_at ? <div className="small">Due at {new Date(loan.due_at).toLocaleString()}</div> : null}
                  </div>
                  <div style={{ minWidth: 128 }}>
                    <div className={`tag ${loan.status === 'OVERDUE' ? 'warning' : 'success'}`}>{loan.status}</div>
                    <div style={{ marginTop: 10 }}>
                      <button
                        className="secondary"
                        onClick={() => void handleReturn(loan.id)}
                        type="button"
                        disabled={returningLoanId === loan.id}
                      >
                        {returningLoanId === loan.id ? 'Recording...' : 'Record return'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
