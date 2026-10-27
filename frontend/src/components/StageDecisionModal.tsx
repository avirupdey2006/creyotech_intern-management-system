"use client";

import React, { useEffect, useState } from "react";
import {
  FileCheck2,
  X,
  Calendar,
  Briefcase,
  UserCheck,
  MapPin,
  MessageSquareQuote,
  Loader2,
  AlertCircle,
  XCircle,
} from "lucide-react";
import { apiClient, extractErrorMessage } from "@/lib/api";
import { InternProfile, StageDecisionResponse } from "@/types";

interface StageDecisionModalProps {
  isOpen: boolean;
  profile: InternProfile | null;
  targetStatus:
    | "PROVISIONAL_APPROVED"
    | "FINAL_APPROVED"
    | "COMPLETED"
    | "REJECTED"
    | null;
  onClose: () => void;
  onSuccess: (response: StageDecisionResponse) => void;
}

const STAGE_META = {
  PROVISIONAL_APPROVED: {
    title: "Issue CREYOTECH Provisional Offer Letter",
    subtitle: "Configure evaluation period terms, work mode, schedule & HR remarks",
    buttonText: "Approve & Generate Provisional Offer PDF",
    defaultRemarks:
      "Selected for the provisional evaluation phase at CREYOTECH based on strong technical screening and verified KYC credentials.",
  },
  FINAL_APPROVED: {
    title: "Issue CREYOTECH Final Internship Offer Letter",
    subtitle: "Confirm appointment designation, commencement date, reporting manager & terms",
    buttonText: "Approve & Generate Final Offer PDF",
    defaultRemarks:
      "Successfully completed the evaluation period. Confirmed for official internship appointment at CREYOTECH IT Services.",
  },
  COMPLETED: {
    title: "Issue CREYOTECH Internship Completion Certificate",
    subtitle: "Finalize internship tenure, designation & official evaluation comments for public verification",
    buttonText: "Approve & Issue Completion Certificate PDF",
    defaultRemarks:
      "Demonstrated exceptional technical proficiency, commitment to assigned responsibilities, and professional conduct throughout the internship tenure at CREYOTECH.",
  },
  REJECTED: {
    title: "Reject Application / Revoke Credentials",
    subtitle: "Provide administrative reason for rejection",
    buttonText: "Confirm Application Rejection",
    defaultRemarks: "Application did not meet the required evaluation criteria at this stage.",
  },
};

