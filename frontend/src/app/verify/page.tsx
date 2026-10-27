"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  BadgeCheck,
  ShieldAlert,
  Search,
  Building2,
  Calendar,
  Briefcase,
  UserCheck,
  MessageSquareQuote,
  Lock,
  Loader2,
  CheckCircle2,
  Hash,
  Clock,
  GraduationCap,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { DOCUMENT_TYPE_LABELS, formatDate, formatDateTime } from "@/lib/utils";
import { CertificateVerificationResponse } from "@/types";

function CertificateVerifierContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialCode = searchParams.get("code") || "";

  const [codeInput, setCodeInput] = useState(initialCode.toUpperCase());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CertificateVerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const performVerification = useCallback(async (rawCode: string) => {
    const clean = rawCode.replace(/[^A-Z0-9]/gi, "").toUpperCase();
    if (clean.length !== 12) {
      setError("Please enter a valid 12-character alphanumeric verification code.");
      setResult(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.get<CertificateVerificationResponse>(
        `/verify/${clean}`
      );
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(
        extractErrorMessage(
          err,
          "No matching certificate or offer letter found for this verification code."
        )
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialCode && initialCode.replace(/[^A-Z0-9]/gi, "").length === 12) {
      setCodeInput(initialCode.replace(/[^A-Z0-9]/gi, "").toUpperCase());
      void performVerification(initialCode);
    }
  }, [initialCode, performVerification]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = codeInput.replace(/[^A-Z0-9]/gi, "").toUpperCase();
    setCodeInput(clean);
    router.replace(`/verify?code=${clean}`, { scroll: false });
    void performVerification(clean);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-8">
      {/* Top Authority Header Card */}
      <section className="rounded-2xl bg-slate-900 text-white p-6 sm:p-9 shadow-lg border border-slate-800 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-sky-400 bg-sky-950/70 border border-sky-800/70 px-2.5 py-1 rounded">
              <BadgeCheck className="h-3.5 w-3.5" />
              CREYOTECH Official Credential Verification Registry
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white pt-1">
              Verify Internship Certificate &amp; Offer Authenticity
            </h1>
            <p className="text-xs text-slate-400">
              Enter the 12-character alphanumeric code printed at the bottom of any CREYOTECH
              certificate or offer letter.
            </p>
          </div>
        </div>

        {/* 12-Char Verification Search Bar */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <label
            htmlFor="verify-code-input"
            className="block text-xs font-medium text-slate-300"
          >
            12-Character Alphanumeric Verification Code
          </label>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Hash className="h-4 w-4 text-slate-400 absolute left-3.5 top-3.5" />
              <input
                id="verify-code-input"
                type="text"
                maxLength={16}
                required
                value={codeInput}
                onChange={(e) =>
                  setCodeInput(e.target.value.replace(/[^a-zA-Z0-9]/g, "").toUpperCase())
                }
                placeholder="e.g. K9M4P7X2R8W5"
                className="w-full rounded-lg bg-slate-950 border border-slate-700 pl-10 pr-4 py-2.5 text-base font-mono tracking-[0.22em] text-white placeholder:text-slate-600 placeholder:tracking-normal focus:border-sky-400 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading || codeInput.trim().length < 6}
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-lg text-xs font-semibold bg-sky-500 text-slate-950 hover:bg-sky-400 disabled:opacity-50 transition-colors shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Verifying Cryptographic Record...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Verify Credential
                </>
              )}
            </button>
          </div>
          <p className="text-[11px] text-slate-400">
            Code length:{" "}
            <span className="font-mono text-slate-200">{codeInput.length}/12</span> characters •
            Case-insensitive • Instant SHA-256 registry lookup
          </p>
        </form>
      </section>

      {/* Error / Unverified State */}
      {error && (
        <section className="rounded-xl bg-rose-50 border border-rose-200 p-6 flex items-start gap-4 text-rose-950 shadow-2xs">
          <div className="h-10 w-10 rounded-lg bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-700 shrink-0">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h2 className="text-sm font-bold text-rose-900">
              Credential Verification Failed — Record Not Found
            </h2>
            <p className="text-xs text-rose-800 leading-relaxed">{error}</p>
            <p className="text-[11px] text-rose-700 pt-1">
              Please double-check the 12-character code printed at the bottom of the document.
            </p>
          </div>
        </section>
      )}

      {/* Verified Credential Dossier Card */}
      {result && (
        <section className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          {/* Status Banner */}
          <div
            className={`px-6 py-4 border-b flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
              result.validity_status === "VALID"
                ? "bg-emerald-50/90 border-emerald-200"
                : "bg-rose-50/90 border-rose-200"
            }`}
          >
            <div className="flex items-center gap-3">
              {result.validity_status === "VALID" ? (
                <div className="h-10 w-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs shrink-0">
                  <CheckCircle2 className="h-5 w-5" />
                </div>
              ) : (
                <div className="h-10 w-10 rounded-xl bg-rose-600 text-white flex items-center justify-center shadow-xs shrink-0">
                  <ShieldAlert className="h-5 w-5" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                      result.validity_status === "VALID"
                        ? "bg-emerald-100 text-emerald-900 border-emerald-300"
                        : "bg-rose-100 text-rose-900 border-rose-300"
                    }`}
                  >
                    STATUS: {result.validity_status}
                  </span>
                  <span className="text-xs font-mono text-slate-600">
                    Code: <strong>{result.verification_code}</strong>
                  </span>
                </div>
                <h2 className="text-base font-bold text-slate-900 mt-1">
                  {DOCUMENT_TYPE_LABELS[result.document_type]?.title || result.document_type}
                </h2>
              </div>
            </div>

            <div className="text-left sm:text-right text-xs text-slate-600">
              <span className="block text-[10px] font-mono uppercase text-slate-400">
                Issued By Authority
              </span>
              <span className="font-semibold text-slate-900">
                CREYOTECH (CREYOTECH IT Services)
              </span>
            </div>
          </div>

          {/* Verified Candidate & Internship Details Grid */}
          <div className="p-6 sm:p-8 space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4 space-y-1">
                <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                  <UserCheck className="h-3.5 w-3.5 text-brand-600" />
                  Intern Full Legal Name
                </span>
                <p className="text-base font-bold text-slate-900">{result.intern_name}</p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4 space-y-1">
                <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                  <Briefcase className="h-3.5 w-3.5 text-brand-600" />
                  Internship Designation
                </span>
                <p className="text-base font-bold text-slate-900">
                  {result.internship_designation}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4 space-y-1">
                <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5 text-brand-600" />
                  Internship Duration &amp; Tenure
                </span>
                <p className="text-sm font-semibold text-slate-900">{result.duration_display}</p>
                <p className="text-xs text-slate-500">
                  Commenced {formatDate(result.start_date)} &rarr; Completed{" "}
                  {formatDate(result.end_date)}
                </p>
              </div>

              <div className="rounded-xl bg-slate-50 border border-slate-200/80 p-4 space-y-1">
                <span className="text-[11px] font-medium text-slate-500 flex items-center gap-1.5">
                  <GraduationCap className="h-3.5 w-3.5 text-brand-600" />
                  Academic Institution &amp; Work Mode
                </span>
                <p className="text-sm font-semibold text-slate-900">{result.college_name}</p>
                <p className="text-xs text-slate-500">
                  Mode: {result.work_mode || "Remote"} • Supervisor:{" "}
                  {result.reporting_manager || "CREYOTECH Engineering"}
                </p>
              </div>
            </div>

            {/* Optional Comments from Issuing HR / Admin */}
            <div className="rounded-xl bg-amber-50/70 border border-amber-200 p-4 sm:p-5 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-amber-950">
                <MessageSquareQuote className="h-4 w-4 text-amber-600" />
                <span>Issuing HR / Administrator Official Comments</span>
              </div>
              <p className="text-xs sm:text-sm text-slate-800 leading-relaxed">
                {result.issuer_remarks ||
                  "Verified and issued in good standing upon successful satisfaction of all CREYOTECH internship criteria."}
              </p>
            </div>

            {/* Cryptographic Seal Footer */}
            <div className="rounded-xl bg-slate-900 text-slate-200 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <Lock className="h-3.5 w-3.5" />
                  <span>SHA-256 Cryptographic Document Checksum</span>
                </div>
                <p className="font-mono text-[11px] text-slate-400 truncate">
                  {result.checksum_sha256}
                </p>
              </div>
              <div className="text-left sm:text-right shrink-0">
                <span className="text-[10px] font-mono uppercase text-slate-400 block">
                  Timestamp of Issuance
                </span>
                <span className="font-mono text-xs text-white inline-flex items-center gap-1">
                  <Clock className="h-3 w-3 text-sky-400" />
                  {formatDateTime(result.issued_at)}
                </span>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default function VerifyCertificatePage() {
  return (
    <Suspense
      fallback={
        <div className="max-w-4xl mx-auto px-4 py-14 text-center text-xs text-slate-500">
          Loading CREYOTECH Verification Registry...
        </div>
      }
    >
      <CertificateVerifierContent />
    </Suspense>
  );
}