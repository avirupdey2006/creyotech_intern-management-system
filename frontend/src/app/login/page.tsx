"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShieldCheck, Lock, Mail, AlertCircle, Loader2, KeyRound } from "lucide-react";
import { useAuth, getDashboardRouteForRole } from "@/context/AuthContext";
import { extractErrorMessage } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email.trim(), password);
      router.push(getDashboardRouteForRole(user.role));
    } catch (err) {
      setError(extractErrorMessage(err, "Invalid email or password."));
    } finally {
      setSubmitting(false);
    }
  };

  const fillDemoCredentials = (role: "HR" | "ADMIN") => {
    if (role === "HR") {
      setEmail("hr.reviewer@ims.local");
      setPassword("HrReviewer@IMS2026!");
    } else {
      setEmail("admin@ims.local");
      setPassword("Admin@IMS2026!");
    }
    setError(null);
  };

  return (
    <div className="min-h-[calc(100vh-8rem)] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md space-y-6">
        <div className="rounded-xl bg-white border border-slate-200 shadow-xs p-6 sm:p-8 space-y-6">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 text-xs font-mono text-brand-700 bg-brand-50 border border-brand-100 px-2.5 py-1 rounded">
              <ShieldCheck className="h-3.5 w-3.5" />
              RBAC Session Authentication
            </div>
            <h1 className="text-xl font-bold text-slate-900">Sign in to IMS Portal</h1>
            <p className="text-xs text-slate-500">
              Authenticates via short-lived JWTs stored in{" "}
              <span className="font-mono text-slate-700">HttpOnly; SameSite=Strict</span> cookies.
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-2.5 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800">
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="block text-xs font-medium text-slate-700 mb-1.5"
              >
                Email Address
              </label>
              <div className="relative">
                <Mail className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="login-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@organization.com"
                  className="w-full rounded-md border border-slate-300 pl-9 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block text-xs font-medium text-slate-700 mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  id="login-password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full rounded-md border border-slate-300 pl-9 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-md text-xs font-semibold bg-slate-900 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Verifying Credentials...
                </>
              ) : (
                "Sign In to Portal"
              )}
            </button>
          </form>

          {/* Seeded Role Switcher Helper */}
          <div className="pt-4 border-t border-slate-200 space-y-2.5">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500">
              <KeyRound className="h-3 w-3 text-slate-400" />
              <span>Quick-Fill Seeded Reviewer &amp; Admin Accounts:</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => fillDemoCredentials("HR")}
                className="py-1.5 px-2.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-[11px] font-mono text-slate-700 text-left transition-colors"
              >
                <span className="font-semibold block text-slate-900">HR_REVIEWER</span>
                hr.reviewer@ims.local
              </button>
              <button
                type="button"
                onClick={() => fillDemoCredentials("ADMIN")}
                className="py-1.5 px-2.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-[11px] font-mono text-slate-700 text-left transition-colors"
              >
                <span className="font-semibold block text-slate-900">ADMIN</span>
                admin@ims.local
              </button>
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-600">
          Applying as a new intern candidate?{" "}
          <Link href="/register" className="font-semibold text-brand-600 hover:underline">
            Create Candidate Account &rarr;
          </Link>
        </p>
      </div>
    </div>
  );
}