export function StageDecisionModal({
  isOpen,
  profile,
  targetStatus,
  onClose,
  onSuccess,
}: StageDecisionModalProps) {
  const [internshipRole, setInternshipRole] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [workMode, setWorkMode] = useState("Remote");
  const [workSchedule, setWorkSchedule] = useState("Monday to Friday (10:00 AM - 6:00 PM IST)");
  const [reportingManager, setReportingManager] = useState(
    "Technical Project Manager, CREYOTECH"
  );
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [pinCode, setPinCode] = useState("");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (profile && targetStatus) {
      setInternshipRole(profile.internship_role || "Full-Stack Software Engineer");
      setStartDate(profile.start_date || "2026-11-01");
      setEndDate(profile.end_date || "2027-04-30");
      setWorkMode(profile.work_mode || "Remote");
      setWorkSchedule(
        profile.work_schedule || "Monday to Friday (10:00 AM - 6:00 PM IST)"
      );
      setReportingManager(
        profile.reporting_manager || "Technical Project Manager, CREYOTECH"
      );
      setAddress(profile.address || "Sector V, Salt Lake");
      setCity(profile.city || "Kolkata");
      setState(profile.state || "West Bengal");
      setPinCode(profile.pin_code || "700091");
      setRemarks(STAGE_META[targetStatus].defaultRemarks);
      setError(null);
    }
  }, [profile, targetStatus]);

  if (!isOpen || !profile || !targetStatus) return null;

  const meta = STAGE_META[targetStatus];
  const isRejection = targetStatus === "REJECTED";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await apiClient.post<StageDecisionResponse>(
        `/admin/applications/${profile.profile_id}/decision`,
        {
          target_status: targetStatus,
          remarks: remarks.trim(),
          internship_role: internshipRole.trim(),
          start_date: startDate,
          end_date: endDate,
          work_mode: workMode.trim(),
          work_schedule: workSchedule.trim(),
          reporting_manager: reportingManager.trim(),
          address: address.trim(),
          city: city.trim(),
          state: state.trim(),
          pin_code: pinCode.trim(),
        }
      );
      onSuccess(data);
      onClose();
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to process stage decision."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/65 p-4 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-2xl rounded-xl bg-white border border-slate-200 shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div
          className={`px-6 py-4 flex items-center justify-between text-white ${
            isRejection ? "bg-rose-900" : "bg-slate-900"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {isRejection ? (
              <XCircle className="h-5 w-5 text-rose-300" />
            ) : (
              <FileCheck2 className="h-5 w-5 text-sky-400" />
            )}
            <div>
              <h2 className="text-sm font-semibold">{meta.title}</h2>
              <p className="text-[11px] text-slate-300">{meta.subtitle}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5 text-xs">
          {/* Candidate Banner */}
          <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">
                Applicant Record
              </span>
              <span className="font-semibold text-slate-900 text-sm">{profile.full_name}</span>
              <span className="text-slate-500 ml-2">({profile.college_name})</span>
            </div>
            <span className="font-mono text-[11px] text-slate-600 bg-white px-2.5 py-1 rounded border border-slate-200">
              {profile.phone_number}
            </span>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-3 text-rose-800">
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {!isRejection && (
            <>
              {/* Section 1: Designation, Commencement & Duration */}
              <div className="space-y-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Briefcase className="h-3.5 w-3.5 text-brand-600" />
                  1. Official Designation &amp; Internship Tenure
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-1">
                    <label className="block font-medium text-slate-700 mb-1">
                      Designation / Position
                    </label>
                    <input
                      type="text"
                      required
                      value={internshipRole}
                      onChange={(e) => setInternshipRole(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">
                      Commencement (Start Date)
                    </label>
                    <input
                      type="date"
                      required
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">
                      Completion (End Date)
                    </label>
                    <input
                      type="date"
                      required
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Section 2: Work Mode, Schedule & Reporting Manager */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <UserCheck className="h-3.5 w-3.5 text-brand-600" />
                  2. Work Mode, Schedule &amp; Reporting Authority
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Work Mode</label>
                    <select
                      value={workMode}
                      onChange={(e) => setWorkMode(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 bg-white focus:border-brand-600 focus:outline-none"
                    >
                      <option value="Remote">Remote</option>
                      <option value="Hybrid">Hybrid</option>
                      <option value="On-Site (Office)">On-Site (Office)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">Work Schedule</label>
                    <input
                      type="text"
                      required
                      value={workSchedule}
                      onChange={(e) => setWorkSchedule(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">
                      Reporting Manager
                    </label>
                    <input
                      type="text"
                      required
                      value={reportingManager}
                      onChange={(e) => setReportingManager(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Section 3: Candidate Address Block for Offer Letter Header */}
              <div className="space-y-3 pt-2 border-t border-slate-100">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5 text-brand-600" />
                  3. Recipient Mailing Address (Printed on Offer Letter Header)
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block font-medium text-slate-700 mb-1">Street Address</label>
                    <input
                      type="text"
                      required
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">City</label>
                    <input
                      type="text"
                      required
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700 mb-1">PIN Code</label>
                    <input
                      type="text"
                      required
                      value={pinCode}
                      onChange={(e) => setPinCode(e.target.value)}
                      className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs font-mono text-slate-900 focus:border-brand-600 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Section 4: Issuing HR / Admin Comments (Visible on Public Verification Portal) */}
          <div className="space-y-2 pt-2 border-t border-slate-100">
            <label className="font-semibold text-slate-800 flex items-center gap-1.5">
              <MessageSquareQuote className="h-3.5 w-3.5 text-brand-600" />
              Issuing HR / Administrator Comments (Displayed on Certificate Verification Portal)
            </label>
            <textarea
              rows={3}
              required
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="Enter official evaluation comments or remarks..."
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-xs text-slate-900 focus:border-brand-600 focus:outline-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-md text-xs font-medium text-slate-700 border border-slate-300 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className={`inline-flex items-center gap-1.5 px-5 py-2 rounded-md text-xs font-semibold text-white disabled:opacity-50 transition-colors ${
                isRejection
                  ? "bg-rose-600 hover:bg-rose-700"
                  : "bg-slate-900 hover:bg-brand-700"
              }`}
            >
              {submitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Generating Encrypted PDF...
                </>
              ) : (
                <>
                  <Calendar className="h-3.5 w-3.5" />
                  {meta.buttonText}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}