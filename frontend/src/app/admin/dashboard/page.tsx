"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Shield,
  Award,
  FileCheck2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Loader2,
  AlertCircle,
  FolderOpen,
  X,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { StatusBadge } from "@/components/StatusBadge";
import { AuditLogTable } from "@/components/AuditLogTable";
import { DocumentDownloadCard } from "@/components/DocumentDownloadCard";
import { StageDecisionModal } from "@/components/StageDecisionModal";
import {
  AuditLog,
  DocumentMetadata,
  InternProfile,
  StageDecisionResponse,
} from "@/types";

export default function AdminDashboardPage() {
  const [activeTab, setActiveTab] = useState<"WORKFLOW" | "AUDIT">("WORKFLOW");
  const [applications, setApplications] = useState<InternProfile[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(
    null
  );

  // Stage Decision Modal State
  const [decisionProfile, setDecisionProfile] = useState<InternProfile | null>(null);
  const [decisionTarget, setDecisionTarget] = useState<
    | "PROVISIONAL_APPROVED"
    | "FINAL_APPROVED"
    | "COMPLETED"
    | "REJECTED"
    | null
  >(null);

  // Document Vault Inspector Modal State
  const [selectedProfile, setSelectedProfile] = useState<InternProfile | null>(null);
  const [profileDocs, setProfileDocs] = useState<DocumentMetadata[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  const fetchAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const [appsResp, logsResp] = await Promise.all([
        apiClient.get<InternProfile[]>("/admin/applications"),
        apiClient.get<AuditLog[]>("/admin/audit-logs?limit=150"),
      ]);
      setApplications(appsResp.data);
      setAuditLogs(logsResp.data);
    } catch (err) {
      setFeedback({
        type: "error",
        text: extractErrorMessage(err, "Failed to load Administrator console data."),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAdminData();
  }, [fetchAdminData]);

  const openProfileDocuments = async (profile: InternProfile) => {
    setSelectedProfile(profile);
    setDocsLoading(true);
    try {
      const { data } = await apiClient.get<DocumentMetadata[]>(
        `/documents/profile/${profile.profile_id}`
      );
      setProfileDocs(data);
    } catch {
      setProfileDocs([]);
    } finally {
      setDocsLoading(false);
    }
  };

  const stats = {
    total: applications.length,
    provisional: applications.filter((a) => a.application_status === "PROVISIONAL_APPROVED")
      .length,
    finalApproved: applications.filter((a) => a.application_status === "FINAL_APPROVED").length,
    completed: applications.filter((a) => a.application_status === "COMPLETED").length,
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-900 bg-slate-200/80 px-2.5 py-0.5 rounded mb-1.5">
            <Shield className="h-3.5 w-3.5 text-brand-700" />
            CREYOTECH ADMINISTRATOR GOVERNANCE CONSOLE
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
            Executive Approvals, Certificate Issuance &amp; Immutable Audit Logs
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure appointment details, issue Final Offer Letters &amp; Completion Certificates
            with 12-char verification codes, and inspect JSONB audit logs.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
            <button
              type="button"
              onClick={() => setActiveTab("WORKFLOW")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === "WORKFLOW"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Approvals &amp; Documents ({applications.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("AUDIT")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                activeTab === "AUDIT"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Audit Logs ({auditLogs.length})
            </button>
          </div>

          <button
            type="button"
            onClick={() => void fetchAdminData()}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium bg-white border border-slate-300 text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* KPI Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl bg-white border border-slate-200 p-4">
          <span className="text-xs text-slate-500">Total Intern Profiles</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{stats.total}</p>
        </div>
        <div className="rounded-xl bg-amber-50/70 border border-amber-200 p-4">
          <span className="text-xs font-medium text-amber-900">
            Awaiting Final Offer Approval
          </span>
          <p className="text-2xl font-bold text-amber-950 mt-1">{stats.provisional}</p>
        </div>
        <div className="rounded-xl bg-indigo-50/70 border border-indigo-200 p-4">
          <span className="text-xs font-medium text-indigo-900">
            Active Interns (Final Approved)
          </span>
          <p className="text-2xl font-bold text-indigo-950 mt-1">{stats.finalApproved}</p>
        </div>
        <div className="rounded-xl bg-emerald-50/70 border border-emerald-200 p-4">
          <span className="text-xs font-medium text-emerald-900">
            Graduated &amp; Certified
          </span>
          <p className="text-2xl font-bold text-emerald-950 mt-1">{stats.completed}</p>
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

      {activeTab === "AUDIT" ? (
        <AuditLogTable logs={auditLogs} />
      ) : (
        <div className="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                All Candidate Applications &amp; Lifecycle Controls
              </h3>
              <p className="text-xs text-slate-500">
                Click any approval button to configure appointment dates, designation, manager &amp;
                remarks before generating the PDF.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  <th className="py-3 px-4">Candidate &amp; Location</th>
                  <th className="py-3 px-4">Designation &amp; College</th>
                  <th className="py-3 px-4">Tenure &amp; Mode</th>
                  <th className="py-3 px-4">Current Stage</th>
                  <th className="py-3 px-4">Documents</th>
                  <th className="py-3 px-4 text-right">Administrator Stage Controls</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-xs">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-500">
                      <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2 text-slate-400" />
                      Loading applications...
                    </td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-500">
                      No applications submitted yet.
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
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
                      <td className="py-3.5 px-4">
                        <button
                          type="button"
                          onClick={() => void openProfileDocuments(app)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-slate-300 bg-white hover:bg-slate-50 text-xs font-medium text-slate-700"
                        >
                          <FolderOpen className="h-3.5 w-3.5 text-brand-600" />
                          Inspect Vault
                        </button>
                      </td>
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="inline-flex items-center justify-end gap-2">
                          {app.application_status === "IDENTITY_VERIFIED" && (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionProfile(app);
                                setDecisionTarget("PROVISIONAL_APPROVED");
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-amber-600 text-white hover:bg-amber-700"
                            >
                              <FileCheck2 className="h-3.5 w-3.5" />
                              Issue Provisional Offer
                            </button>
                          )}

                          {app.application_status === "PROVISIONAL_APPROVED" && (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionProfile(app);
                                setDecisionTarget("FINAL_APPROVED");
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-700"
                            >
                              <FileCheck2 className="h-3.5 w-3.5" />
                              Approve Final Offer
                            </button>
                          )}

                          {app.application_status === "FINAL_APPROVED" && (
                            <button
                              type="button"
                              onClick={() => {
                                setDecisionProfile(app);
                                setDecisionTarget("COMPLETED");
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700"
                            >
                              <Award className="h-3.5 w-3.5" />
                              Issue Completion Certificate
                            </button>
                          )}

                          {app.application_status !== "COMPLETED" &&
                            app.application_status !== "REJECTED" && (
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
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Stage Decision & Appointment Configuration Modal */}
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
          void fetchAdminData();
        }}
      />

      {/* Candidate Document Vault Inspector Modal */}
      {selectedProfile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-[1px]"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-2xl rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 bg-slate-900 text-white">
              <div>
                <h3 className="text-sm font-semibold">
                  Encrypted Document Vault — {selectedProfile.full_name}
                </h3>
                <p className="text-[11px] text-slate-300 font-mono">
                  Profile UUID: {selectedProfile.profile_id}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedProfile(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 max-h-[75vh] overflow-y-auto space-y-3">
              {docsLoading ? (
                <div className="py-10 text-center text-xs text-slate-500">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                  Inspecting encrypted storage...
                </div>
              ) : profileDocs.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  No documents have been generated for this candidate profile yet.
                </div>
              ) : (
                profileDocs.map((doc) => (
                  <DocumentDownloadCard key={doc.document_id} doc={doc} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}