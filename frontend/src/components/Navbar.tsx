"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldCheck,
  LogOut,
  Menu,
  X,
  FileCheck2,
  Users,
  Lock,
  Activity,
  UserCheck,
  BadgeCheck,
} from "lucide-react";
import { useAuth, getDashboardRouteForRole } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const roleBadgeLabel =
    user?.role === "ADMIN"
      ? "Administrator"
      : user?.role === "HR_REVIEWER"
      ? "HR Reviewer"
      : "Candidate";

  const navItems = [
    ...(user?.role === "CANDIDATE"
      ? [
          {
            href: "/candidate/dashboard",
            label: "Onboarding & Documents",
            icon: FileCheck2,
          },
        ]
      : []),
    ...(user?.role === "HR_REVIEWER" || user?.role === "ADMIN"
      ? [
          {
            href: "/hr/dashboard",
            label: "HR Verification Queue",
            icon: UserCheck,
          },
        ]
      : []),
    ...(user?.role === "ADMIN"
      ? [
          {
            href: "/admin/dashboard",
            label: "Admin & Audit Console",
            icon: Users,
          },
        ]
      : []),
    {
      href: "/verify",
      label: "Verify Certificate",
      icon: BadgeCheck,
    },
  ];

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Identity */}
          <div className="flex items-center gap-6">
            <Link
              href={user ? getDashboardRouteForRole(user.role) : "/"}
              className="flex items-center gap-2.5 group focus:outline-none"
            >
              <div className="h-9 w-9 rounded-lg bg-slate-900 flex items-center justify-center text-white shadow-xs group-hover:bg-brand-700 transition-colors">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900 tracking-tight text-sm sm:text-base">
                    CREYOTECH IMS
                  </span>
                  <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                    v1.2
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 hidden sm:block">
                  CREYOTECH IT Services • Onboarding &amp; Credential Authority
                </p>
              </div>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1 ml-4 pl-6 border-l border-slate-200">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "inline-flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium transition-colors",
                      active
                        ? "bg-slate-900 text-white"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right Security & User Controls */}
          <div className="hidden md:flex items-center gap-4">
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] font-medium">
              <Lock className="h-3 w-3 text-emerald-600" />
              <span>TLS 1.3 • Fernet PII • HttpOnly</span>
            </div>

            {user ? (
              <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
                <div className="text-right">
                  <p className="text-xs font-medium text-slate-900 truncate max-w-[180px]">
                    {user.email}
                  </p>
                  <p className="text-[11px] font-mono text-slate-500">{roleBadgeLabel}</p>
                </div>
                <button
                  type="button"
                  onClick={() => void logout()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 hover:text-rose-700 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Sign out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-3.5 py-1.5 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-colors"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="px-3.5 py-1.5 rounded-md text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 transition-colors"
                >
                  Candidate Apply
                </Link>
              </div>
            )}
          </div>

          {/* Mobile Hamburger Trigger */}
          <div className="flex md:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen((prev) => !prev)}
              aria-label="Toggle navigation menu"
              className="p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:outline-none"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-4 space-y-3">
          {user && (
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div>
                <p className="text-xs font-semibold text-slate-900">{user.email}</p>
                <p className="text-[11px] font-mono text-slate-500">{roleBadgeLabel}</p>
              </div>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-mono border border-emerald-200">
                <Activity className="h-3 w-3" /> Active Session
              </span>
            </div>
          )}
          <div className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2.5 rounded-md text-sm font-medium",
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-700 hover:bg-slate-100"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </div>
          {user ? (
            <button
              type="button"
              onClick={() => {
                setMobileMenuOpen(false);
                void logout();
              }}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          ) : (
            <div className="grid grid-cols-2 gap-2 pt-2">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="text-center py-2 rounded-md text-xs font-medium border border-slate-300 text-slate-700"
              >
                Sign in
              </Link>
              <Link
                href="/register"
                onClick={() => setMobileMenuOpen(false)}
                className="text-center py-2 rounded-md text-xs font-medium bg-slate-900 text-white"
              >
                Candidate Apply
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}