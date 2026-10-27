"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldCheck,
  FileCheck2,
  UserCheck,
  Lock,
  ArrowRight,
  Database,
  Cpu,
  MailCheck,
} from "lucide-react";
import { useAuth, getDashboardRouteForRole } from "@/context/AuthContext";

const WORKFLOW_STEPS = [
  {
    step: "01",
    title: "Submit Application",
    desc: "Candidate submits academic & internship details. Phone PII is encrypted at rest via Fernet before persisting to Neon PostgreSQL.",
    icon: FileCheck2,
  },
  {
    step: "02",
    title: "Zero-Retention KYC",
    desc: "OTP verification via authorized KYC gateway. Raw ID numbers are discarded from volatile memory immediately after HMAC-SHA256 hashing.",
    icon: ShieldCheck,
  },
  {
    step: "03",
    title: "HR & Admin Review",
    desc: "Strict RBAC separation: HR Reviewers approve Provisional stage; Administrators authorize Final Offer and Completion credentials.",
    icon: UserCheck,
  },
  {
    step: "04",
    title: "Encrypted PDF Engine",
    desc: "Kafka event workers compile PDF documents, compute SHA-256 checksums, encrypt files on disk, and serve time-bound signed URLs.",
    icon: Lock,
  },
  {
    step: "05",
    title: "Idempotent Dispatch",
    desc: "Automated SMTP/TLS email notifications with PDF attachments, protected by transaction idempotency keys and daily quota guards.",
    icon: MailCheck,
  },
];

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-12">
      {/* Hero Banner */}
      <section className="rounded-2xl bg-white border border-slate-200 p-6 sm:p-10 shadow-2xs">
        <div className="max-w-3xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span>Production Architecture • Next.js + FastAPI + Apache Kafka + Neon</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-900">
            Enterprise Intern Onboarding, KYC Verification &amp; Document Automation
          </h1>

          <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
            A cryptographic, event-driven onboarding platform automating candidate intake,
            third-party government identity verification, multi-stage HR/Admin approvals,
            encrypted PDF issuance, and idempotent notification delivery.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            {user ? (
              <Link
                href={getDashboardRouteForRole(user.role)}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-slate-900 text-white hover:bg-brand-700 transition-colors"
              >
                Open {user.role.replace("_", " ")} Portal
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-slate-900 text-white hover:bg-brand-700 transition-colors"
                >
                  Apply as Internship Candidate
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium bg-white text-slate-800 border border-slate-300 hover:bg-slate-50 transition-colors"
                >
                  HR Reviewer / Admin Sign In
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* 5-Stage End-to-End Architecture Pipeline */}
      <section className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              End-to-End Onboarding &amp; Compliance Workflow
            </h2>
            <p className="text-xs text-slate-500">
              Strict state machine governed by Role-Based Access Control and immutable audit logs
            </p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono text-slate-500">
            <span className="inline-flex items-center gap-1">
              <Database className="h-3.5 w-3.5 text-slate-400" /> Neon PostgreSQL 16
            </span>
            <span className="inline-flex items-center gap-1">
              <Cpu className="h-3.5 w-3.5 text-slate-400" /> Kafka Event Bus
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {WORKFLOW_STEPS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.step}
                className="rounded-xl bg-white border border-slate-200 p-5 flex flex-col justify-between gap-4 hover:border-slate-300 transition-colors"
              >
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-brand-600 bg-brand-50 border border-brand-100 px-2 py-0.5 rounded">
                      STEP {item.step}
                    </span>
                    <Icon className="h-4 w-4 text-slate-500" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-900">{item.title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{item.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}