import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Neighborhood Library',
  description: 'Minimal frontend for the Neighborhood Library Service.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
