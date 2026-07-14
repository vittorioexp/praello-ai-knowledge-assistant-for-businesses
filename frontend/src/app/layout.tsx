import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Praello AI Knowledge Assistant for Businesses",
  description: "Praello AI — production-ready enterprise knowledge assistant powered by AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
