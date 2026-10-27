import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { ApplicationStatus, DocumentType } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

export const STATUS_META: Record<
  ApplicationStatus,
  { label: string; badgeClass: string; dotClass: string; stepIndex: number }
> = {
  SUBMITTED: {
    label: "Submitted",
    badgeClass: "bg-slate-100 text-slate-800 border-slate-300",
    dotClass: "bg-slate-500",
    stepIndex: 1,
  },
  IDENTITY_VERIFIED: {
    label: "KYC Verified",
    badgeClass: "bg-sky-50 text-sky-800 border-sky-200",
    dotClass: "bg-sky-600",
    stepIndex: 2,
  },
  PROVISIONAL_APPROVED: {
    label: "Provisional Approved",
    badgeClass: "bg-amber-50 text-amber-900 border-amber-200",
    dotClass: "bg-amber-600",
    stepIndex: 3,
  },
  FINAL_APPROVED: {
    label: "Final Approved",
    badgeClass: "bg-indigo-50 text-indigo-800 border-indigo-200",
    dotClass: "bg-indigo-600",
    stepIndex: 4,
  },
  COMPLETED: {
    label: "Completed",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
    dotClass: "bg-emerald-600",
    stepIndex: 5,
  },
  REJECTED: {
    label: "Rejected",
    badgeClass: "bg-rose-50 text-rose-800 border-rose-200",
    dotClass: "bg-rose-600",
    stepIndex: -1,
  },
};

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, { title: string; subtitle: string }> = {
  PROVISIONAL_OFFER: {
    title: "Provisional Offer Letter",
    subtitle: "Issued upon HR Reviewer approval & KYC verification",
  },
  FINAL_OFFER: {
    title: "Final Offer Letter",
    subtitle: "Issued upon Administrator onboarding clearance",
  },
  COMPLETION_CERTIFICATE: {
    title: "Internship Completion Certificate",
    subtitle: "Official credential upon tenure completion",
  },
};