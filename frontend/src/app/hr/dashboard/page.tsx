"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  UserCheck,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Filter,
  Loader2,
  AlertCircle,
  FileCheck2,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";
import { StageDecisionModal } from "@/components/StageDecisionModal";
import { ApplicationStatus, InternProfile, StageDecisionResponse } from "@/types";

const STATUS_FILTERS: Array<{ label: string; value: ApplicationStatus | "ALL" }> = [
  { label: "All Applications", value: "ALL" },
  { label: "KYC Verified (Ready for HR)", value: "IDENTITY_VERIFIED" },
  { label: "Submitted (Pending KYC)", value: "SUBMITTED" },
  { label: "Provisional Approved", value: "PROVISIONAL_APPROVED" },
  { label: "Final Approved", value: "FINAL_APPROVED" },
  { label: "Completed", value: "COMPLETED" },
  { label: "Rejected", value: "REJECTED" },
];

export default function HrReviewerDashboardPage() {
  const [applications, setApplications] = useState<InternProfile[]>([]);
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null
  );

  // Modal State
  const [decisionProfile, setDecisionProfile] = useState<InternProfile | null>(null);
  const [decisionTarget, setDecisionTarget] = useState<
    "PROVISIONAL_APPROVED" | "REJECTED" | null
  >(null);

  const fetchApplications = useCallback(async () => {
    setLoading(true);
    try {
      const params = statusFilter !== "ALL" ? { application_status: statusFilter } : {};
      const { data } = await apiClient.get<InternProfile[]>("/admin/applications", { params });
      setApplications(data);
    } catch (err) {
      setFeedback({
        type: "error",
        text: extractErrorMessage(err, "Failed to load candidate applications."),
      });
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void fetchApplications();
  }, [fetchApplications]);

  const filteredApps = applications.filter((app) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      app.full_name.toLowerCase().includes(q) ||
      app.college_name.toLowerCase().includes(q) ||
      app.internship_role.toLowerCase().includes(q)
    );
  });

  const countReadyForHr = applications.filter(
    (a) => a.application_status === "IDENTITY_VERIFIED"
  ).length;
  const countProvisional = applications.filter(
    (a) => a.application_status === "PROVISIONAL_APPROVED"
  ).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-mono text-brand-700 bg-brand-50 border border-brand-100 px-2.5 py-0.5 rounded mb-1.5">
            <UserCheck className="h-3.5 w-3.5" />
            CREYOTECH HR_REVIEWER WORKSPACE
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Candidate Verification &amp; Provisional Offer Queue
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure candidate evaluation period dates, work mode, schedule &amp; HR remarks to
            issue CREYOTECH Provisional Offer Letters.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void fetchApplications()}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 self-start sm:self-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh Queue
        </button>
      </div>

      {/* KPI Summary Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl bg-white border border-slate-200 p-4">
          <span className="text-xs text-slate-500">Total Visible Applications</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{applications.length}</p>
        </div>
        <div className="rounded-xl bg-sky-50/70 border border-sky-200 p-4">
          <span className="text-xs font-medium text-sky-900">
            KYC Verified • Ready for HR Approval
          </span>
          <p className="text-2xl font-bold text-sky-950 mt-1">{countReadyForHr}</p>
        </div>
        <div className="rounded-xl bg-amber-50/70 border border-amber-200 p-4">
          <span className="text-xs font-medium text-amber-900">
            Provisional Offer Issued (Awaiting Admin Final)
          </span>
          <p className="text-2xl font-bold text-amber-950 mt-1">{countProvisional}</p>
        </div>
      </div>

      {feedback && (
        <div
          className={`rounded-lg border p-4 flex items-center justify-between gap-3 text-xs ${
            feedback.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            )}
            <span className="font-medium">{feedback.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="underline font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
            <Filter className="h-3.5 w-3.5 text-slate-400 shrink-0" />
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setStatusFilter(f.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  statusFilter === f.value
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-64">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search candidate, college..."
              className="w-full rounded-md border border-slate-300 pl-8 pr-3 py-1.5 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-4">Candidate &amp; City</th>
                <th className="py-3 px-4">Designation &amp; Institution</th>
                <th className="py-3 px-4">Tenure &amp; Mode</th>
                <th className="py-3 px-4">Current Status</th>
                <th className="py-3 px-4 text-right">HR Reviewer Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-xs">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-500">
                    <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2 text-slate-400" />
                    Loading candidate profiles...
                  </td>
                </tr>
              ) : filteredApps.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-10 text-center text-slate-500">
                    No candidate applications match the current filter.
                  </td>
                </tr>
              ) : (
                filteredApps.map((app) => {
                  const canApproveProvisional = app.application_status === "IDENTITY_VERIFIED";
                  const canReject =
                    app.application_status !== "COMPLETED" &&
                    app.application_status !== "REJECTED";

                  return (
                    <tr key={app.profile_id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-900">{app.full_name}</div>
                        <div className="font-mono text-[11px] text-slate-500">
                          {app.phone_number} • {app.city || "Kolkata"}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-medium text-slate-900">{app.internship_role}</div>
                        <div className="text-slate-500">{app.college_name}</div>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                        <div>
                          {formatDate(app.start_date)} &rarr; {formatDate(app.end_date)}
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {app.work_mode || "Remote"} • {app.reporting_manager || "CREYOTECH"}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusBadge status={app.application_status} size="sm" />
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="inline-flex items-center justify-end gap-2">
                          {canApproveProvisional ? (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionProfile(app);
                                setDecisionTarget("PROVISIONAL_APPROVED");
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-brand-600 text-white hover:bg-brand-700 transition-colors"
                            >
                              <FileCheck2 className="h-3.5 w-3.5" />
                              Configure &amp; Approve Provisional
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">
                              {app.application_status === "SUBMITTED"
                                ? "Awaiting Candidate KYC"
                                : "HR Stage Completed"}
                            </span>
                          )}

                          {canReject && (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionProfile(app);
                                setDecisionTarget("REJECTED");
                              }}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                              Reject
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <StageDecisionModal
        isOpen={Boolean(decisionProfile && decisionTarget)}
        profile={decisionProfile}
        targetStatus={decisionTarget}
        onClose={() => {
          setDecisionProfile(null);
          setDecisionTarget(null);
        }}
        onSuccess={(res: StageDecisionResponse) => {
          setFeedback({
            type: "success",
            text: res.message,
          });
          void fetchApplications();
        }}
      />
    </div>
  );
}