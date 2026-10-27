import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Navbar } from "@/components/Navbar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "IMS Enterprise | Intern Onboarding, KYC & Document Governance",
  description:
    "Production Intern Management System with Third-Party KYC Verification, Kafka Event Streaming, Encrypted PDF Automation, and Neon PostgreSQL.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen flex flex-col bg-canvas text-slate-900">
        <AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-200 bg-white py-4 px-4 sm:px-6 lg:px-8 text-xs text-slate-500">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <span>
                Intern Management System • Next.js + FastAPI + Kafka + Neon PostgreSQL
              </span>
              <span className="font-mono text-[11px] text-slate-400">
                OWASP CSP/HSTS • Fernet AES-128-CBC • SHA-256 Verified
              </span>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}