"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  FileText,
  CheckCircle2,
  Clock,
  Building2,
  Phone,
  Calendar,
  Briefcase,
  AlertCircle,
  RefreshCw,
  Lock,
  Sparkles,
  Loader2,
  MapPin,
  BadgeCheck,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { formatDate, STATUS_META } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";
import { KycVerificationModal } from "@/components/KycVerificationModal";
import { DocumentDownloadCard } from "@/components/DocumentDownloadCard";
import { DocumentMetadata, InternProfile } from "@/types";

const TIMELINE_STAGES = [
  { key: "SUBMITTED", title: "1. Profile Submitted", desc: "Application details & encrypted PII" },
  { key: "IDENTITY_VERIFIED", title: "2. KYC Verified", desc: "Government ID OTP hash verified" },
  { key: "PROVISIONAL_APPROVED", title: "3. Provisional Offer", desc: "Approved by HR Reviewer" },
  { key: "FINAL_APPROVED", title: "4. Final Offer", desc: "Confirmed by Administrator" },
  { key: "COMPLETED", title: "5. Completed", desc: "Completion Certificate issued" },
] as const;

export default function CandidateDashboardPage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<InternProfile | null>(null);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [kycModalOpen, setKycModalOpen] = useState(false);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);

  // Profile Submission Form State
  const [fullName, setFullName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("+91");
  const [collegeName, setCollegeName] = useState("");
  const [internshipRole, setInternshipRole] = useState("Full-Stack Software Engineer");
  const [startDate, setStartDate] = useState("2026-11-01");
  const [endDate, setEndDate] = useState("2027-04-30");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("Kolkata");
  const [state, setState] = useState("West Bengal");
  const [pinCode, setPinCode] = useState("700114");
  const [workMode, setWorkMode] = useState("Remote");
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchCandidateData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      const { data: prof } = await apiClient.get<InternProfile>("/candidates/profile/me");
      setProfile(prof);
      const { data: docs } = await apiClient.get<DocumentMetadata[]>("/documents/my");
      setDocuments(docs);
    } catch {
      setProfile(null);
      setDocuments([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void fetchCandidateData();
  }, [fetchCandidateData]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSubmitting(true);
    try {
      const { data } = await apiClient.post<InternProfile>("/candidates/profile", {
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim(),
        college_name: collegeName.trim(),
        internship_role: internshipRole.trim(),
        start_date: startDate,
        end_date: endDate,
        address: address.trim() || "Sector V, Salt Lake",
        city: city.trim() || "Kolkata",
        state: state.trim() || "West Bengal",
        pin_code: pinCode.trim() || "700091",
        work_mode: workMode,
      });
      setProfile(data);
      setBannerMessage(
        "Intern profile submitted and encrypted at rest! Next step: Complete Government ID KYC verification."
      );
    } catch (err) {
      setFormError(extractErrorMessage(err, "Failed to submit intern profile."));
    } finally {
      setFormSubmitting(false);
    }
  };

  const currentStepIndex = profile ? STATUS_META[profile.application_status]?.stepIndex ?? 1 : 0;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="h-24 rounded-xl bg-slate-200/70 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-80 rounded-xl bg-slate-200/70 animate-pulse lg:col-span-2" />
          <div className="h-80 rounded-xl bg-slate-200/70 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              CREYOTECH Candidate Onboarding &amp; Document Portal
            </h1>
            {profile && <StatusBadge status={profile.application_status} />}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Signed in as <span className="font-mono text-slate-700">{user?.email}</span> • Track
            application progress, verify KYC identity, and download CREYOTECH offer letters &amp;
            certificates.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Link
            href="/verify"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-medium bg-slate-100 text-slate-800 hover:bg-slate-200"
          >
            <BadgeCheck className="h-3.5 w-3.5 text-brand-600" />
            Public Certificate Verifier
          </Link>
          {profile && (
            <button
              type="button"
              onClick={() => void fetchCandidateData(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
          )}
        </div>
      </div>

      {bannerMessage && (
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-center justify-between gap-3 text-xs text-emerald-900">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            <span className="font-medium">{bannerMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setBannerMessage(null)}
            className="text-emerald-700 hover:underline font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Workflow Stage Progress Bar */}
      <section className="rounded-xl bg-white border border-slate-200 p-5 shadow-2xs">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            5-Stage Onboarding Progression
          </h2>
          {profile && (
            <span className="text-[11px] font-mono text-slate-500">
              Profile ID: {profile.profile_id}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
          {TIMELINE_STAGES.map((stage, idx) => {
            const stepNum = idx + 1;
            const isCompleted = currentStepIndex > stepNum || currentStepIndex === 5;
            const isCurrent = currentStepIndex === stepNum && currentStepIndex !== 5;
            return (
              <div
                key={stage.key}
                className={`rounded-lg border p-3.5 transition-colors ${
                  isCompleted
                    ? "bg-emerald-50/60 border-emerald-200 text-emerald-950"
                    : isCurrent
                    ? "bg-brand-50/70 border-brand-300 text-slate-900 ring-1 ring-brand-500/20"
                    : "bg-slate-50/60 border-slate-200 text-slate-400"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{stage.title}</span>
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                  ) : isCurrent ? (
                    <Clock className="h-4 w-4 text-brand-600 shrink-0" />
                  ) : null}
                </div>
                <p className="text-[11px] leading-snug opacity-85">{stage.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {!profile ? (
        <section className="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden max-w-3xl">
          <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">
                Step 1: Submit CREYOTECH Internship Application Profile
              </h2>
              <p className="text-xs text-slate-300">
                Your details and mailing address will be formatted onto your official Offer Letters.
              </p>
            </div>
            <Lock className="h-4 w-4 text-sky-400" />
          </div>

          <form onSubmit={handleProfileSubmit} className="p-6 space-y-5">
            {formError && (
              <div className="flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-800">
                <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Full Legal Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Avirup Dey"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Phone Number (Encrypted at Rest)
                </label>
                <input
                  type="tel"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+919876543210"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  College / University Name
                </label>
                <input
                  type="text"
                  required
                  value={collegeName}
                  onChange={(e) => setCollegeName(e.target.value)}
                  placeholder="e.g. Guru Nanak Institute of Technology"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Internship Position / Role
                </label>
                <input
                  type="text"
                  required
                  value={internshipRole}
                  onChange={(e) => setInternshipRole(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Street / Locality Address (For Offer Letter Header)
                </label>
                <input
                  type="text"
                  required
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="e.g. Panihati, Sodepur"
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">City</label>
                <input
                  type="text"
                  required
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">State</label>
                  <input
                    type="text"
                    required
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5">
                    PIN Code
                  </label>
                  <input
                    type="text"
                    required
                    value={pinCode}
                    onChange={(e) => setPinCode(e.target.value)}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono text-slate-900 focus:border-brand-600 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Preferred Start Date
                </label>
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5">
                  Expected End Date
                </label>
                <input
                  type="date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-brand-600 focus:outline-none"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end">
              <button
                type="submit"
                disabled={formSubmitting}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md text-xs font-semibold bg-slate-900 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors"
              >
                {formSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Encrypting &amp; Submitting...
                  </>
                ) : (
                  "Submit Internship Application"
                )}
              </button>
            </div>
          </form>
        </section>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Profile Summary & KYC Action Card */}
          <div className="space-y-6 lg:col-span-1">
            <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Identity Verification (KYC)
                </span>
                <ShieldCheck
                  className={`h-5 w-5 ${
                    profile.application_status === "SUBMITTED"
                      ? "text-amber-500"
                      : "text-emerald-600"
                  }`}
                />
              </div>

              {profile.application_status === "SUBMITTED" ? (
                <>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Your profile is submitted. Please verify your government ID via OTP so HR
                    Reviewers can issue your Provisional Offer Letter.
                  </p>
                  <button
                    type="button"
                    onClick={() => setKycModalOpen(true)}
                    className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-md text-xs font-semibold bg-brand-600 text-white hover:bg-brand-700 transition-colors"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Verify Government ID (OTP)
                  </button>
                </>
              ) : (
                <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3.5 text-xs text-emerald-900 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    <span>KYC Identity Cryptographically Verified</span>
                  </div>
                  <p className="text-emerald-800 text-[11px]">
                    Zero raw digits stored. Reference hash sealed in{" "}
                    <span className="font-mono">verification_logs</span>.
                  </p>
                </div>
              )}
            </div>

            <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-2xs space-y-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Submitted Intern Record
              </h3>

              <dl className="space-y-3 text-xs">
                <div className="flex items-start gap-2.5">
                  <Briefcase className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <dt className="text-slate-500">Full Name &amp; Designation</dt>
                    <dd className="font-semibold text-slate-900 mt-0.5">{profile.full_name}</dd>
                    <dd className="text-slate-600">{profile.internship_role}</dd>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <Building2 className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <dt className="text-slate-500">Academic Institution</dt>
                    <dd className="font-medium text-slate-900 mt-0.5">{profile.college_name}</dd>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <MapPin className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <dt className="text-slate-500">Address &amp; Work Mode</dt>
                    <dd className="font-medium text-slate-900 mt-0.5">
                      {profile.address}, {profile.city}, {profile.state} – {profile.pin_code}
                    </dd>
                    <dd className="text-slate-500">
                      {profile.work_mode || "Remote"} • {profile.work_schedule}
                    </dd>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <Phone className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <dt className="text-slate-500">Decrypted Phone (Fernet PII)</dt>
                    <dd className="font-mono font-medium text-slate-900 mt-0.5">
                      {profile.phone_number}
                    </dd>
                  </div>
                </div>

                <div className="flex items-start gap-2.5">
                  <Calendar className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <div>
                    <dt className="text-slate-500">Internship Tenure</dt>
                    <dd className="font-medium text-slate-900 mt-0.5">
                      {formatDate(profile.start_date)} &rarr; {formatDate(profile.end_date)}
                    </dd>
                  </div>
                </div>
              </dl>
            </div>
          </div>

          {/* Right 2 Columns: Official Encrypted Document Vault */}
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-xl bg-white border border-slate-200 p-5 shadow-2xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">
                    Official CREYOTECH Offer Letters &amp; Completion Certificates
                  </h3>
                  <p className="text-xs text-slate-500">
                    Each document carries a unique 12-character verification code and QR code at
                    the bottom
                  </p>
                </div>
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-xs font-mono">
                  <FileText className="h-3.5 w-3.5" /> {documents.length} Issued
                </span>
              </div>

              {documents.length === 0 ? (
                <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50/50 p-8 text-center space-y-2">
                  <FileText className="h-8 w-8 text-slate-400 mx-auto" />
                  <h4 className="text-xs font-semibold text-slate-800">
                    No Documents Issued Yet
                  </h4>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    {profile.application_status === "SUBMITTED"
                      ? "Complete your KYC Identity Verification first. Once verified, HR Reviewers will issue your CREYOTECH Provisional Offer Letter."
                      : "Your identity is verified! As HR and Administrators approve each stage, your encrypted PDFs will appear here automatically."}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {documents.map((doc) => (
                    <DocumentDownloadCard key={doc.document_id} doc={doc} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <KycVerificationModal
        isOpen={kycModalOpen}
        onClose={() => setKycModalOpen(false)}
        onVerified={(res) => {
          setBannerMessage(
            `KYC Verification ${res.verification.status}! Reference Hash: ${res.verification.transaction_reference.slice(
              0,
              16
            )}...`
          );
          void fetchCandidateData(true);
        }}
      />
    </div>
  );
}