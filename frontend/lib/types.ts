export type Book = {
  id: string;
  isbn: string | null;
  title: string;
  author: string;
  description: string | null;
  published_year: number | null;
  total_copies: number;
  available_copies: number;
  is_active: boolean;
};

export type Member = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  address: string | null;
  is_active: boolean;
};

export type Loan = {
  id: string;
  book_id: string;
  member_id: string;
  borrowed_at: string;
  due_at: string | null;
  returned_at: string | null;
  notes: string | null;
  status: 'BORROWED' | 'RETURNED' | 'OVERDUE';
  book_title: string;
  member_name: string;
};

export type Dashboard = {
  total_books: number;
  total_members: number;
  active_loans: number;
};
